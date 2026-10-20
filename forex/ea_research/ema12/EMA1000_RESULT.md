# EMA1000 result: 1,000 variations of the 12 EMA rule on all 46 MT5 broker (run 20 Oct 2026 10:11-10:15, main PC, local clock)

Pre-registration `PREREG_EMA1000.md` (sha256 2fd54d7d4aef3e541e68441b6ecad195a142ef51b7f39d35aa1d279a39b2f589, 10:08). Engine `ema1000.py`; engine checks `EMA1000_DRYRUN_OUTPUT.txt` (reproduces `MANUALRULE_TRIALS.csv` exactly for XAUUSD / NSDQ x London / NY, truncation test 72 trades 0 mismatches); output `EMA1000_OUTPUT.txt`, `EMA1000_TRIALS.csv`, `EMA1000_MARKETS.csv`; follow-up `ema1000_followup.py`, `EMA1000_FOLLOWUP_OUTPUT.txt`, `EMA1000_FOLLOWUP.csv`. Data: MT5 broker M1 bid / ask, DEV 2022-24, VAL 2025; nothing after 2025-12-31 was ever loaded (the sealed 2026 days are untouched).

## Result: 0 candidates of 1,000, and not even a near miss
- All 1,000 variants lose money in development: share with DEV mean R > 0 is 0%; median DEV mean R -0.180 a trade, the best variant -0.076; the day-clustered t runs from -64.9 to -9.5 (the bar was +3.72). 2025 (VAL) is the same: median -0.174.
- Every one of the 46 markets has a negative median DEV mean R over the 1,000 variants (least negative EURJPY -0.034, USDJPY -0.039, GBPUSD -0.041, NSDQ -0.049, XAUUSD -0.063; crypto -0.59 to -0.77). No market is positive.
- Nothing varies much with the choices: median DEV mean R by timeframe 1 / 3 / 5 min -0.234 / -0.178 / -0.150, by target ATR1 -0.245, SW -0.227, K2 -0.176, K3 -0.142, K1 -0.131, by stop multiple 1.5 / 2 / 3 -0.222 / -0.196 / -0.135, London -0.201, NY -0.158.

## Why: the drag, not the signal (descriptive follow-up, not a bar)
- The SAME entries with a random side (the mirror trade) lose -0.183 R a trade (median over variants; range -0.445 to -0.069). That is the spread and structure drag of a 0.33-0.67 R target on 1-minute distances: the rule loses money mainly because every trade pays the spread against a small target, not because its direction is bad.
- The rule's direction skill (excess over a random side, day-clustered) is +0.0023 R at the median (+0.0032 in 2025), with 66% of the variants slightly above zero (the variants are strongly correlated); the skill t runs from -1.76 to +2.36, none reaches 2.58, let alone 3.72. The registered top 5 by DEV t have skill t 1.0-1.5. A real but tiny directional tilt cannot be excluded; it is about 60 times smaller than the drag.

## What it means
- A mechanical version of the rule has no edge on any of the 46 markets, on any of 1,000 reasonable variants of the rule; with the earlier 44 trials on gold and Nasdaq (0 of 44) the mechanical question is closed (2,044 mechanical trials of this family on MT5 broker prices, 0 passes).
- It does not test the trader's discretion (which candle he picks, whether the day looks right): the blind replay does. January's blind result (excess +0.115 R, P 0.25, n 20) is the only evidence on that.
- The drag is the useful number: on gold the 0.48 spread is about 0.06 R a trade at the January stops (median 8.1 points) and about 0.11 R at the April-May stops (median 4.3 points); any discretionary edge has to beat that before it matters on MT5 broker.
- No candidate, so the 2026 hold-out is NOT opened and nothing from this family goes anywhere near the account.
