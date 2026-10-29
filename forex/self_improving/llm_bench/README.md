# llm_bench: a local, free replica of the "Who's the Best AI Trader?" setup (reel 10)

the trader 2026-10-14: "we cant invest anymore money, everything has to be local". Everything here runs on this PC: Ollama models on localhost:11434 (no API, no cost), MT5 broker data, Python.

## Same shape as the video
| his setup | here |
|---|---|
| paste a model code, "Test AI model" | `python -m forex.self_improving.llm_bench.runner --model <ollama name>` |
| same prompt, same train data for every model | `runner.PROMPT`; the model only ever receives the TRAIN rows (first 70% of each source) |
| up to 3 train rounds (model writes code, `run_dev`, reads the result, fixes) | `runner.run_model` (3 rounds, TRAIN metrics only are fed back) |
| sealed holdout, scored once | `harness.score`: the last 30% of each source, run once |
| 3 lanes x 8 gates | 2 lanes (MULTI: 16 hourly markets 2021-12..2025-12; TICK: EURUSD/XAUUSD/BTCUSD 1-minute bars with MT5 tick volume, 2025-04..2025-12) x 8 gates |
| controls: buy and hold, coin flips | `runner.CONTROLS` (+ two classic rules for reference) |
| placebo (share of random-entry runs beaten, gate 90%) | G7: the model's own position series circularly shifted 60 times; it must beat 90% |
| quarantine of bad data | the harness drops no source silently: the MT5 broker bars were already cleaned (bid/ask checked, duplicates removed) |
| costs: 0.1% per round trip | real MT5 broker bid/ask at every position change + 0.1 bp slippage; no changes in the 23:00-00:59 server window |
| cost per run | tokens only, $0 (local) |
| scoreboard | `--board` (and `data\llm_bench\results\*.json`) |

Gates per lane: G1 valid output on all sources, G2 causal (the future is cut and the positions must not change), G3 active but not hyperactive (median >= 20 trades, < 0.2 changes per bar), G4 median holdout net > 0, G5 holdout positive in >= 60% of sources, G6 beats buy-and-hold in >= 60% of sources, G7 placebo >= 90%, G8 profitable in BOTH train and holdout in >= 60% of sources.

## What is not replicated (and why)
- His LIQUIDATION lane (BTC/ETH/SOL/XRP liquidation columns, 2 years): historical liquidations are not free data; they can only be recorded live. Not available here.
- His purchased tick data: we use the MT5 ticks/tick volume from the MT5 broker terminal (since 2025-04 for tick volume; real ticks since 2025-10).
- Paid models (OpenRouter): replaced by local Ollama models. At the time of writing only `gemma4:latest` (8B) is installed.
- 2026 stays sealed: the data stops at 2025-12-31, so nothing this bench finds has touched the unread 2026 period.

## Files
`data.py` (builds the sources into data/llm_bench/data), `sandbox.py` (runs model code in a separate interpreter: AST allow-list, only numpy/pandas/math, no file/network access, 240 s timeout), `harness.py` (costs, rollover rule, gates, placebo, causality), `runner.py` (Ollama loop, controls, scoreboard).
