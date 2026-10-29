# Timeline

Dates come from the commit history (original dates were kept). Most work before late September
was committed in a few large snapshots, so the commit counts understate it.

| when | what | where |
|---|---|---|
| 23-26 Jun 2026 | first commits: an MNQ order-flow simulation backend and the first NinjaScript strategies | `futures/early_sim/`, `futures/ninjascript/` (history only) |
| 21 Jul 2026 | a reinforcement-learning MNQ scalper and its bridge to the trading platform | `futures/ai_research/` (history only) |
| Jul-Sep 2026 | the first wave of intraday futures ideas, a testing suite, knowledge-graph notes | `futures/_archive/`, `archive/` |
| 18-22 Sep 2026 | the live bot is built and run on a practice account; the round-by-round engine starts being committed | `futures/live_bot/`, `futures/engine/` |
| Sep-Oct 2026 | about 450 engine rounds: ORB, VWAP, POC/value area, FVG/OTE, meta-labeling | `futures/engine/` |
| 30 Sep 2026 | the switch to MetaTrader 5: EAs, batch testing, many markets at once | `forex/early_mt5/` (history only), `forex/ea_batch/` |
| 13 Oct 2026 | the main MT5 research phase: pre-registered tests, overnight and swap-free drift, the self-improving loop | `forex/ea_research/`, `forex/self_improving/` |
| 15 Oct 2026 | the swap-free drift book (D2) passes every pre-registered bar | [swap-costs.md](swap-costs.md) |
| 23 Oct 2026 | blind chart-reading tests begin, with a one-bar-at-a-time replay app | `forex/apprentice/` |
| 26-28 Oct 2026 | back to CME futures: London-open gold, Tokyo MNQ, the half-R comparison | `futures/london_open_gold/` |
| 29 Oct 2026 | this public version: history scrubbed of private details, docs and indexes written | `docs/` |

Commits per month: June 2, July 2, September 143, October 618. Busy days were grouped into at most 40 commits each
for the public version; the content and dates are unchanged.
