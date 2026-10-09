//+------------------------------------------------------------------+
//| GuardSelfTest.mq5 -- Strategy Tester harness for AccountGuard.mqh |
//| One EA = the real guard code + a STUBBORN driver that opens a      |
//| position on a schedule (and, if InpStubborn, keeps trying every    |
//| few seconds even while the guard has stopped trading), standing in |
//| for the third-party EAs, which cannot be run together with the     |
//| guard in the tester (one EA per test). Everything is logged to     |
//| InpLogName (agent MQL5\Files) for the Python checks.               |
//+------------------------------------------------------------------+
#property copyright "Round 347"
#property version   "1.00"
#property strict
#include "AccountGuard.mqh"

input bool   InpGuardOn       = true;
input double InpInitial       = 100000.0;
input double InpDailyStopPct  = 4.0;
input double InpFloorStopPct  = 9.0;
input double InpTargetPct     = 0.0;
input double InpLockBufferPct = 0.3;
input int    InpMinDays       = 4;
input datetime InpPhaseStart  = D'2022.01.01 00:00';
input double InpDriverLots    = 3.0;      // lots per driver trade
input int    InpEveryMin      = 45;       // scheduled open every N minutes
input int    InpHoldMin       = 40;       // scheduled close after N minutes
input bool   InpStubborn      = true;     // also try to open every 10 s whenever flat (even during a stop)
input int    InpDirMode       = 0;        // 0 pseudo-random, 1 always buy, 2 always sell
input int    InpKillAfter     = 0;        // 0 = kill switch off
input string InpLogName       = "guard_test.csv";
input double InpProfitCapPct  = 0.0;      // day profit cap halt, % of initial (0 = off)
input int    InpShiftSec      = 3600;     // server time minus the day-reset clock (0 = server midnight, as on MT5)
input int    InpRestartHour   = -1;       // >= 0: once a day at this server hour rebuild the day start like a restarted EA and log old vs rebuilt (RESTARTCHK)

class CTestGuard : public CAccountGuard
  {
public:
   virtual void OnKill() { Print("[GUARDTEST] kill switch"); ExpertRemove(); }
  };
CTestGuard guard;
CTrade        drv;
int           fh=INVALID_HANDLE;
datetime      lastSched=0, lastTry=0, lastSnap=0;
datetime      openTime=0;
ulong         seed=12345;
int           opens=0, failedOpens=0;
long          lastRestartDay=-2;

int NextDir()
  {
   if(InpDirMode==1) return 1;
   if(InpDirMode==2) return -1;
   seed=(seed*1103515245+12345)&0x7fffffff;
   return ((seed>>16)&1)?1:-1;
  }

void Log(string ev,string detail="")
  {
   if(fh==INVALID_HANDLE) return;
   FileWrite(fh,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),ev,DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),
             DoubleToString(guard.m_dayRef,2),PositionsTotal(),detail);
  }

int OnInit()
  {
   fh=FileOpen(InpLogName,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   guard.Init(InpInitial,InpDailyStopPct,InpFloorStopPct,InpTargetPct,InpLockBufferPct,InpMinDays,InpPhaseStart,"GUARDTEST",InpKillAfter,InpProfitCapPct);
   guard.m_pragueShiftSec=InpShiftSec;
   drv.SetDeviationInPoints(100);
   EventSetTimer(1);
   Log("START","guardOn="+(string)InpGuardOn);
   return INIT_SUCCEEDED;
  }

void Drive(bool scheduled)
  {
   datetime now=TimeCurrent();
   // close the scheduled position after the hold time
   if(openTime>0 && now-openTime>=InpHoldMin*60 && PositionsTotal()>0)
     {
      for(int i=PositionsTotal()-1;i>=0;i--) { ulong t=PositionGetTicket(i); if(t>0) drv.PositionClose(t); }
      Log("DRV_CLOSE");
      openTime=0;
     }
   bool flat=(PositionsTotal()==0);
   bool due=(scheduled && now-lastSched>=InpEveryMin*60);
   bool stubborn=(InpStubborn && flat && now-lastTry>=10);
   if(flat && (due || stubborn))
     {
      int dir=NextDir();
      bool ok=(dir>0)?drv.Buy(InpDriverLots,_Symbol):drv.Sell(InpDriverLots,_Symbol);
      lastTry=now; if(due) lastSched=now;
      if(ok) { openTime=now; opens++; Log("DRV_OPEN",(dir>0?"buy":"sell")); }
      else   { failedOpens++; }
     }
  }

void Step()
  {
   if(InpGuardOn)
     {
      string ev=guard.Check();
      if(ev!="") Log(ev);
      if(guard.m_killed && ev=="ENFORCE") Log("KILL");
     }
   datetime now=TimeCurrent();
   if(InpRestartHour>=0)
     {
      MqlDateTime dtm; TimeToStruct(now,dtm); long dayid=guard.DayId();
      if(dtm.hour==InpRestartHour && dayid!=lastRestartDay)
        {
         lastRestartDay=dayid;
         CTestGuard g2; g2.Init(InpInitial,InpDailyStopPct,InpFloorStopPct,InpTargetPct,InpLockBufferPct,InpMinDays,InpPhaseStart,"GUARDTEST2",InpKillAfter,InpProfitCapPct); g2.m_pragueShiftSec=InpShiftSec;
         double rebuilt=g2.DayStartBalance(AccountInfoDouble(ACCOUNT_BALANCE));
         Log("RESTARTCHK","old="+DoubleToString(guard.m_dayRef,2)+" rebuilt="+DoubleToString(rebuilt,2));
        }
     }
   if(now-lastSnap>=60) { lastSnap=now; Log("SNAP"); }
  }

void OnTick()
  {
   Step();
   Drive(true);
  }

void OnTimer()
  {
   Step();
   Drive(false);
  }

void OnDeinit(const int reason)
  {
   Log("END","opens="+(string)opens+" failedOpens="+(string)failedOpens);
   if(fh!=INVALID_HANDLE) FileClose(fh);
   EventKillTimer();
  }
//+------------------------------------------------------------------+
