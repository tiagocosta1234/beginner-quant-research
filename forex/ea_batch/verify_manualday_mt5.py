"""ManualDay.mq5 (one gold setup a day, 1:1, 2,000 USD risk; DAY2K-E object O2 + 24h direction) in the MT5 Strategy Tester on MT5 broker real ticks
(portable tester terminal), 2025-10-01..2025-12-31 (inside VAL; the 2026 hold-out of the DAY2K family stays sealed), compared day by day with the Python engine.
   python -m forex.ea_batch.verify_manualday_mt5"""
from __future__ import annotations

import glob, os, re
from pathlib import Path

import numpy as np, pandas as pd

from forex.ea_batch import mt5data_run as ER

TR, TERM = ER.TR, ER.TERM_DIR
FRM, TO = "2025.10.01", "2025.12.31"


def ea_log() -> list[str]:
    files = sorted(glob.glob(str(TERM / "Tester" / "Agent-*" / "logs" / "*.log")), key=os.path.getmtime)
    if not files: return []
    raw = Path(files[-1]).read_bytes(); txt = raw.decode("utf-16", errors="ignore") if raw[:2] == b"\xff\xfe" else raw.decode("utf-8", errors="ignore")
    return [l for l in txt.splitlines() if "[ManualDay]" in l]


def python_side():
    from forex.self_improving.day2k import day2ke as E, day2k as D, day2kb as B
    days, R, RES, F, usd, mac, dates = E.data()
    m = (days >= D.d64("2025-10-01")) & (days <= D.d64("2025-12-31")); s = F[:, 0, 1, B.FI["m1"]].astype(float)
    rows = []
    for di in np.where(m)[0]:
        if not np.isfinite(s[di]) or s[di] == 0 or not np.isfinite(R[di, 1, 0, 0]): continue
        side = "BUY" if s[di] > 0 else "SELL"; r = R[di, 1, 0, 0 if side == "BUY" else 1]
        rows.append(dict(date=str(np.datetime64(int(days[di]), "D")), side=side, R=float(r)))
    return pd.DataFrame(rows)


def main() -> int:
    r = TR.run_test("manualday", r"the trader\ManualDay.ex5", "XAUUSD+", "M1", FRM, TO, None, timeout=7200)
    print(f"tester: net {r['net']:,.2f} | note {r['note']!r} | seconds {r['seconds']} | eq DD {r['eq_dd']}")
    L = ea_log(); ent = [l for l in L if re.search(r"\] \d{4}\.\d\d\.\d\d (BUY|SELL)", l)]; ex = [l for l in L if "] EXIT " in l]
    print(f"log lines {len(L)} | entries {len(ent)} | forced day-close exits {len(ex)}")
    T = pd.DataFrame([dict(date=re.search(r"(\d{4}\.\d\d\.\d\d) (BUY|SELL)", l).group(1).replace(".", "-"), side=re.search(r"(\d{4}\.\d\d\.\d\d) (BUY|SELL)", l).group(2),
                           lots=float(re.search(r"(BUY|SELL) ([\d.]+) lots", l).group(2))) for l in ent])
    d = r["deals"]
    if d is not None and len(d):
        o = d[d.direction.astype(str).str.lower().str.startswith("out")].copy(); o["date"] = pd.to_datetime(o.time).dt.strftime("%Y-%m-%d"); o["usd"] = o.profit + o.commission + o.swap
        g = o.groupby("date").usd.sum(); T["tester_usd"] = T.date.map(g)
        print(f"tester closed trades {len(o)} | +risk days {int((o.usd > 1800).sum())} | -risk days {int((o.usd < -1800).sum())} | other {int(((o.usd.abs() <= 1800)).sum())} | worst {o.usd.min():.0f} best {o.usd.max():.0f}")
    P = python_side(); M = P.merge(T, on="date", how="outer", suffixes=("_py", "_ea"))
    M["same_side"] = M.side_py == M.side_ea; M["same_outcome"] = np.sign(M.R) == np.sign(M.tester_usd)
    print(M.to_string(index=False))
    both = M.dropna(subset=["side_py", "side_ea"])
    print(f"\ndays: python {P.shape[0]}, EA {T.shape[0]}, both {len(both)} | same side {int(both.same_side.sum())}/{len(both)} | same outcome sign {int(both.same_outcome.sum())}/{len(both)}")
    print(f"python R total {P.R.sum():+.2f} ({2000 * P.R.sum():+,.0f} USD at 2,000) | wins {int((P.R > 0).sum())} losses {int((P.R < 0).sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
