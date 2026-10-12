//+------------------------------------------------------------------+
//| ManualONB.mq5 -- overnight-bias opening-range breakout, NSDQ+       |
//| 2026-10-12, the trader: "constroi e testa" (strategy 3 of the video     |
//| "Top 3 strategies", forex/early_mt5/ea_research/PREREG_NQ3.md).              |
//| All times are America/Chicago (CT); the chart/server clock is     |
//| Europe/Athens (MT5), conversions handle EU and US daylight saving. |
//|  - overnight range: 23:00 CT (previous day) .. 08:30 CT.          |
//|  - open at 08:30 CT inside the range: top third -> long bias,     |
//|    bottom third -> short bias, middle -> no trade today.          |
//|  - opening range = M1 high/low of 08:30-08:44 CT.                 |
//|  - from 09:00 to 14:15 CT, on each new M15 bar: the closed M15    |
//|    bar closed beyond the opening range in the bias direction and  |
//|    Wilder ADX(14, M15) > 20 -> market entry (one trade a day).    |
//|  - stop = 0.30 x A15 points, target = 3 x stop (server-side),     |
//|    A15 = mean true range of the 15 sessions before today          |
//|    (session 00:00-16:00 CT). Forced exit at 14:30 CT.             |
//|  - Size: InpRiskUSD at the stop (or InpLots when > 0).            |
//| NEVER trades another symbol; position tagged with InpMagic.       |
//+------------------------------------------------------------------+
#property copyright "the trader / Round NQ3"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>

input double InpRiskUSD     = 300.0;       // risk per trade at the stop, USD (ignored when InpLots > 0)
input double InpLots        = 0.0;         // fixed lots (0 = size from InpRiskUSD)
input double InpStopATR     = 0.30;        // stop distance = this x A15
input double InpRR          = 3.0;         // target = RR x stop
input double InpADXMin      = 20.0;        // ADX gate on the signal bar
input int    InpADXPeriod   = 14;
input double InpDevPoints   = 2.0;         // max slippage on market orders, in INDEX points
input long   InpMagic       = 261021;      // magic number
input bool   InpVerbose     = true;        // print every decision

CTrade g_trade;
int    g_adx=INVALID_HANDLE;
datetime g_ctDay=0;        // CT calendar day of the current state
bool   g_ready=false;      // bias and opening range computed for this day
int    g_side=0;           // +1 long bias, -1 short bias, 0 none
double g_orh=0,g_orl=0,g_dist=0,g_pos=0;
bool   g_traded=false;     // one trade a day
datetime g_lastM15=0;

//--- calendar helpers (same as ManualDip) -------------------------------------------
datetime MakeTime(int y,int mo,int d,int h,int mi)
  {
   MqlDateTime s; ZeroMemory(s); s.year=y; s.mon=mo; s.day=d; s.hour=h; s.min=mi; s.sec=0; return StructToTime(s);
  }
int DowOf(datetime t) { MqlDateTime s; TimeToStruct(t,s); return s.day_of_week; }
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
bool EUSummerUTC(datetime utc)   // EU DST: last Sunday March 01:00 UTC .. last Sunday October 01:00 UTC
  {
   MqlDateTime s; TimeToStruct(utc,s);
   datetime a=NthSunday(s.year,3,-1)+3600, b=NthSunday(s.year,10,-1)+3600; return (utc>=a && utc<b);
  }
datetime UTCtoServer(datetime utc) { return utc+(EUSummerUTC(utc)?3:2)*3600; }
// Chicago local wall time -> UTC (US DST: 2nd Sunday March 02:00 .. 1st Sunday November 02:00 local)
datetime CTtoUTC(datetime loc)
  {
   MqlDateTime s; TimeToStruct(loc,s);
   datetime a=NthSunday(s.year,3,2)+2*3600, b=NthSunday(s.year,11,1)+2*3600;
   int off=(loc>=a && loc<b)?-5:-6; return loc-off*3600;
  }
