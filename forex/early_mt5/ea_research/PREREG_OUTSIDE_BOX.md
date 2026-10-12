# Pre-registration: out-of-the-box round (written 2026-10-12, before any of these tests was run)

the trader: "(original wording omitted)". Price-only pattern rules and video strategies are exhausted (about 25 families). This round looks at the STRUCTURE of the problem. Ideas registered here, run one at a time and appended to LEDGER.csv; each has a fixed rule and a pass bar.

## EC: equity-curve timing (when to START an attempt)
Idea (from the Matio video, "losing streaks cluster"): the installed system's chance of passing depends on the regime it is in; if its own recent P&L predicts the next 22 / 44 business days, then starting an account when the system is "on form" raises the pass probability, at no cost in edge.
Series: the installed system (pair x1.5 + ManualDip 500, guard 1,500, CPI news flat), FT 2022-26 (1,225 days) and MT5 broker 12-month pools, as `replay_check.py`. Empirical replay of a FRESH account from EVERY start day (rules as `eval_cycles_2026_final.py`).
Rule (one, fixed): ON if the system's realised P&L over the previous 40 business days (strictly before the start day) is > 0, else OFF. Statistic: pass rate within 22 and 44 business days, ON vs OFF, and the breach rate.
Accept if, in the FT pool, pass22 and pass44 are both at least 1.3 times higher when ON than when OFF, AND the same sign holds in the MT5 broker pool, AND ON has at least 150 start days. Caveat declared: overlapping 22-day windows mean about 40 independent windows in FT and about 11 in MT5 broker, so a difference is a hint, not proof; no change to the live account follows from this test alone.
## WB: WTI / Brent spread reversion (market neutral)
MT5 broker WTI+ and BRENT+ (M1 bid/ask 2021-12 on, swap-free), daily prices at 15:59 New York (bid-open), z-score of ln(BRENT/WTI) over the previous 60 trading days, enter at |z| >= 2 (short the rich, long the cheap, dollar neutral, ask/bid on all four fills), exit at |z| <= 0.5 or 20 days; per-trade bp of one leg's notional (the GS machinery of `new_eas.py`, `more_eas.pair_trades`). Accept: DEV 2022-24 >= 15 trades, mean >= +25 bp, t >= 1.65; VAL 2025 mean > 0; HOLD 2026 mean > 0 (one look).
## IN: volatility compression breakout (inside day / NR7) on gold and the four indices
Daily bars at the 15:59 New York cut (MT5 broker M1). Signal day = the day whose range is the narrowest of the last 7 days (NR7); the next trading day, a buy-stop 0.0 above the signal day's high / sell-stop at its low (first touch decides, exit at that day's close). Accept per market group (gold; indices): DEV 2022-24 >= 40 trades, mean >= +20 bp net of the spread, t >= 1.65; VAL > 0; HOLD > 0.
## PH: pre-holiday and option-expiration effects on the US indices
PH1 long SP/NSDQ/DOW from the close before a US market holiday to the next close (about 9 a year); PH2 long from the close before the monthly option-expiration Friday week's Monday... fixed as: long on the Thursday close, sell at the Friday close of each third-Friday-of-month (one trade a month). DEV 2022-24, VAL 2025, HOLD 2026; accept mean >= +10 bp net, t >= 1.65 (pooled indices, day-averaged), VAL > 0, HOLD > 0.

## Honest prior
EC: moderate that the sign is right (the pair lives off gold regimes), low that the sample can show it. WB: low to moderate (the oil leg was the only positive lead earlier, WTI and Brent are one market). IN: low. PH: low and tiny (few trades). A pass anywhere is a candidate leg or a timing rule for a future account, not a way to pass in 30 days; the 30-day target needs Sharpe about 6.
