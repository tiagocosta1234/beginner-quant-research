//+------------------------------------------------------------------+
//| ManualORB.mq5 -- the daily card's opening-range breakout, automated |
//| 2026-10-15 (breakout research day; forex/mt5_DAILY_CARD_WEEK_*.md,    |
//| forex/ea_research/BREAKOUT_KNOWLEDGE.md). UNVALIDATED: no tested     |
//| edge (card legs ~coin flips; Nasdaq trend leg is the best lead).  |
//| One instance per chart symbol:                                    |
//|   XAUUSD+ chart: InpSession=LONDON, 08:00, box 30, stop BOX       |
//|   NSDQ+  chart:  InpSession=NEWYORK, 09:30, box 30, stop HALFBOX  |
//|  - Box = bid high/low of the first InpBoxMin minutes of the       |
//|    session (local time; server clock = Europe/Athens, EU and US   |
//|    daylight saving handled).                                      |
//|  - Buy stop at the box high, sell stop at the box low (or only    |
//|    the trend side), one-cancels-other, valid InpValidMin minutes. |
//|  - Stop: other side of the box (BOX) or the box middle (HALFBOX), |
//|    clipped to [InpStopMinPct, InpStopMaxPct] of price; skip if    |
//|    the box is wider than InpSkipBoxPct of price or narrower than  |
//|    InpMinBoxSpreads spreads (cost lesson of the research day).    |
//|  - Target InpTPmult x risk (0 = none, hold to the time exit).     |
//|  - Size: InpRiskUSD lost at the stop.                             |
//|  - Account day guard (server day, all symbols, closed + floating):|
//|    at <= -InpDayStopUSD or >= +InpDayTargetUSD close this EA's    |
//|    positions and orders and stop until the next day.              |
//|  - Time exit at InpExitHHMM local time. News flat (InpNewsFlat):  |
//|    flat and done for the day around releases listed in the news   |
//|    file. Never trades another                                     |
//|    symbol; tagged with InpMagic.                                  |
//+------------------------------------------------------------------+
#property copyright "the trader / breakout day"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>

enum ENUM_SESS  { LONDON=0, NEWYORK=1 };
enum ENUM_STOPM { STOP_BOX=0, STOP_HALFBOX=1 };

input ENUM_SESS  InpSession       = NEWYORK;  // session clock
input int        InpOpenHHMM      = 930;      // session open, local time (e.g. 800 London, 930 New York)
input int        InpBoxMin        = 30;       // box length, minutes
input int        InpValidMin      = 120;      // orders live this many minutes after the box
input int        InpExitHHMM      = 1530;     // time exit, local time (e.g. 1400 London, 1530 New York)
input ENUM_STOPM InpStopMode      = STOP_HALFBOX;
input double     InpStopMinPct    = 0.17;     // stop at least this % of price
input double     InpStopMaxPct    = 0.34;     // stop at most this % of price
input double     InpSkipBoxPct    = 0.0;      // skip if the box is wider than this % of price (0 = off; gold card 0.48)
input double     InpMinBoxSpreads = 25.0;     // skip if the box is narrower than this many average spreads (0 = off)
input double     InpTPmult        = 2.0;      // target = this x the risk (0 = no target)
input bool       InpTrendOnly     = true;     // only the side of the daily trend (previous D1 close vs SMA20)
input double     InpRiskUSD       = 350.0;    // loss at the stop, USD
input double     InpDayStopUSD    = 2000.0;   // account day guard: stop at this day loss (closed + floating)
input double     InpDayTargetUSD  = 2000.0;   // account day guard: stop at this day profit (MT5 broker counts at most 2%)
input long       InpMagic         = 261015;
input bool       InpVerbose       = true;
input bool       InpNewsFlat      = true;     // flat (and done for the day) from InpNewsBeforeMin before to InpNewsAfterMin after a listed release
input string     InpNewsFile      = "ManualNewsAll.csv"; // COMMON Files folder, "YYYY.MM.DD HH:MM,label" per line, SERVER clock (forex/tools/make_news_file.py --kinds CPI,NFP,FOMC)
input int        InpNewsBeforeMin = 5;
input int        InpNewsAfterMin  = 5;

