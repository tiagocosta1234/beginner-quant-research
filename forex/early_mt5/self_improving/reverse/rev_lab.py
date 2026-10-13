"""python -m mt5broker.self_improving.reverse.rev_lab [--placebo 81]  (PREREG_REVERSE.md)"""
import sys
ARGV = sys.argv[1:]
import argparse, json, os
from pathlib import Path
os.environ.setdefault("FF6_MT5ONLY", "1")
import numpy as np, pandas as pd
from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.freeform import ff6_data as D, ff6_agent as A
LED = Path("D:/finance/si_ledgers")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); a = ap.parse_args(ARGV)
    df = pd.read_csv(LED / "FF10_mt5real.csv", usecols=["stage", "hash", "rule"]); df = df[df.stage == "a"].drop_duplicates("hash")
    rules = [json.loads(x) for x in df.rule]; out = []
    for cls in P3.CLASSES:
        st = D.Stack(cls, a.placebo); ev = A.Evaluator({cls: st}); rs = [r for r in rules if r["cls"] == cls]; rows = []
        for i, r in enumerate(rs):
            s = ev.stat(r, "val")
            if s["n"] >= 100 and s["clusters"] >= 20 and s["mean_bp"] >= 5.0 and np.isfinite(s["z"]): rows.append((s["z"], s, r))
        print(f"[{cls}] rules {len(rs)} passing the 2025 fit filter {len(rows)}", flush=True)
        seen = set(); rows.sort(key=lambda x: -x[0])
        for z, s, r in rows:
            k = (r["side"], r["H"], tuple(sorted(c[0] for c in r["conds"])))
            if k in seen: continue
            seen.add(k); sa, sb = ev.stat(r, "a"), ev.stat(r, "b")
            out.append(dict(cls=cls, rule=json.dumps(r), v_n=s["n"], v_net=s["mean_bp"], v_z=z, a_n=sa["n"], a_net=sa["mean_bp"], a_ex=sa["ex_bp"], a_p=sa["p"], b_n=sb["n"], b_net=sb["mean_bp"], b_ex=sb["ex_bp"], b_p=sb["p"]))
            if len([o for o in out if o["cls"] == cls]) >= 20: break
        del st, ev
    d = pd.DataFrame(out)
    # keep the 20 best overall by 2025 z
    d = d.sort_values("v_z", ascending=False).head(20).copy()
    d["real"] = (d.a_n >= 50) & (d.b_n >= 50) & (d.a_net > 0) & (d.b_net > 0) & (d.a_p < 0.05) & (d.b_p < 0.05)
    d.to_csv(LED / f"REV_{'pl' + str(a.placebo) if a.placebo is not None else 'real'}.csv", index=False)
    pd.set_option("display.width", 250); print(d.drop(columns="rule").round(2).to_string())
    print(f"DONE: 2025 top-20 mean net {d.v_net.mean():+.1f} bp | on 2022-23H1 {d.a_net.mean():+.1f} bp | on 2023H2-24 {d.b_net.mean():+.1f} bp | REAL winners {int(d.real.sum())}")
if __name__ == "__main__": main()
