# BRK100C result - another 100 ideas (CME microstructure, MT5 broker liquidity-weighted prices, minute lead-lag, untested calendars, adaptive rules, untested indicators): 0 pass

Run 2026-10-18 22:33 (local clock, second PC PC-2). Pre-registration `PREREG_BRK100C.md` (SHA-256
b2e2e89089172fd0f8b3196af3e3c5a6537bd7c65569072619e18d55fc4d045d recorded 21:59:18 in `C:\work\scratch\brk100c_prereg.sha256`, before
any code and before any BRK100B result; no commits on 18 Oct), engine `brk100c.py` (BRK100B's helpers). Three code-vs-pre-registration
mismatches were found by reading the code before any run and fixed (N011 used the ES share instead of the NQ share, N022 measured from
01:05 server instead of 01:05 local, the Amihud history skipped days without a next-day session). The first dry run (4 worker
processes, 22:2x) was stopped by Claude Code for low memory; the trader chose a restart with 2 workers. Dry run `BRK100C_DRYRUN.txt`
(truncation identical on EURUSD, XAUUSD and NSDQ for trades and helper states; 12 hand checks), output `BRK100C_OUTPUT.txt`, table
`BRK100C_SUMMARY.csv`, 100 ledger rows. 526,176 trades on the 38 non-crypto markets.
Bars as BRK100B: DEV 2022-24 n >= 100, day-clustered t >= 3.29, >= 2 of 3 years positive, information t >= 2.0; VAL 2025 t >= 1.65.

## Verdict: 0 of 100; the 2026 hold-out stays sealed
- DEV t-values (99 with enough trades; N036 had one): mean -1.37, SD 1.66; 19 positive; 1 above t 1.65 (5 expected by luck); none
  above 3.29; no DEV + VAL passer.

| group | tests | DEV t mean | positive | t > 1.65 | mean R |
|---|---|---|---|---|---|
| A CME microstructure (research) | 15 | -0.63 | 5 | 0 | -0.06 |
| B MT5 broker liquidity (MT5-native) | 11 | -1.50 | 0 | 0 | -0.09 |
| C minute lead-lag (MT5-native) | 12 | -1.96 | 1 | 0 | -0.04 |
| D calendar (scheduled) | 14 | -0.69 | 7 | 1 | +0.01 |
| E adaptive rules | 5 | -3.04 | 0 | 0 | -0.08 |
| F + G + H untested MAs / oscillators / candlesticks | 34 | -1.75 | 3 | 0 | -0.05 |
| I cross-market factors | 3 | -0.45 | 1 | 0 | -0.02 |
| J CME attention for other markets | 3 | +0.26 | 2 | 0 | +0.04 |
| K extensions / event load | 3 | -0.98 | 0 | 0 | -0.20 |

## The closest (all fail)
| idea | DEV 2022-24 | years | VAL 2025 | why it fails |
|---|---|---|---|---|
| N048 earnings season (USI NB follow, days 8-35 of Jan / Apr / Jul / Oct) | +0.253 R (t 2.46), n 556, info t 2.32 | +0.35 / +0.21 / +0.24 | +0.149 (t 0.87) | DEV t below 3.29 |
| N004 Kyle lambda high (CME box follow) | +0.086 (t 1.25), info t 2.16 | +0.11 / +0.01 / +0.12 | -0.094 | reversed in 2025 |
| N093 index-factor residual (USI NB) | +0.101 (t 1.06) | +0.13 / +0.04 / +0.14 | -0.119 | reversed in 2025 |
| N010 NQ volume-share surge (NSDQ NB) | +0.308 (t 1.05) | -0.01 / +0.28 / +0.50 | +0.168 | n 22 |
| N041 Diwali week (XAUUSD LB long) | +0.654 (t 1.11) | +1.02 / +0.56 / -1.00 | -0.001 | n 8 |

## What it showed
- **CME microstructure (A):** VPIN, Kyle's lambda, Amihud and signed volume carry no usable direction: high-VPIN boxes neither follow
  (+0.021) nor fade (-0.197, t -2.8); the volume shares and the roll week are small samples around zero.
- **MT5 broker liquidity (B):** MT5 broker's spreads are nearly constant, so the 1 / spread "liquidity-weighted price" equals the TWAP on most
  markets (the LWAP-over-TWAP rule N020 fired 107 times in three years); the TWAP rules lose like BRK100B's VWAP rules (reclaim
  -0.059 t -4.1, 2-sigma break -0.077 t -3.2). Spread-persistence fades -0.153 (t -3.5).
- **Data finding (affects BRK100B too):** spread shocks are frequent in MT5 broker's 2022-24 minute spreads and rare in 2025-26 (BRK100B M001:
  2,273 DEV trades, 148 in 2025, 49 in 2026; here N024-N026 the same), and the persistence condition is the reverse. The recorded spread
  field appears to change character after 2024, so spread-shock ideas cannot be validated out of sample on these files.
- **Minute lead-lag (C):** no follower lags its leader enough to pay the spread on a 15-minute hold: XAUUSD -> AUDUSD -0.064 (t -4.7),
  XAUUSD -> XAGUSD -0.154 (t -4.7), USDJPY -> NIKKEI -0.077 (t -4.6), DAX -> EURUSD -0.016; Brent -> WTI never fired (the two move
  together minute by minute).
- **Calendar (D):** thin days punish fades: UK bank holidays -0.405 (t -4.0), year-end weeks -0.414 (t -5.8); moon phases, DST
  weeks, the Fed blackout, the half-year switch and payroll weeks are about zero or negative; earnings-season NB follow is the one
  consistent positive (above), short of the bar.
- **Adaptive (E):** the Turtle "only after a loser" filter -0.042 (anti-Turtle -0.093); choosing follow or fade by the last 20 trades
  -0.102 (t -5.4): breakout outcomes carry no memory a filter can use.
- **Untested indicators (F, G, H):** t mean -1.75; the H1 oscillators lose the spread (SMI -0.075 t -4.2, intraday momentum index
  -0.094 t -5.2, Chande dynamic momentum index -0.100 t -5.9); the 13 moving-average crosses -0.014 .. -0.108; candlesticks about zero.

## Account view (2022-25, from 95,472, MT5 broker rules)
N048 at $250 (NSDQ): 0.1% pass by 30 Jun 2027, 0% breach; N004 at $250: 0.2% pass / 16% breach; the rest 0.0%. Nothing is usable.

## Tally
18 Oct: GN1-GN13 40 + BRK50B 50 + BRK30 30 + BRK100 100 + BRK26 26 + BRK100B 100 + BRK100C 100 = **446 pre-registered tests, 0 passes**.
Every kind of information the second PC holds has now been tried (prices, spreads, CME volume and prices, Yahoo daily series, event /
FOMC / auction / holiday calendars). What is left needs the main PC: the MT5 economic calendar with forecasts (surprise-conditioned
rules) and MT5 broker tick volume / ticks.
