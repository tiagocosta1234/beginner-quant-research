# forex/

Research run on a MetaTrader 5 account from late September to late October 2026: forex pairs,
gold and silver, stock-index and oil CFDs, and crypto, using MT5's own bid/ask history (M1 and
ticks) and its strategy tester. Some folders (notably `apprentice/`) also use CME futures data
for the same ideas.

| folder | what it holds |
|---|---|
| `ea_research/` | 200+ pre-registered tests with results; see [ea_research/INDEX.md](ea_research/INDEX.md) |
| `apprentice/` | blind chart-reading tests at the London open; see its [README](apprentice/README.md) |
| `self_improving/` | an automated rule-search loop calibrated on placebo markets; see its [README](self_improving/README.md) |
| `intraday_lab/`, `factor_lab/`, `agent_lab/` | earlier labs: intraday rules, cross-market factors, an LLM research agent |
| `ea_batch/`, `expert_advisors/`, `multi_fx_ea/`, `specs/` | MT5 expert advisors, their batch runner and symbol specs |
| `tools/`, `tradingview/`, `tests/` | data pulls, chart helpers and tests |
| root scripts | data pulls (`data_pull.py`, `d1_pull.py`, `crypto_pull.py`, `stock_pull.py`), spread, slippage and rollover probes, the tick-bar builder |

The first weeks on MT5 (`forex/early_mt5/` in the history) used the same layout; most of that
folder was later merged into the paths above.

## Main findings

- Breakouts and opening ranges were tested on dozens of markets at once; a USD/JPY London
  breakout was the best of them at about +0.05 to +0.15 R a trade after spreads, small and
  fragile.
- Overnight index holding earned a real but tiny premium (+2.8 bp a night against 50-90 bp of
  noise).
- A long-only, trend-filtered drift book passed every pre-registered bar, because the account
  charged no swap. See [../docs/swap-costs.md](../docs/swap-costs.md).
- Most other families (news bars, analog days, machine-learning direction, crypto weekends,
  month-end flows) did not pass.
