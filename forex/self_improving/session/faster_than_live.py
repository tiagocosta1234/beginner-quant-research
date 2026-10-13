"""Can we assemble a system faster than the live one? Same pipeline for both: daily series from the 1-minute guard simulator (clean_guard_sim, MT5 broker daily-loss and counted-profit rules), day-block bootstrap (pass70.simulate, 20,000 paths, 250 business days).
Baseline = the live plan without ManualDip: pair x1.5, daily loss stop 1.5%, no profit stop. Candidates: size {1.5, 2, 2.5, 3} x loss stop {1500, 2000} x profit stop {none, 2000} x SDB runner {off, on}. Selection on FT 2022-24 (as history only):
max P(pass<=44 business days) with breach <= 5%; the picks and the baseline are then reported on the MT5 broker pool only. python -m forex.self_improving.session.faster_than_live"""
import itertools
import numpy as np, pandas as pd
from forex.ea_research import pass70 as P
from forex.self_improving.session import session_sdbrunner as R
from forex.ea_research import clean_boot_lib as L
from forex.ea_research.combo_grid import bars

P.C0 = 0.0; H = 250; NONE = 1e9


def series(tr, lo, hi, m, Pc, Lc, ref=None):
    t = {k: np.array(v, copy=True) for k, v in tr.items()}; t["q"] = t["q"] * m; t["pl"] = t["pl"] * m
    r = L.C.simulate(bars, t, lo, hi, Pc, Lc); idx = pd.Index(r["days"]); return dict(V=np.asarray(r["V"], float), B=np.asarray(r["B"], float), Hi=np.asarray(r["Hi"], float), days=np.asarray(r["days"]))


def stats(S):
    st, dy = P.simulate([S] * len(P.MULTS), P.I12, H); ps = st == 1
    return dict(p22=100 * np.mean(ps & (dy < 22)), p44=100 * np.mean(ps & (dy < 44)), p66=100 * np.mean(ps & (dy < 66)), p120=100 * np.mean(ps & (dy < 120)), breach=100 * np.mean(st == 2), med=float(np.median(dy[ps] + 1)) if ps.any() else np.nan)


def main():
    TRN = R.load_flag("FT", "2022-01-01", "2024-12-31"); MT5 = R.load_flag("MT5"); rows = []
    cfgs = [(m, Lc, Pc, rn) for m, Lc, Pc, rn in itertools.product((1.5, 2.0, 2.5, 3.0), (1500.0, 2000.0), (NONE, 2000.0), (False, True))]
    for nm, T in (("train", TRN), ("MT5", MT5)):
        tr, lo, hi = T; trs = {False: tr, True: R.runner_leg(tr, 0, "sdb")}
        for m, Lc, Pc, rn in cfgs:
            rows.append(dict(window=nm, m=m, loss=Lc, profit=("none" if Pc == NONE else Pc), runner=rn, **stats(series(trs[rn], lo, hi, m, Pc, Lc))))
    d = pd.DataFrame(rows); d.to_csv("D:/finance/si_ledgers/FASTER_THAN_LIVE.csv", index=False)
    tr = d[d.window == "train"]; mt5 = d[d.window == "MT5"]
    base = mt5[(forex.m == 1.5) & (forex.loss == 1500) & (forex.profit == "none") & (~forex.runner)].iloc[0]; print("BASELINE (live plan x1.5, stop 1.5%, no ManualDip) on MT5:", {k: round(float(base[k]), 1) for k in ("p22", "p44", "p66", "p120", "breach", "med")})
    ok = tr[tr.breach <= 5].sort_values("p44", ascending=False).head(5); print("train picks (breach<=5%):"); print(ok.round(1).to_string(index=False))
    out = []
    for t in ok.itertuples():
        r = mt5[(forex.m == t.m) & (forex.loss == t.loss) & (forex.profit.astype(str) == str(t.profit)) & (forex.runner == t.runner)].iloc[0]; out.append(r)
    print("same configs on MT5:"); print(pd.DataFrame(out).round(1).to_string(index=False))
    print("all MT5 broker configs by median days (breach<=5%):"); print(mt5[forex.breach <= 5].sort_values("med").head(8).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
