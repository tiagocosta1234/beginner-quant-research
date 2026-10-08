//+------------------------------------------------------------------+
//| ManualSDB.mq5 -- our own implementation of the Stochastic Daily    |
//| Breakout rule, for a dedicated broker account (2026-10-07).   |
//|                                                                  |
//| Rule (frozen, same as forex/early_mt5/intraday_lab/sdb.py and the public    |
//| MQL5 CodeBase EA 77900, verified trade-for-trade against it in   |
//| the Strategy Tester before use, see forex/early_mt5/expert_advisors/        |
//| ManualSDB_VERIFY.md): on the first tick of every bar, a buy stop   |
//| at yesterday's high when the stochastic signal line turns down   |
//| (a peak two bars ago) and the open three bars ago is below the  |
//| upper Bollinger band (9, 2.0, weighted price, read on bar 4);    |
//| a sell stop at yesterday's low when the signal turns up and that |
//| open is above the lower band. Stop = target = InpStopPct of the  |
//| entry, the pending order lives InpExpiryBars bars, one position  |
//| at a time.                                                       |
//| Added here (the rule itself is untouched):                       |
//|  - InpRiskPct > 0: lot from the stop distance so one loss costs  |
//|    InpRiskPct of InpRiskBase (fixed base, no compounding); 0 =   |
//|    fixed InpLots, which reproduces the original EA exactly.      |
//|  - account guard (AccountGuard.mqh): day stop, emergency floor,  |
//|    optional pass lock. It closes everything on THIS account, so  |
//|    run the EA on a dedicated account only.                       |
//| It never trades outside the symbol and magic it is given.        |
//| No DLL, no web requests.                                         |
//+------------------------------------------------------------------+
#property copyright "the trader (own implementation of a published rule)"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>
#include "AccountGuard.mqh"

input double InpLots        = 0.01;    // fixed volume when InpRiskPct = 0
input double InpRiskPct     = 0.0;     // % of InpRiskBase lost on a stop-out (0 = use InpLots)
input double InpRiskBase    = 100000;  // fixed risk base (0 = current balance)
input int    InpMagic       = 260931;  // magic number
input bool   InpDropOppositePending = false; // true = delete this EA's pending orders while it holds a position (only for a firm that forbids opposite positions; false reproduces the original EA exactly)
input int    InpBandPeriod  = 9;       // Bollinger period (weighted price, 2.0 deviations)
input int    InpKPeriod     = 23;      // stochastic %K period
input int    InpDPeriod     = 3;       // stochastic signal period
input int    InpSlowing     = 7;       // stochastic slowing
input double InpStopPct     = 1.9;     // stop distance, % of entry
input double InpTargetPct   = 1.9;     // target distance, % of entry
input int    InpExpiryBars  = 9;       // bars a pending order stays alive
input bool   InpUseGuard    = false;   // account guard on/off
input double InpGuardInitial= 100000;  // guard: initial balance
input double InpGuardDayPct = 1.5;     // guard: day stop, % of initial (MT5 broker hard limit 2.5)
input double InpGuardFloorPct = 6.5;   // guard: emergency floor, % of initial (MT5 broker static limit 8)
input double InpGuardTargetPct = 0;    // guard: phase target % for the pass lock (MT5 broker test 8; 0 = no lock)
input double InpGuardBufferPct = 0.3;  // guard: extra % above the target before locking
input int    InpGuardMinDays   = 0;    // guard: minimum trading days before the lock
input int    InpGuardPragueShiftSec = 3600; // server time minus the firm's day-reset clock (CHECK per firm)

#define WINDOW   2000     // bars used to seed the smoothed stochastic
#define MIN_BARS 30
#define SHIFT    3        // the bar whose open the band filter reads

int      g_bands = INVALID_HANDLE;
datetime g_lastBar = 0;
CAccountGuard g_guard;

double RoundPrice(const double p)
  {
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   return(tick>0 ? NormalizeDouble(MathRound(p/tick)*tick,_Digits) : NormalizeDouble(p,_Digits));
  }

