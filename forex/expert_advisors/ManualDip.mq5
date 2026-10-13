//+------------------------------------------------------------------+
//| ManualDip.mq5 -- index dip reversal (DA2), one chart, 4 index CFDs  |
//| 2026-10-11, the trader: "constroi o EA do dip-reversal".                |
//| Rule (forex/ea_research/PREREG_DIP_ADDON.md, amendment DA2):       |
//|  - decision minute 15:49 New York (SP+, NSDQ+, DOW+) and 17:19    |
//|    Berlin (DAX+); dec = BID close of that M1 bar, one per day.    |
//|  - sigma60 = std of the last 60 daily returns of dec (min 40);    |
//|    z3 = ln(dec_t / dec_t-3) / (sigma60 x sqrt 3).                 |
//|  - BUY at the next minute when z3 <= -InpZ, Monday-Thursday only; |
//|    stop at entry x (1 - InpKStop x sigma60) (server-side SL);     |
//|    exit at the next trading day's decision minute (market close). |
//|  - Size: one "idea" per day = InpRiskUSD at the stops, shared by  |
//|    every index that signals that day (DAX decides first and books |
//|    1 / (1 + US indices signalling at that moment) of the budget;  |
//|    the US indices share the rest). Notional cap per index.        |
//|  - Server clock = Europe/Athens (MT5): conversions handle US / EU  |
//|    daylight saving separately (the weeks when they differ too).   |
//| NEVER trades another symbol, never touches other EAs' positions;  |
//| the account guard on the ManualSDB chart can still close its        |
//| positions (day stop, news flat), which is intended.               |
//+------------------------------------------------------------------+
#property copyright "the trader / Round DA2"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>

input string InpUSSymbols   = "SP+,NSDQ+,DOW+";   // US index CFDs (decide 15:49 New York)
input string InpDAXSymbol   = "DAX+";             // DAX CFD (decides 17:19 Berlin); empty = off
input double InpZ           = 1.5;                // dip threshold (z3 <= -Z)
input double InpKStop       = 3.0;                // stop distance in daily sigmas
input double InpRiskUSD     = 500.0;              // risk of the whole day's idea at the stops (0.5% of 100K)
input double InpCapUSD      = 150000.0;           // notional cap per index, USD
input long   InpMagic       = 261011;             // magic number
input int    InpLookbackDays= 130;                // calendar days of M1 history read for sigma60 (needs about 64 trading days)
input bool   InpVerbose     = true;               // print every decision

CTrade g_trade;
string g_us[];
datetime g_lastDec[8];     // last server time a decision was taken, per symbol slot
datetime g_dayBooked=0;    // server date (00:00) of the current budget
double   g_riskUsedDAX=0;  // budget the DAX booked today (US share the rest)

//--- calendar helpers ---------------------------------------------------------
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
datetime BerlinToUTC(datetime loc) { datetime g=loc-2*3600; return EUSummerUTC(g)?g:loc-3600; }
datetime UTCtoServer(datetime utc) { return utc+(EUSummerUTC(utc)?3:2)*3600; }
// decision bar OPEN time (server clock) for a calendar day (00:00 of that day, any clock: only y/m/d are used)
datetime DecisionBar(datetime day,bool dax)
  {
   MqlDateTime s; TimeToStruct(day,s);
   datetime loc=dax?MakeTime(s.year,s.mon,s.day,17,19):MakeTime(s.year,s.mon,s.day,15,49);
   return UTCtoServer(dax?BerlinToUTC(loc):NYtoUTC(loc));
  }
// local calendar date (00:00) of a server time, in New York or Berlin
datetime LocalDay(datetime server,bool dax)
  {
   datetime utc=server-(EUSummerUTC(server-3*3600)?3:2)*3600;
   datetime loc;
   if(dax) loc=utc+(EUSummerUTC(utc)?2:1)*3600;
   else
     {
      loc=utc-5*3600; datetime l4=utc-4*3600;
      if(NYtoUTC(l4)==utc) loc=l4;
     }
   return loc-(loc%86400);
  }