datetime CTtoServer(datetime ct) { return UTCtoServer(CTtoUTC(ct)); }
datetime ServerToCT(datetime server)
  {
   datetime utc=server-(EUSummerUTC(server-3*3600)?3:2)*3600;
   datetime l5=utc-5*3600; if(CTtoUTC(l5)==utc) return l5;
   return utc-6*3600;
  }

//--- helpers ------------------------------------------------------------------------
bool HiLo(datetime ctFrom,datetime ctTo,double &hi,double &lo,int &n)
  {
   MqlRates r[]; n=CopyRates(_Symbol,PERIOD_M1,CTtoServer(ctFrom),CTtoServer(ctTo),r); if(n<=0) return false;
   hi=r[0].high; lo=r[0].low;
   for(int i=1;i<n;i++) { if(r[i].high>hi) hi=r[i].high; if(r[i].low<lo) lo=r[i].low; }
   return true;
  }
// A15: mean true range of the 15 sessions (00:00-16:00 CT) before ctDay
bool ComputeA15(datetime ctDay,double &a15)
  {
   double H[],L[],C[]; int n=0; ArrayResize(H,0); ArrayResize(L,0); ArrayResize(C,0);
   for(int k=1;k<=60 && n<16;k++)
     {
      datetime d=ctDay-k*86400; MqlRates r[]; int m=CopyRates(_Symbol,PERIOD_M1,CTtoServer(d),CTtoServer(d+15*3600+59*60),r);
      if(m<30) continue;
      double hi=r[0].high,lo=r[0].low; for(int i=1;i<m;i++) { if(r[i].high>hi) hi=r[i].high; if(r[i].low<lo) lo=r[i].low; }
      ArrayResize(H,n+1); ArrayResize(L,n+1); ArrayResize(C,n+1); H[n]=hi; L[n]=lo; C[n]=r[m-1].close; n++;
     }
   if(n<16) return false;
   double s=0;
   for(int i=0;i<15;i++) { double tr=MathMax(H[i]-L[i],MathMax(MathAbs(H[i]-C[i+1]),MathAbs(L[i]-C[i+1]))); s+=tr; }
   a15=s/15.0; return true;
  }
bool HasPos(ulong &ticket,datetime &opened)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(tk==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) { ticket=tk; opened=(datetime)PositionGetInteger(POSITION_TIME); return true; }
     }
   return false;
  }
double LotsFor(double distPts)
  {
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double lots=InpLots;
   if(lots<=0)
     {
      double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE), ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
      if(tv<=0 || ts<=0 || distPts<=0) return 0;
      lots=InpRiskUSD/(distPts/ts*tv);
     }
   lots=MathFloor(lots/step)*step; if(lots<mn) lots=mn; if(lots>mx) lots=mx; return NormalizeDouble(lots,2);
  }
void Say(const string s) { if(InpVerbose) Print("[ManualONB] ",s); }

//--- daily setup at 08:45 CT -----------------------------------------------------------
void Setup(datetime ctDay)
  {
   g_ready=true; g_side=0;                                        // decided once per day, whatever the outcome
   double a15=0; if(!ComputeA15(ctDay,a15)) { Say(TimeToString(ctDay,TIME_DATE)+" no A15 (history)"); return; }
   double hi,lo; int n;
   if(!HiLo(ctDay-86400+23*3600,ctDay+8*3600+29*60,hi,lo,n) || hi<=lo || n<200) { Say(TimeToString(ctDay,TIME_DATE)+" no overnight range"); return; }
   int sh=iBarShift(_Symbol,PERIOD_M1,CTtoServer(ctDay+8*3600+30*60),true); if(sh<0) { Say(TimeToString(ctDay,TIME_DATE)+" no 08:30 bar"); return; }
   double open830=iOpen(_Symbol,PERIOD_M1,sh); g_pos=(open830-lo)/(hi-lo);
   double oh,ol; int on; if(!HiLo(ctDay+8*3600+30*60,ctDay+8*3600+44*60,oh,ol,on) || on<10) { Say(TimeToString(ctDay,TIME_DATE)+" no opening range"); return; }
   g_orh=oh; g_orl=ol; g_dist=InpStopATR*a15; g_side=(g_pos>=2.0/3.0)?1:((g_pos<=1.0/3.0)?-1:0);
   Say(StringFormat("%s CT: overnight %.1f..%.1f open830 %.1f pos %.2f -> %s | OR %.1f..%.1f | A15 %.1f dist %.1f",TimeToString(ctDay,TIME_DATE),lo,hi,open830,g_pos,g_side>0?"LONG bias":(g_side<0?"SHORT bias":"no trade"),ol,oh,a15,g_dist));
  }

