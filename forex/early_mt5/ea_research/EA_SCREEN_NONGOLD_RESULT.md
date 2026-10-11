# XS: non-gold screen of the 1,220 CodeBase EAs: result (2026-10-11)

Pre-registration `PREREG_EA_SCREEN_NONGOLD.md` (commit 6c31414), screen `ea_screen_nongold.py`, disqualifier and hold-out log
`EA_SCREEN_NONGOLD_DISQ.txt`, real-tick check `forex/early_mt5/ea_batch/xs_realtick_check.py` -> `EA_SCREEN_NONGOLD_REALTICK.txt`.

## Verdict: nothing survives real ticks; closed
- 606 non-gold EAs with deals; 30 pass the yearly screen (net > 0 every year 2022-25, monthly t >= 3.5, PF >= 1.2, >= 100 trades).
- 25 of the 30 are grids / martingales / never close a loser (max open volume up to 1,474x a single trade, PF ~1e12). The registered
  reality check is not meaningful for such smooth closed-P&L series (null median t +17): reported, not used.
- The 5 clean ones were all positive in 2026 on the MT5 broker M1-bar batch, and ALL lose on MT5 broker's real ticks for 2025-10-01..2026-09-30
  (default inputs, USD 100K):

| EA | MT5 broker M1 bars: trades / net / PF / win | MT5 broker real ticks: trades / net / PF / win |
|---|---|---|
| 39425 DeMarker Pending 2 (H1) | 1,609 / +693,640 / 2.28 / 96% | 644 / -4,780 / 0.96 / 46% |
| 17741 EMA (M5) | 901 / +639 / 1.16 / 80% | 897 / -830 / 0.81 / 76% |
| 68934 SilviosEAbest26 (H1) | 811 / +133,693 / 1.31 / 78% | 779 / -26,378 / 0.77 / 71% |
| 17390 BollTrade (M30) | 3,533 / +125,758 / 1.29 / 90% | 2,947 / -13,303 / 0.85 / 84% |
| 41732 LazyBot (H1) | 188 / +15 / 1.44 / 41% | 192 / -16 / 0.68 / 34% |

## Reading
The batch's M1-bar model invents fills (pending orders filled inside a bar, tight take-profits hit before the stop): exactly the
artifact behind the trader's 2026-10-05 rule "always real ticks". Every "steady every year" non-gold EA in the CodeBase was either a grid or
an artifact of that model. No EA.
