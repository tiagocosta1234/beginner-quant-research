"""ManualONB.mq5 (strategy S3) in the MT5 Strategy Tester on MT5 broker real ticks (portable tester terminal), NSDQ+, 2025-10-01 .. 2026-09-30, risk 300 USD per trade;
R0 = no execution delay, R1 = 250 ms delay; compared with the Python model of the same rule (forex/ea_research/nq3.py, spread floor 1.67, slippage 0 and 1).
   python -m forex.ea_batch.verify_manualonb_mt5"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import mt5data_run as ER

TR, TERM = ER.TR, ER.TERM_DIR
FRM, TO = "2025.10.01", "2026.09.30"


def ea_log() -> list[str]:
    files = sorted(glob.glob(str(TERM / "Tester" / "Agent-*" / "logs" / "*.log")), key=os.path.getmtime)
    if not files: return []
    raw = Path(files[-1]).read_bytes(); txt = raw.decode("utf-16", errors="ignore") if raw[:2] == b"\xff\xfe" else raw.decode("utf-8", errors="ignore")
    return [l for l in txt.splitlines() if "[ManualONB]" in l]


def trades_from_deals(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy(); d["dir"] = d.direction.astype(str).str.lower(); rows = []; opn = None
    for _, r in d.sort_values("time").iterrows():
        if r.dir.startswith("in"): opn = r
        elif r.dir.startswith("out") and opn is not None:
            side = 1 if opn.price < r.price or True else -1                              # side from the sign of the profit vs price move
            move = r.price - opn.price; side = 1 if (r.profit >= 0) == (move >= 0) else -1
            rows.append(dict(entry=opn.time, exit=r.time, side=side, pts=side * move, net=r.profit + r.commission + r.swap + opn.commission + opn.swap)); opn = None
    return pd.DataFrame(rows)


def run(tag: str, mode: int) -> tuple[dict, list[str], pd.DataFrame]:
    r = TR.run_test(f"manualonb_{tag}", r"the trader\ManualONB.ex5", "NSDQ+", "M1", FRM, TO, {"InpRiskUSD": "300"}, timeout=14400, execution_mode=mode)
    L = ea_log(); T = trades_from_deals(r["deals"]) if r["deals"] is not None and len(r["deals"]) else pd.DataFrame(columns=["entry", "exit", "side", "pts", "net"])
    return r, L, T


def main() -> int:
    out = {}
    for tag, mode in (("R0", 0), ("R1", 250)):
        r, L, T = run(tag, mode); out[tag] = (r, L, T)
        buys = [l for l in L if "] BUY " in l or "] SELL " in l]; setups = [l for l in L if "CT: overnight" in l]
        print(f"\n=== {tag} (execution delay {mode} ms): net {r['net']:,.2f} | eq DD {r['eq_dd']} | seconds {r['seconds']} | note {r['note']!r}")
        print(f"EA log: {len(L)} lines | daily setups {len(setups)} | entries {len(buys)} | closed trades {len(T)}")
        if len(T):
            w, l_ = T.net[T.net > 0].sum(), -T.net[T.net < 0].sum(); print(f"tester: trades {len(T)}, win {100 * (T.net > 0).mean():.0f}%, net {T.net.sum():+,.0f} USD, PF {w / l_ if l_ else float('inf'):.2f}, avg {T.pts.mean():+.1f} pts per trade, avg USD {T.net.mean():+.0f}")
    os.environ["NQ3_FLOOR"] = "1.67"
    from forex.ea_research import nq3 as N
    cx = N.Ctx(); res = {}
    for slip in (0.0, 1.0):
        N.SLIP = slip; P = pd.DataFrame(N.s3(cx)); P = P[(P.entry >= "2025-10-01") & (P.entry < "2026-10-01")]; res[slip] = P
        print(f"\nPython S3 slip {slip:.0f}: {len(P)} trades, avg {P.pts.mean():+.1f} pts, total {P.pts.sum():+.0f} pts")
    for tag in ("R0", "R1"):
        T = out[tag][2]
        if not len(T): continue
        t = T.copy(); t["day"] = pd.to_datetime(t.entry).dt.normalize()
        for slip, P in res.items():
            p = P.copy(); p["day"] = p.entry.dt.normalize(); m = t.merge(p[["day", "side", "pts"]], on=["day", "side"], suffixes=("_ea", "_py"))
            print(f"{tag} vs Python slip {slip:.0f}: EA trades {len(t)} | Python {len(p)} | same day and side {len(m)} | mean pts EA {t.pts.mean():+.1f} vs Python {p.pts.mean():+.1f} | on matched trades EA {m.pts_ea.mean():+.1f} vs Python {m.pts_py.mean():+.1f} pts")
    r1 = out["R1"][2]
    if len(r1):
        w, l_ = r1.net[r1.net > 0].sum(), -r1.net[r1.net < 0].sum(); pf = w / l_ if l_ else float("inf"); acc = bool(len(r1) >= 30 and r1.net.sum() > 0 and pf >= 1.1)
        print(f"\nREGISTERED CHECK (R1: >= 30 trades, net > 0, PF >= 1.1): trades {len(r1)}, net {r1.net.sum():+,.0f}, PF {pf:.2f} -> {'PASS' if acc else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
