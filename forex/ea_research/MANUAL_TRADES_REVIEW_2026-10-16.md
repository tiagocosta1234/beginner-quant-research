# the trader's Notion "Manual backtest": what separates winning from losing setups (2026-10-16 19:02 local, local clock, second PC)

the trader: "open notion and try to learn what im doing wrong on my trades, detect what divides a losing setup from a winning
setup". Read-only via Notion's own API from the logged-in browser tab (no edits). Descriptive review, not a registered
trial. Scripts: `data\scratch\manual_trades\gold_practice.py` (+ inline analysis), trades cached in
`data\scratch\manual_trades\gold_practice.parquet`.

## The table (115 rows)
| | wins | losses | other | win rate |
|---|---|---|---|---|
| NSDQ (56 rows) | 23 | 33 | - | 41% |
| XAU (59 rows) | 17 | 39 | 2 BE, 1 blank | 29% |
By group: XAU long London 6/22, XAU short London 11/17; NSDQ long London 11/9, long New York 5/11, short New York 6/9,
short London 1/4. **Only 36 rows have a date** (all XAU); the 56 NSDQ rows and 23 XAU rows have only a chart image and
cannot be matched to market data.

## The 36 dated rows
- Aug-Sep 2026, breakout (box 08:00-08:30 local, first break, SL other side, TP 2R): 19 trades, 4 W / 15 L, -6.9 R.
- Nov-Dec 2023, "setup A" fade (TP the other edge, about +0.54 R, SL about -1 R): 13 trades, 7 W / 6 L, -2.2 R.
  At +0.54 / -1 the fade needs a win rate above ~65% to break even; 54% was logged. Fades at the London box were
  negative on 42-44 of 46 MT5 broker in the 15-16 Oct rounds.
- May 2023 FX Replay examples: 2 trades -2 R, 2 no-trade days (`MANUAL_EXAMPLES.md`).

## Execution check
The breakout rule rebuilt on MT5 broker M1 bid/ask (zero-spread minutes fixed) reproduces **19 of 19** Aug-Sep rows: same
side, same win/loss, same trigger minute. The losses are the rule's, not execution errors. The Notion "Tendência 5d"
labels decode as tr5 = 5-day move in the trade's direction / ATR20: Contra <= -0.59, A favor >= +0.59, else Neutra.

## In the 19 trades vs on 1,222 gold trades 2022-26 (same rule, every day)
| feature | the trader's 19 trades | 2022-24 R/trade (t) | 2025 | 2026 |
|---|---|---|---|---|
| against the 5-day trend | 0 W / 8 L | +0.064 (0.75) | +0.013 | +0.091 |
| neutral trend | 1 W / 4 L | -0.027 | +0.074 | -0.309 (-2.07) |
| with the 5-day trend | 3 W / 3 L | +0.064 (0.72) | +0.226 (1.53) | -0.034 |
| trigger 0-1 min after 08:30 | 1 W / 6 L | -0.115 (-1.45) | +0.069 | +0.081 |
| trigger 2-8 min | | +0.099 | -0.106 | -0.481 (-3.03) |
| trigger > 8 min | | +0.141 (1.67) | +0.273 (1.95) | +0.019 |
| all trades | 4 W / 15 L | +0.035 (36% win) | +0.112 (38%) | -0.088 (32%) |
- **Trading against the trend is not what lost**: on history it is as good as trading with it. The 0/8 was luck.
- **The late trigger (> 8 min after 08:30) is the only feature positive in all three periods**, weak (t 1.7 / 2.0 / 0.1).
  It is already filter F2 of the registered forward test LDN3F (`PREREG_LDN3F.md`, from 2026-10-19).
- No other split separates winners from losers reliably; the rule itself is about zero (+0.03 R a trade 2022-26,
  -0.09 in 2026), with a 12-loss longest streak and a -35.7 R worst drawdown. 15 losses in 19 is within normal luck for
  a 33-38% win rate (expected sum about -1.7 R, standard deviation about 6 R).

