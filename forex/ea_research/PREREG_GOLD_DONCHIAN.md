# Pre-registration: a gold "convex" second leg (H1 Donchian breakout, tight ATR stop, trailing exit) next to SDB and the 5-minute EA

Written 2026-10-09 ~10:10 local, BEFORE any simulation of this rule. the trader asked for "an EA of a different nature, gold only, with a smaller stop, a second leg with low correlation". Own-EA programme, family G (gold). Trials already logged: 29 of 40; this round uses 6 (35).

## Why this design (the hypothesis, written first)
The pair's two losing days that mattered (2026-04-14, 04-20) were an SDB stop-out plus three losers of the 5-minute EA on the same trend day. The 5-minute EA is concave (win rate 67%, payoff 0.94: many small wins, losses a little larger, stacking into trends); SDB is a 1:1 breakout swing (stop = target = 1.9% of price, about 80 USD). A leg that is CONVEX (win rate 35-40%, payoff 2-3, a small stop of about 1.5 ATR(H1) = about 15 USD, no fixed target, trailing exit) wins on exactly the strong-trend days on which the concave leg bleeds, so its daily P&L should correlate weakly or negatively with the pair on bad days. The rule is the plainest trend-follower there is (a 24-hour channel breakout with an ATR stop and a chandelier trail), not a tuned one; gold's 2022-26 uptrend flatters any trend follower, which is why only the gate below (correlation, behaviour on the pair's worst days, portfolio effect) and not the leg's own profit decides.

## Data, clock, costs
MT5 broker's own gold M1 bars `forex/data_mt5/XAUUSD_M1_rates.parquet` (bid OHLC + bar spread, 2021-12-01 .. 2026-10-08), server clock; H1 bars built from M1 on server hours. Costs as in the other rounds: buy at the ask (bid + the bar's spread), sell at the bid, 0.15 USD/oz slippage on every market entry and every stop exit, both-levels-in-one-bar = stop first, swap-free account (swap zero). Stop checks run on the M1 bars (finer than the H1 decision clock); entries and trailing updates on H1 closes. P&L in USD per ounce and in R (R = the initial stop distance).

## Rule G1 (primary)
At every H1 close, if flat: LONG if the close is above the highest high of the previous 24 H1 bars, SHORT if it is below the lowest low of the previous 24 H1 bars; entry at the next H1 bar's open. Initial stop = entry -/+ 1.5 x ATR(14, H1) measured at the signal bar. Trailing stop (updated at each H1 close, from the next bar on): highest close since entry - 2.5 x ATR for a long, lowest close since entry + 2.5 x ATR for a short, never loosened; the effective stop is the tighter of the initial and the trailing level. No fixed target. Time exit at the open after 72 H1 bars. One position at a time; after an exit a new entry needs a NEW 24-bar extreme (the same condition, on a later bar).

## Periods (fixed now)
DEV 2022-01-01 .. 2024-12-31, VAL 2025-01-01 .. 2025-12-31, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, only for G1 after DEV and VAL), Dec 2021 = warm-up.

## Trials (6; only G1 can be accepted)
G1 primary. G2 lookback 48 bars. G3 lookback 12 bars. G4 stop 1.0 ATR and trail 2.0 ATR. G5 long signals only. G6 entries only on signals whose entry bar opens between 03:00 and 19:00 server time.

## Acceptance of G1 (all must hold)
1. DEV: >= 150 trades, expectancy > 0 after costs, profit factor >= 1.10, daily-P&L t >= 2.0 (days without a trade count as zero).
2. VAL: expectancy > 0, profit factor >= 1.05.
3. Diversification gate on 2022-2025 (DEV + VAL): correlation of the leg's daily P&L with the pair's daily P&L (SDB 0.12 + 5-minute EA 0.04, MT5 broker-based real-tick series, swap-free, as in `mt5_mc_config.py`) <= 0.20, AND the leg's mean daily P&L on the pair's 10 worst days is >= 0.
4. HOLD-OUT 2026 (one look): expectancy > 0.
5. Portfolio fit (only if 1-4 hold): pair + leg at risk weights 0.25 / 0.5 / 1.0 of the pair's, MT5 broker Pro rules with our 2% caps, 2022-26 starts: P(pass within 62 business days) up by >= 5 points with breach <= 5% and not worse than the pair alone (sum of the daily lows used as the pessimistic combined low).
Only after all five an MQL5 EA (fixed lots, hard stop on every order, IOC fills, own magic, AccountGuard-compatible), validated against the Python trades in the MT5 broker portable tester; nothing near the live account without the trader's go.

## Honest prior
Moderate that a gold trend follower is positive in 2022-26 (gold trended), low that it adds to the pair: SDB is already a breakout rule, so correlation with SDB may be high even if the 5-minute EA is complemented; and MT5 broker's daily line punishes a leg that stops out several times on a choppy day (4-6 stops of 15 USD at the lots needed to matter is a real cost).
