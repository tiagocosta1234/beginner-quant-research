# beginner-quant-research

[![tests](https://github.com/tiagocosta1234/beginner-quant-research/actions/workflows/tests.yml/badge.svg)](https://github.com/tiagocosta1234/beginner-quant-research/actions/workflows/tests.yml)

Five months of a beginner's systematic trading research, June to October 2026: intraday ideas
on CME futures, a move to forex and CFDs on MetaTrader 5, and a return to futures. Everything is
kept, including (mostly) the failures, with the original commit dates. Much of the code and
testing was done with an AI coding assistant; the ideas, decisions and trading were mine.

**Headline result:** no fast intraday edge survived realistic costs and out-of-sample testing in
either market. The one idea that passed every pre-registered bar was slow: a long-only,
trend-filtered drift book that only works when holding positions overnight is cheap. The
difference between forex swaps and futures financing turned out to matter more than any entry
signal.

This is not financial advice, and nothing here is a working trading system.

## Rerun the main result

The original tests used broker data I can't share, so [drift_book/](drift_book/) rebuilds the
drift book on free daily data, adds a decade the research never saw (2010-19), and compares
swap-free, CFD-swap and futures holding costs:

```
pip install -r requirements.txt
python -m drift_book          # about 15 seconds, writes drift_book/results/
python -m pytest drift_book   # no network needed
```

On free data it makes about 7.6% a year swap-free since 2010, 6.2% on futures and 4.3% with a
normal CFD swap. The trend filter halves the worst drawdown but doesn't add return.
[Full results](drift_book/results/RESULTS.md).

## Start here

1. [docs/journey.md](docs/journey.md): what was tried, in order, and why the market changed twice.
2. [docs/swap-costs.md](docs/swap-costs.md): swap and financing in forex versus futures, and the
   drift book.
3. [docs/methods.md](docs/methods.md): pre-registration, hold-outs, random baselines, costs, and
   [docs/statistics.md](docs/statistics.md): the maths behind them (random-walk win rates,
   multiple testing, how much a Sharpe ratio is worth), each number checked by simulation.
4. [docs/lessons.md](docs/lessons.md): what each wrong turn taught.
   Also: [docs/results-summary.md](docs/results-summary.md), [docs/timeline.md](docs/timeline.md) and
   [docs/glossary.md](docs/glossary.md).
5. [forex/ea_research/INDEX.md](forex/ea_research/INDEX.md) and [futures/engine/INDEX.md](futures/engine/INDEX.md): every test, by family.

## What is where

| folder | contents |
|---|---|
| `drift_book/` | the drift book rebuilt on free data: small, tested, one command |
| `futures/engine/` | the futures research engine: one numbered "round" script and result per idea |
| `futures/london_open_gold/` | the last week: micro-gold London-open indicator, Tokyo test, half-R test |
| `futures/live_bot/` | a tested live-trading scaffold (risk limits, fills, strategies) with an abstract broker |
| `futures/_archive/`, `futures/docs/` | older experiments and design notes |
| `forex/ea_research/` | the MT5 research: 200+ pre-registered tests (breakouts, overnight, swap-free drift, ML, events) |
| `forex/apprentice/` | blind chart-reading tests and a local one-bar-at-a-time replay app |
| `forex/self_improving/` | an automated research loop and its placebo checks |
| `forex/ea_batch/`, `forex/expert_advisors/` | MT5 expert advisors and batch-testing code |
| `archive/` | the earliest testing suite and retired code |
| `docs/` | the write-ups above and [data.md](docs/data.md) |

Some early work was deleted from the working tree along the way and lives only in the commit
history: the first MNQ simulation backend (`futures/early_sim/`), a reinforcement-learning scalper
(`futures/ai_research/`), NinjaScript strategies (`futures/ninjascript/`) and the first weeks on MT5
(`forex/early_mt5/`). `git log -- <path>` shows them.

## Data

No market data is included (licensed sources). Derived results (trade lists, equity curves,
result tables) are. See [docs/data.md](docs/data.md) for what to supply to rerun a script.

## Licence

Apache License 2.0, see [LICENSE](LICENSE).
