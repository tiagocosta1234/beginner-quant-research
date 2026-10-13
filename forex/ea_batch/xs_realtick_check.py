"""Family XS step 2: the 5 clean non-gold survivors re-run on MT5 broker's REAL TICKS (Model=4, EURUSD+, 2025-10-01..2026-09-30, default inputs,
USD 100,000), against the MT5 M1-bar batch result for the same window. Portable tester terminal only.   python -m forex.ea_batch.xs_realtick_check"""
from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import mt5data_run as ER

TR, TERM = ER.TR, ER.TERM_DIR
HERE = Path(__file__).resolve().parent
EAS = {39425: ("DeMarker_Pending_2.mq5", "H1"), 17741: ("EMA.mq5", "M5"), 68934: ("SilviosEAbest26.mq5", "H1"), 17390: ("BollTrade.mq5", "M30"), 41732: ("LazyBot_MT5_V1.mq5", "H1")}


def stats(d: pd.DataFrame) -> dict:
    o = d[d.direction.astype(str).str.lower().str.startswith("out")]; pl = o.profit + o.commission + o.swap
    return dict(trades=len(o), net=float(pl.sum()), pf=float(pl[pl > 0].sum() / max(-pl[pl < 0].sum(), 1e-9)), win=float((pl > 0).mean()) if len(pl) else np.nan)


def main() -> int:
    z = zipfile.ZipFile(HERE / "sources.zip"); ex = TERM / "MQL5" / "Experts" / "xs"; ex.mkdir(parents=True, exist_ok=True); rows = []
    for i, (src, tf) in EAS.items():
        f = ex / src; f.write_bytes(z.read(f"{i}/{src}")); log = Path(r"D:\finance\tmp") / f"xs_{i}.log"
        subprocess.run([str(TERM / "MetaEditor64.exe"), "/portable", f"/compile:{f}", f"/log:{log}"], timeout=180)
        res = [l for l in log.read_bytes().decode("utf-16", errors="ignore").splitlines() if l.startswith("Result")]
        if not res or " 0 errors" not in res[-1]: print(i, "compile failed", res); continue
        r = TR.run_test(f"xs_{i}", rf"xs\{src.replace('.mq5', '.ex5')}", "EURUSD+", tf, "2025.10.01", "2026.09.30", None, timeout=5400)
        mt5 = stats(r["deals"]) if r["deals"] is not None else dict(trades=0, net=np.nan, pf=np.nan, win=np.nan)
        fd = pd.read_csv(HERE / "results" / f"{i}.csv"); fd["t"] = pd.to_datetime(fd.time, format="%Y.%m.%d %H:%M:%S", errors="coerce")
        ft = stats(fd[(fd.t >= "2025-10-01") & (fd.t < "2026-10-01")])
        rows.append(dict(id=i, ea=src[:-4], tf=tf, mt5_trades=mt5["trades"], mt5_net=round(mt5["net"]), mt5_pf=round(mt5["pf"], 2), mt5_win=round(100 * mt5["win"], 1), mt5_eqdd=r["eq_dd"],
                         mt5broker_m1_trades=ft["trades"], mt5broker_m1_net=round(ft["net"]), mt5broker_m1_pf=round(ft["pf"], 2), mt5broker_m1_win=round(100 * ft["win"], 1), note=r["note"], sec=r["seconds"]))
        print(rows[-1], flush=True)
    R = pd.DataFrame(rows); txt = R.to_string(index=False); print(txt)
    (HERE.parent / "ea_research" / "EA_SCREEN_NONGOLD_REALTICK.txt").write_text(txt, encoding="utf-8"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
