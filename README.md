# beginner-quant-research

Five months of a beginner's systematic trading research, June to October 2026: intraday ideas
on CME futures, a move to forex and CFDs on MetaTrader 5, and a return to futures. Everything is
kept, including (mostly) the failures, with the original commit dates.

**Headline result:** no fast intraday edge survived realistic costs and out-of-sample testing in
either market. The one idea that passed every pre-registered bar was slow: a long-only,
trend-filtered drift book that only works when holding positions overnight is cheap. The
difference between forex swaps and futures financing turned out to matter more than any entry
signal.

This is not financial advice, and nothing here is a working trading system.

## Start here

1. [docs/journey.md](docs/journey.md): what was tried, in order, and why the market changed twice.
2. [docs/swap-costs.md](docs/swap-costs.md): swap and financing in forex versus futures, and the
   drift book.
3. [docs/methods.md](docs/methods.md): pre-registration, hold-outs, random baselines, costs.
4. [docs/lessons.md](docs/lessons.md): what each wrong turn taught.
5. [forex/ea_research/INDEX.md](forex/ea_research/INDEX.md) and [futures/engine/INDEX.md](futures/engine/INDEX.md): every test, by family.

## What is where

| folder | contents |
|---|---|
| `futures/engine/` | the futures research engine: one numbered "round" script and result per idea |
| `futures/london_open_gold/` | the last week: micro-gold London-open indicator, Tokyo test, half-R test |
| `futures/live_bot/` | a tested live-trading scaffold (risk limits, fills, strategies) with an abstract broker |
| `futures/ai_research/`, `futures/early_sim/`, `futures/ninjascript/` | an RL scalper, the first simulation backend, NinjaScript strategies |
| `futures/_archive/`, `futures/docs/` | older experiments and design notes |
| `forex/ea_research/` | the MT5 research: 200+ pre-registered tests (breakouts, overnight, swap-free drift, ML, events) |
| `forex/apprentice/` | blind chart-reading tests and a local one-bar-at-a-time replay app |
| `forex/self_improving/` | an automated research loop and its placebo checks |
| `forex/ea_batch/`, `forex/expert_advisors/`, `forex/early_mt5/` | MT5 expert advisors and batch-testing code |
| `archive/` | the earliest testing suite and retired code |
| `docs/` | the write-ups above and [data.md](docs/data.md) |

## Data

No market data is included (licensed sources). Derived results (trade lists, equity curves,
result tables) are. See [docs/data.md](docs/data.md) for what to supply to rerun a script.

## Licence

Apache License 2.0, see [LICENSE](LICENSE).
