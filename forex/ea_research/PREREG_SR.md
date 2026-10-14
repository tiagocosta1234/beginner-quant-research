# Pre-registration SR: objective support/resistance trading on every MT5 broker symbol (written 2026-10-14 before any run)
the trader: "master support and resistance trading". S/R is discretionary by nature; this registers one objective, causal definition and tests whether levels carry any edge against random levels. Related closed work: round-number levels (DAY2K-F), prior-day pivots (EURUSD-LAB2 family P): both nothing.

## Levels (causal)
Bars: MT5 broker M1 bid/ask resampled to H1, H2, H4 (server-day aligned); mid OHLC for levels and signals, ATR14 (EWM alpha 1/14 of the true range). A swing high at bar i: mid high[i] > the highs of the 5 previous bars and >= the highs of the next 5 bars; swing low mirrored. It is CONFIRMED (usable) only at bar i+5, so nothing uses the future. Each confirmed swing becomes a level at its price; a new swing within z = 0.25 x ATR of an existing level merges into it (touches + 1, price = running mean). Levels expire after 300 bars. strength = touches (s1: every level; s2: levels with at least 2 touches).
## Signals (known at the close of bar j; one per mode per bar, nearest level within 3 ATR)
- BOUNCE (fade the level): short if high[j] >= L - z, close[j] < L - z and close[j-1] < L (rejection at a level above); long if low[j] <= L + z, close[j] > L + z and close[j-1] > L.
- BREAKOUT (follow the level): long if close[j] > L + z and close[j-1] <= L + z; short if close[j] < L - z and close[j-1] >= L - z.
## Trade
Entry at the open of bar j+1 (ask long, bid short) unless its open is in server hours 23/0 (then no trade); stop = L beyond the far side by z + 0.5 x ATR (bounce: stop on the other side of the level; breakout: stop back through the level), minimum 0.5 ATR from entry; target 1.5 R; time exit at the open of bar j+25; stop first if both are touched in a bar; real bid/ask for fills and for the touch tests; one position per cell at a time; no commission, no swap. Result in R (stop distance = 1 R).
## Grid and gates
46 symbols x 3 timeframes x 2 modes x 2 strengths = 552 cells. DEV 2021-12-01..2023-12-31, VAL 2024-01-01..2025-12-31, HOLD 2026 (sealed for this family; never loaded without `--hold`).
CANDIDATE: DEV mean R >= +0.05, t >= 4.0 (5% / 552), n >= 100; VAL mean > 0, t >= 1.65, n >= 50; DEV t above the 95th percentile of the placebo maximum over all cells (10 draws; placebo = every new level's price moved by a random uniform offset of -2..+2 ATR, i.e. arbitrary levels instead of swing levels). Reported: share of cells positive in both periods, bounce vs breakout by timeframe, long-only drift yardstick (each trade's mean R from a random entry with the same stops is not computed; the by-side table is).
A candidate is audited (year, hour, spread, latency) before the 2026 hold-out is opened once. No variants after the run.
Honest prior: under 3% that a swing-level rule survives; if bounce and breakout both lose by about the spread, levels carry no information.
