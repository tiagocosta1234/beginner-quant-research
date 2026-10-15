# PREREG_MONTHEND_FX - month-end FX rebalancing flows into the London 16:00 fix (written 2026-10-15, committed 15:18 local clock, before any P&L)

## Idea and source
Melvin & Prins (2015, "Equity hedging and exchange rates at the London 4 p.m. fix"): foreign investors who hedge their US equity holdings re-balance the hedge at month-end. If US equities outperformed foreign equities over the month, hedgers sell USD into the WM/Reuters 16:00 London fix on the last trading day (and the reverse). A flow, not a chart pattern: information the breakout family did not use. Only MT5-native data (MT5 broker index CFDs and FX quotes), so it is deployable. Not tested before in this repo (the gold-fix round GOLD_FIX tested the LBMA gold auctions, not FX month-end).

## Rules (fixed now)
- Day: the last weekday of each calendar month with MT5 broker bars at the decision time (calendar known in advance: causal).
- London 14:00 = server 16:00 and London 16:00 = server 18:00 all year (London and Athens change DST on the same dates).
- Equity signal at the decision minute: month return of SP (US) minus month return of the foreign index, each in local currency, from the previous month's last-day decision minute to this one (last bar at or before the minute). Foreign: DAX for EUR, NIKKEI for JPY, ASX for AUD; the basket = mean of the three.
- Trade: sell USD if US outperformed (signal > 0), buy USD if it under-performed. Enter at the ask/bid of the bar opening at the entry minute, exit at the bid/ask of the bar opening at server 18:00 (= the fix minute). One trade per pair per month. P&L in bp of price, net of MT5 broker's real spread.
- Never in server hours 23 or 0 (all times are 10:00-20:00 server).

## Cells (4 trials, Bonferroni over 4)
- M1 basket signal, 7 USD pairs (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD), entry London 14:00 (server 16:00), exit London 16:00.
- M2 as M1, entry London 08:00 (server 10:00).
- M3 pair-specific signal for EURUSD (DAX), USDJPY (NIKKEI), AUDUSD (ASX), entry London 14:00.
- M4 post-fix reversal: the OPPOSITE of M1's direction from London 16:00 (server 18:00) to London 18:00 (server 20:00).
- Control (not a trial): M1's rule on business day 10 of each month (signal from the previous month-end to that day): the effect should be specific to month-end.

## Data and periods
- MT5 broker M1 bid/ask; months 2022-01..2024-12 DEV (36 months), 2025 VAL (12), HOLD 2026-01..2026-09 (9 months, one look for a cell that passes).
- OOT 2020-01..2021-11 on HistData M1 (bid; ask = bid + MT5 broker's median spread of the pair at the same server hour in 2022-24; EST without DST -> UTC -> Europe/Athens). Foreign indices on HistData: JPXJPY (Nikkei), AUXAUD (ASX), and for Europe the GRXEUR file, which is the DAX until 2020-06-12 and a Euro Stoxx-like index afterwards (PREREG_SWAPFREE_DRIFT Amendment 1): used as the European signal, stated as a proxy.
- Real-tick check of any passer: MT5 broker ticks 2025-10..2026-09 (first tick at or after the entry minute + 300 ms).

## Acceptance (all required)
1. t of the MONTHLY mean (all pairs of the cell averaged within a month = one cluster) over DEV+VAL (48 months) >= 2.40 (one-sided 5% over 4 trials, Student t with 47 df).
2. Monthly mean > 0 separately in DEV, VAL and OOT.
3. HOLD monthly mean > 0 (one look).
4. Real-tick mean per trade >= 75% of the M1 mean on the same months, or within 1 bp.
5. Reported, not an edge bar: the cell's placebo control, by year, by pair, and the account effect (12 trading days a year; as an add-on next to the gold EA pair).

## Dry run
Counts of month-end days and trades per period, the signal for two months computed by hand, truncation test (cut data after each decision minute: signal identical).

## Honest prior
The effect was published on 1997-2010 data and is well known to banks (fix reform in 2015 widened the fix window to 5 minutes). Post-publication decay is likely. Prior that a cell passes 1-4: about 15%. With 12 trades a year it cannot change the pass speed of the account by itself.

## Amendment 1 (dry run, before any P&L)
The signal minute is the earlier of London 14:00 and the cell's entry minute, so M2 (entry London 08:00) measures the month's equity returns at London 08:00 of both month-ends (the first draft measured them at 14:00, after M2's entry: look-ahead). M1, M3, M4 unchanged.
