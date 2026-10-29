# PREREG_SWAPFREE_DRIFT - a long-only risk-balanced book that uses MT5 broker's swap-free terms (written 2026-10-15 15:07 local clock, before any P&L)

## Why this family (not another breakout)
On a normal CFD account a long index or gold position pays about 5-7% a year in financing; that eats most of the equity / gold premium. Account <acct> pays NO swap and NO commission: verified again today from the deal history (gold positions held 5 nights incl. a weekend and Nasdaq positions held overnight: swap 0.00, commission 0.00, fee 0.00), although the symbol specs list swaps (XAUUSD+ -65 points long, indices -3%/year): the swap-free account does not apply them. The only cost of holding is the spread paid when buying. Earlier panels found that only drift made money (confluence panel K: long-only non-FX book net Sharpe +1.56 walk-forward 2023-25). This round turns that into a fully specified, causal book and tests whether it is profitable after MT5 broker's real costs and whether it helps the account.

## Book and rules (fixed now)
- Markets (5): SP, NSDQ, DAX, NIKKEI, XAUUSD (MT5 broker M1 bid/ask; P&L converted to USD: DAX with EURUSD, NIKKEI with USDJPY, daily mid).
- Decision time: Monday 18:00 server (first trading day of the week if Monday is closed), never in server hours 23 or 0. Signals use daily closes marked at the last bar at or before 22:55 server of each earlier day (bid), so only data known before the decision is used.
- Weights: inverse 60-day volatility of daily close-to-close returns, w_i = (1/vol_i) / sum_j(1/vol_j), gross notional = G (sizing parameter, chosen only in the MT5 broker simulation).
- Execution: buys at the ask, sells at the bid of the 18:00 bar's open; positions marked at the bid. No-trade band: a market is re-traded only if |target - current| > 25% of target or its signal flipped.
- Daily P&L: change of the bid-marked value from the last bar of one server day to the last bar of the next. Day low for the MT5 broker breach rule: the sum over markets of the worst bid (bl) of each market inside the server day (conservative: lows of different markets are added as if simultaneous).

## Variants (4 trials, Bonferroni over 4)
- D1 always long, inverse-vol weights.
- D2 D1 + trend: a market is held only if its last daily close > its 200-day simple moving average (else flat).
- D3 D1 + book volatility target: G scaled each week so the ex-ante book volatility (60-day covariance) is constant, leverage capped at 2x the D1 average gross.
- D4 D2 + D3.

## Data and periods
- MT5 broker M1 bid/ask 2021-12-01..2026-10-14. Signal warm-up (60-day vol, 200-day SMA) uses HistData daily closes before 2021-12, ratio-spliced to MT5 broker at 2021-12-01 (signals only, never P&L).
- DEV 2022-01-03..2024-12-31, VAL 2025-01-01..2025-12-31.
- OOT 2020-01-01..2021-11-30 on HistData M1 (bid only; ask = bid + MT5 broker's median spread of that market at the same server hour in 2022-24; HistData times are EST without DST, converted to UTC then to Europe/Athens = server clock). D2/D4 can only trade from about mid-October 2020 (200-day warm-up inside 2020; pre-2020 data needs the trader's OK, not asked): lost power stated, not hidden.
- HOLD 2026-01-01..2026-10-14 (MT5 broker): looked at ONCE, only for variants that pass development.

## Acceptance (all required)
1. Daily t of net USD P&L over DEV+VAL (2022-01-03..2025-12-31) >= 2.24 (one-sided 5% / 4 trials).
2. Mean daily P&L > 0 separately in DEV, VAL and OOT.
3. HOLD mean > 0 (one look).
4. Real-tick check: the same book on MT5 broker real ticks (data/ticks, server clock, 300 ms latency, execution at the first tick at or after 18:00:00.3) for 2025-10-01..2026-10-14 earns at least 75% of the M1 engine's P&L over the same days.
5. Account usefulness (reported, not an edge test): from today (balance 97,708.08, counted -2,291.92, MT5 broker rules: day gain counted up to +2,000, breach at an intraday -2,500 or equity <= 92,000, pass at counted +8,000), block bootstrap (5-day blocks) over 2020-25 days, P(pass) and P(breach) by 22 Dec, 31 Mar 2027 and 30 Jun 2027 at gross G = 50k, 100k, 150k, 200k USD; daily correlation with the gold EA pair (clean_boot_lib.series("MT5 broker", 1.2)) reported.

## Dry run (before any P&L)
Counts of decision days, trades and data coverage per market and period; truncation test (cut all data after a decision time, recompute that decision's weights and signals: must be identical); hand check of one decision (weights by hand from the printed vols).

## Amendment 1 (2026-10-15, dry run, before any P&L)
- The HistData GRXEUR file is not the DAX after 2020-06-12: it drops from ~11,700 to ~3,200 on 2020-06-15 and then moves like the Euro Stoxx 50 (levels 2,950-4,250). The other HistData series (SPX, NSX, JPX, XAU, EURUSD, USDJPY) have no level break (largest daily moves = March 2020).
- OOT is therefore run on FOUR markets (SP, NSDQ, NIKKEI, XAUUSD), weights re-normalised; the lost diversification is stated.
- For the MT5 broker periods the DAX SIGNAL warm-up (Jan-Sep 2022 decisions only) uses the HistData series from 2020-06-15 onward (a European-index proxy) ratio-spliced to MT5 broker's DAX at 2021-12-01; DAX P&L always comes from MT5 broker data.
- MT5 broker M1 data end on 2026-10-02, so HOLD is 2026-01-01..2026-10-02. The real-tick check stays 2025-10-01..2026-10-14 (ticks go to 10-13).

## Honest prior
The premium is real over decades, but 2020-26 contains a 2022 bear market (Nasdaq -33%) and a gold boom; with a Sharpe near 1 a four-year t is about 2, so bar 1 may fail even if the drift is real. Prior that a variant passes 1-4: about 30%. Even if it passes, a drift book is beta, not a forecasting edge: it can lose for a year (2022) and its pass speed is slow. It is judged on the numbers above, not on its story.