CTrade g_trade;
datetime g_day=0; bool g_done=false, g_halt=false; ulong g_buy=0, g_sell=0;
datetime g_news[];

//--- calendar helpers ---------------------------------------------------------------------
datetime MakeTime(int y,int mo,int d,int h,int mi) { MqlDateTime s; ZeroMemory(s); s.year=y; s.mon=mo; s.day=d; s.hour=h; s.min=mi; return StructToTime(s); }
int DowOf(datetime t) { MqlDateTime s; TimeToStruct(t,s); return s.day_of_week; }
datetime NthSunday(int y,int mo,int n)
  {
   if(n>0) { datetime t=MakeTime(y,mo,1,0,0); int dw=DowOf(t); int first=1+((7-dw)%7); return MakeTime(y,mo,first+7*(n-1),0,0); }
   datetime nxt=(mo==12)?MakeTime(y+1,1,1,0,0):MakeTime(y,mo+1,1,0,0); datetime t=nxt-86400; int dw=DowOf(t); return t-dw*86400;
  }
bool EUSummerUTC(datetime utc) { MqlDateTime s; TimeToStruct(utc,s); return utc>=NthSunday(s.year,3,-1)+3600 && utc<NthSunday(s.year,10,-1)+3600; }
bool USSummerLocal(datetime loc) { MqlDateTime s; TimeToStruct(loc,s); return loc>=NthSunday(s.year,3,2)+2*3600 && loc<NthSunday(s.year,11,1)+2*3600; }
datetime ServerToUTC(datetime srv) { return srv-(EUSummerUTC(srv-3*3600)?3:2)*3600; }
datetime UTCToServer(datetime utc) { return utc+(EUSummerUTC(utc)?3:2)*3600; }
datetime LocalToUTC(datetime loc)
  {
   if(InpSession==LONDON) { datetime u=loc; return EUSummerUTC(u-3600)?loc-3600:loc; }
   return loc+(USSummerLocal(loc)?4:5)*3600;
  }
datetime UTCToLocal(datetime utc)
  {
   if(InpSession==LONDON) return utc+(EUSummerUTC(utc)?3600:0);
   datetime l4=utc-4*3600; if(LocalToUTC(l4)==utc) return l4; return utc-5*3600;
  }
datetime LocalToServer(datetime loc) { return UTCToServer(LocalToUTC(loc)); }

//--- helpers ------------------------------------------------------------------------------
void Say(const string s) { if(InpVerbose) Print("[ManualORB ",_Symbol,"] ",s); }
double LotsFor(double riskPts)
  {
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS), ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE); if(tv<=0 || ts<=0 || riskPts<=0) return 0;
   double lots=MathFloor(InpRiskUSD/(riskPts/ts*tv)/step)*step; if(lots<mn) return 0; if(lots>mx) lots=mx; return NormalizeDouble(lots,2);
  }
bool MyPosition(ulong &tk)
  {
   for(int i=PositionsTotal()-1;i>=0;i--) { ulong t=PositionGetTicket(i); if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) { tk=t; return true; } }
   return false;
  }
void CancelOrders() { if(g_buy>0 && OrderSelect(g_buy)) g_trade.OrderDelete(g_buy); if(g_sell>0 && OrderSelect(g_sell)) g_trade.OrderDelete(g_sell); g_buy=0; g_sell=0; }
void CloseMine() { ulong tk; while(MyPosition(tk)) { if(!g_trade.PositionClose(tk)) break; } CancelOrders(); }
double AccountDayPnL(datetime srvDayStart)
  {
   double pnl=0;
   if(HistorySelect(srvDayStart,TimeCurrent()+60))
      for(int i=HistoryDealsTotal()-1;i>=0;i--)
        { ulong d=HistoryDealGetTicket(i); long e=HistoryDealGetInteger(d,DEAL_ENTRY); if(e==DEAL_ENTRY_OUT || e==DEAL_ENTRY_INOUT || e==DEAL_ENTRY_OUT_BY)
            pnl+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_COMMISSION); }
   return pnl+AccountInfoDouble(ACCOUNT_PROFIT);
  }
