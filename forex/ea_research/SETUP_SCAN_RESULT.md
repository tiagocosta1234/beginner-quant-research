# SC result: systematic setup scan over 46 MT5 broker symbols (2026-10-12)

Pre-registration: PREREG_SETUP_SCAN.md. 12 variants (RSI2F, RSI2, DON, STK, BB, MOM, long and short) x 46 symbols = 552 tests (277 with at least 30 DEV trades), MT5 broker bid/ask, spread paid, daily 15:59 New York.

## Verdict: 0 survivors (Benjamini-Hochberg q = 0.10 on DEV passes 0 of 277 eligible tests).
- Nominal winners: 38 tests with one-sided p < 0.05 in DEV against about 14 expected by luck; 264 of 552 positive in DEV; 309 of 541 positive in VAL (57%). A weak overall excess, nothing individually significant after the multiple-testing correction.
- Top DEV t: SP short RSI2F (3 trades), EURCHF BB short (14), DAX RSI2F long (20, VAL -79 bp), NSDQ RSI2F long (21 trades, +94 bp, VAL +75, HOLD +107; below the 30-trade bar).
- Pooled by variant, side and asset class (trade-weighted, DEV / VAL / HOLD): the only groups positive in all three windows are LONG setups on equity indices: RSI2F long +39 / +40 / +58 bp; RSI2 long +30 / +87 / +78; STK long +19 / +67 / +53; BB long +13 / +19 / +27; DON long +96 / +181 / +56. That is the dip-buying edge again plus the 2022-26 index drift (the indices doubled), not a new pattern. FX shows nothing (all pooled means within a few bp of zero), crypto swings widely and loses on average, metals and energy are small and unstable.

## State today (12 Oct close, live read-only): no index dip setup is active
RSI(2): SP 64.6, NSDQ 22.6 (-0.70% today), DOW 90.1, DAX 74.1, NIKKEI 27.7, ASX 89.3 (below its SMA200); none under 10, no 3-down streak, none below the lower Bollinger band. ASX closed above its 20-day high (DON long, not validated per symbol).
