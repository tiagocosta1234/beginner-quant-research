# PREREG DAY2K-G - the strongest-trend market of the day, traded with the trend, wide 1:1 (written 2026-10-14, the trader: "you're missing something, you know what I'm asking is possible")

Rounds A-F tested direction rules inside fixed markets and a per-market trend rule (exploratory: gold 58-63% wins at 1.5-2 ATR, the other 14 markets about 50%). Gold's number was the 2023-25 gold trend. What was never tested: an ADAPTIVE selector that each day moves to whichever market is trending most strongly, so the exposure is to "a trend, wherever it is" and not to gold.

## Rule (all parameters fixed here)
Universe (39 liquid markets): the 28 FX pairs, XAUUSD, XAGUSD, SP, NSDQ, DOW, DAX, NIKKEI, BRENT, WTI, BTCUSD, ETHUSD. Each business day at 10:05 server (decision uses bars started <= 10:04), score of a market = (price now - price L trading days earlier) / ATR20, L in {20, 60, 120}; markets whose median spread/ATR20 exceeds 2% are excluded (altcoins, some exotics). The market with the largest |score| is traded in the direction of its score: entry at the open of the 10:06 bar on the executable side, stop = target = k x ATR20 from the fill, k in {1.0, 1.5, 2.0}, HELD UNTIL ONE IS HIT (no 21:55 close, gap fills at the real price; searched up to 250 days). Two execution modes: (a) ONE AT A TIME (the next setup is picked on the first day after the previous trade closed; this is the MT5 broker mode), (b) EVERY DAY (a new setup each day, overlapping trades, used only for per-trade statistics because overlapping positions can stack a day's loss past MT5 broker's -2,500).

## Trials (9) and acceptance
3 lookbacks x 3 k = 9 cells (mode a for the MT5 broker cycle, mode b for the per-trade statistics). Bonferroni for 9, one-sided 5%: DEV (2021-12..2024) mean R > 0 with block-t >= 2.45 on the daily-start (mode b) series AND win share of resolved trades above the always-trend-in-gold-only yardstick of the same L,k is NOT required (reported); VAL 2025: mean R > 0 and block-t >= 1.65. Power note: mode a gives only about 25-50 trades a year, so the one-at-a-time statistics are weak; mode b's 800+ overlapping trades (heavily autocorrelated, 5-day blocks understate the dependence of week-long holds) are the better test and block-t uses blocks of 20 days for this round.
HOLD (2026) is opened once, only for a survivor.

## Gates
Positive control (oracle side) > +0.3 R; placebo worlds: the same selector run on trend scores computed from a day-shuffled copy of each market's series (seeds 151-153) must give 0 survivors; truncation test of the score/selection on random days.

## Reported regardless
Win share of resolved trades ("P of a +2,000 trade"), trades per year, the market picked (share by class and by year), holding days (median, 90th percentile), worst gap loss, MT5 broker rolling-start cycles for mode a at risk 2,000 and 900, and the gold-only yardstick.

## Dry-run record (2026-10-14, before any cell P&L)
34 of 39 markets pass the 2% spread/ATR filter (dropped: CADCHF, NZDCHF, XAGUSD, BRENT, ETHUSD). The selector rotates: pick share FX 40-51%, indices 21-34%, metals 10-11%, crypto 12-13%, energy 2-6% (most picked: BTCUSD, XAUUSD, USDJPY, DAX). Days with a pick: 944-1,044 of 1,066. 97.2-97.3% of trades resolve within 250 days (the rest are 2025 entries cut off by the data end; they are excluded). Truncation test 90/90 identical. No cell, trial count, threshold or period changed.

## Calibration result and amendment A1 (2026-10-14, before any real cell was read)
First calibration run: positive control +0.96..+0.99 R, but placebo worlds 152 and 153 each produced one survivor (best DEV t 3.01 / 2.52, VAL t 4.77 / 3.48). The gate says nothing is read in that case. Diagnosis: shuffling the days of the scores keeps the pick mix (mostly up-trending BTCUSD, XAUUSD, USDJPY, long) and that mix earns the 2023-25 drift, so the placebo is not a null for timing skill (lesson (b): every test needs the drift yardstick next to it). A1: S1 additionally requires a permutation p <= 0.0055 (0.05 / 9) for the DEV mean R against 400 shuffles that permute the picks (market and side) among the days that have a pick, i.e. the same market/side mix with the timing destroyed; the null mean R is reported next to every cell. The placebo gate is re-run with this rule. Nothing else changes.
