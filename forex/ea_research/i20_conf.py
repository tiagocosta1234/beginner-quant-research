"""I20_CONF: 7 pre-registered confluences for the I20 post-expansion-day fade, in-sample 2022-25 shortlist (PREREG_I20_CONF.md).
No 2026 row is read.   python -m forex.ea_research.i20_conf"""
import numpy as np, pandas as pd
from forex.ea_research.brk50 import Mkt, ts, LIS, CACHE

FLAGS = ["C1_continuation", "C2_close_at_extreme", "C3_stretched_5d", "C4_rsi2_extreme", "C5_morning", "C6_slow_approach", "C7_isolated_spike"]


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def features(sym, ev):
    M = Mkt(sym); Dd = M.Dd; rs = rsi2(Dd.C).to_numpy(); out = []
    for r in ev.itertuples():
        p = M.pos.get(int(r.day.timestamp()) // 86400)
        if p is None or p < 6:
            continue
        y, yy = Dd.iloc[p - 1], Dd.iloc[p - 2]; atr = Dd.atr.iloc[p]
        pdh = r.side < 0                                                       # fade short at PDH, long at PDL
        up = y.C > y.O
        cp = (y.C - y.L) / (y.H - y.L)
        ch5 = y.C - Dd.C.iloc[p - 6]
        k = int(np.searchsorted(M.t, r.t_entry)) - 1                            # the touch minute (entry is the next minute)
        mv30 = M.mc[k] - M.mc[k - 30]
        out.append(dict(sym=sym, t_entry=r.t_entry,
                        C1_continuation=(pdh and up) or ((not pdh) and (not up)),
                        C2_close_at_extreme=(cp >= 0.75) if pdh else (cp <= 0.25),
                        C3_stretched_5d=(ch5 >= 1.5 * atr) if pdh else (ch5 <= -1.5 * atr),
                        C4_rsi2_extreme=(rs[p - 1] >= 90) if pdh else (rs[p - 1] <= 10),
                        C5_morning=(M.t[k] < ts(r.day.year, r.day.month, r.day.day, 12, 0, LIS)),
                        C6_slow_approach=(mv30 < 0.25 * atr) if pdh else (-mv30 < 0.25 * atr),
                        C7_isolated_spike=(yy.H - yy.L) < 1.2 * Dd.atr.iloc[p - 2]))
    return pd.DataFrame(out)


def wt(a, b):
    se = np.sqrt(a.var() / len(a) + b.var() / len(b)); return (a.mean() - b.mean()) / se if se > 0 else np.nan


def main():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T = pd.read_parquet(CACHE); E = T[(T.idea == "I20") & (T.day < "2026-01-01")].copy()
    F = pd.concat([features(s, g) for s, g in E.groupby("sym")], ignore_index=True)
    E = E.merge(F, on=["sym", "t_entry"]); E["per"] = np.where(E.day < "2025-01-01", "2022-24", "2025")
    print(f"I20 trades 2022-25: {len(E)} (2022-24 {int((E.per == '2022-24').sum())}, 2025 {int((E.per == '2025').sum())}); all: "
          f"{E[E.per=='2022-24'].R.mean():+.3f} / {E[E.per=='2025'].R.mean():+.3f} R\n")
    kept = []
    for c in FLAGS:
        w, wo = E[E[c]], E[~E[c]]
        r_dev = (w[w.per == "2022-24"].R.mean(), wo[wo.per == "2022-24"].R.mean()); r_val = (w[w.per == "2025"].R.mean(), wo[wo.per == "2025"].R.mean())
        t = wt(w.R, wo.R)
        keep = (w.R.mean() > wo.R.mean() and t >= 2.0 and r_dev[0] > r_dev[1] and r_val[0] > r_val[1] and r_dev[0] > 0 and r_val[0] > 0 and len(w) >= 80)
        kept += [c] if keep else []
        print(f"{c:20s} with n {len(w):3d} {w.R.mean():+.3f} R (win {(w.R > 0).mean():.2f}) | without n {len(wo):3d} {wo.R.mean():+.3f} | diff t {t:+.2f}"
              f" | 2022-24 {r_dev[0]:+.3f} vs {r_dev[1]:+.3f} | 2025 {r_val[0]:+.3f} vs {r_val[1]:+.3f} -> {'KEEP' if keep else 'drop'}")
    print("\nkept:", kept or "none")
    rule = E[np.logical_and.reduce([E[c] for c in kept])] if kept else E
    lab = " AND ".join(kept) if kept else "I20 as is"
    print(f"shortlist rule ({lab}): n {len(rule)}, 2022-24 {rule[rule.per=='2022-24'].R.mean():+.3f} R, 2025 {rule[rule.per=='2025'].R.mean():+.3f} R (IN-SAMPLE)")
    print("\nby class (2022-25, I20 as is):", E.assign(cls=E.sym.map(__import__('forex.ea_research.analog', fromlist=['mclass']).mclass)).groupby("cls").R.agg(["size", "mean"]).round(3).to_dict("index"))
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1621)
    for label, sel, risk, cap in (("NSDQ+XAUUSD $250", rule[rule.sym.isin(["NSDQ", "XAUUSD"])], 250, 10), ("38 markets $50, <= 5/day", rule, 50, 5),
                                  ("38 markets $250, <= 5/day", rule, 250, 5)):
        if not len(sel):
            continue
        sel = sel.sort_values("t_entry").groupby("day").head(cap)
        Rd = sel.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        print(f"  account {label} ({len(sel)} trades 2022-25, {sel.R.mean():+.3f} R, in-sample): " + "  ".join(
            f"{k} pass {100*np.mean((st==1)&(ev<h)):.1f}% / breach {100*np.mean((st==2)&(ev<h)):.0f}%" for k, h in HZ.items() if k in ("22 Dec", "31 Mar 27", "30 Jun 27")))


if __name__ == "__main__":
    main()
