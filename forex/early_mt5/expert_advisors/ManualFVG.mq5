//+------------------------------------------------------------------+
//| ManualFVG.mq5 -- ICT fair value gap retracement in the killzones    |
//| 2026-10-12, the trader: "constroi e testa" (rule FVG_KZ of              |
//| forex/early_mt5/ea_research/PREREG_ICT_SCAN.md, the DAX lead).               |
//| Chart symbol (DAX+). Times are America/New_York; the server clock |
//| is Europe/Athens (MT5), EU and US daylight saving handled.         |
//|  - M15 bars. A closed bar k completes a bullish gap when          |
//|    Low[k] > High[k-2] (bearish: High[k] < Low[k-2]) and bar k     |
//|    closes in the London (02:00-05:00 NY) or NY AM (08:30-11:00)   |
//|    killzone.                                                      |
//|  - Trade the displacement: limit at the gap midpoint, valid for   |
//|    the next 8 bars, cancelled if the far stop level trades first. |
//|    If price is already through the midpoint: market order.        |
//|  - Stop = Low[k-2] (bullish) / High[k-2] (bearish); target = 2 x  |
//|    the risk; skipped if the risk is below 4 spreads; forced exit  |
//|    180 minutes after the fill or at 16:00 NY, whichever is first. |
//|  - One filled trade per killzone per day; size = InpRiskUSD at    |
//|    the stop. NEVER trades another symbol; position tagged with    |
//|    InpMagic.                                                      |
//+------------------------------------------------------------------+
#property copyright "the trader / Round ICT"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>

input double InpRiskUSD     = 500.0;      // risk per trade at the stop, USD
input double InpTPmult      = 2.0;        // target = this x the risk
input int    InpValidBars   = 8;          // the limit order lives this many M15 bars after the gap bar
input int    InpExitMinutes = 180;        // forced exit after the fill (or 16:00 NY)
input double InpMinStopSpr  = 4.0;        // skip when the risk is below this many spreads
input double InpMaxMarginPct= 0.0;       // cap the size so the margin used by this order is at most this % of the FREE margin (0 = off)
input long   InpMagic       = 261031;     // magic number
input bool   InpVerbose     = true;

CTrade g_trade;
datetime g_lastM15=0, g_day=0;
bool     g_winDone[2];
ulong    g_pend=0; int g_pendWin=-1, g_pendSide=0; double g_pendStop=0;

//--- calendar helpers (as ManualDip) ---------------------------------------------------
datetime MakeTime(int y,int mo,int d,int h,int mi)
  { MqlDateTime s; ZeroMemory(s); s.year=y; s.mon=mo; s.day=d; s.hour=h; s.min=mi; s.sec=0; return StructToTime(s); }
int DowOf(datetime t) { MqlDateTime s; TimeToStruct(t,s); return s.day_of_week; }
datetime NthSunday(int y,int mo,int n)
  {
   if(n>0) { datetime t=MakeTime(y,mo,1,0,0); int dw=DowOf(t); int first=1+((7-dw)%7); return MakeTime(y,mo,first+7*(n-1),0,0); }
   int nd=(mo==12)?31:(int)((MakeTime(mo==12?y+1:y,mo==12?1:mo+1,1,0,0)-MakeTime(y,mo,1,0,0))/86400);
   datetime t=MakeTime(y,mo,nd,0,0); int dw=DowOf(t); return t-dw*86400;
  }
datetime NYtoUTC(datetime loc)
  { MqlDateTime s; TimeToStruct(loc,s); datetime a=NthSunday(s.year,3,2)+2*3600, b=NthSunday(s.year,11,1)+2*3600; int off=(loc>=a && loc<b)?-4:-5; return loc-off*3600; }
bool EUSummerUTC(datetime utc)
  { MqlDateTime s; TimeToStruct(utc,s); datetime a=NthSunday(s.year,3,-1)+3600, b=NthSunday(s.year,10,-1)+3600; return (utc>=a && utc<b); }
datetime UTCtoServer(datetime utc) { return utc+(EUSummerUTC(utc)?3:2)*3600; }
datetime ServerToNY(datetime server)
  {
   datetime utc=server-(EUSummerUTC(server-3*3600)?3:2)*3600; datetime l4=utc-4*3600;
   if(NYtoUTC(l4)==utc) return l4; return utc-5*3600;
  }
datetime NYtoServer(datetime ny) { return UTCtoServer(NYtoUTC(ny)); }

//--- helpers -----------------------------------------------------------------------------
bool HasPos(ulong &ticket,datetime &opened)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(tk==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) { ticket=tk; opened=(datetime)PositionGetInteger(POSITION_TIME); return true; }
     }
   return false;
  }
double LotsFor(double riskPts,double price)
  {
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE), ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE); if(tv<=0 || ts<=0 || riskPts<=0) return 0;
   double lots=InpRiskUSD/(riskPts/ts*tv);
   if(InpMaxMarginPct>0)
     { double m1=0; if(OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,1.0,price,m1) && m1>0) { double maxl=AccountInfoDouble(ACCOUNT_MARGIN_FREE)*InpMaxMarginPct/100.0/m1; if(lots>maxl) lots=maxl; } }
   lots=MathFloor(lots/step)*step; if(lots<mn) lots=mn; if(lots>mx) lots=mx; return NormalizeDouble(lots,2);
  }
