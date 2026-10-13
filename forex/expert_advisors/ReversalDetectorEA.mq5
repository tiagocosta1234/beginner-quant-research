//+------------------------------------------------------------------+
//| ReversalDetectorEA.mq5                                           |
//| the trader's "Reversal Prediction Indicator" (RSI divergence + MACD    |
//| histogram direction + ATR spike) as an Expert Advisor for the    |
//| MT5 Strategy Tester. The rules are the ones backtested in Rounds |
//| 311-315 (forex/ Python simulator):                                |
//|   M1 bid candles; RSI(14) Wilder, MACD(12,26,9) with an EMA      |
//|   signal line, ATR(14) Wilder (computed here by hand: MT5's      |
//|   iATR and iMACD use different smoothing than the original).     |
//|   LONG  = lowest close(L) < lowest close(L) one bar earlier AND  |
//|           lowest RSI(L) > the same one bar earlier AND histogram |
//|           change > -0.01 AND histogram rising AND the bar's      |
//|           range > SpikeATR x ATR. SHORT is the mirror.           |
//|   Entry at the open of the next bar (market), stop = StopATR x   |
//|   ATR, target = TargetR x the stop, ATR of the signal bar; one   |
//|   position at a time; exit at the close after MaxHoldBars bars.  |
//|   Lots: RiskPercent of equity lost at the stop.                  |
//| SAFETY: refuses to run outside the Strategy Tester unless        |
//| AllowLive is set (default false). Research: no edge is claimed;  |
//| see Knowledge_Base/CURRENT_STATE.md (Rounds 311-315).            |
//+------------------------------------------------------------------+
#property copyright "the trader"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input double RiskPercent   = 1.0;    // risk per trade, % of equity lost at the stop
input double StopATR       = 4.0;    // stop distance, x ATR (the original used 1.0)
input double TargetR       = 3.0;    // target = this x the stop (the original used 2.0)
input int    MaxHoldBars   = 120;    // exit at the market after this many M1 bars
input double SpikeATR      = 1.0;    // bar range must exceed this x ATR
input int    Lookback      = 3;      // divergence lookback
input int    RsiPeriod     = 14;
input int    MacdFast      = 12;
input int    MacdSlow      = 26;
input int    MacdSignalLen = 9;
input int    AtrPeriod     = 14;
input double MacdChangeAbs = 0.01;   // the original's ABSOLUTE histogram-change threshold (a no-op on EURUSD, real on gold / indices)
input bool   UseMacdDirection = true;// histogram rising / falling required (Strict); false = the "Much more" level of Round 314
input long   Magic         = 31415;
input bool   AllowLive     = false;  // keep false: the EA is for the Strategy Tester only

CTrade trade;

// ---- indicator state (updated once per closed M1 bar)
bool   haveFirst = false;
double prevClose = 0, atr = 0, avgUp = 0, avgDn = 0, ema12 = 0, ema26 = 0, macdSig = 0;
int    nBars = 0;
#define KEEP 16
double hClose[KEEP], hRsi[KEEP], hHist[KEEP];     // index 0 = the latest closed bar, 1 = the one before, ...
double lastHigh = 0, lastLow = 0, lastAtr = 0;
datetime lastBarTime = 0, lastDone = 0;
int    nTrades = 0;

double Alpha(int n) { return 2.0 / (n + 1.0); }

void Shift()
{
   for(int i = KEEP - 1; i > 0; i--) { hClose[i] = hClose[i-1]; hRsi[i] = hRsi[i-1]; hHist[i] = hHist[i-1]; }
}

// consume one closed bar (oldest to newest)
void Update(const MqlRates &b)
{
   double c = b.close, h = b.high, l = b.low;
   double tr = haveFirst ? MathMax(h - l, MathMax(MathAbs(h - prevClose), MathAbs(l - prevClose))) : (h - l);
   double rsi = 50.0;
   if(!haveFirst)
   {
      atr = tr; ema12 = c; ema26 = c; macdSig = 0.0; avgUp = 0.0; avgDn = 0.0;
   }
   else
   {
      atr += (tr - atr) / AtrPeriod;
      double d = c - prevClose;
      double up = MathMax(d, 0.0), dn = MathMax(-d, 0.0);
      if(nBars == 1) { avgUp = up; avgDn = dn; }
      else { avgUp += (up - avgUp) / RsiPeriod; avgDn += (dn - avgDn) / RsiPeriod; }
      ema12 += Alpha(MacdFast) * (c - ema12);
      ema26 += Alpha(MacdSlow) * (c - ema26);
   }
   double macd = ema12 - ema26;
   if(!haveFirst) macdSig = macd; else macdSig += Alpha(MacdSignalLen) * (macd - macdSig);
   double hist = macd - macdSig;
   rsi = (avgDn == 0.0) ? 100.0 : 100.0 - 100.0 / (1.0 + avgUp / avgDn);
   Shift();
   hClose[0] = c; hRsi[0] = rsi; hHist[0] = hist;
   lastHigh = h; lastLow = l; lastAtr = atr;
   prevClose = c; haveFirst = true; nBars++;
}

