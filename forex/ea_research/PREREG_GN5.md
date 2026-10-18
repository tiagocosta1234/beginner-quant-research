# PREREG GN5 - out-of-time check of the Nasdaq overnight-range breakout (GN3 O1) on 2020-21 NQ futures

Registered 2026-10-18 11:12 local (local clock, second PC PC-2), before any 2020-21 number of this rule was computed.
the trader: "keep going until you find an ultra profitable breakout idea". GN3's O1 (`GN3_RESULT.md`) is the best breakout level
found on gold / Nasdaq so far: +0.102 R a trade in 2022-24 (t 1.61, below its 2.24 bar), +0.127 R over random entries, both
sides positive, fading by year, +0.061 in 2025. It FAILED its registered DEV bar. As with the USDJPY London breakout (picked
in-sample, then confirmed on 2020-21 HistData, `PRESAMPLE_RESULT.md`), the honest next step for a near-miss is one test on years
it has never touched; this round is that test and nothing else (no variants, no tuning).

## Data (new to this rule)
Databento CME NQ continuous 1-minute futures bars (`futures/data/databento/futures_NQ.F_1m.parquet`, trade prices,
UTC, 2019-10..2026-09). OOT period: New York dates 2020-01-02..2021-12-31 (the trader's 2020-onward rule; nothing from 2019 is used).
The continuous series switches contract at 00:00 UTC on the Monday of each quarterly expiry week (the only intraday jumps above
0.4% in 2020-25 sit there): those Mondays are excluded (their overnight range spans two contracts).
MT5 broker cost model: bid = the futures trade price, ask = bid + 1.67 points (the MT5 broker NSDQ median spread 2022-26), so longs fill at the
ask and exit at the bid and shorts the reverse, exactly as the MT5 broker engine does with real bid/ask.

## Rule (O1, unchanged, code copied from `gn3.py`)
Overnight range = high / low from 18:00 New York of the previous calendar day (Sunday for Monday) to 09:30 New York (>= 80% of
the minutes present); one-cancels-other stop orders 09:30-12:00 New York (buy when the ask reaches the range high, sell when
the bid reaches the range low; both in one minute = no trade); stop at the range midpoint; exit 15:55 New York. Control =
5 random-side entries a day in the same window with the same stop distance and exit.

## Engine checks (in the dry run, before the OOT number)
1. Identity: the copied engine on MT5 broker NSDQ 2022-01-03..2026-10-16 reproduces `gn3.trades("O1")` trade for trade.
2. Port: the same engine on NQ futures 2022-24 (with the cost model above) is compared with the MT5 broker O1 DEV result
   (+0.102 R, n 708): mean R per trade within +/-0.06 R and daily R correlated >= 0.6 on common days, else the port is
   investigated before the OOT result is read.

## Acceptance (one test)
OOT 2020-21: mean net R > 0 with day-clustered t >= 1.65 (one-sided 5%) AND both 2020 and 2021 means > 0. Information over the
random control reported. If it passes, O1 earns its single look at the MT5 broker 2026 hold-out (2026-01-01..2026-10-16: mean > 0,
t >= 1.65) and the account replay from 95,472; if it fails, O1 is closed and is not re-tuned.

## Honest prior
About 20%. The year-by-year fade (+0.19 in 2022, +0.12, 0.00, +0.06) fits the knowledge-base fact that breakout information
was a 2022 phenomenon; 2020-21 were high-volatility trend years for Nasdaq, which favours breakouts, so a pass there would
still leave the 2023-26 decay unexplained.

## Running count
GN1 5 + GN2 4 + GN3 4 + GN4 4 + GN5 1 = 18 of 40 variants in this research window.

## Amendments
(none yet)
