# forex/intraday_lab

An iterative intraday lab on MT5 data: each `iterNN_*.py` is one step of a running search
(sessions, relative value, releases, regimes, forex cross-sections, swap-aware rules, gold fades,
lead-lag). `lab.py`, `families.py` and `run_grid.py` hold the shared machinery, `scan*.py` the
grid scans, and `LESSONS.md` what each iteration taught. Iterations 23-24 are the first place the
cost of holding (swap) changed the ranking of rules, which led to the work in
[../../docs/swap-costs.md](../../docs/swap-costs.md).