double MinOf(const double &a[], int from, int cnt) { double m = a[from]; for(int i = from + 1; i < from + cnt; i++) m = MathMin(m, a[i]); return m; }
double MaxOf(const double &a[], int from, int cnt) { double m = a[from]; for(int i = from + 1; i < from + cnt; i++) m = MathMax(m, a[i]); return m; }

// +1 long, -1 short, 0 none -- evaluated on the latest closed bar
int Signal()
{
   if(nBars < 300 || Lookback + 2 >= KEEP) return 0;
   double lc  = MinOf(hClose, 0, Lookback), lcp = MinOf(hClose, 1, Lookback);
   double hc  = MaxOf(hClose, 0, Lookback), hcp = MaxOf(hClose, 1, Lookback);
   double lr  = MinOf(hRsi, 0, Lookback),   lrp = MinOf(hRsi, 1, Lookback);
   double hr  = MaxOf(hRsi, 0, Lookback),   hrp = MaxOf(hRsi, 1, Lookback);
   double dh  = hHist[0] - hHist[1];
   bool spike = (lastHigh - lastLow) > lastAtr * SpikeATR;
   bool bull  = lc < lcp && lr > lrp && dh > -MacdChangeAbs;
   bool bear  = hc > hcp && hr < hrp && dh <  MacdChangeAbs;
   if(bull && (!UseMacdDirection || hHist[0] > hHist[1]) && spike) return 1;
   if(bear && (!UseMacdDirection || hHist[0] < hHist[1]) && spike) return -1;
   return 0;
}

bool HavePosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == Magic) return true;
   }
   return false;
}

double LotsFor(ENUM_ORDER_TYPE type, double entry, double sl)
{
   double profit = 0.0;
   if(!OrderCalcProfit(type, _Symbol, 1.0, entry, sl, profit) || profit >= 0.0) return 0.0;
   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0;
   double lots = riskMoney / (-profit);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step + 1e-9) * step;
   double margin = 0.0;
   if(OrderCalcMargin(type, _Symbol, lots, entry, margin) && margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.95 && margin > 0.0)
      lots = MathFloor(lots * AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.95 / margin / step) * step;
   if(lots < vmin) return 0.0;
   return MathMin(lots, vmax);
}

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) && !AllowLive)
   {
      Print("ReversalDetectorEA: not in the Strategy Tester and AllowLive=false -- refusing to run.");
      return INIT_FAILED;
   }
   if(_Period != PERIOD_M1) { Print("ReversalDetectorEA: set the chart / tester period to M1."); return INIT_FAILED; }
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(50);
   MqlRates r[];
   int got = CopyRates(_Symbol, PERIOD_M1, 1, 5000, r);        // closed bars, oldest first (series = false)
   if(got < 400) { Print("ReversalDetectorEA: not enough M1 history (", got, ")"); return INIT_FAILED; }
   ArraySetAsSeries(r, false);
   for(int i = 0; i < got; i++) { Update(r[i]); lastDone = r[i].time; }
   lastBarTime = iTime(_Symbol, PERIOD_M1, 0);
   PrintFormat("ReversalDetectorEA ready on %s: %d warm-up bars, ATR %.5f, risk %.2f%%, stop %.1f ATR, target %.1fR, hold %d bars", _Symbol, got, atr, RiskPercent, StopATR, TargetR, MaxHoldBars);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime t0 = iTime(_Symbol, PERIOD_M1, 0);
   if(t0 == lastBarTime) return;                                  // work once per new M1 bar
   lastBarTime = t0;
   MqlRates r[];
   int got = CopyRates(_Symbol, PERIOD_M1, 1, 1, r);              // the bar that just closed
   if(got != 1 || r[0].time <= lastDone) return;
   Update(r[0]); lastDone = r[0].time;

   // time exit
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      if((TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME)) >= (long)MaxHoldBars * 60) trade.PositionClose(tk);
   }
   if(HavePosition()) return;

   int sig = Signal();
   if(sig == 0) return;
   double dist = StopATR * lastAtr;
   MqlTick tk; if(!SymbolInfoTick(_Symbol, tk)) return;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double entry = (sig > 0) ? tk.ask : tk.bid;
   double sl = NormalizeDouble(entry - sig * dist, digits);
   double tp = NormalizeDouble(entry + sig * TargetR * dist, digits);
   ENUM_ORDER_TYPE type = (sig > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double lots = LotsFor(type, entry, sl);
   if(lots <= 0.0) return;
   bool ok = (sig > 0) ? trade.Buy(lots, _Symbol, 0.0, sl, tp, "RevDet") : trade.Sell(lots, _Symbol, 0.0, sl, tp, "RevDet");
   if(ok) { nTrades++; PrintFormat("%s %s %.2f lots @ %.5f SL %.5f TP %.5f (ATR %.5f)", TimeToString(TimeCurrent()), sig > 0 ? "BUY" : "SELL", lots, entry, sl, tp, lastAtr); }
}

void OnDeinit(const int reason) { PrintFormat("ReversalDetectorEA: %d trades opened", nTrades); }