int OnInit()
  {
   g_adx=iADXWilder(_Symbol,PERIOD_M15,InpADXPeriod); if(g_adx==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber(InpMagic); g_trade.SetDeviationInPoints((ulong)MathMax(1.0,InpDevPoints/_Point)); g_trade.SetTypeFillingBySymbol(_Symbol);
   Say(StringFormat("started on %s: tick value %.5f tick size %.5f point %.5f digits %d contract %.2f lot step %.3f min %.3f | risk %.0f USD | stop %.2f x A15, RR %.1f, ADX > %.0f",
       _Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),_Point,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),
       SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),InpRiskUSD,InpStopATR,InpRR,InpADXMin));
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { if(g_adx!=INVALID_HANDLE) IndicatorRelease(g_adx); }

void OnTick()
  {
   datetime now=TimeCurrent(), ct=ServerToCT(now); datetime ctDay=ct-ct%86400; MqlDateTime cs; TimeToStruct(ct,cs); int hm=cs.hour*100+cs.min;
   if(ctDay!=g_ctDay)
     {
      g_ctDay=ctDay; g_ready=false; g_side=0; g_traded=false;
      HistorySelect(CTtoServer(ctDay),now+60);                    // restart safety: one trade a day even after a restart
      for(int i=HistoryDealsTotal()-1;i>=0;i--) { ulong dt=HistoryDealGetTicket(i); if(dt>0 && HistoryDealGetInteger(dt,DEAL_MAGIC)==InpMagic && HistoryDealGetString(dt,DEAL_SYMBOL)==_Symbol) { g_traded=true; break; } }
     }
   //--- forced exit at 14:30 CT, and any position left over from a previous CT day
   ulong tk; datetime opened;
   if(HasPos(tk,opened))
     {
      datetime oct=ServerToCT(opened);
      if(hm>=1430 || (oct-oct%86400)<ctDay) { Say(StringFormat("TIME EXIT %s CT",TimeToString(ct,TIME_DATE|TIME_MINUTES))); g_trade.PositionClose(tk); }
      return;
     }
   if(g_traded) return;
   if(!g_ready && hm>=845 && hm<1415) Setup(ctDay);
   if(!g_ready || g_side==0) return;
   datetime m15=iTime(_Symbol,PERIOD_M15,0); if(m15==g_lastM15) return;
   g_lastM15=m15;                                                   // evaluate once per new M15 bar (the bar that just closed is shift 1)
   if(hm<900 || hm>1415) return;
   double adx[1]; if(CopyBuffer(g_adx,0,1,1,adx)!=1) return;
   double cl=iClose(_Symbol,PERIOD_M15,1);
   bool go=(g_side>0 && cl>g_orh) || (g_side<0 && cl<g_orl);
   if(!go || adx[0]<=InpADXMin) return;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID); double lots=LotsFor(g_dist); if(lots<=0) return;
   bool ok;
   if(g_side>0) ok=g_trade.Buy(lots,_Symbol,0,NormalizeDouble(ask-g_dist,_Digits),NormalizeDouble(ask+InpRR*g_dist,_Digits),"ManualONB");
   else         ok=g_trade.Sell(lots,_Symbol,0,NormalizeDouble(bid+g_dist,_Digits),NormalizeDouble(bid-InpRR*g_dist,_Digits),"ManualONB");
   Say(StringFormat("%s %s %.2f lots at %s CT: close %.1f vs OR %.1f..%.1f, ADX %.1f, stop %.1f pts, result %d",g_side>0?"BUY":"SELL",_Symbol,lots,TimeToString(ct,TIME_DATE|TIME_MINUTES),cl,g_orl,g_orh,adx[0],g_dist,(int)ok));
   if(ok) g_traded=true;
  }
