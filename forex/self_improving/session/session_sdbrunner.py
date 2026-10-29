"""Runner mode ('let winners run to break-even stop or 22:00') applied per leg: none / both legs / SDB only / XAU5 only, SAFE base (L1500, m0 1.5), same-day and two-day. Fixed comparison, nothing tuned.
python -m forex.self_improving.session.session_sdbrunner"""
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L
from forex.ea_research.combo_grid import news_flat, bars, CH
from forex.self_improving.session import session_lab as S, session_mgmt as M


def load_flag(pool, lo_s=None, hi_s=None):
    src, a, b = L.POOLS[pool]; lo = L.day(lo_s or a); hi = L.day(hi_s or b)
    s = L.ea_trades(src, "sdb", CH["sdb"], lo); x = L.ea_trades(src, "xau5", CH["xau5"], lo); s["ea"] = np.ones(len(s["in_s"])); x["ea"] = np.zeros(len(x["in_s"]))
    tr = news_flat(L.merge(s, x), G.EV, bars); o = np.argsort(tr["in_s"], kind="stable"); return {k: v[o] for k, v in tr.items()}, lo, hi


def runner_leg(tr, days, leg):
    t = M.runner(tr, days); keep = (tr["ea"] == 1) if leg == "sdb" else (tr["ea"] == 0)
    for k in ("out_s", "pl", "exit"): t[k] = np.where(keep, t[k], tr[k])
    return t


def main():
    rows = []
    for nm, T in (("train FT 2022-24", load_flag("FT", "2022-01-01", "2024-12-31")), ("MT5 12m", load_flag("MT5"))):
        tr, lo, hi = T; print(nm, "trades", len(tr["in_s"]), "SDB", int((tr["ea"] == 1).sum()), "XAU5", int((tr["ea"] == 0).sum()), flush=True)
        for mode, days in (("none", None), ("same-day", 0), ("two-day", 1)):
            for leg in (("-",) if days is None else ("both", "sdb", "xau5")):
                t = tr if days is None else (M.runner(tr, days) if leg == "both" else runner_leg(tr, days, leg)); S.BOOST = 0.0; df = S.run(t, lo, hi, 1500.0, 1.5, 0.0, 0.0, 0.0); o = M.m(df)
                rows.append(dict(window=nm, mode=mode, leg=leg, **o)); print(f"{nm:17s} {mode:8s} {leg:5s}: +2000 {o['up']:.1f}% -1500 {o['down']:.1f}% ratio {o['ratio']:.0f}% | P44 {o['p44']:.1f}% P120 {o['p120']:.1f}% breach {o['breach']:.1f}% med {o['med']:.0f}", flush=True)
    pd.DataFrame(rows).to_csv("data/si_ledgers/SESSION_sdbrunner.csv", index=False)


if __name__ == "__main__":
    main()
