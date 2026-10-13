# N: US index overnight (15:55 ET -> 09:35 ET) on MT5 broker: result (2026-10-10, local local clock)

Pre-registration `PREREG_OVERNIGHT.md` (commit fc17e38, before any statistic), script `overnight.py`, output `OVERNIGHT_DEV_OUTPUT.txt`, ledger family overnight. Hold-out NOT opened.

## Verdict: both trials fail acceptance 1 (DEV t +0.99 and +0.94) and are barely positive in 2025; closed
| | P(night > 0) | mean net bp/night | sd | worst night |
|---|---|---|---|---|
| 2022 (equal-weight SP/NSDQ/DOW) | 49.2% | -2.8 | 92 | -255 bp |
| 2023 | 54.8% | +3.4 | 51 | -156 |
| 2024 | 58.9% | +7.8 | 51 | -166 |
| 2025 | 54.9% | +0.4 | 68 | -320 |
N1 (every Mon-Thu night) DEV +2.76 bp, t +0.99; VAL +0.39 bp. N2 (only after a down session) DEV +1.81 bp per calendar night (+3.66 when active), t +0.94; VAL +0.34. The night's gross at mids is +3.1 bp on average and the spread costs 0.9 bp. The Friday->Monday window (not traded) is up 61.3% of the time, mean +4.1 bp, but its worst is -372 bp.

## What it means for "raise the risk to pass fast"
The overnight is a coin weighted about 55/45 with a tiny average win against large swings: +2.8 bp of mean against 50-90 bp of sd per night (Sharpe per night about 0.03-0.05). To make the 500 USD a day the 70%-this-month spec needs, the position would have to be about 1.8 million USD of index notional (18 times the account). Its typical night would then swing about 12,000 USD and its worst historical night would lose about 46,000-58,000 USD. MT5 broker's daily line is 2,500 and a gap cannot be stopped. At MT5 broker's 1%-per-idea size (worst night <= 1,000 USD, i.e. about 31,000-39,000 USD notional) the edge is worth about 1 USD a day. The overnight premium is real over decades and visible in 2023-24, but it is far too small relative to its risk to speed up a test, and in 2022 and 2025 it was absent.
