//+------------------------------------------------------------------+
//| ManualDay.mq5 -- one gold setup a day, 1:1, fixed USD risk          |
//| Rule (DAY2K-E object O2, forex/self_improving/day2k): at 16:35       |
//| server time take ONE trade on the chart symbol in the direction   |
//| of its last 24 hours (bid close of the 16:34 M1 bar today vs the  |
//| previous weekday); stop = target = InpK x ATR20 (mean daily       |
//| high-low of the previous 20 D1 bars) from the executable entry    |
//| price; lots sized so the stop costs InpRiskUSD. The tight stop    |
//| makes the day end at +risk or -risk in about 99% of cases; any    |
//| position still open at InpExitHour:InpExitMin is closed.          |
//| UNVALIDATED: the rule has no confirmed edge (DAY2K_E_RESULT.md).  |
//+------------------------------------------------------------------+
#property strict
#property version   "1.01"
#include <Trade\Trade.mqh>

input double InpRiskUSD    = 2000.0;   // USD lost at the stop (= USD won at the target)
input double InpK          = 0.15;     // stop = target distance in ATR20 units
input int    InpATRDays    = 20;       // daily bars in the ATR
input int    InpEntryHour  = 16;       // decision time (server): the 16:34 bar closes at 16:35
input int    InpEntryMin   = 35;
input int    InpEntryWindowMin = 5;    // entry allowed from decision+1 min to decision+1+window
input int    InpExitHour   = 21;       // forced close (server)
input int    InpExitMin    = 55;
input long   InpMagic      = 261020;
input double InpMinMarginLevel = 200.0; // lots are capped so the margin level stays >= this % even after a full stop (MT5 broker force-closes at 100%)
input bool   InpVerbose    = false;

CTrade g_trade;

datetime DayStart(datetime t) { return t - (t % 86400); }
int      Dow(datetime t)      { MqlDateTime s; TimeToStruct(t, s); return s.day_of_week; }

// bid close of the M1 bar that starts at 'bar' (exact, within 5 minutes before if missing); 0 if none
double CloseAt(datetime bar)
  {
   int sh = iBarShift(_Symbol, PERIOD_M1, bar, false);
   if(sh < 0) return 0.0;
   datetime bt = iTime(_Symbol, PERIOD_M1, sh);
   if(bt > bar || bar - bt > 300) return 0.0;
   return iClose(_Symbol, PERIOD_M1, sh);
  }

double ATR20()
  {
   double s = 0; int n = 0;
   for(int i = 1; i <= InpATRDays; i++)
     {
      double h = iHigh(_Symbol, PERIOD_D1, i), l = iLow(_Symbol, PERIOD_D1, i);
      if(h > 0 && l > 0) { s += h - l; n++; }
     }
   return (n >= 15) ? s / n : 0.0;
  }

bool TradedToday(datetime day0)
  {
   if(!HistorySelect(day0, TimeCurrent() + 60)) return false;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(d, DEAL_MAGIC) == InpMagic && HistoryDealGetString(d, DEAL_SYMBOL) == _Symbol && HistoryDealGetInteger(d, DEAL_ENTRY) == DEAL_ENTRY_IN) return true;
     }
   return false;
  }

bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol) return true;
     }
   return false;
  }

void CloseAll(const string why)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      double p = PositionGetDouble(POSITION_PROFIT);
      if(g_trade.PositionClose(t)) PrintFormat("[ManualDay] EXIT %s (%s) profit %.2f", _Symbol, why, p);
     }
  }

double LotsFor(double dist)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(ts <= 0 || tv <= 0 || dist <= 0) return 0.0;
   double perLot = dist / ts * tv, raw = InpRiskUSD / perLot;
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lots = MathFloor(raw / step) * step, mpl = 0.0, px = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, 1.0, px, mpl) && mpl > 0 && InpMinMarginLevel > 0)
     {
      double cap = ((AccountInfoDouble(ACCOUNT_EQUITY) - InpRiskUSD) / (InpMinMarginLevel / 100.0) - AccountInfoDouble(ACCOUNT_MARGIN)) / mpl;
      cap = MathFloor(cap / step) * step;
      if(cap < lots) { PrintFormat("[ManualDay] lots capped by margin: %.2f -> %.2f (risk %.0f instead of %.0f USD; margin %.0f per lot)", lots, cap, cap * perLot, InpRiskUSD, mpl); lots = cap; }
     }
   if(lots < vmin) return 0.0;
   return MathMin(lots, vmax);
  }

void Step()
  {
   datetime now = TimeCurrent(), day0 = DayStart(now); int dw = Dow(now);
   if(now >= day0 + InpExitHour * 3600 + InpExitMin * 60 && HasPosition()) CloseAll("day close");
   if(dw < 1 || dw > 5) return;
   datetime dec = day0 + InpEntryHour * 3600 + InpEntryMin * 60;           // decision time
   if(now < dec + 60 || now > dec + 60 + InpEntryWindowMin * 60) return;   // entry at the bar that opens one minute after the decision
   if(HasPosition() || TradedToday(day0)) return;
   datetime prev = day0 - 86400; while(Dow(prev) == 0 || Dow(prev) == 6) prev -= 86400;
   double pNow = CloseAt(dec - 60), pPrev = CloseAt(prev + (dec - day0) - 60), atr = ATR20();
   if(pNow <= 0 || pPrev <= 0 || atr <= 0 || pNow == pPrev)
     {
      if(InpVerbose) PrintFormat("[ManualDay] %s no setup (pNow %.2f pPrev %.2f atr %.2f)", TimeToString(day0, TIME_DATE), pNow, pPrev, atr);
      return;
     }
   double dist = InpK * atr, lots = LotsFor(dist); int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(lots <= 0) { PrintFormat("[ManualDay] size below the minimum (dist %.2f)", dist); return; }
   bool buy = pNow > pPrev; bool ok;
   if(buy)
     {
      double a = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      ok = g_trade.Buy(lots, _Symbol, 0, NormalizeDouble(a - dist, dg), NormalizeDouble(a + dist, dg), "ManualDay long");
     }
   else
     {
      double b = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      ok = g_trade.Sell(lots, _Symbol, 0, NormalizeDouble(b + dist, dg), NormalizeDouble(b - dist, dg), "ManualDay short");
     }
   PrintFormat("[ManualDay] %s %s %.2f lots, dist %.2f (atr %.2f), 24h %.2f -> %.2f, %s", TimeToString(day0, TIME_DATE), buy ? "BUY" : "SELL", lots, dist, atr, pPrev, pNow, ok ? "sent" : "FAILED " + IntegerToString(g_trade.ResultRetcode()));
  }

int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic); g_trade.SetDeviationInPoints(100); EventSetTimer(1);
   PrintFormat("[ManualDay] started on %s: risk %.0f USD, stop = target %.2f x ATR%d, decision %02d:%02d server, close %02d:%02d, magic %I64d (UNVALIDATED rule)", _Symbol, InpRiskUSD, InpK, InpATRDays, InpEntryHour, InpEntryMin, InpExitHour, InpExitMin, InpMagic);
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int r) { EventKillTimer(); }
void OnTick()  { Step(); }
void OnTimer() { Step(); }
