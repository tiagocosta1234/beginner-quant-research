# ManualFVG (DAX) at 500 and 1,000 USD risk per trade, back-to-back MT5 broker evaluation cycles (2026-10-12)

MT5 tester, DAX+, M15, real ticks, 2025-10-01 .. 2026-09-30, 250 ms delay, 100,000 deposit (tester leverage 1:100; the DAX+ margin works out near 1:15). Evaluation cycles on the closed-trade daily P&L (counted profit capped at +2,000 a day, target +8,000, breach at a day <= -2,500 or balance <= -8,000); floating drawdown inside a day is not in the tester report, so intraday breaches can only be more frequent than shown. Script `manualfvg_cycles.py`; the EA got an optional margin cap (`InpMaxMarginPct`, default 0 = off, so the 500 USD run is unchanged).

| | 500 USD risk | 1,000 USD, no cap | 1,000 USD, margin cap 50% of free margin |
|---|---|---|---|
| What happened | normal | **stop-out on 2025-10-28** (10.4 lots of DAX on a 16.5-point stop), the tester stopped after 31 trades | 356 trades, normal |
| Net (12 months) | +10,668 (+10.7%) | -1,824 | +8,884 (+8.9%) |
| Win rate / PF | 37% / 1.10 | 32% / 0.91 | 37% / 1.04 |
| Worst trade / worst day | -798 / -1,074 | -1,057 / -2,018 | -1,601 / -2,153 |
| Days <= -2,000 | 0 | 2 | 12 |
| Realised max drawdown | 11,195 | 8,507 | **23,722** |
| Back-to-back evaluations | 3 passed (51, 21, 67 business days), 1 breached, 1 open | 0 passed, 1 open | **2 passed (48, 23 days), 1 breached**, 1 open |
| Every start day: pass / breach within 22 bd | 5.4% / 2.1% | 0.0% / 0.4% | **24.3% / 18.8%** |
| within 44 bd | 25.8% / 5.5% | 0.0% / 0.5% | **37.3% / 30.0%** |
Installed system for comparison (same replay, MT5 broker 12-month pool): 30.9% / 0.4% within 22 bd, 72.4% / 0.5% within 44 bd.
Months at 1,000 (capped): Oct -3.7k, Nov +12.4k, Dec +8.6k, Jan -2.7k, Feb -5.8k, Mar +9.7k, Apr -5.4k, May +7.7k, Jun +1.9k, Jul -6.2k, Aug +3.9k, Sep -11.6k.

## Reading
- 1,000 USD per trade is not usable as sized: the DAX stop is only 16-40 points, so 1,000 USD of risk is 4-10 lots (up to 1.5 million of notional) and the margin runs out (stop-out on the 28th of the first month). With a margin cap the trades run but the strategy then has a 23.7k drawdown and 12 days at -2,000 or worse; an test passes quickly when it goes right (48 and 23 business days) and the breach rate is about one in five within 22 days.
- Compared with 500 USD: more passes per start day (24% against 5% within 22 days) but 9 times the breach rate; compared with the installed system it passes less often (24% against 31% within 22 days) with 47 times the breach rate. Not an improvement.