//--- daily series ---------------------------------------------------------------
// dec[] oldest first: bid close of the decision bar for every local day that has that exact M1 bar, up to and including 'lastDay'
int DecSeries(const string sym,bool dax,datetime lastDay,double &dec[],datetime &days[])
  {
   ArrayResize(dec,0); ArrayResize(days,0); int n=0;
   for(int k=InpLookbackDays;k>=0;k--)
     {
      datetime d=lastDay-k*86400; int dw=DowOf(d); if(dw==0 || dw==6) continue;
      datetime bt=DecisionBar(d,dax); int sh=iBarShift(sym,PERIOD_M1,bt,true);
      if(sh<0) continue;
      double c=iClose(sym,PERIOD_M1,sh); if(c<=0) continue;
      ArrayResize(dec,n+1); ArrayResize(days,n+1); dec[n]=c; days[n]=d; n++;
     }
   return n;
  }
// z3 and sigma60 at the last element; false if not enough history
bool Signal(const double &dec[],double &z3,double &sd)
  {
   int n=ArraySize(dec); if(n<44) return false;
   int m=MathMin(60,n-1); double r[]; ArrayResize(r,m);
   for(int i=0;i<m;i++) r[i]=dec[n-m+i]/dec[n-m+i-1]-1.0;
   double mu=0; for(int i=0;i<m;i++) mu+=r[i]; mu/=m;
   double v=0; for(int i=0;i<m;i++) v+=(r[i]-mu)*(r[i]-mu); sd=MathSqrt(v/(m-1));
   if(m<40 || sd<=0) return false;
   z3=MathLog(dec[n-1]/dec[n-4])/(sd*MathSqrt(3.0)); return true;
  }

//--- positions ----------------------------------------------------------------
bool HasPos(const string sym)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     { ulong t=PositionGetTicket(i); if(t>0 && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==sym) return true; }
   return false;
  }
// closes only positions opened BEFORE 'before' (a restart inside the decision window must not close today's fresh entry)
void ClosePos(const string sym,const string why,datetime before)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==sym && (datetime)PositionGetInteger(POSITION_TIME)<before)
         if(g_trade.PositionClose(t)) PrintFormat("[ManualDip] EXIT %s (%s) at bid %.2f",sym,why,SymbolInfoDouble(sym,SYMBOL_BID));
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

//--- one decision for one symbol at its decision minute --------------------------------
// returns 1 if a buy was opened, 0 otherwise. 'shareUSD' is the risk this symbol may use.
int Decide(const string sym,bool dax,datetime today,double z3,double sd,double shareUSD)
  {
   int dw=DowOf(today);
   if(dw<1 || dw>4) return 0;                                     // Monday-Thursday entries only
   if(z3>-InpZ) return 0;
   if(HasPos(sym)) return 0;
   double ask=SymbolInfoDouble(sym,SYMBOL_ASK); double lots=LotsFor(sym,shareUSD,sd,ask);
   if(lots<=0) { PrintFormat("[ManualDip] %s signal z3 %.2f but size below the minimum (risk %.0f)",sym,z3,shareUSD); return 0; }
   double sl=NormalizeDouble(ask*(1.0-InpKStop*sd),(int)SymbolInfoInteger(sym,SYMBOL_DIGITS));
   g_trade.SetExpertMagicNumber(InpMagic);
   if(g_trade.Buy(lots,sym,0,sl,0,"ManualDip z3 "+DoubleToString(z3,2)))
     { PrintFormat("[ManualDip] BUY %s %.2f lots at %.2f, SL %.2f, z3 %.2f, sigma %.4f, risk %.0f USD",sym,lots,ask,sl,z3,sd,shareUSD); return 1; }
   PrintFormat("[ManualDip] BUY %s failed: %d",sym,g_trade.ResultRetcode()); return 0;
  }

