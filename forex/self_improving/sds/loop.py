"""SDS loop: one cycle of the self-developing system (DESIGN.md).
   python -m forex.self_improving.sds.loop --plan                      what would run, nothing executed
   python -m forex.self_improving.sds.loop --once [--engines ml,hf]    calibrate if needed, run real, verify, write STATE.md
   python -m forex.self_improving.sds.loop --backfill                  record the history already established (idempotent)
Never places orders, never touches the live terminal. Heavy engines run only with --heavy."""
import sys
ARGV = sys.argv[1:]

import argparse
import hashlib
import json
import time
from pathlib import Path

from forex.self_improving.sds import constraints as C, engines as E, registry as R, verifier as V

HISTORY = [   # (engine, verdict, passes, one line): results established before the SDS existed, recorded once from the *_RESULT.md files
    ("freeform", "NO_FINDING", 0, "v4 hourly 86,048 rules, v5 macro+intrabar 148,966 rules, v6 M1 patterns 173,831 rules: 0 S1/S2 (FF_RESULT, FF9_RESULT, FF10_RESULT)"),
    ("regime", "NO_FINDING", 0, "100,000 policies on the installed system, 0 survivors (REGIME_RESULT)"),
    ("ml", "NO_FINDING", 0, "XGBoost on raw 15-minute bars: 0 of 12 cells after the rollover artefact was excluded (ML_RESULT)"),
    ("hf", "NO_FINDING", 0, "tick lab: 0 of 48 cells, no cell with positive net (HF_RESULT)"),
    ("slow", "NO_FINDING", 0, "COT + ALFRED + cross-asset at 1/5/20 days: 0 of 12 cells (SLOW_RESULT)"),
]


def data_hash(spec):
    h = hashlib.sha1()
    for d in spec.get("data", []):
        p = Path(d)
        if p.is_file(): st = p.stat(); h.update(f"{p}{st.st_size}{int(st.st_mtime)}".encode())
        elif p.is_dir(): h.update(f"{p}{sum(1 for _ in p.iterdir())}".encode()); [h.update(f"{x.name}{x.stat().st_size}".encode()) for x in sorted(p.iterdir())[:200] if x.is_file()]
    return h.hexdigest()[:10]


def due(spec):
    """An experiment is repeated only if (engine, code hash, data hash) is new."""
    dh = data_hash(spec); done = [e for e in R.events() if e.get("engine") == spec["name"] and e.get("kind") == "real" and e.get("code_hash") == spec["hash"] and e.get("data_hash") == dh and e.get("verdict") != "ENGINE_UNCALIBRATED"]
    return (not done), dh


def backfill():
    have = {(e.get("engine"), e.get("note")) for e in R.events() if e.get("kind") == "historical"}
    for eng, ver, passes, note in HISTORY:
        if (eng, note) not in have: R.append(dict(engine=eng, kind="historical", verdict=ver, passes=passes, note=note))


def cycle(names, heavy, plan_only):
    # static audit of the engine sources against the lessons (a failed check blocks the engine)
    for n in names:
        spec = E.ENGINES[n]
        if spec["heavy"] and not heavy: print(f"[{n}] heavy engine skipped (use --heavy)"); continue
        bad = V.static_audit(spec)
        if bad: print(f"[{n}] BLOCKED by lessons: {bad}"); R.append(dict(engine=n, kind="blocked", code_hash=spec["hash"], problems=bad)); continue
        todo, dh = due(spec); cal = R.calibrated(n, spec["hash"]); worlds = R.gate_state(n, spec["hash"])[1]
        print(f"[{n}] code {spec['hash']} calibrated={cal} real due={todo} placebo worlds missing={0 if cal else worlds}")
        if plan_only: continue
        if R.broken(n, spec["hash"]): print(f"[{n}] BROKEN (a placebo world passed): diagnose before believing anything"); continue
        while R.gate_state(n, spec["hash"])[0] == "need_more":
            seed = R.next_seed(n); passes, log = E.run_engine(spec, "placebo", seed); R.append(dict(engine=n, kind="placebo", seed=seed, code_hash=spec["hash"], passes=passes, log=str(log)))
            print(f"[{n}] placebo {seed}: passes={passes} gate={R.gate_state(n, spec['hash'])}")
        cal = R.calibrated(n, spec["hash"])
        if not cal: print(f"[{n}] not calibrated: real result not read"); R.append(dict(engine=n, kind="real", code_hash=spec["hash"], data_hash=dh, passes=None, verdict="ENGINE_UNCALIBRATED")); continue
        if not todo: continue
        passes, log = E.run_engine(spec, "real"); ver = V.verdict(spec, True, passes); cand = None
        if ver.endswith("CANDIDATE_NEEDS_AUDIT"): cand = str(V.write_candidate(spec, log.stem, passes))
        R.append(dict(engine=n, kind="real", code_hash=spec["hash"], data_hash=dh, passes=passes, verdict=ver, log=str(log), candidate=cand)); print(f"[{n}] real: passes={passes} verdict={ver}")
    R.render_state(E.ENGINES, C.LESSONS, note="Rendered by sds/loop.py. Nothing here is applied to the account; candidates are proposals for the trader's hand.")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--plan", action="store_true"); ap.add_argument("--once", action="store_true"); ap.add_argument("--backfill", action="store_true"); ap.add_argument("--heavy", action="store_true"); ap.add_argument("--engines", default="ml,slow,hf,regime"); a = ap.parse_args(ARGV)
    if a.backfill: backfill(); R.render_state(E.ENGINES, C.LESSONS, note="backfilled history")
    if a.plan or a.once: cycle(a.engines.split(","), a.heavy, plan_only=a.plan)


if __name__ == "__main__":
    main()
