# PREREG_LONDON12_APLUS: the A+ London 12 EMA plan as a mechanical backtest on gold futures

Written Mon 26 Oct 2026 ~09:4x local (local clock), BEFORE any result of this test was computed. the trader: "now backtest again the london 12 ema".
Not a rerun of EMA12 / MANUALRULE / EMA1000 (MT5 broker CFD prices 2022-25, all failed): this is the frozen demo plan `A_PLUS_SETUP_AND_DEMO_PLAN_DRAFT.md`
(25 Oct) on gold FUTURES (Databento GC 1-minute, 2019-09 to 2026-09), micro costs, with 1:1 and 1.5R targets, 2026 included.

## Rules (London time; one trade a day at most)
- **Bias (plan item 2):** the 15m candle 07:45-08:00: close above its 15m EMA12 AND that EMA12 above its value 4 candles earlier = LONG; both below = SHORT; else no trade.
- **Trigger (item 3):** the first 1-minute candle that opens 07:59-08:14 (closes 08:00-08:15) with: close on the bias side of the 1m EMA12, the previous candle's close on the other side (a fresh cross), body > the bigger wick. Entry = its close.
- **Stop (item 4, mechanical stand-in for "beyond an OB / FVG"):** beyond the extreme of the trigger candle and the 5 candles before it, plus 1 tick (0.1). Risk must be 1.5 to 6.0 points, else no trade.
- **Target:** T1 = 1.0R (the demo card), T15 = 1.5R (the plan's minimum RR). Stop first on a tie; flat at the open of the first bar at or after 16:00.
- **News (item 6):** not applied (no historical red-folder list for 07:45-09:00; US releases fall at 13:30). Stated, not hidden.
- **Confluence (need 2 of 3 for A+):** C1 zone = the trigger candle trades into a 1m fair-value gap of the bias direction formed in the previous 60 minutes; C2 sweep = between 07:00 and the trigger, price took out the Asia range (00:00-07:00) low (long) / high (short); C3 = the 07:00-08:00 1h candle closed on the bias side of the 1h EMA12.
- **Costs:** 0.32 points round trip a trade (1 tick slippage per side + USD 1.20 commission per MGC), net R = gross R - 0.32 / risk.

## Tests (one run, one look)
- **Primary (two, alpha 0.025 each):** A+ (hard rules + 2 of 3 confluence) with T1, and with T15.
- **Pass iff:** mean net R > 0 AND random-side P <= 0.025 (20,000 draws flipping each trade to its mirror by coin) AND mean > 0 in at least 5 of the 7 years 2020-2026 AND n >= 100.
- **Secondary (no bar):** "B" = hard rules only (no confluence) at T1 / T15, so we see what the confluence filter adds; 2026 alone; trades a year; win rate.

## Honest prior
Every earlier mechanical 12 EMA form lost at real costs; the demo plan's filters are standard but untuned. Expected: no pass. A pass justifies the forward demo, not a purchase.

## Amendment 1 (26 Oct 2026 ~10:0x, after the first run; BUG FIX ONLY, rules unchanged)
The first run counted 0 A+ days because `c1 + c2 + c3` mixed numpy and Python booleans (numpy adds booleans as OR, so the sum was never 2). Fixed with int(). The B (hard-only) results of the first run were seen before the fix; they do not change. The confluence definitions, bars and targets are unchanged. Disclosed: C1 as written fires on 91% of trades (loose: any same-direction 1m gap of the last 60 minutes that the trigger candle spans) and C2 on 1%, so A+ is in practice C1 + C3.