int TrendSide()
  {
   double c[]; if(CopyClose(_Symbol,PERIOD_D1,1,20,c)<20) return 0;   // oldest first: c[19] = yesterday's close
   double s=0; for(int i=0;i<20;i++) s+=c[i]; double sma=s/20.0;     // SMA20 ending yesterday (as orb_refine: sign(prev close - prev SMA20))
   return c[19]>sma ? 1 : (c[19]<sma ? -1 : 0);
  }

//--- news flat (2026-10-15: on MT5 broker real ticks >50% of CPI / NFP releases jump past a card-sized stop within 10 s, NEWS_GAPS_RESULT.md)
int LoadNews()
  {
   ArrayResize(g_news,0);
   int fh=FileOpen(InpNewsFile,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(fh==INVALID_HANDLE) return -1;
   int n=0;
   while(!FileIsEnding(fh))
     {
      string line=FileReadString(fh); StringTrimLeft(line); StringTrimRight(line);
      if(StringLen(line)<16 || StringGetCharacter(line,0)=='#') continue;
      datetime t=StringToTime(StringSubstr(line,0,16)); if(t<=0) continue;
      ArrayResize(g_news,n+1); g_news[n]=t; n++;
     }
   FileClose(fh); ArraySort(g_news); return n;
  }
bool InNewsWindow(datetime now)
  {
   for(int i=0;i<ArraySize(g_news);i++)
     {
      if(now<g_news[i]-InpNewsBeforeMin*60) return false;
      if(now<=g_news[i]+InpNewsAfterMin*60) return true;
     }
   return false;
  }

int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic); g_trade.SetTypeFillingBySymbol(_Symbol);
   if(InpNewsFlat)
     {
      int n=LoadNews();
      if(n<0) { Alert("[ManualORB] news file ",InpNewsFile," not found in the COMMON Files folder: EA not started (set InpNewsFlat=false to run without it)"); return INIT_FAILED; }
      datetime nxt=0; for(int i=0;i<n;i++) if(g_news[i]>TimeCurrent()) { nxt=g_news[i]; break; }
      Say(StringFormat("news flat ON: %d releases loaded, next %s",n,nxt>0?TimeToString(nxt):"NONE (update the file)"));
     }
   Say(StringFormat("started: %s open %04d box %d min, valid %d min, exit %04d, stop %s [%.2f%%-%.2f%%], min box %.0f spreads, TP %.1fR, trend-only %s, risk %.0f USD, day guard -%.0f/+%.0f",
       InpSession==LONDON?"London":"New York",InpOpenHHMM,InpBoxMin,InpValidMin,InpExitHHMM,InpStopMode==STOP_BOX?"box":"half box",InpStopMinPct,InpStopMaxPct,InpMinBoxSpreads,InpTPmult,InpTrendOnly?"yes":"no",InpRiskUSD,InpDayStopUSD,InpDayTargetUSD));
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   datetime now=TimeCurrent(), utc=ServerToUTC(now), loc=UTCToLocal(utc), locDay=loc-loc%86400;
   if(locDay!=g_day) { g_day=locDay; g_done=false; g_halt=false; g_buy=0; g_sell=0; }
   datetime srvDay=now-now%86400;
   //--- account day guard
   if(!g_halt)
     {
      double dp=AccountDayPnL(srvDay);
      if(dp<=-InpDayStopUSD || dp>=InpDayTargetUSD) { g_halt=true; CloseMine(); Say(StringFormat("DAY GUARD at %.0f USD: flat and stopped until tomorrow",dp)); return; }
     }
   else return;
   //--- news flat: close, cancel and stop for the day
   if(InpNewsFlat && InNewsWindow(now))
     {
      ulong tkn; bool had=MyPosition(tkn) || g_buy>0 || g_sell>0;
      if(had) CloseMine();
      if(had || !g_done) Say("NEWS FLAT: release window, flat and done for the day");
      g_done=true; g_halt=true; return;
     }
   datetime tOpen=LocalToServer(locDay+(InpOpenHHMM/100)*3600+(InpOpenHHMM%100)*60);
   datetime tBox=tOpen+InpBoxMin*60, tValid=tBox+InpValidMin*60, tExit=LocalToServer(locDay+(InpExitHHMM/100)*3600+(InpExitHHMM%100)*60);
   //--- time exit
   if(now>=tExit) { ulong tk; if(MyPosition(tk) || g_buy>0 || g_sell>0) { CloseMine(); Say("TIME EXIT"); } return; }
   //--- one-cancels-other
   ulong tk;
   if(MyPosition(tk)) { if(g_buy>0 || g_sell>0) { CancelOrders(); Say("filled: other order cancelled"); } return; }
   if(now>=tValid && (g_buy>0 || g_sell>0)) { CancelOrders(); Say("orders expired"); }
   if(g_done || now<tBox || now>=tValid) return;
   //--- the box (M1 bid bars of [tOpen, tBox))
   MqlRates r[]; int n=CopyRates(_Symbol,PERIOD_M1,tOpen,tBox-60,r); g_done=true;
   if(n<InpBoxMin*0.6) { Say(StringFormat("box skipped: only %d M1 bars",n)); return; }
   double hi=-DBL_MAX, lo=DBL_MAX, sp=0; for(int i=0;i<n;i++) { hi=MathMax(hi,r[i].high); lo=MathMin(lo,r[i].low); sp+=r[i].spread*_Point; } sp/=n;
   double box=hi-lo, px=(hi+lo)/2.0;
   if(box<=0) return;
   if(InpSkipBoxPct>0 && box>InpSkipBoxPct/100.0*px) { Say(StringFormat("box %.2f wider than %.2f%% of price: no trade",box,InpSkipBoxPct)); return; }
   if(InpMinBoxSpreads>0 && sp>0 && box<InpMinBoxSpreads*sp) { Say(StringFormat("box %.2f = %.1f spreads < %.0f: no trade (cost)",box,box/sp,InpMinBoxSpreads)); return; }
   double dist=(InpStopMode==STOP_BOX?box:box/2.0); dist=MathMax(dist,InpStopMinPct/100.0*px); dist=MathMin(dist,InpStopMaxPct/100.0*px);
   double lots=LotsFor(dist); if(lots<=0) { Say("size below the minimum lot: no trade"); return; }
   int trend=InpTrendOnly?TrendSide():0;
   datetime exp=tValid;
   double hiN=NormalizeDouble(hi,_Digits), loN=NormalizeDouble(lo,_Digits);
   //--- price already through the box at placement time: a stop order there would be rejected, so enter at market (as the backtest fills it)
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(ask>=hiN && (!InpTrendOnly || trend>0))
     {
      double tp=InpTPmult>0?NormalizeDouble(ask+InpTPmult*dist,_Digits):0;
      if(g_trade.Buy(lots,_Symbol,0,NormalizeDouble(hiN-dist,_Digits),tp,"ManualORB")) Say(StringFormat("ask %.5f already above the box high %.5f: bought at market, stop %.5f",ask,hiN,hiN-dist));
      return;
     }
   if(bid<=loN && (!InpTrendOnly || trend<0))
     {
      double tp=InpTPmult>0?NormalizeDouble(bid-InpTPmult*dist,_Digits):0;
      if(g_trade.Sell(lots,_Symbol,0,NormalizeDouble(loN+dist,_Digits),tp,"ManualORB")) Say(StringFormat("bid %.5f already below the box low %.5f: sold at market, stop %.5f",bid,loN,loN+dist));
      return;
     }
   if(!InpTrendOnly || trend>0)
     {
      double tp=InpTPmult>0?NormalizeDouble(hiN+InpTPmult*dist,_Digits):0;
      if(g_trade.BuyStop(lots,hiN,_Symbol,NormalizeDouble(hiN-dist,_Digits),tp,ORDER_TIME_SPECIFIED,exp,"ManualORB")) g_buy=g_trade.ResultOrder();
     }
   if(!InpTrendOnly || trend<0)
     {
      double tp=InpTPmult>0?NormalizeDouble(loN-InpTPmult*dist,_Digits):0;
      if(g_trade.SellStop(lots,loN,_Symbol,NormalizeDouble(loN+dist,_Digits),tp,ORDER_TIME_SPECIFIED,exp,"ManualORB")) g_sell=g_trade.ResultOrder();
     }
   Say(StringFormat("box %.2f-%.2f (%.1f spreads), stop %.2f, lots %.2f, trend %d -> buy stop %s, sell stop %s",lo,hi,box/MathMax(sp,_Point),dist,lots,trend,g_buy>0?"placed":"-",g_sell>0?"placed":"-"));
  }
