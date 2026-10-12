# Pre-registration: systematic setup scan over every MT5 broker symbol (family SC) (written 2026-10-12, before the scan was run)

the trader: "(original wording omitted)". A scan of 46 MT5 broker symbols with a fixed library of classic daily setups, with false-discovery control, so that "setups found" means "setups that survive": 12 variants x 46 symbols = 552 tests, about 28 false positives expected at p < 0.05 by luck alone.

## Data and execution
MT5 broker M1 bid/ask (`data_mt5`, 2021-12 .. 2026-10-02, swap-free), 46 symbols (indices, metals, energy, crypto, 28 FX pairs). Daily price = 15:59 New York bid-open (ask-open for entries of longs), per symbol. Long: entry at the ask, exit at the bid; short: entry at the bid, exit at the ask (spread paid, no other cost). One position per symbol and variant at a time; per-trade return in bp.
## Library (12 variants, fixed, no tuning; each long AND short)
- RSI2F: Wilder RSI(2) < 10 with close > SMA(200) (long) / RSI(2) > 90 with close < SMA(200) (short); exit close > SMA(5) or RSI(2) > 70 (long) / close < SMA(5) or RSI(2) < 30 (short), or 5 days.
- RSI2: the same without the SMA(200) filter.
- DON: close above the highest close of the previous 20 days (long) / below the lowest (short); exit at the opposite 10-day extreme (long exits below the lowest close of 10 days, short above the highest).
- STK: three consecutive lower closes -> long, three higher -> short, hold 3 days (mean-reversion streak).
- BB: close below SMA(20) - 2 sd -> long, above SMA(20) + 2 sd -> short; exit when the close crosses the SMA(20) or after 10 days.
- MOM: every Friday close, go with the sign of the previous 20-day return for 5 trading days.
## Windows and the rule that makes a "setup"
DEV = entries 2022-01-01 .. 2024-12-31; VAL = 2025; HOLD-OUT = 2026-01-01 .. 2026-09-30 (one look, survivors only).
A (variant, side, symbol) test is a SURVIVOR only if ALL of: DEV >= 30 trades; DEV mean >= +15 bp per trade after the spread; DEV one-sided p-value (mean > 0, Student t) passes Benjamini-Hochberg across all 552 tests at q = 0.10; VAL >= 8 trades with mean > 0; and then HOLD mean > 0.
Survivors are the only "setups" reported; their current state (signal today or not) is read from the live terminal's market data, read-only. Everything else is noise by this rule and is not shown as a setup.
Reported as well: how many tests are nominally positive in DEV and in VAL (against what luck gives), the top 10 by DEV t, and the mean DEV t.
## Honest prior
Low: we ran about 25 families before this and the only confirmed daily pattern is the dip buying in US indices (RSI2F long on SP, NSDQ, DOW). The scan should rediscover that one and little else; a fully clean result (a few survivors, all in equity indices) would confirm the survival rule works. No order is placed and nothing goes live from this round.