void Say(const string s) { if(InpVerbose) Print("[ManualFVG] ",s); }
int WindowOf(datetime barStartServer)
  {
   datetime ny=ServerToNY(barStartServer); MqlDateTime s; TimeToStruct(ny,s); int close=s.hour*60+s.min+15;
   if(close>=120 && close<=300) return 0;
   if(close>=510 && close<=660) return 1;
   return -1;
  }

int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic); g_trade.SetTypeFillingBySymbol(_Symbol); g_winDone[0]=false; g_winDone[1]=false;
   Say(StringFormat("started on %s: tick value %.5f tick size %.5f point %.5f digits %d | risk %.0f USD, TP %.1f R, valid %d bars, exit %d min",_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),
       SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),_Point,_Digits,InpRiskUSD,InpTPmult,InpValidBars,InpExitMinutes));
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   datetime now=TimeCurrent(), ny=ServerToNY(now), day=ny-ny%86400;
   if(day!=g_day) { g_day=day; g_winDone[0]=false; g_winDone[1]=false; }
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID), ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   //--- the pending order: filled? still valid?
   ulong tk; datetime opened;
   if(g_pend!=0)
     {
      if(OrderSelect(g_pend))
        {
         if((g_pendSide>0 && bid<=g_pendStop) || (g_pendSide<0 && ask>=g_pendStop)) { Say("pending order cancelled: the stop level traded first"); g_trade.OrderDelete(g_pend); g_pend=0; }
        }
      else { if(HasPos(tk,opened) && g_pendWin>=0) { g_winDone[g_pendWin]=true; Say(StringFormat("order filled (window %d)",g_pendWin)); } g_pend=0; }
     }
   //--- forced exit: 180 minutes after the fill or 16:00 NY
   if(HasPos(tk,opened))
     {
      datetime onyday=ServerToNY(opened); onyday-=onyday%86400; datetime dl=MathMin(opened+InpExitMinutes*60,NYtoServer(onyday+16*3600));
      if(now>=dl) { Say(StringFormat("TIME EXIT %s",TimeToString(ny,TIME_DATE|TIME_MINUTES))); g_trade.PositionClose(tk); }
     }
   //--- a new M15 bar: look at the bar that just closed (shift 1) and the two before
   datetime m15=iTime(_Symbol,PERIOD_M15,0); if(m15==g_lastM15) return; g_lastM15=m15;
   if(g_pend!=0) return;
   datetime t1=iTime(_Symbol,PERIOD_M15,1), t3=iTime(_Symbol,PERIOD_M15,3); if(t1==0 || t3==0 || (t1-t3)>45*60) return;
   int w=WindowOf(t1); if(w<0 || g_winDone[w]) return;
   double H1=iHigh(_Symbol,PERIOD_M15,1), L1=iLow(_Symbol,PERIOD_M15,1), H3=iHigh(_Symbol,PERIOD_M15,3), L3=iLow(_Symbol,PERIOD_M15,3);
   int side=0; double mid=0, stop=0;
   if(L1>H3)      { side=1;  mid=(L1+H3)/2.0; stop=L3; }
   else if(H1<L3) { side=-1; mid=(H1+L3)/2.0; stop=H3; }
   else return;
   double spr=ask-bid, risk=MathAbs(mid-stop); if(risk<InpMinStopSpr*spr || risk<=0) return;
   double lots=LotsFor(risk,mid); if(lots<=0) return;
   datetime exp=t1+(InpValidBars+1)*900; bool ok=false;
   mid=NormalizeDouble(mid,_Digits); stop=NormalizeDouble(stop,_Digits);
   if(side>0)
     {
      if(ask<=mid) { double r2=MathAbs(ask-stop); if(r2<=0) return; ok=g_trade.Buy(LotsFor(r2,ask),_Symbol,0,stop,NormalizeDouble(ask+InpTPmult*r2,_Digits),"ManualFVG"); if(ok) g_winDone[w]=true; }
      else ok=g_trade.BuyLimit(lots,mid,_Symbol,stop,NormalizeDouble(mid+InpTPmult*risk,_Digits),ORDER_TIME_SPECIFIED,exp,"ManualFVG");
     }
   else
     {
      if(bid>=mid) { double r2=MathAbs(stop-bid); if(r2<=0) return; ok=g_trade.Sell(LotsFor(r2,bid),_Symbol,0,stop,NormalizeDouble(bid-InpTPmult*r2,_Digits),"ManualFVG"); if(ok) g_winDone[w]=true; }
      else ok=g_trade.SellLimit(lots,mid,_Symbol,stop,NormalizeDouble(mid-InpTPmult*risk,_Digits),ORDER_TIME_SPECIFIED,exp,"ManualFVG");
     }
   Say(StringFormat("%s gap %s window %d: mid %.1f stop %.1f risk %.1f pts (%.1f spreads) lots %.2f -> %s",side>0?"BULLISH":"BEARISH",TimeToString(ny,TIME_DATE|TIME_MINUTES),w,mid,stop,risk,risk/MathMax(spr,_Point),lots,ok?"placed":"REJECTED"));
   if(ok && !g_winDone[w]) { ulong o=g_trade.ResultOrder(); if(o>0) { g_pend=o; g_pendWin=w; g_pendSide=side; g_pendStop=stop; } }
  }
