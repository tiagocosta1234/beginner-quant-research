//+------------------------------------------------------------------+
//| ManualRSI2.mq5 -- RSI(2) dips on the US index CFDs (SP+, NSDQ+, DOW+)|
//| 2026-10-14, the trader: "cria o EA do RSI(2)". One chart, 3 symbols.     |
//| Rule (forex/ea_research/PREREG_RSI2_LEG.md, fincept_mt5_verify EV1):   |
//|  - daily series = BID OPEN of the 15:59 New York M1 bar of every   |
//|    local day that has that exact bar (server clock = Athens).      |
//|  - at the first minute of 15:59 NY: rsi = Wilder RSI(2) of the     |
//|    series (EWM alpha 1/2), sma200, sma5 of the series incl. today, |
//|    sigma60 = std of the last 60 daily returns (min 40).            |
//|  - BUY (long only) at the ASK when rsi < 10 AND series > sma200    |
//|    and no position on that symbol and not the day a position was   |
//|    closed; stop at entry x (1 - InpKStop x sigma60) (server-side). |
//|  - EXIT at the BID on the first later decision minute when series  |
//|    > sma5 OR rsi > 70 OR 5 trading days have passed.               |
//|  - Size: one "idea" per day = InpRiskUSD at the stops, shared by   |
//|    the indices that open that day; notional cap per index.         |
//| NEVER trades another symbol, never touches other EAs' positions;   |
//| the account guard on the ManualSDB chart can still close its         |
//| positions (day stop, news flat), which is intended.                |
//+------------------------------------------------------------------+
#property copyright "the trader / RSI(2) leg"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>

input string InpSymbols     = "SP+,NSDQ+,DOW+";   // US index CFDs (decide 15:59 New York)
input double InpRsiBuy      = 10.0;               // enter when RSI(2) < this
input double InpRsiSell     = 70.0;               // exit when RSI(2) > this
input int    InpMaxDays     = 5;                  // exit after this many trading days
input double InpKStop       = 3.0;                // stop distance in daily sigmas
input double InpRiskUSD     = 500.0;              // risk of the whole day's idea at the stops
input double InpCapUSD      = 150000.0;           // notional cap per index, USD
input long   InpMagic       = 261012;             // magic number
input int    InpLookbackDays= 340;                // calendar days of M1 history read (sma200 needs about 285)
input bool   InpVerbose     = true;

CTrade g_trade;
string g_sym[];
datetime g_lastDec=0;

//--- calendar helpers (same as ManualDip) ---------------------------------------
datetime MakeTime(int y,int mo,int d,int h,int mi)
  {
   MqlDateTime s; ZeroMemory(s); s.year=y; s.mon=mo; s.day=d; s.hour=h; s.min=mi; s.sec=0; return StructToTime(s);
  }
int DowOf(datetime t) { MqlDateTime s; TimeToStruct(t,s); return s.day_of_week; }
// n-th Sunday (n >= 1) of a month, or the last one (n = -1), at 00:00
datetime NthSunday(int y,int mo,int n)
  {
   if(n>0)
     {
      datetime t=MakeTime(y,mo,1,0,0); int dw=DowOf(t); int first=1+((7-dw)%7);
      return MakeTime(y,mo,first+7*(n-1),0,0);
     }
   int nd=(mo==12)?31:(int)((MakeTime(mo==12?y+1:y,mo==12?1:mo+1,1,0,0)-MakeTime(y,mo,1,0,0))/86400);
   datetime t=MakeTime(y,mo,nd,0,0); int dw=DowOf(t); return t-dw*86400;
  }
// New York local wall time -> UTC (US DST: 2nd Sunday March 02:00 .. 1st Sunday November 02:00 local)
datetime NYtoUTC(datetime loc)
  {
   MqlDateTime s; TimeToStruct(loc,s);
   datetime a=NthSunday(s.year,3,2)+2*3600, b=NthSunday(s.year,11,1)+2*3600;
   int off=(loc>=a && loc<b)?-4:-5; return loc-off*3600;
  }
bool EUSummerUTC(datetime utc)   // EU DST: last Sunday March 01:00 UTC .. last Sunday October 01:00 UTC
  {
   MqlDateTime s; TimeToStruct(utc,s);
   datetime a=NthSunday(s.year,3,-1)+3600, b=NthSunday(s.year,10,-1)+3600; return (utc>=a && utc<b);
  }
