# PREREG BRK_TWOWAY - can stacked confluences predict "break" vs "bounce" at the box edge well enough to trade BOTH ways?

Registered 2026-10-16 20:18 local (local clock, second PC PC-2), before any P&L or label of these events was computed.
the trader: "add more confluences to increase the prediction rate of a breakout or bounce (we can trade both)". Earlier ML rounds
(BRK_META, BRK_ML2) only ranked breakouts and FOLLOWED the best; they learned where the cost is (narrow boxes), which hurts a
fade as much as a follow. This round asks the direction question alone: a symmetric bracket makes follow and fade mirror
images, so only "which side wins" can pay, and the spread is paid on every trade.

## Events and trades
- Boxes: LDN 08:00-08:30 local (touch window 08:30-11:00, exit 17:00 local); NY 09:30-10:00 New York (window 10:00-12:00,
  exit 16:00 New York). Box high / low from bid highs / lows (as `brk_confirm.py`). 38 non-crypto MT5 broker, MT5 broker M1 bid/ask
  2021-12..2026-10-16, zero-spread minutes repaired as in `PREREG_BRK_PATTERNS.md`.
- Event: the FIRST minute in the window whose ask high >= box high (up-touch) or bid low <= box low (down-touch); a minute
  touching both sides is skipped. side = +1 for an up-touch, -1 for a down-touch. One event per market, box and day.
- Decision at the close of the touch minute; entry at the next minute's open at market. Bracket half-width u = box width W.
  FOLLOW: position `side`, SL entry - side*W, TP entry + side*W. FADE: position `-side`, SL entry + side*W, TP entry - side*W.
  Long fills / exits on the correct side of the quote (buy at ask, sell at bid), `brk_patterns.walk` rules (gap = open beyond
  the level; same-minute SL + TP = SL; on the entry minute only the SL counts); exit at the session end if neither is hit.
  R = net P&L / W. Label y = 1 if FOLLOW reached its TP first (else 0).

## Confluences (22, all known at the close of the touch minute; daily values from completed earlier days only)
box_atr (W / ATR20 of daily mid ranges), box_spread (W / median box spread), delay (minutes from box end to the touch),
app5 / app30 (side x mid move over the last 5 / 30 minutes, in W), day_move (side x move from the 00:00 local mid, in ATR),
pdx (side x distance from the level to the previous day's high (up) / low (down), in ATR), beyond_pd (level beyond that
extreme, 0/1), asia (side x distance from the level to the 01:00-07:00 local range extreme, in ATR), tr5 (side x 5-day
change / ATR), tr20 (side x (previous close - SMA20) / ATR), gap (side x (box mid - previous close) / ATR), box_in_pd (box mid
inside the previous day's range, 0..1), range_so_far (today's range before the touch / ATR), sp_touch (touch-minute spread /
median box spread), volreg (ATR20 / ATR100), weekday, box (LDN/NY), class (fx / index / metal / energy, one-hot), yday
(yesterday's label of the same box and market, -1 if none), touch_body (side x close-open of the touch minute / W).

## Trials (4) = 2 models x 2 boxes
- **COUNT** (hand-built confluence count): on the training data each feature is cut at its training terciles; a feature
  votes +1 / -1 when the event is in the tercile whose follow-win rate is highest / lowest, only if that tercile spread is
  >= 2 percentage points; score = sum of votes.
- **GBM**: sklearn HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=200,
  l2_regularization=1.0, random_state=0), all 22 features.
- Trading rule (both models): FOLLOW when the score / probability is >= the 80th percentile of the training predictions,
  FADE when it is <= the 20th percentile, otherwise no trade.
- Fitting: DEV is scored by cross-fitting by year (fit on two DEV years, predict the third); VAL and HOLD by a fit on all DEV.

## Periods
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for a trial passing DEV and VAL).

## Yardsticks and placebo (not trials)
always-FOLLOW, always-FADE on the same events; shuffled-label placebo: the whole pipeline re-run with y permuted within
market x year (3 seeds), the real DEV result must beat all three.

## Acceptance
- DEV (cross-fitted): n >= 1,000 trades; mean net R > 0 with day-clustered t >= 2.5 (Bonferroni, 4 trials); beats each
  placebo; positive in >= 2 of the 3 DEV years.
- VAL: mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment (standing rule): for a full passer, replay on NSDQ + XAUUSD at $250 a trade from 95,472 (MT5 broker rules, as in
  `usdjpy_account_env.py`); usable only if P(pass) > P(breach) by 30 Jun 2027. The NSDQ + XAUUSD account view is printed for
  every trial.

## Descriptive ("prediction rate", what the trader asked)
Out-of-fold AUC on DEV and on VAL; follow-win rate in the predicted-continuation group and fade-win rate in the
predicted-bounce group vs the base rates; win rate by prediction decile; feature importance (GBM permutation importance on DEV).

## Dry run (no labels, no P&L)
`python -m forex.ea_research.brk_twoway --dry-run`: event counts by box, period and market class; feature coverage and ranges;
truncation causality test of the FEATURES (cut the data at random times on 3 markets: every event and feature value before
the cut day identical); hand check of 3 events.

## Honest prior
About 5%. Every single-feature test on these boxes was within noise; combining weak features lifted breakouts from -0.06 to
~0 (BRK_META). The new part is the fade leg, which only helps if bounces are predictable from information other than cost.

## Window
New family (two-way level classifier): 4 of 40 variants.

## Amendments
1. (2026-10-16 ~20:21, after the dry run, before any label or P&L was looked at) The truncation test failed on XAUUSD by one
   event (cut on Sunday 2024-12-01, after the early-closing Thanksgiving Friday): the engine required a minute AFTER the
   session end to accept a session, which a truncated series cannot have. A session now counts as finished when its end is
   before the data end (the cut, or the last minute + 1 min). Feature values were identical; this only affects the last
   session before a data end. Same check exists in `brk_confirm.py` (only its final session can be affected; its results
   stand). Also noted: in COUNT, a missing feature value (volreg 3%) falls into the top tercile bin of `np.digitize`; kept as is.
