"""LON_COMBO (PREREG_LON_COMBO.md): MT5 broker cycles of the 7 kept London rules alone and in all 127 combinations; 2026 vs 2022-25 vs 2020-21.
   python -m forex.ea_research.lon_combo"""
from itertools import combinations

import numpy as np
import pandas as pd

import forex.ea_research.orb11_entry as oe
import forex.ea_research.orb11_entry_oot as oo
from forex.ea_research.best3m_cycle import cycle
from forex.ea_research.lon_persym import london_spread, HD_OK

SIZES = (250, 500, 1000)
WIN = {"2026": ("2026-01-01", "2026-08-31"), "2022-25": ("2022-01-01", "2025-12-31"), "2020-21": ("2020-01-01", "2021-10-31")}


def series():
    S = pd.read_csv("data/si_ledgers/LON_PERSYM.csv"); K = S[S.kept]
    T = pd.read_parquet("data/si_ledgers/ORB11_ENTRY.parquet"); T = T[(T.sess == "LON") & (T.trig != "CTRL")]
    out = {}; load0 = oe.load
    for r in K.itertuples():
        g = T[(T.mkt == r.mkt) & (T.trig == r.trig)]; g = g[oe.fmask(g, r.filt)]
        parts = [g.set_index("day")[r.exit]]
        if r.mkt != "DOW" and HD_OK(r.mkt):
            D = oo.load_hd(r.mkt, london_spread(r.mkt)); oe.load = lambda s, e, D=D: D
            X = pd.DataFrame(oe.market((r.mkt, oe.END)), columns=oe.COLS); X = X[(X.sess == "LON") & (X.trig == r.trig)]; X = X[oe.fmask(X, r.filt)]
            parts.insert(0, X.set_index("day")[r.exit]); oe.load = load0
        s = pd.concat(parts).sort_index(); out[r.mkt] = s[~s.index.duplicated()]
    return out


def daily(ser, syms):
    df = pd.concat({m: ser[m] for m in syms}, axis=1)
    return pd.DataFrame({"net": df.sum(axis=1, min_count=1).fillna(0), "neg": df.clip(upper=0).sum(axis=1)})


def cycles(d, win, X, pess, end_data):
    a, b = WIN[win]; days = d.index
    st = [i for i, x in enumerate(days) if pd.Timestamp(a) <= x <= pd.Timestamp(b) and (end_data - x).days >= 30]
    if not st: return np.nan, np.nan, 0
    res = [cycle(d, i, X, pess) for i in st]
    s = np.array([r[0] for r in res]); n = np.array([r[1] for r in res])
    return np.mean((s == 1) & (n <= 30)), np.mean((s == 2) & (n <= 30)), len(st)


def main():
    pd.set_option("display.width", 250)
    ser = series(); syms = sorted(ser)
    ends = {"2026": pd.Timestamp("2026-10-02"), "2022-25": pd.Timestamp("2026-10-02"), "2020-21": pd.Timestamp("2021-11-30")}
    rows = []
    for k in range(1, len(syms) + 1):
        for combo in combinations(syms, k):
            d = daily(ser, combo)
            for X in SIZES:
                for pess in (False, True):
                    r = dict(combo="+".join(combo), k=k, X=X, line="pess" if pess else "opt")
                    for w in WIN:
                        dd = d[d.index <= ends[w]] if w == "2020-21" else d[d.index >= "2022-01-01"]
                        if w == "2020-21" and "DOW" in combo and len(combo) == 1: r.update({f"pass_{w}": np.nan, f"breach_{w}": np.nan}); continue
                        p, b_, n = cycles(dd, w, X, pess, ends[w]); r.update({f"pass_{w}": p, f"breach_{w}": b_})
                    rows.append(r)
    R = pd.DataFrame(rows); R.to_csv("data/si_ledgers/LON_COMBO.csv", index=False)
    cols = ["combo", "X", "pass_2026", "breach_2026", "pass_2022-25", "breach_2022-25", "pass_2020-21", "breach_2020-21"]
    o = R[R.line == "opt"]
    print("1. EACH SYMBOL ALONE, pass / breach within 30 days of each start (optimistic daily line):")
    print(o[o.k == 1][cols].round(3).to_string(index=False))
    print("\n2. ALL 127 COMBINATIONS: top 15 by 2026 pass rate within 30 days (optimistic line), with the same combination in 2022-25 and 2020-21:")
    print(o.sort_values(["pass_2026", "breach_2026"], ascending=[False, True]).head(15)[["combo", "k"] + cols[1:]].round(3).to_string(index=False))
    best = o.sort_values(["pass_2026", "breach_2026"], ascending=[False, True]).head(10)
    print(f"\n   top 10 by 2026: mean 2026 pass {best.pass_2026.mean():.1%} / breach {best.breach_2026.mean():.1%} -> 2022-25 {best['pass_2022-25'].mean():.1%} / {best['breach_2022-25'].mean():.1%} -> 2020-21 {best['pass_2020-21'].mean():.1%} / {best['breach_2020-21'].mean():.1%}")
    pr = o[(o["pass_2020-21"] > o["breach_2020-21"]) & (o["pass_2022-25"] > o["breach_2022-25"])]
    print(f"   combinations (any size) passing more than breaching in BOTH 2020-21 and 2022-25: {len(pr)} of {len(o)}")
    if len(pr): print(pr.sort_values("pass_2020-21", ascending=False).head(10)[["combo", "k"] + cols[1:]].round(3).to_string(index=False))
    p = R[R.line == "pess"]
    print("\n3. Pessimistic daily line, the same top 10 by 2026 (optimistic): ")
    print(p.set_index(["combo", "X"]).loc[[(c, x) for c, x in zip(best.combo, best.X)]][cols[2:]].round(3).to_string())


if __name__ == "__main__":
    main()