datetime UTCtoServer(datetime utc) { return utc+(EUSummerUTC(utc)?3:2)*3600; }
// decision bar open time (server clock) for a calendar day: 15:59 New York
datetime DecisionBar(datetime day)
  {
   MqlDateTime s; TimeToStruct(day,s);
   return UTCtoServer(NYtoUTC(MakeTime(s.year,s.mon,s.day,15,59)));
  }
// New York local calendar date (00:00) of a server time
datetime LocalDay(datetime server)
  {
   datetime utc=server-(EUSummerUTC(server-3*3600)?3:2)*3600;
   datetime loc=utc-5*3600; datetime l4=utc-4*3600;
   if(NYtoUTC(l4)==utc) loc=l4;
   return loc-(loc%86400);
  }

//--- daily series ---------------------------------------------------------------
// v[] oldest first: BID OPEN of the decision bar for every local day that has that exact M1 bar, up to and including lastDay
int Series(const string sym,datetime lastDay,double &v[],datetime &days[])
  {
   ArrayResize(v,0); ArrayResize(days,0); int n=0;
   for(int k=InpLookbackDays;k>=0;k--)
     {
      datetime d=lastDay-k*86400; int dw=DowOf(d); if(dw==0 || dw==6) continue;
      datetime bt=DecisionBar(d); int sh=iBarShift(sym,PERIOD_M1,bt,true);
      if(sh<0) continue;
      double o=iOpen(sym,PERIOD_M1,sh); if(o<=0) continue;
      ArrayResize(v,n+1); ArrayResize(days,n+1); v[n]=o; days[n]=d; n++;
     }
   return n;
  }
// RSI(2) Wilder (EWM alpha 1/2, adjust=false), sma200, sma5, sigma60 at the last element
bool Indicators(const double &v[],double &rsi,double &s200,double &s5,double &sd)
  {
   int n=ArraySize(v); if(n<205) return false;
   double up=0,dn=0; bool first=true;
   for(int i=1;i<n;i++)
     {
      double d=v[i]-v[i-1], u=MathMax(d,0.0), w=MathMax(-d,0.0);
      if(first) { up=u; dn=w; first=false; } else { up=0.5*up+0.5*u; dn=0.5*dn+0.5*w; }
     }
   rsi=(dn<=0.0)?((up>0.0)?100.0:50.0):100.0-100.0/(1.0+up/dn);
   s200=0; for(int i=n-200;i<n;i++) s200+=v[i]; s200/=200.0;
   s5=0; for(int i=n-5;i<n;i++) s5+=v[i]; s5/=5.0;
   int m=MathMin(60,n-1); double mu=0; double r[]; ArrayResize(r,m);
   for(int i=0;i<m;i++) { r[i]=v[n-m+i]/v[n-m+i-1]-1.0; mu+=r[i]; }
   mu/=m; double vv=0; for(int i=0;i<m;i++) vv+=(r[i]-mu)*(r[i]-mu); sd=MathSqrt(vv/(m-1));
   return (m>=40 && sd>0);
  }

//--- positions ----------------------------------------------------------------
bool HasPos(const string sym,datetime &opened)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==sym) { opened=(datetime)PositionGetInteger(POSITION_TIME); return true; }
     }
   return false;
  }
void ClosePos(const string sym,const string why)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==sym)
         if(g_trade.PositionClose(t)) PrintFormat("[ManualRSI2] EXIT %s (%s) at bid %.2f",sym,why,SymbolInfoDouble(sym,SYMBOL_BID));
     }
  }
double LotsFor(const string sym,double riskUSD,double sd,double price)
  {
   double ts=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE), tv=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(ts<=0 || tv<=0 || sd<=0 || price<=0) return 0;
   double perLotPerPrice=tv/ts;                                   // USD per 1.0 price move per lot
   double lots=riskUSD/(InpKStop*sd*price*perLotPerPrice);
   double cap=InpCapUSD/(price*perLotPerPrice); lots=MathMin(lots,cap);
   double step=SymbolInfoDouble(sym,SYMBOL_VOLUME_STEP), vmin=SymbolInfoDouble(sym,SYMBOL_VOLUME_MIN), vmax=SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX);
   lots=MathFloor(lots/step+1e-9)*step; if(lots<vmin) return 0; return MathMin(lots,vmax);
  }