// true inside a trading session of the symbol, in server time
bool MarketOpen()
  {
   datetime now=TimeTradeServer(); MqlDateTime dt; TimeToStruct(now,dt);
   int tod=(int)(now%86400); datetime from,to;
   for(int s=0; SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)dt.day_of_week,s,from,to); s++)
     {
      int f=(int)(from%86400),t=(int)(to%86400);
      if(f<t ? (tod>=f && tod<=t) : (tod>=f || tod<=t)) return(true);
     }
   return(false);
  }

// stochastic signal line, oldest bar first (close-to-close range, smoothed twice with the SMMA recursion, seed 50)
bool SignalLine(double &sig[])
  {
   int n=MathMin(Bars(_Symbol,_Period),WINDOW);
   double c[]; if(CopyClose(_Symbol,_Period,0,n,c)<n) return(false);
   double k[],m[]; ArrayResize(k,n); ArrayResize(m,n); ArrayResize(sig,n);
   for(int i=0;i<n;i++)
     {
      double hi=50,lo=50;
      if(i>=InpKPeriod+1)
        {
         hi=c[i]; lo=c[i];
         for(int a=i-InpKPeriod+1;a<=i;a++) { hi=MathMax(hi,c[a]); lo=MathMin(lo,c[a]); }
        }
      double num=NormalizeDouble(c[i]-lo,8), den=NormalizeDouble(hi-lo,8);
      if(MathAbs(den)<0.00000001) k[i]=(i==0)?50:k[i-1];
      else k[i]=MathMin(100,MathMax(0,100*num/den));
      double pm=(i==0)?50:m[i-1];
      m[i]=(i+1>=InpSlowing)?(pm*(InpSlowing-1)+k[i])/InpSlowing:0;
      double ps=(i==0)?50:sig[i-1];
      sig[i]=(i+1>=InpDPeriod)?(ps*(InpDPeriod-1)+m[i])/InpDPeriod:0;
     }
   return(true);
  }

bool SendReq(MqlTradeRequest &rq)
  {
   MqlTradeResult rs; ZeroMemory(rs);
   return(OrderSend(rq,rs) && (rs.retcode==TRADE_RETCODE_DONE || rs.retcode==TRADE_RETCODE_PLACED));
  }

bool DeletePending(const ulong ticket)
  {
   MqlTradeRequest rq; ZeroMemory(rq);
   rq.action=TRADE_ACTION_REMOVE; rq.order=ticket;
   return(SendReq(rq));
  }

void ExpireOld()
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong t=OrderGetTicket(i);
      if(!OrderSelect(t) || OrderGetInteger(ORDER_MAGIC)!=InpMagic || OrderGetString(ORDER_SYMBOL)!=_Symbol) continue;
      if(iBarShift(_Symbol,_Period,(datetime)OrderGetInteger(ORDER_TIME_SETUP))>=InpExpiryBars) DeletePending(t);
     }
  }

// volume for a stop-out that costs InpRiskPct of the base; fixed InpLots when InpRiskPct = 0
double Volume(const double entry)
  {
   if(InpRiskPct<=0) return(InpLots);
   double base=(InpRiskBase>0)?InpRiskBase:AccountInfoDouble(ACCOUNT_BALANCE);
   double stopDist=entry*InpStopPct/100.0;
   double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double tickLoss=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickSize<=0 || tickLoss<=0 || stopDist<=0) return(0);
   double lossPerLot=stopDist/tickSize*tickLoss;
   double lots=base*InpRiskPct/100.0/lossPerLot;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   lots=MathFloor(lots/step+1e-9)*step;
   if(lots<vmin) return(0);                       // never round UP past the risk budget
   return(MathMin(lots,vmax));
  }

bool HavePosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(PositionSelectByTicket(PositionGetTicket(i)) && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==_Symbol) return(true);
   return(false);
  }

// MT5 broker forbids opposite positions on the same asset: while this EA holds a position, delete every pending order of its own
// (the original EA let the other side's older pending order fill: 4 of 201 trades in 2021-26 started inside another trade)
void DropPendingWhileInPosition()
  {
   if(!HavePosition()) return;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong t=OrderGetTicket(i);
      if(OrderSelect(t) && OrderGetInteger(ORDER_MAGIC)==InpMagic && OrderGetString(ORDER_SYMBOL)==_Symbol) DeletePending(t);
     }
  }

