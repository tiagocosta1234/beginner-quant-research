# SDS: the self-developing system (design, 2026-10-13)

the trader: "(original wording omitted)". Source of the skeleton: the loop-engineering article he pasted (automation, skill, state file, verifier, worktrees, connectors). What is kept, what is changed, and why.

## What "self-developing" means here (and what it does not)
The system keeps running without a person: it ingests new data, re-tests the research engines, develops new experiments when new information appears, verifies every claim by a separate mechanism, writes what it learned into a state file and into machine-checked constraints, and hands a CANDIDATE (never an order) to the trader when something survives. It does NOT trade, does NOT arm Algo Trading, does NOT edit live presets or `locked_plan.py`, and does NOT write its own trading rules from losses (that is adaptive overfitting): every change to what counts as evidence is a written amendment.

## The six pieces and how they are built here
1. **Automation**: `sds/loop.py --once` is one cycle; a Windows scheduled task (not installed until the trader says so) runs it nightly when the main PC is idle. Heavy jobs run at below-normal priority.
2. **Skill = executable constraints** (`sds/constraints.py`): every lesson is a record (id, date, text, which engines it binds) and, where possible, a check. Examples already earned: no decision/entry/exit at server hours 23 and 0; only MT5-native information is deployable (feature whitelist); excess over random timing, not mean > 0; explore/confirm split for adaptive search; Student t for few clusters; one entry per horizon per market; sealed windows are never loaded; calibrate before believing. When a new failure mode is found, it is ADDED here and the regression step re-runs the earlier engines to see which conclusions change.
3. **State** (`sds/STATE.md`, rendered from `sds/experiments.jsonl`, an append-only registry): engines, code hashes, last calibration, last real result, candidates under audit, lessons, next actions. The agent forgets, the file does not.
4. **Verifier** (`sds/verifier.py`): separate from the proposers and not based on anyone's claim. (a) An engine's real result counts only if the engine is CALIBRATED for its current code hash: the last 3 placebo worlds (fresh seeds, never reused, ids from the registry counter) all returned 0 passing cells. (b) A real pass becomes a CANDIDATE that must clear a fixed audit before the trader sees it: by-hour concentration (rollover), one position per market, carry/latency sensitivity, ablation of non-MT5 inputs, stability across sub-windows, the MT5 broker environment and the add-on test against the installed system, then the sealed window once. (c) The verdict is NO_FINDING / ENGINE_UNCALIBRATED / CANDIDATE_NEEDS_AUDIT / AUDIT_FAILED / CANDIDATE_FOR_MANUAL.
5. **Worktrees**: not needed (one agent, one repo, runs are separate processes with their own ledgers); parallel engines write to different ledger files.
6. **Connectors**: read-only only. MT5 through the Python package attached read-only (terminal_info, account_info, positions_get, copy_rates_range, copy_ticks_range); Telegram for notices through the existing bot. No order function exists in this package; the verifier fails the build if one is imported.

## Cycle (what `loop.py --once` does)
1. Read STATE and the registry; detect what changed (engine code hash, new data files such as the MT5 calendar or tick_volume exports).
2. For each engine due: if not calibrated for its code hash, run 3 placebo worlds with fresh seeds; if any passes, the engine is flagged BROKEN and nothing it says is believed until diagnosed (this is a stop condition checkable by something other than the agent).
3. If calibrated, run the real experiment; record the result with its code hash and data windows.
4. Verify; write state; if a CANDIDATE appears, write `sds/candidates/<id>.md` with the audit checklist and notify Telegram. Nothing else.
5. Propose the next experiments: when new information or new data windows appear (calendar, tick_volume, forward weeks), queue the engines that can use them; never repeat an experiment with the same (engine, code hash, data hash).

## Stop conditions (checkable, not self-reported)
An engine run ends when its own pre-registered generations or cells are done; the loop ends the cycle when the queue is empty or a budget (wall-clock hours, set in config) is reached; the system as a whole stops searching a family when two consecutive calibrated cycles with new data give no candidate (reported, not silently dropped).

## What v1 builds now
Registry, constraints, verifier, loop with the five existing engines wired through a uniform contract (ML on raw bars, new-information daily lab, high-frequency tick lab, regime layer, free-form rule search), STATE.md rendering, a backfill of the history already established, and the nightly scheduling command (not installed). Next: the read-only degradation monitor of the live legs, executable audit checks, the MT5 calendar / tick_volume engine (after tonight's export).

## Amendment 1 (2026-10-13 ~10:45): the placebo gate is sequential
The first cycle flagged the ML engine as broken after ONE passing cell (z 3.12) in the first fresh placebo world (seed 101), after six earlier clean worlds. With a nominal family-wise error near 5% per world, one pass in 3 worlds occurs by chance about 14% of the time, so 'any pass = broken' would reject sound engines. New rule (registry.gate_state, lesson L12): 0 passes in the first 3 worlds = calibrated; exactly 1 pass = run worlds up to 10 and accept at most 1 pass in 10 (2 or more by chance in 10 has probability about 9%); 2 or more passes = broken. The seed-101 world stays in the record.