int OnInit()
  {
   StringSplit(InpUSSymbols,',',g_us);
   for(int i=0;i<ArraySize(g_us);i++) { StringTrimLeft(g_us[i]); StringTrimRight(g_us[i]); SymbolSelect(g_us[i],true); }
   if(InpDAXSymbol!="") SymbolSelect(InpDAXSymbol,true);
   ArrayInitialize(g_lastDec,0);
   g_trade.SetDeviationInPoints(500);
   EventSetTimer(1);
   PrintFormat("[ManualDip] started: US %s, DAX %s, Z %.2f, stop %.1f sigma, day risk %.0f USD",InpUSSymbols,InpDAXSymbol,InpZ,InpKStop,InpRiskUSD);
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { EventKillTimer(); }
void OnTick() { Step(); }
void OnTimer() { Step(); }

// slot 0..n-1 = US symbols, slot 7 = DAX
void Step()
  {
   datetime now=TimeTradeServer(); int nus=ArraySize(g_us);
   // DAX decision (17:19 Berlin = 11:19 New York, before the US decision)
   if(InpDAXSymbol!="") Handle(InpDAXSymbol,true,7,now,nus);
   for(int i=0;i<nus;i++) Handle(g_us[i],false,i,now,nus);
  }

void Handle(const string sym,bool dax,int slot,datetime now,int nus)
  {
   datetime today=LocalDay(now,dax); datetime bar=DecisionBar(today,dax);
   if(now<bar+60 || now>bar+300 || g_lastDec[slot]==bar) return;   // act once, in the first 4 minutes after the decision bar closes
   if(iBarShift(sym,PERIOD_M1,bar,true)<0) return;                   // the decision bar must exist (market open that minute)
   g_lastDec[slot]=bar;
   ClosePos(sym,"next-day exit",bar);                    // exit first: any position of ours is from a previous decision
   datetime srvDay=now-(now%86400);
   if(srvDay!=g_dayBooked) { g_dayBooked=srvDay; g_riskUsedDAX=0; }
   double dec[]; datetime days[]; int n=DecSeries(sym,dax,today,dec,days); double z3,sd;
   if(n<2 || days[n-1]!=today || !Signal(dec,z3,sd)) { if(InpVerbose) PrintFormat("[ManualDip] %s %s: no signal data (%d days)",sym,TimeToString(today,TIME_DATE),n); return; }
   if(InpVerbose) PrintFormat("[ManualDip] %s %s: z3 %.2f sigma60 %.4f",sym,TimeToString(today,TIME_DATE),z3,sd);
   if(z3>-InpZ) return;
   double share;
   if(dax)
     {
      int nusSig=0;                                                   // US indices signalling NOW (their decision comes later today)
      for(int i=0;i<nus;i++)
        {
         double d2[]; datetime dd2[]; int m=DecSeries(g_us[i],false,today-86400,d2,dd2); if(m<44) continue;
         ArrayResize(d2,m+1); d2[m]=SymbolInfoDouble(g_us[i],SYMBOL_BID); double z,s;
         if(Signal(d2,z,s) && z<=-InpZ) nusSig++;
        }
      share=InpRiskUSD/(1.0+nusSig);
      if(Decide(sym,true,today,z3,sd,share)==1) g_riskUsedDAX=share;
     }
   else
     {
      int k=0;                                                        // US indices that signal at this decision (same minute for all three)
      for(int i=0;i<nus;i++)
        {
         double d2[]; datetime dd2[]; int m=DecSeries(g_us[i],false,today,d2,dd2); double z,s;
         if(m>1 && dd2[m-1]==today && Signal(d2,z,s) && z<=-InpZ) k++;
        }
      if(k<1) k=1;
      share=(InpRiskUSD-g_riskUsedDAX)/k;
      Decide(sym,false,today,z3,sd,share);
     }
  }
//+------------------------------------------------------------------+