int OnInit()
  {
   StringSplit(InpSymbols,',',g_sym);
   for(int i=0;i<ArraySize(g_sym);i++) { StringTrimLeft(g_sym[i]); StringTrimRight(g_sym[i]); SymbolSelect(g_sym[i],true); }
   g_trade.SetDeviationInPoints(500); g_trade.SetExpertMagicNumber(InpMagic);
   EventSetTimer(1);
   PrintFormat("[ManualRSI2] started: %s, buy RSI(2) < %.0f, sell > %.0f, max %d days, stop %.1f sigma, day risk %.0f USD",InpSymbols,InpRsiBuy,InpRsiSell,InpMaxDays,InpKStop,InpRiskUSD);
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { EventKillTimer(); }
void OnTick() { Step(); }
void OnTimer() { Step(); }

void Step()
  {
   datetime now=TimeTradeServer(); int n=ArraySize(g_sym);
   datetime today=LocalDay(now); datetime bar=DecisionBar(today);
   if(now<bar || now>bar+240) return;                                  // decision window: the first 4 minutes from the 15:59 NY bar open
   if(g_lastDec==bar) return;
   if(iBarShift(g_sym[0],PERIOD_M1,bar,true)<0) return;                // the decision bar must exist
   g_lastDec=bar;
   double rsi[8],s200[8],s5[8],sd[8]; bool sig[8]; double v[]; datetime days[];
   for(int i=0;i<n && i<8;i++)
     {
      sig[i]=false;
      int m=Series(g_sym[i],today,v,days);
      if(m<205 || days[m-1]!=today) { if(InpVerbose) PrintFormat("[ManualRSI2] %s %s: no signal data (%d days)",g_sym[i],TimeToString(today,TIME_DATE),m); continue; }
      if(!Indicators(v,rsi[i],s200[i],s5[i],sd[i])) continue;
      datetime opened=0; bool has=HasPos(g_sym[i],opened);
      if(InpVerbose) PrintFormat("[ManualRSI2] %s %s: series %.2f rsi2 %.1f sma200 %.2f sma5 %.2f sigma60 %.4f%s",g_sym[i],TimeToString(today,TIME_DATE),v[m-1],rsi[i],s200[i],s5[i],sd[i],has?" (in position)":"");
      if(has)
        {
         int ei=-1; datetime od=LocalDay(opened); for(int k=m-1;k>=0;k--) if(days[k]<=od) { ei=k; break; }
         int held=(ei<0)?InpMaxDays:(m-1-ei);
         if(v[m-1]>s5[i] || rsi[i]>InpRsiSell || held>=InpMaxDays) ClosePos(g_sym[i],(v[m-1]>s5[i])?"close above sma5":((rsi[i]>InpRsiSell)?"rsi2 above sell":"max days"));
        }
      else if(rsi[i]<InpRsiBuy && v[m-1]>s200[i]) sig[i]=true;
     }
   int k=0; for(int i=0;i<n && i<8;i++) if(sig[i]) k++;
   if(k<1) return;
   double share=InpRiskUSD/k;
   for(int i=0;i<n && i<8;i++)
     {
      if(!sig[i]) continue;
      double ask=SymbolInfoDouble(g_sym[i],SYMBOL_ASK); double lots=LotsFor(g_sym[i],share,sd[i],ask);
      if(lots<=0) { PrintFormat("[ManualRSI2] %s signal rsi2 %.1f but size below the minimum (risk %.0f)",g_sym[i],rsi[i],share); continue; }
      double sl=NormalizeDouble(ask*(1.0-InpKStop*sd[i]),(int)SymbolInfoInteger(g_sym[i],SYMBOL_DIGITS));
      if(g_trade.Buy(lots,g_sym[i],0,sl,0,"ManualRSI2 rsi "+DoubleToString(rsi[i],1)))
         PrintFormat("[ManualRSI2] BUY %s %.2f lots at %.2f, SL %.2f, rsi2 %.1f, sigma %.4f, risk %.0f USD",g_sym[i],lots,ask,sl,rsi[i],sd[i],share);
      else PrintFormat("[ManualRSI2] BUY %s failed: %d",g_sym[i],g_trade.ResultRetcode());
     }
  }
//+------------------------------------------------------------------+
