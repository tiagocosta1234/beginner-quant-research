"""Shared pieces for the bootstrap and weekend-policy studies (the trader 2026-10-09: "(original wording omitted)", items A2 and A3).
Builds the guarded daily series (V = day result, B = lowest in-day equity vs the day's start, Hi = highest) of the pair for a size multiplier and a WEEKEND POLICY, on the two pools used everywhere in the clean studies:
  MT5   = last 12 months (2025-10-01..2026-09-30): MT5 broker real-tick trades + MT5 broker bars ("regime 12M", gold in a strong trend)
  FT   = 2022-01-01..2026-09-30: MT5 broker trades scaled by 4,100 / price + MT5 broker bars ("regime 5Y")
Loss cap 2,000 only (profit cap and pass lock OFF), exactly as clean_nolock_plan.py. Series are cached in D:\\finance\\scratch\\clean_cache.
Weekend policies: HOLD (as live), FLAT_ALL (every position closed 10 minutes before the last bar of each market closure longer than 30 hours, never reopened), FLAT_SDB, FLAT_XAU5."""
from __future__ import annotations

import sys
from pathlib import Path

_ARGS = sys.argv[1:]; sys.argv = ["x", "--source", "mt5broker"]
import numpy as np
import pandas as pd

from forex.ea_research import clean_guard_sim as C
from forex.ea_batch.mt5_mc_config import CH, FU
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch.mt5data_sizing_long import trades_mt5broker

A, CAPD, TARGET = C.A, C.CAPD, C.TARGET
CACHE = Path(r"D:\finance\scratch\clean_cache"); CACHE.mkdir(parents=True, exist_ok=True)
POOLS = {"MT5": ("mt5", "2025-10-01", "2026-09-30"), "FT": ("mt5broker", "2022-01-01", "2026-09-30")}
_bars = None


def bars():
    global _bars
    if _bars is None:
        _bars = C.load_bars()
    return _bars


def day(s: str) -> int:
    return (pd.Timestamp(s) - C.EPOCH).days


def ea_trades(src: str, which: str, lots: float, lo: int) -> dict:
    eid = "77900" if which == "sdb" else "mkt_xau5min"
    tr = C.prep([trades_mt5broker(eid, lots) if src == "mt5broker" else GC.trades(eid, lots)])
    if src == "mt5broker":
        keep = tr["out_s"] >= lo * 86400
        for k in list(tr):
            tr[k] = tr[k][keep]
        f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
    return tr


def flatten_weekends(tr: dict) -> dict:
    """Close every position 10 minutes before the last bar of a closure > 30 h; drop trades opened inside those last 10 minutes."""
    tm, bc, sp = bars(); gaps = np.nonzero(np.diff(tm) > 30 * 3600)[0]
    in_s, out_s = tr["in_s"].copy(), tr["out_s"].copy(); pl, ex = tr["pl"].copy(), tr["exit"].copy(); alive = np.ones(len(in_s), bool)
    for i in gaps:
        t_last = tm[i]; t_cut = t_last - 600; ic = int(np.searchsorted(tm, t_cut, side="right")) - 1
        span = np.nonzero(alive & (in_s <= t_cut) & (out_s > t_cut))[0]
        for j in span:
            px = bc[ic] if tr["side"][j] > 0 else bc[ic] + sp[ic]
            pl[j] = tr["side"][j] * (px - tr["entry"][j]) * tr["q"][j]; ex[j] = px; out_s[j] = t_cut
        late = np.nonzero(alive & (in_s > t_cut) & (in_s <= t_last))[0]
        alive[late] = False
    out = {k: v[alive] for k, v in tr.items()}; out["out_s"] = out_s[alive]; out["pl"] = pl[alive]; out["exit"] = ex[alive]
    return out


def merge(a: dict, b: dict) -> dict:
    return {k: np.concatenate([a[k], b[k]]) for k in a}


def series(pool: str, mult: float, policy: str = "HOLD", live: bool = False) -> dict:
    f = CACHE / f"{pool}_{mult}_{policy}_{'F' if live else 'C'}.npz"
    if f.exists():
        z = np.load(f, allow_pickle=True); return {k: z[k] for k in z.files}
    src, a, b = POOLS[pool]; lo, hi = day(a), day(b); base = FU if live else CH
    s = ea_trades(src, "sdb", base["sdb"] * mult, lo); x = ea_trades(src, "xau5", base["xau5"] * mult, lo)
    if policy in ("FLAT_ALL", "FLAT_SDB"):
        s = flatten_weekends(s)
    if policy in ("FLAT_ALL", "FLAT_XAU5"):
        x = flatten_weekends(x)
    r = C.simulate(bars(), merge(s, x), lo, hi, None, CAPD)
    out = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"], total=np.array([r["total_pl"]]))
    np.savez(f, **out); return out
