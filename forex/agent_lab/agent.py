"""Self-running research agent (local, free).
   python -m forex.agent_lab.agent --model gemma4:latest --n 10     # the local model proposes, codes, refines on TRAIN feedback, then ONE validation per idea
   python -m forex.agent_lab.agent --inbox                           # validate strategies dropped in forex/agent_lab/inbox/*.py (e.g. written by Claude Code), then move them to inbox/done
   python -m forex.agent_lab.agent --board                           # registry summary
Loop: propose -> code -> sandbox run on DEV markets / TRAIN period -> up to 2 refinements -> ONE validation (spends alpha, raises the bar) -> promoted/ if every check passes.
Promotion only means 'worth paper-trading'. Nothing here touches the live account."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from forex.agent_lab import evaluate as EV
from forex.agent_lab import registry as RG

HERE = Path(__file__).resolve().parent
INBOX = HERE / "inbox"

BRIEF = """You are a quantitative researcher. Propose ONE new trading hypothesis and implement it as a Python function `strategy(df)` that returns a numpy array of positions (-1, 0, 1), one per row.
df: hourly bars with columns open, high, low, close, spread_bp, tick_volume (may be NaN), in time order. The position at row i may use rows <= i only and is held over the next bar.
Costs: the real bid/ask spread on every change. Allowed imports: numpy as np, pandas as pd, math.
The idea must have an economic reason (who loses money to you and why), must work across FX, metals, indices and crypto with the same code, and must change position rarely (costs).
It will be judged on markets and periods you will never see, against random timing with the same exposure. Most ideas fail; prefer simple, robust ones.
Start the code with one comment line: # HYPOTHESIS: <one sentence>.
Ideas already tried (do not repeat them):
{tried}
Reply with only the code in one ```python block."""


def ollama(model, messages):
    body = json.dumps({"model": model, "messages": messages, "stream": False, "think": False, "options": {"temperature": 0.8, "num_predict": 2500, "num_ctx": 8192}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["message"]["content"]


def extract(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def hypothesis(code):
    m = re.search(r"#\s*HYPOTHESIS:\s*(.+)", code)
    return m.group(1).strip()[:200] if m else "(no hypothesis line)"


def fmt(rows):
    out = []
    for m, r in rows:
        out.append(f"{m}: ERROR {r}" if isinstance(r, str) else f"{m}: train net {r['net'] * 100:+.1f}%  trades {r['trades']}  sharpe {r['sharpe']:+.2f}")
    return "\n".join(out)


def median_net(rows):
    v = sorted(r["net"] for _, r in rows if not isinstance(r, str))
    return v[len(v) // 2] if v else None


def test_and_log(code, source, extra=None):
    if RG.seen(code):
        print("  duplicate code, skipped")
        return None
    trial = RG.n_validations() + 1
    res = EV.validate(code, trial)
    entry = dict(hash=RG.code_hash(code), source=source, hypothesis=hypothesis(code), validated=True, **(extra or {}), **res)
    RG.log(entry)
    if res.get("promoted"):
        RG.promote(entry, code)
    print(f"  trial {trial}: bar z {res['z_bar']:.2f} | zA {res.get('zA', 0):+.2f} zB {res.get('zB', 0):+.2f} zC {res.get('zC', 0):+.2f} | causal {res.get('causal')} active {res.get('active')} | PROMOTED {res.get('promoted')}", flush=True)
    return entry


def run_model(model, n, until=None, max_val=None):
    start_val = RG.n_validations()
    deadline = None
    if until:                                   # next occurrence of HH:MM (today, or tomorrow if already past)
        hh, mm = map(int, until.split(":"))
        now = time.localtime()
        deadline = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hh, mm, 0, 0, 0, -1))
        if deadline <= time.time():
            deadline += 86400
        print(f"deadline {time.strftime('%Y-%m-%d %H:%M', time.localtime(deadline))}", flush=True)
    for k in range(n):
        if deadline and time.time() >= deadline:
            print(f"stop: reached {until}", flush=True)
            break
        if max_val is not None and RG.n_validations() - start_val >= max_val:
            print(f"stop: {max_val} validations spent in this run (each one raises the bar for every later idea)", flush=True)
            break
        tried = "\n".join(f"- {r['hypothesis']}" for r in RG.rows()[-25:]) or "- (none yet)"
        msgs = [{"role": "user", "content": BRIEF.format(tried=tried)}]
        code, train = None, None
        for rd in range(3):
            try:
                text = ollama(model, msgs)
            except Exception as e:
                print("model call failed:", e)
                break
            code = extract(text)
            rows = EV.dev_feedback(code)
            train = median_net(rows)
            print(f"[{k + 1}/{n}] round {rd + 1}: {hypothesis(code)[:90]} | median train net {train if train is None else round(train * 100, 1)}%", flush=True)
            if train is not None and train > 0 and rd >= 1:
                break
            msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": "Train results on the development markets (the validation markets and periods stay hidden):\n" + fmt(rows) +
                                                        "\nFix errors; if it loses, change the idea or trade less. Reply with the full code in one ```python block."}]
        if code is None or train is None:
            RG.log(dict(hash=RG.code_hash(code or str(time.time())), source=model, hypothesis=hypothesis(code or ""), validated=False, error="did not run"))
            continue
        if train <= 0:
            RG.log(dict(hash=RG.code_hash(code), source=model, hypothesis=hypothesis(code), validated=False, train_median_net=train, note="not validated: loses on its own training data"))
            print("  not validated (loses on training data; no alpha spent)")
            continue
        test_and_log(code, model, dict(train_median_net=train))


def run_inbox():
    INBOX.mkdir(exist_ok=True)
    (INBOX / "done").mkdir(exist_ok=True)
    for p in sorted(INBOX.glob("*.py")):
        code = p.read_text(encoding="utf-8")
        rows = EV.dev_feedback(code)
        tr = median_net(rows)
        print(f"{p.name}: {hypothesis(code)[:90]} | median train net {tr if tr is None else round(tr * 100, 1)}%")
        if tr is None or tr <= 0:
            RG.log(dict(hash=RG.code_hash(code), source="inbox:" + p.name, hypothesis=hypothesis(code), validated=False, train_median_net=tr, note="not validated: loses on its own training data"))
            print("  not validated (loses on training data; no alpha spent)")
        else:
            test_and_log(code, "inbox:" + p.name, dict(train_median_net=tr))
        p.rename(INBOX / "done" / p.name)


def board():
    rs = RG.rows()
    v = [r for r in rs if r.get("validated")]
    print(f"{len(rs)} ideas logged, {len(v)} validated (next bar z = {EV.z_bar(len(v) + 1):.2f}), promoted {sum(1 for r in v if r.get('promoted'))}")
    for r in v[-15:]:
        print(f"  #{r['trial']:3d} {r['source'][:22]:22s} zA {r.get('zA', 0):+.2f} zB {r.get('zB', 0):+.2f} zC {r.get('zC', 0):+.2f} {'PROMOTED' if r.get('promoted') else '':8s} {r['hypothesis'][:80]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--model" in a:
        run_model(a[a.index("--model") + 1], int(a[a.index("--n") + 1]) if "--n" in a else 5,
                  a[a.index("--until") + 1] if "--until" in a else None, int(a[a.index("--max-val") + 1]) if "--max-val" in a else None)
    if "--inbox" in a:
        run_inbox()
    board()
