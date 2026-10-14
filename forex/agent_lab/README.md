# forex/agent_lab: a research agent that tests trading ideas by itself without fooling itself (built 2026-10-14)

the trader chose "an AI agent that researches and trades itself". This is the research half plus the promotion queue. Trading live stays behind a human gate (repo hard rule: the assistant never places orders; promoted ideas go to paper first, then to the trader).

## Why it is built this way
Every family tested this week failed, and the main danger in an automated search is that hundreds of tries on the same data always produce some "winners" by luck. The agent is constrained so that luck cannot get promoted:
1. **Two market groups.** DEV (EURUSD, USDJPY, USDCAD, EURJPY, XAUUSD, SP, DAX, BTCUSD): the agent sees TRAIN-period results here and nothing else. VAL (GBPUSD, AUDUSD, USDCHF, GBPJPY, XAGUSD, NSDQ, NIKKEI, ETHUSD): never shown to the agent in any form.
2. **Three checks, all required, each run once per idea:** A = DEV markets in the sealed later period; B = VAL markets in the sealed later period; C = VAL markets in the early period. Data: MT5 broker hourly bars 2021-12..2025-12 (70% early / 30% later); 2026 stays sealed for everything.
3. **Timing skill, not drift.** Each check's statistic is the strategy's net return minus the mean of 20 circular shifts of its own position series (same exposure, same turnover, wrong timing), Newey-West t per market, Stouffer-combined assuming 0.3 correlation. Buy-and-hold bull-market drift scores zero here.
4. **A bar that rises with every test.** Alpha spending alpha_i = 0.05 x 6/(pi^2 i^2): the bar is z 2.16 for the first idea, 3.24 for the 5th, 3.61 for the 10th, 4.37 for the 50th, 4.67 for the 100th. The registry is append-only and the counter never resets, so the agent cannot try its way past the bar.
5. **Real costs** (MT5 broker bid/ask at every change), no changes in the rollover window, sandboxed code (numpy/pandas/math only), causality test (the future is cut and positions must not change), and an activity check.
6. **No alpha for losers:** an idea that loses on its own training data is logged but not validated (it cannot pass and should not raise the bar).

## Use
```
python -m forex.agent_lab.agent --model gemma4:latest --n 10   # local model (free): propose, code, refine on TRAIN feedback (max 3 rounds), validate once
python -m forex.agent_lab.agent --inbox                         # validate strategies dropped into forex/agent_lab/inbox/*.py (e.g. written by Claude Code)
python -m forex.agent_lab.agent --board                         # registry and current bar
```
Files: `evaluate.py` (groups, checks, timing-skill z, bar), `registry.py` (append-only `registry.jsonl`, `promoted/`), `agent.py` (loop, inbox, board). Reuses the sandbox and cost model of `forex/self_improving/llm_bench`.

## What happens to a promoted idea (next stage, not built yet)
promoted/ -> paper forward log on live MT5 prices (read-only) for at least 60 trading days -> the trader reviews -> only then an EA in the MT5 tester on MT5 broker real ticks -> the trader decides on live. The quick trader (`forex/quick_trader`, LIVE_LOCK) and the gold pair are separate and untouched.
