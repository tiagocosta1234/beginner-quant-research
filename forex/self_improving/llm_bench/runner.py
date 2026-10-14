"""Local 'AI trader' bench runner.
   python -m forex.self_improving.llm_bench.runner --controls            # buy-and-hold, coin flips, two classic rules
   python -m forex.self_improving.llm_bench.runner --model gemma4:latest # one Ollama model: 3 train rounds, then the sealed holdout once
   python -m forex.self_improving.llm_bench.runner --board               # scoreboard of every saved result
Everything is local and free (Ollama on localhost:11434)."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from forex.self_improving.llm_bench import harness as H

RES = Path("D:/finance/llm_bench/results")
OLLAMA = "http://localhost:11434/api/chat"

PROMPT = """You are an algorithmic trader. Write ONE Python function `strategy(df)` that returns a numpy array of positions, one per row of `df`, with values -1 (short), 0 (flat) or 1 (long).
df is a pandas DataFrame of bars with columns: open, high, low, close, spread_bp, tick_volume (tick_volume may contain NaN). Rows are in time order.
Rules (enforced by the harness):
- The position at row i is decided with information up to and including row i only (no look-ahead: a test cuts the future and the positions must not change), and is held over the NEXT bar (entered at its open).
- You pay the real bid/ask spread on every position change plus a small slippage; changing position often loses money. No changes are possible in the 23:00-00:59 server window.
- Allowed imports: numpy as np, pandas as pd, math. No file, network or system access.
- The strategy is run on 16 different hourly markets (FX, gold, silver, indices, crypto) and on 3 one-minute markets; the same function, no per-symbol code. It is judged on a SEALED later period you never see.
- To count as good it must beat buy-and-hold and random timing on most markets, not just make money in a bull market. Most strategies do not; do not overfit.
Reply with only the code in one ```python block."""


def ollama(model, messages, temperature=0.7, num_predict=2500):
    body = json.dumps({"model": model, "messages": messages, "stream": False, "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": 8192}}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d["message"]["content"], d.get("eval_count", 0) + d.get("prompt_eval_count", 0)


def extract(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def fmt(rep):
    lines = []
    for lane, rows in rep.items():
        for f, m in rows:
            if isinstance(m, str):
                lines.append(f"{lane} {f}: ERROR {m}")
            else:
                lines.append(f"{lane} {f.split('__')[1].split('.')[0]}: train net {m['net'] * 100:+.1f}%  trades {m['trades']}  sharpe {m['sharpe']:+.2f}  maxDD {m['mdd'] * 100:.1f}%")
    return "\n".join(lines)


def run_model(model, label=None, rounds=3):
    t0 = time.time()
    msgs = [{"role": "user", "content": PROMPT}]
    tokens, code, log = 0, None, []
    for rd in range(1, rounds + 1):
        try:
            text, tk = ollama(model, msgs)
        except Exception as e:
            log.append(f"round {rd}: model call failed: {e}")
            break
        tokens += tk
        code = extract(text)
        rep = H.train_report(code)
        txt = fmt(rep)
        med = sorted(m["net"] for rows in rep.values() for _, m in rows if not isinstance(m, str))
        log.append(f"round {rd}: {len(med)} sources ok, median train net {med[len(med) // 2] * 100:+.1f}%" if med else f"round {rd}: no source ran: {txt[:200]}")
        print(log[-1], flush=True)
        msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": "Train results of your strategy (the sealed holdout is NOT shown):\n" + txt[:3500] +
                                                    "\nImprove it if you can (fix errors first, fewer trades if costs bite, no overfitting). Reply with the full corrected code in one ```python block."}]
    if code is None:
        return dict(model=model, label=label or model, error="no code produced", log=log)
    res = H.score(code)
    out = dict(model=model, label=label or model, score=sum(l["passed"] for l in res.values()), max_score=8 * len(res), lanes=res, code=code, rounds=len(log), tokens=tokens, secs=round(time.time() - t0), cost_usd=0.0, log=log)
    return out


CONTROLS = {
    "control: buy and hold": "def strategy(df):\n    return np.ones(len(df))\n",
    "control: coin flips": "def strategy(df):\n    rng = np.random.default_rng(1)\n    p = np.zeros(len(df)); cur = 0\n    for i in range(len(df)):\n        if rng.random() < 1 / 24: cur = rng.choice([-1, 0, 1])\n        p[i] = cur\n    return p\n",
    "rule: SMA 50/200 trend": "def strategy(df):\n    c = df.close\n    return np.where(c.rolling(50).mean() > c.rolling(200).mean(), 1, -1) * (c.rolling(200).mean().notna())\n",
    "rule: RSI(14) mean reversion": "def strategy(df):\n    c = df.close; d = c.diff()\n    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()\n    rsi = 100 - 100 / (1 + up / dn)\n    return np.where(rsi < 30, 1, np.where(rsi > 70, -1, 0))\n",
}


def save(out):
    RES.mkdir(parents=True, exist_ok=True)
    (RES / (re.sub(r"[^a-z0-9]+", "_", out["label"].lower()).strip("_") + ".json")).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


def board():
    rows = []
    for p in sorted(RES.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if "lanes" not in d:
            continue
        m, t = d["lanes"].get("MULTI", {}), d["lanes"].get("TICK", {})
        rows.append((d["score"], d["label"], f"{m.get('passed', 0)}/8", f"{t.get('passed', 0)}/8", f"{m.get('sources_positive', 0)}/{m.get('sources', 0)}", f"{m.get('buyhold_positive', 0)}/{m.get('sources', 0)}", d.get("tokens", 0), d.get("secs", 0)))
    print(f"{'model / control':34s}{'score':>6s}{'MULTI':>7s}{'TICK':>6s}{'holdout+':>9s}{'B&H+':>6s}{'tokens':>8s}{'secs':>6s}")
    for r in sorted(rows, reverse=True):
        print(f"{r[1][:34]:34s}{r[0]:>4d}/16{r[2]:>7s}{r[3]:>6s}{r[4]:>9s}{r[5]:>6s}{r[6]:>8d}{r[7]:>6d}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--controls" in a:
        for name, code in CONTROLS.items():
            res = H.score(code)
            out = dict(model=name, label=name, score=sum(l["passed"] for l in res.values()), max_score=8 * len(res), lanes=res, code=code, tokens=0, secs=0, cost_usd=0.0)
            save(out)
            print(name, {k: v["passed"] for k, v in res.items()}, {k: v["gates"] for k, v in res.items()}, flush=True)
    if "--model" in a:
        mdl = a[a.index("--model") + 1]
        out = run_model(mdl)
        save(out)
        print(mdl, "score", out.get("score"), out.get("log"))
    if "--board" in a or "--controls" in a or "--model" in a:
        board()
