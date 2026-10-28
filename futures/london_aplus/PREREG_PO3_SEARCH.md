# PREREG_PO3_SEARCH: one finite search for a profitable version of the claude.pine PO3 (Asia range sweep + reclaim) rule

Written Tue 2026-10-27 (local clock) BEFORE any result. the trader: "do a more profitable indicator". Base rate first: the default rule loses -0.21 R (GC, 1 STDV target) and
-0.23 to -0.28 R at every fixed target, 0 of 8 years positive; 10 earlier families and a 147-cell filter search found nothing. Likely outcome: NOT SHOWN.
This is the one allowed search; it ends today. If it fails the PO3 rule is closed.

## Rule family (GC, NQ, ES, SI; Databento 1m -> 5m, 2019-06..2026-09, costs GC 0.32, SI 0.025, NQ 1.1, ES 0.74 points round trip)
Asia range 20:00-00:00 New York; min range 0.15 x prior daily ATR14; sweep of one side; reclaim = a 5m close back inside the range = entry at that close, opposite the
sweep; sweep depth <= 1 x range; flat at 11:00 New York (exit at that bar's open); stop first when a bar touches both. Cells (32):
sweep window ends 05:00 or 08:00 | stop = sweep extreme + 2 ticks, or + 0.25 x range further | target 0.5 / 1 / 1.5 / 2 R | trend filter off, or trade only with the
prior daily close vs its SMA20 (long if above).

## Protocol
DEV = trading days before 2023-01-01, TEST = 2023-01-01 on. Pick the cell with the best pooled DEV mean net R (>= 200 DEV trades). Run it ONCE on TEST.
Mirror = same fill bar and price, opposite side, same stop distance and target size.

## Bar (one look)
TEST pooled mean net R > 0 AND random-side P <= 0.05 (20,000 flips of each trade to its mirror) AND mean > 0 in at least 3 of the 4 markets AND n >= 150.
Also reported, not gating: DEV-to-TEST correlation of cell means, the top-5 DEV cells on TEST. Nothing is re-tuned after the look.

## RESULT (one look, Tue 2026-10-27 ~10:1x local clock; `po3_search.py` -> PO3_SEARCH_OUTPUT.txt) -- NOT SHOWN
All 32 cells negative on DEV and TEST (DEV/TEST correlation 0.94: the losses are stable, not noise). Chosen cell (sweep to 05:00, wide stop, 0.5 R, with-trend):
TEST 1,076 trades, 64.0% wins, mean -0.125 R, mirror -0.088, random-side P 0.83, markets positive 0/4 (ES -0.122, GC -0.167, NQ -0.050, SI -0.140), every year negative.
The PO3 rule is closed; claude.pine keeps it as a drawing tool only.
