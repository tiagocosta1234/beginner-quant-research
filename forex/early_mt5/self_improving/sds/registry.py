"""SDS registry: append-only experiment log and the STATE.md rendered from it (DESIGN.md, piece 3)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "experiments.jsonl"; STATE = HERE / "STATE.md"; CAND = HERE / "candidates"; CAND.mkdir(exist_ok=True)


def now(): return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def append(ev):
    ev = dict(ev); ev.setdefault("when", now())
    with open(LOG, "a", encoding="utf-8") as f: f.write(json.dumps(ev, sort_keys=True) + "\n")


def events():
    if not LOG.exists(): return []
    return [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]


def code_hash(files):
    h = hashlib.sha1()
    for f in sorted(files):
        p = Path(f)
        if p.exists(): h.update(p.read_bytes())
    return h.hexdigest()[:12]


def next_seed(engine):
    """Fresh placebo seed for an engine: never reused (counter lives in the registry)."""
    used = [e["seed"] for e in events() if e.get("engine") == engine and e.get("kind") == "placebo" and "seed" in e]
    return (max(used) + 1) if used else {"ml": 101, "slow": 201, "hf": 301, "regime": 401, "freeform": 501}.get(engine, 601)


def gate_state(engine, chash):
    """Sequential placebo gate (Amendment 1 of DESIGN.md): the nominal family-wise error per placebo world is about 5%, so 'any pass = broken' would fail a sound engine
    about 14% of the time in 3 worlds. Rule: 0 passes in the first 3 worlds -> calibrated; exactly 1 -> run up to 10 worlds and accept at most 1 pass in 10; 2 or more passes -> broken."""
    runs = [e for e in events() if e.get("engine") == engine and e.get("kind") == "placebo" and e.get("code_hash") == chash]
    fails = sum(1 for r in runs if (r.get("passes") or 0) > 0); n = len(runs)
    if fails >= 2: return "broken", 0
    if n >= 3 and fails == 0: return "calibrated", 0
    if n >= 10 and fails <= 1: return "calibrated", 0
    return "need_more", (3 - n) if n < 3 else (10 - n)


def calibrated(engine, chash, worlds=3): return gate_state(engine, chash)[0] == "calibrated"


def broken(engine, chash): return gate_state(engine, chash)[0] == "broken"


def render_state(engines, lessons, note=""):
    ev = events(); L = [f"# SDS STATE (rendered {now()} from experiments.jsonl, {len(ev)} events)", "", note, "", "## Engines"]
    L.append("| engine | family | code hash | calibrated | last real | verdict |"); L.append("|---|---|---|---|---|---|")
    for name, spec in engines.items():
        h = spec["hash"]; reals = [e for e in ev if e.get("engine") == name and e.get("kind") == "real"]; last = reals[-1] if reals else None
        cal = "BROKEN" if broken(name, h) else ("yes" if calibrated(name, h) else "no")
        L.append(f"| {name} | {spec.get('family')} | {h} | {cal} | {(last['when'] + ' passes=' + str(last.get('passes'))) if last else '-'} | {last.get('verdict') if last else '-'} |")
    L += ["", "## Candidates for the trader"]; cands = sorted(CAND.glob("*.md")); L += [f"- {c.name}" for c in cands] or ["- none"]
    L += ["", "## Lessons enforced (constraints.py)"] + [f"- {x['id']} ({x['date']}) [{x['binds']}] {x['text']}" for x in lessons]
    L += ["", "## Last 12 events"] + [f"- {e['when']} {e.get('engine', '-')} {e.get('kind')} {json.dumps({k: v for k, v in e.items() if k not in ('when', 'engine', 'kind')})[:200]}" for e in ev[-12:]]
    STATE.write_text("\n".join(L) + "\n", encoding="utf-8")
