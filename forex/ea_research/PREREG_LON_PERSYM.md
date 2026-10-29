# PREREG_LON_PERSYM - one London-open breakout strategy per symbol, chosen and validated separately (written 2026-10-15 local clock 21:22, before the selection is run)
the trader: "(original wording omitted)" (a London-open breakout strategy for each symbol on its own).

## Candidates per symbol (72, from ORB11_ENTRY, London session only)
30-minute box 08:00-08:30 London; 6 triggers (touch, 5- / 15-minute close outside, still outside after 15 minutes, retest limit, fade of the failed break) x 6 filters (none, daily trend, box >= 40 spreads, squeeze, box direction, trend + wide) x 2 exits (1:1, hold to 17:00 London); MT5 broker bid/ask, spreads paid; trades table data/si_ledgers/ORB11_ENTRY.parquet (truncation-tested).

## Procedure (per symbol, 46 symbols)
1. Choose the rule with the highest mean R in DEV 2022-24 (at least 50 DEV trades). Nothing else is looked at for the choice.
2. Keep it only if its mean is > 0 in VAL 2025 AND in 2026 (2026 is already open for the breakout family: a non-clean look, stated).
3. Out of time: every kept rule is run on HistData 2020-01-02..2021-11-30 (bid + MT5 broker's median London-session spread 2025-10..2026-10; orb11_entry.market with the HistData loader of orb11_entry_oot; DOW has no HistData series; DAX only to 2020-06-12). Gate per symbol: mean > 0, t >= the one-sided 5% Bonferroni bar over the number of kept rules, both years positive.
4. A symbol that passes 3 still needs MT5 broker real ticks (2025-10..2026-10) and an MT5 broker-rules simulation before it is called a candidate.

## Honest prior
In ORB11_ENTRY the per-cell walk-forward over both sessions lost (DEV +0.230 -> 2025 -0.089 -> 2026 -0.140; 9 of 92 positive in both). Expected: 3-6 symbols kept by chance, 0-1 passing out of time.