void PlaceStop(const bool buy,const double level)
  {
   if(HavePosition()) return;
   ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY_STOP:ORDER_TYPE_SELL_STOP;
   for(int i=OrdersTotal()-1;i>=0;i--)            // replace the previous order of the same side
     {
      ulong t=OrderGetTicket(i);
      if(OrderSelect(t) && OrderGetInteger(ORDER_MAGIC)==InpMagic && OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_TYPE)==type && !DeletePending(t)) return;
     }
   double vol=Volume(level);
   if(vol<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)) return;
   double dir=buy?1.0:-1.0;
   double sl=RoundPrice(level-dir*level*InpStopPct/100.0), tp=RoundPrice(level+dir*level*InpTargetPct/100.0);
   double market=buy?SymbolInfoDouble(_Symbol,SYMBOL_ASK):SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double gap=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point, half=_Point/2;
   if(dir*(level-market)<gap-half || dir*(level-sl)<gap-half || dir*(tp-level)<gap-half) return;
   double margin=0;
   if(!OrderCalcMargin(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,vol,level,margin) || AccountInfoDouble(ACCOUNT_MARGIN_FREE)<=margin) return;
   MqlTradeRequest rq; ZeroMemory(rq);
   rq.action=TRADE_ACTION_PENDING; rq.symbol=_Symbol; rq.type=type; rq.volume=vol; rq.price=level; rq.sl=sl; rq.tp=tp; rq.magic=InpMagic;
   rq.type_filling=((SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE)&SYMBOL_FILLING_FOK)!=0)?ORDER_FILLING_FOK:ORDER_FILLING_IOC;
   if((SymbolInfoInteger(_Symbol,SYMBOL_EXPIRATION_MODE)&SYMBOL_EXPIRATION_GTC)==0) rq.type_time=ORDER_TIME_DAY;
   SendReq(rq);
  }

int OnInit()
  {
   g_bands=iBands(_Symbol,_Period,InpBandPeriod,0,2.0,PRICE_WEIGHTED);
   if(g_bands==INVALID_HANDLE) return(INIT_FAILED);
   if(InpUseGuard)
     {
      g_guard.Init(InpGuardInitial,InpGuardDayPct,InpGuardFloorPct,InpGuardTargetPct,InpGuardBufferPct,InpGuardMinDays,TimeCurrent(),"ManualSDB");
      g_guard.m_pragueShiftSec=InpGuardPragueShiftSec;
      EventSetTimer(1);
     }
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   IndicatorRelease(g_bands);
   if(InpUseGuard) EventKillTimer();
  }

void OnTimer()
  {
   if(InpUseGuard) g_guard.Check();
  }

void OnTick()
  {
   if(InpUseGuard) g_guard.Check();
   if(InpDropOppositePending) DropPendingWhileInPosition();      // off by default: MT5 broker support confirmed (2026-10-08) that opposite positions inside ONE account are allowed
   if(InpUseGuard && (g_guard.m_hardHalt || g_guard.m_dayHalt || g_guard.m_locked)) return;     // no new orders while a stop is active
   datetime bar=iTime(_Symbol,_Period,0);
   if(bar==g_lastBar || Bars(_Symbol,_Period)<MIN_BARS) return;
   g_lastBar=bar;
   if(!MarketOpen()) return;
   ExpireOld();
   double up[],lo[],sig[];
   if(CopyBuffer(g_bands,1,SHIFT+1,1,up)<1 || CopyBuffer(g_bands,2,SHIFT+1,1,lo)<1 || !SignalLine(sig)) return;
   double open3=iOpen(_Symbol,_Period,SHIFT);
   int n=ArraySize(sig);
   double s3=sig[n-4], s2=sig[n-3], s1=sig[n-2];
   bool peak=(s3<s2 && s2>s1), trough=(s3>s2 && s2<s1);
   bool buy=(open3<up[0] && peak), sell=(open3>lo[0] && trough);
   if(buy) PlaceStop(true,RoundPrice(iHigh(_Symbol,PERIOD_D1,1)));
   else if(sell) PlaceStop(false,RoundPrice(iLow(_Symbol,PERIOD_D1,1)));
  }
//+------------------------------------------------------------------+
