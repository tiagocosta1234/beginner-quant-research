"""BRK-XS exactly as in PREREG_BRK_XS.md: cross-sectional selection of session breakouts (46 MT5).
   python -m forex.ea_research.brk_xs --dry | (no flag) run   (needs data/si_ledgers/BRK_META_events.parquet from brk_meta)"""
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")


def closes(sym):
    D = load(sym, END)
    t = D["t"]
    day, sod = t // 86400, t % 86400
    ok = (sod >= 3600) & (sod < 23 * 3600)
    s = pd.Series(D["mc"][ok], index=day[ok]).groupby(level=0).last()
    return sym, s


def state():
    with ProcessPoolExecutor(8) as ex:
        res = dict(ex.map(closes, SYMS))
    C = pd.DataFrame(res).sort_index().ffill(limit=3)
    r20, r60 = C / C.shift(20) - 1, C / C.shift(60) - 1
    # rank at the PREVIOUS close, known at the start of each day
    return r20.rank(axis=1, pct=True).shift(1), r60.rank(axis=1, pct=True).shift(1)


def build():
    ev = pd.read_parquet("data/si_ledgers/BRK_META_events.parquet")
    k20, k60 = state()
    ev["rk20"] = [k20.at[d, m] if d in k20.index else np.nan for d, m in zip(ev.sday, ev.mkt)]
    ev["rk60"] = [k60.at[d, m] if d in k60.index else np.nan for d, m in zip(ev.sday, ev.mkt)]
    ev = ev.sort_values("t_entry")
    ev["order"] = ev.groupby("sday").cumcount()
    return ev


def cells(ev):
    long_, short_ = ev.side > 0, ev.side < 0
    return {"XS1_rs20": ev[(long_ & (ev.rk20 >= 0.8)) | (short_ & (ev.rk20 <= 0.2))],
            "XS2_rs60": ev[(long_ & (ev.rk60 >= 0.8)) | (short_ & (ev.rk60 <= 0.2))],
            "XS3_crowd": ev[ev.breadth >= 0.15],
            "XS4_early5": ev[ev.order < 5]}


def stats(x, a, b):
    s = x[(x.day >= a) & (x.day <= b)]
    return len(s), s.X4.mean(), nw_t(s.groupby("day").X4.mean().to_numpy())


def dry():
    ev = build()
    print("rank coverage:", round(ev.rk20.notna().mean(), 3), round(ev.rk60.notna().mean(), 3))
    for k, v in cells(ev).items():
        print(f"  {k}: DEV {stats(v, *DEV)[0]} VAL {stats(v, *VAL)[0]} 2026 {stats(v, *Y26)[0]}")
    x = ev[(ev.mkt == "NSDQ") & (ev.day == "2024-06-12")]
    print("hand check NSDQ 2024-06-12:", x[["side", "X4", "rk20", "rk60", "breadth", "order"]].round(3).to_dict("records"))


def run():
    ev = build()
    rng = np.random.default_rng(5)
    base = ev[(ev.day >= DEV[0]) & (ev.day <= DEV[1])]
    rows = []
    for name, c in cells(ev).items():
        r = dict(cell=name)
        for lab, p in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            r[f"n {lab}"], r[f"R {lab}"], r[f"t {lab}"] = stats(c, *p)
        p95 = np.percentile([base.X4.to_numpy()[rng.choice(len(base), r["n DEV"], replace=False)].mean() for _ in range(1000)], 95)
        g = [r["R DEV"] >= 0.05 and r["t DEV"] >= 2.5, r["R VAL"] > 0 and r["t VAL"] >= 1.65, r["R DEV"] > p95]
        r["random95"], r["gates"], r["PASS"] = p95, "".join("Y" if v else "n" for v in g), all(g)
        ix = c[c.c_index > 0]
        r["indices"] = " / ".join(f"{ix[(ix.day >= a) & (ix.day <= b)].X4.mean():+.3f}" for a, b in (DEV, VAL, Y26))
        rows.append(r)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 240)
    print(R.round(3).to_string(index=False))
    R.to_csv("data/si_ledgers/BRK_XS_cells.csv", index=False)
    for name, c in cells(ev).items():
        c = c.assign(cl=c.mkt.map(mclass))
        print(f"  {name}: " + " | ".join(f"{cl} {g[g.day <= DEV[1]].X4.mean():+.3f}/{g[(g.day >= VAL[0]) & (g.day <= VAL[1])].X4.mean():+.3f}" for cl, g in c.groupby("cl")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
