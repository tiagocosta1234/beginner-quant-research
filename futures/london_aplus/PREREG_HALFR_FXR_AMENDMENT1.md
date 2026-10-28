# Amendment 1 to PREREG_HALFR_FXR: two descriptive log columns

Written Wed 2026-10-28 17:0x (local clock), before trade 1 of the scored test. `HALFR_LOG.csv` has no trade rows yet.

## What changes
`HALFR_LOG.csv` gains two columns: `stop_pts` and `mfe_pts` (header now `date,session,fx_session_id,side,risk_usd,stop_pts,mfe_pts,pnl,notes`).
- `stop_pts`: the stop distance of the trade in price points (1R in points). Filled in at entry.
- `mfe_pts`: the furthest the price went in the trade's favour, in points from entry, before the ORIGINAL stop was touched. After the trade ends, keep the replay running until the original stop would have been touched or the session window ends (London 16:00, NY 15:55 ET), and read the furthest favourable price. Leave blank if you did not run it on; blank rows are skipped by the scan.

## What does not change
The plan, the bar (n >= 200, win rate >= 74%, mean R > 0, one-sided bootstrap P <= 0.05), the scored column (`pnl`), the cost rule (`--cost-r 0.05`) and the verdict logic in `score_halfr.py`. The new columns feed only a descriptive "target scan" printed after the verdict: for targets of 0.50, 0.60, 0.68, 0.75 and 1.00 R it shows the hit rate and mean net R implied by each trade's `stop_pts` and `mfe_pts`, with a cost of 0.32 pt a trade (`--cost-pts`). It needs 30 rows with both columns.

## Why
The 28 Oct MGC boxes showed that the cost in R depends on the stop (0.11R on a 2.8-pt stop, 0.05R on 5.9 pts), so the target that kills the costs differs by trade. Logging the stop and the favourable excursion lets the same 200 trades show what each target would have scored, instead of choosing the target by feel.

## How to read the scan
Descriptive only. A target picked after seeing the scan is a new hypothesis for a new test, not a result of this one. A touch (mfe_pts >= target) counts as a hit, which is slightly optimistic against a real limit fill.
