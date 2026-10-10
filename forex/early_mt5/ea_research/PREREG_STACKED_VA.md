# Pre-registration: Griff's "stacked value areas" mean reversion (youtube D9rx8-cXmSs), formalised, on 28 FX pairs + 6 indices (family G, two trials)

Written 2026-10-10 (time = the commit adding this file), BEFORE any simulation. the trader: "(original wording omitted)". Video rules [06:32-10:55]: wait for >= 3 value areas of PREVIOUS days stacked; price breaks out of them "with weakness"; enter on a momentum-shift candle back the other way; stop 2 pips beyond the extreme; target the PREVIOUS day's low (shorts) / high (longs); never fade a strong trend. Claimed about 70% wins; the two examples shown (1:3.84, 1:4.49) were found in replay.

## Data and profile
MT5 broker M1 bid/ask, 2021-12 .. 2026-09, server days, Monday-Friday. Markets: the 28 FX pairs and SP, NSDQ, DOW, DAX, NIKKEI, ASX. MT5 broker M1 bars carry no volume, so the profile is the time profile (TPO): every minute adds 1 to the bin of its mid close; bin = 1 bp of the previous day's close. POC = the bin with most minutes (lowest price on ties); value area = grow from the POC, adding the larger adjacent side, until >= 70% of the day's minutes.

## Rule (two trials; G2 = G1 without the trend filter)
- Stacked on day D: the value areas of D-1, D-2, D-3 overlap (max of the three VALs < min of the three VAHs) AND the spread of their three POCs <= 0.5 x the mean width of the three value areas. Zone = [lowest VAL, highest VAH] of the three.
- Signal on an H1 bar of D closing between 02:00 and 21:00 server: SHORT if the bar's high > zone top, its close < zone top (back inside) and its upper wick >= 50% of its range; LONG mirrored at the zone bottom with the lower wick. First signal of the day only, one trade per market per day.
- Entry: the open of the minute 2 minutes after the signal bar's close (sell at the bid / buy at the ask). Stop: 2 bp beyond the signal bar's extreme. Target: the previous day's (D-1) low for a short, high for a long; skip if the target is not at least 1 x the stop distance beyond the entry.
- Exit: stop or target checked on M1 bid/ask (both in one minute = stop), else at 22:55 server. Result in R (R = entry-to-stop distance at execution).
- G1 trend filter (the video's "no reversal against a strong trend"): with r5 = close(D-1)/close(D-6) - 1 and A = mean daily high-low range of the last 20 days as a fraction of price, the trade is allowed if |r5| < A (range-bound) or sign(r5) equals the trade's direction.

## Periods and acceptance (Bonferroni, two trials)
DEV 2022-01 .. 2024-12, VAL 2025, HOLD-OUT 2026-01 .. 2026-09 (one look). Pooled over the 34 markets:
1. DEV: >= 200 trades, mean R > 0, t (per trade) >= 2.24.
2. VAL: mean R > 0.
3. HOLD-OUT: mean R > 0.
Also reported: win rate (against the claimed 70%), mean R by market class, trades per month, and what the rule would add to the test at 1% risk per trade.

## Honest prior
About 10%. It is a value-area rejection, the family that gave this repo's best near-miss on NQ (Rounds 184-186, OOS P 0.972), but the "weakness" and "momentum candle" parts are discretionary in the video and the win rate claimed with 1:4 targets is not credible.

## Dry-run (2026-10-10, no P&L; `STACKED_VA_DRYRUN.txt`)
AUDUSD / EURUSD / SP: 1,251-1,258 days; value area = 52% / 52% / 43% of the day range on average, POC inside it; days whose 3 previous value areas overlap 431 / 425 / 232; days with a full signal (overlap + POC spread + rejection bar + wick) 30 / 45 / 7 before the target-distance filter. Expected pooled sample about 1,000 signals over 34 markets.
