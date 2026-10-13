//+------------------------------------------------------------------+
//| PairReplay.mq5 -- Strategy Tester harness: the REAL AccountGuard  |
//| (per tick) + a REPLAY of the gold pair's historical trades        |
//| (TradeList.mqh: open time, close time, side, lots), standing in   |
//| for SDB + the closed-source XAU5, which cannot share a tester run |
//| with the guard. The replay opens each trade at market at its open |
//| time unless the guard has stopped the day, and closes it at its   |
//| scheduled time. Logged to InpLogName (agent MQL5\Files).          |
//+------------------------------------------------------------------+
#property copyright "the trader session system"
#property version   "1.00"
#property strict
#include "AccountGuard.mqh"
#include "TradeList.mqh"

input double InpInitial       = 100000.0;
input double InpDailyStopPct  = 2.4;
input double InpFloorStopPct  = 6.5;
input double InpProfitCapPct  = 2.0;
input int    InpShiftSec      = 0;        // server midnight, as on MT5
input string InpLogName       = "pair_replay.csv";

CAccountGuard guard;
CTrade        drv;
int           fh=INVALID_HANDLE;
int           nextOpen=0;
datetime      lastSnap=0;
ulong         tk[];
bool          opened[], done[];
int           skipped=0, openedN=0;

void Log(string ev,string detail="")
  {
   if(fh==INVALID_HANDLE) return;
   FileWrite(fh,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),ev,DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),
             DoubleToString(guard.m_dayRef,2),PositionsTotal(),detail);
  }

int OnInit()
  {
   fh=FileOpen(InpLogName,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   guard.Init(InpInitial,InpDailyStopPct,InpFloorStopPct,0.0,0.3,0,D'2022.01.01 00:00',"PAIRREPLAY",0,InpProfitCapPct,0.0);
   guard.m_pragueShiftSec=InpShiftSec;
   drv.SetDeviationInPoints(100); drv.SetAsyncMode(false);
   int n=ArraySize(T_OPEN); ArrayResize(tk,n); ArrayResize(opened,n); ArrayResize(done,n); ArrayInitialize(tk,0); ArrayInitialize(opened,false); ArrayInitialize(done,false);
   EventSetTimer(1); Log("START","trades="+(string)n);
   return INIT_SUCCEEDED;
  }

void Step()
  {
   string ev=guard.Check(); if(ev!="") Log(ev);
   datetime now=TimeCurrent(); int n=ArraySize(T_OPEN);
   for(int i=0;i<nextOpen;i++)                       // scheduled closes
      if(opened[i] && !done[i] && now>=T_CLOSE[i])
        {
         if(tk[i]>0 && PositionSelectByTicket(tk[i])) drv.PositionClose(tk[i]);
         done[i]=true;
        }
   while(nextOpen<n && now>=T_OPEN[nextOpen])        // scheduled opens
     {
      int i=nextOpen; nextOpen++;
      if(now>=T_CLOSE[i] || guard.m_hardHalt || guard.m_dayHalt || guard.m_locked) { skipped++; done[i]=true; continue; }
      bool ok=(T_SIDE[i]>0)?drv.Buy(T_LOTS[i],_Symbol,0,0,0,"R"+(string)i):drv.Sell(T_LOTS[i],_Symbol,0,0,0,"R"+(string)i);
      if(ok) { tk[i]=drv.ResultOrder(); ulong deal=drv.ResultDeal(); if(deal>0 && HistoryDealSelect(deal)) tk[i]=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID); opened[i]=true; openedN++; }
      else skipped++;
     }
   if(now-lastSnap>=60) { lastSnap=now; Log("SNAP"); }
  }

void OnTick()  { Step(); }
void OnTimer() { Step(); }

void OnDeinit(const int reason)
  {
   Log("END","opened="+(string)openedN+" skipped="+(string)skipped);
   if(fh!=INVALID_HANDLE) FileClose(fh);
   EventKillTimer();
  }
//+------------------------------------------------------------------+
