"""PREREG_XS_MOM_IDX: cross-country index momentum, long top 2 / short bottom 2 of SP, NSDQ, DOW, DAX, NIKKEI, ASX, weekly. Uses the swapfree_drift book engine
(run_book handles negative units: P&L u x d(bid), spread paid on every buy, incl. buy-to-close). OOT on MT5 D1, DEV / VAL on MT5 M1.
   python -m forex.ea_research.xs_mom_idx --dry-run | --run | --hold C1"""
import sys

import numpy as np
import pandas as pd

from forex.ea_research import swapfree_d2x as X
from forex.ea_research import swapfree_drift as S

U = ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX")
LOOK = {"C1": 252, "C2": 63}
S.CCY.update({"ASX": "AUDUSD"}); S.DROP_DAX_OOT = False
CELL = "C1"


def xs_signals(C, day, variant):
    past = C[C.index < day]; n = LOOK[CELL]
    z = pd.Series(0.0, index=C.columns)
    if len(past) < n + 6 or past.iloc[-(n + 6):].isna().any().any(): return z, z != 0
    vol = np.log(past).diff().iloc[-60:].std() * np.sqrt(252)
    score = (past.iloc[-6] / past.iloc[-(n + 1)] - 1) / vol
    r = score.sort_values(); lo, hi = r.index[:2], r.index[-2:]
    iv = 1 / vol
    z[hi] = 0.5 * iv[hi] / iv[hi].sum(); z[lo] = -0.5 * iv[lo] / iv[lo].sum()
    return z, z != 0


def build():
    E = {m: S.daily(S.load_mt5(m)) for m in U + X.FXM}
    F = {m: X.ft_daily(m, S.mt5_spread18(m) if m not in X.FXM else 0.0) for m in U + X.FXM}
    C = {}
    for m in U:
        e, h = E[m].mark, F[m].mark; C[m] = pd.concat([h * (e.iloc[0] / h.iloc[-1]), e])
    return E, F, pd.DataFrame(C).sort_index().ffill()


def main():
    global CELL
    S.signals = xs_signals; S.MK = U
    E, F, C = build()
    if "--dry-run" in sys.argv:
        for CELL in LOOK:
            for x in (pd.Timestamp("2021-06-07"), pd.Timestamp("2023-05-01"), pd.Timestamp("2025-09-01")):
                a, _ = xs_signals(C, x, ""); b, _ = xs_signals(C[C.index <= x], x, "")
                assert np.allclose(a, b); print(CELL, x.date(), a.round(3).to_dict())
        print("truncation test passed"); return
    hold = sys.argv[sys.argv.index("--hold") + 1] if "--hold" in sys.argv else None
    rows, ser = [], {}
    for CELL in LOOK:
        if hold and CELL != hold: continue
        for p, (a, b) in S.PER.items():
            if (p == "HOLD") != bool(hold): continue
            s = S.run_book(F if p == "OOT" else E, C, "XS", a, b); ser[(CELL, p)] = s
            s = s[s.index >= s.index[np.argmax(s.V.to_numpy() != 0)]] if (s.V != 0).any() else s   # from the first traded day
            st = S.stats(s); rows.append(dict(cell=CELL, period=p, **st, trades=s.attrs.get("trades", np.nan)))
            print(f"{CELL} {p}: days {st['days']}, mean {st['mean']:+.1f}/day per 100k gross, t {st['t']:+.2f}, Sharpe {st['sharpe']:+.2f}, maxDD {st['maxdd']:.0f}", flush=True)
        if not hold:
            st = S.stats(pd.concat([ser[(CELL, 'DEV')], ser[(CELL, 'VAL')]])); rows.append(dict(cell=CELL, period="DEV+VAL", **st))
            print(f"{CELL} DEV+VAL: t {st['t']:+.2f} Sharpe {st['sharpe']:+.2f} (bar 1.96)")
    R = pd.read_parquet("data/si_ledgers/SWAPFREE_RUN_series.parquet")
    for c in LOOK:
        if (c, "DEV") in ser:
            j = pd.concat([ser[(c, "DEV")].V, ser[(c, "VAL")].V]).to_frame("x").join(pd.concat([R.loc["D2_DEV"], R.loc["D2_VAL"]]).V.rename("d2"), how="inner")
            print(f"{c} daily correlation with D2 (2022-25): {j.corr().iloc[0, 1]:+.3f}")
    tag = f"HOLD_{hold}" if hold else "RUN"
    pd.DataFrame(rows).to_csv(f"data/si_ledgers/XS_MOM_IDX_{tag}.csv", index=False)


if __name__ == "__main__":
    main()
