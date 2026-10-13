# SDS STATE (rendered 2026-10-13 10:10 from experiments.jsonl, 35 events)

Rendered by sds/loop.py. Nothing here is applied to the account; candidates are proposals for the trader's hand.

## Engines
| engine | family | code hash | calibrated | last real | verdict |
|---|---|---|---|---|---|
| ml | ml | 037cb7e9ff5b | yes | 2026-10-13 09:50 passes=0 | NO_FINDING |
| slow | slow | 40891665d343 | yes | 2026-10-13 09:27 passes=0 | NO_FINDING |
| hf | hf | bff3ff48af6b | yes | 2026-10-13 10:10 passes=0 | NO_FINDING |
| regime | regime | c642ece0b541 | yes | 2026-10-13 09:45 passes=0 | NO_FINDING |
| freeform | freeform | 1eb70ef626f1 | no | - | - |

## Candidates for the trader
- none

## Lessons enforced (constraints.py)
- L01 (2026-10-13) [*] No decision, entry or exit at server hours 23 and 0: the rollover spread artefact moves the bid predictably (IC +0.52 / +0.40 there, ~0 elsewhere).
- L02 (2026-10-13) [*] Test excess over random timing (same market, side, horizon, grid), never 'mean > 0': drift makes any long rule 'significant'.
- L03 (2026-10-13) [freeform] An adaptive search needs an explore / confirm split; the false-discovery control applies only to rules confirmed on data the search never saw.
- L04 (2026-10-13) [freeform] Gross returns must not contain spread at the exit bar (bid-to-bid); cost avoidance by hour is not timing skill.
- L05 (2026-10-13) [*] Few clusters: Student t with G-1 degrees of freedom and the sqrt(G/(G-1)) correction.
- L06 (2026-10-13) [*] One entry per horizon per market: persistent signals must not be counted as many independent trades.
- L07 (2026-10-13) [*] Every engine must have a placebo mode and be calibrated (0 passing cells in fresh worlds) before its real result is read.
- L08 (2026-10-13) [hf] Passive limit orders do not earn the spread on an MT5 dealer-model account (a buy limit fills when the ASK reaches it).
- L09 (2026-10-13) [*] Only MT5-native information is deployable (prices, spreads, tick_volume, other symbols, MT5 economic calendar); external series are research-only.
- L10 (2026-10-13) [freeform] Total open stop-risk must be capped in the MT5 broker environment (flat risk per trade on correlated signals breaches the account).
- L12 (2026-10-13) [*] The placebo gate has a nominal false-failure rate (~5% per world); use the sequential rule (0 of 3, else at most 1 of 10), never 'any pass = broken'.
- L13 (2026-10-13) [*] MT5 Python API times (ticks, rates) are on the SERVER clock (Europe/Athens, naive), the MT5 calendar is UTC: convert before aligning; verify any clock with the daily spread peak (server hour 0).
- L11 (2026-10-13) [*] The research package never places orders and never arms Algo Trading; live changes are proposals for the trader's hand.

## Last 12 events
- 2026-10-13 09:45 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo104_037cb7e9ff5b.log", "passes": 0, "seed": 104}
- 2026-10-13 09:46 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo105_037cb7e9ff5b.log", "passes": 0, "seed": 105}
- 2026-10-13 09:46 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo106_037cb7e9ff5b.log", "passes": 0, "seed": 106}
- 2026-10-13 09:47 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo107_037cb7e9ff5b.log", "passes": 0, "seed": 107}
- 2026-10-13 09:48 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo108_037cb7e9ff5b.log", "passes": 0, "seed": 108}
- 2026-10-13 09:49 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo109_037cb7e9ff5b.log", "passes": 0, "seed": 109}
- 2026-10-13 09:50 ml placebo {"code_hash": "037cb7e9ff5b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_placebo110_037cb7e9ff5b.log", "passes": 0, "seed": 110}
- 2026-10-13 09:50 ml real {"candidate": null, "code_hash": "037cb7e9ff5b", "data_hash": "da39a3ee5e", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_ml_real_037cb7e9ff5b.log", "passes": 0, "verdict": "NO
- 2026-10-13 10:06 hf placebo {"code_hash": "bff3ff48af6b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_hf_placebo304_bff3ff48af6b.log", "passes": 0, "seed": 304}
- 2026-10-13 10:07 hf placebo {"code_hash": "bff3ff48af6b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_hf_placebo305_bff3ff48af6b.log", "passes": 0, "seed": 305}
- 2026-10-13 10:09 hf placebo {"code_hash": "bff3ff48af6b", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_hf_placebo306_bff3ff48af6b.log", "passes": 0, "seed": 306}
- 2026-10-13 10:10 hf real {"candidate": null, "code_hash": "bff3ff48af6b", "data_hash": "d8b92c8d07", "log": "D:\\finance\\beginner-quant-research\\mt5broker\\self_improving\\sds\\logs\\sds_hf_real_bff3ff48af6b.log", "passes": 0, "verdict": "NO