## In the account's environment (from 95,472, MT5 broker rules, start 19 Oct; bootstrap | replay, pass% / breach%)
| | $250 a trade, 22 Dec | $250, 30 Jun 2027 | $500, 22 Dec | $500, 30 Jun 2027 |
|---|---|---|---|---|
| as traded (every first break) | 0 / 12 \| 0 / 17 | 1.9 / 38 \| 1.3 / 43 | 1.6 / 45 \| 4.0 / 47 | 20 / 65 \| 18 / 72 |
| only triggers > 8 min | 0 / 0 \| 0 / 0 | 0.1 / 6 \| 0 / 0 | 0 / 14 \| 0 / 15 | 14 / 29 \| 12 / 29 |
With a 0.03 R real-tick haircut the "as traded" rule is +0.000 R a trade and breaches more (e.g. $500 by 30 Jun 2027:
15 / 72-79). The buffer is $3,472 = 14 R at $250, 7 R at $500, against a 12-loss streak. None of this passes in time;
the late-trigger subset has the best pass/breach ratio but it is selected after the fact and is in its forward test.

## What the trader is doing wrong (plainly)
1. Nothing in the execution: the rule was followed exactly.
2. The setup has no reliable edge on MT5 broker (2026 negative), so no filter seen in 19 trades can rescue it; the
   patterns visible in small samples (against-trend, first-minute) disappear on 1,222 trades.
3. The fade variant needs a win rate it does not have.
4. 79 of 115 rows have no date, so most of the log cannot be checked; write the date and time on every row.
5. On this account, $500 a trade breaches before it passes; $250 never passes in time.

## Addendum: the Nasdaq trades (dated from the screenshots, `MANUAL_NQ_DATES.csv`)
54 of 56 NSDQ rows dated by matching each chart's box levels to MT5 broker's NSDQ boxes: 23 trades 15 May - 1 Jun 2026, 31 trades
7 Sep - 6 Oct 2023 (FX Replay's feed is ~15-25 points below MT5 broker after the Sep-2023 futures roll); rows 49 and 53 unresolved.
Rule rebuilt from the charts (`data\scratch\manual_trades\nq_practice.py`): 30-min box (London 08:00-08:30 local / New York
09:30-10:00 NY), first break, SL at the box midpoint, TP 1:1, exit 17:00 local / 16:00 NY. It reproduces 45 of 54 win/loss
results (his stop is not always exactly at the midpoint); he took the first break on 46 of 54 (8 reversals / other side).

**His 54 trades:** 21 W / 33 L (39%; 1:1 needs > 50%), about -12 R. Sep-Oct 2023: 10/31, 24 of 31 long while NSDQ fell
15,324 -> 14,648. May-Jun 2026: 11/23. In the sample: London 48% vs New York 31%; trigger > 8 min 53% vs 32-33%; big box 29%.

**On 2,419 trades 2022-26 (same rule):** -0.056 / -0.046 / -0.105 R a trade (2022-24 / 2025 / 2026). Consistent in every
period: London loses (-0.13 / -0.06 / -0.16, t -3.7 in 2022-24) and New York is about zero (+0.02 / -0.03 / -0.05) - the
opposite of his sample; triggers in the first minute lose (-0.10 / -0.04 / -0.27); boxes in the smallest third lose
(-0.11 / -0.12 / -0.23); shorts lose more than longs (-0.09 / -0.07 / -0.19 vs -0.03 each period, the index drift). The
5-day trend separates nothing. Removing all the consistent losers in hindsight (New York only, trigger > 1 min, box not in
the smallest third) leaves +0.079 / -0.022 / +0.036 R (t 1.6 / -0.3 / 0.4): about zero, chosen after the fact.

**Account environment (from 95,472, MT5 broker rules, start 19 Oct; pass% / breach%):** as traded (both sessions, every first
break) $250 a trade: 22 Dec 0 / 21-30, 30 Jun 2027 0 / 83; $500: 22 Dec 0 / 68-70, 30 Jun 2027 0-1.4 / 94 (worse with a
0.03 R tick haircut). The hindsight subset at $500: 30 Jun 2027 0-2.8 / 21-36. No version passes; the as-traded rule
breaches with near certainty within nine months.

**Nasdaq verdict:** as with gold, the losses are the rule's. What the history says to stop doing: London-session Nasdaq
breakouts, immediate first-minute triggers, small boxes, and fighting the trend direction of the market (2023's longs in a
falling month). Doing all of that still leaves no edge.
