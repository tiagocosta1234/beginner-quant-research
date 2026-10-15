"""D2X (PREREG_SWAPFREE_D2X.md): the D2 swap-free drift book with more markets. OOT on MT5 D1 bars, DEV / VAL (/ HOLD) on MT5 M1.
   python -m forex.ea_research.swapfree_d2x --dry-run | --run | --hold X1"""
import sys

import numpy as np
import pandas as pd

from forex.ea_research import swapfree_drift as S

BASE = ("SP", "NSDQ", "DAX", "NIKKEI", "XAUUSD")
VAR = {"REF_D2": BASE, "X1": BASE + ("BTCUSD", "ETHUSD"), "X2": BASE + ("XAGUSD", "DOW", "ASX"), "X3": BASE + ("BTCUSD", "ETHUSD", "XAGUSD", "DOW", "ASX")}
FT = {"SP": "US500.cash", "NSDQ": "US100.cash", "DAX": "GER40.cash", "NIKKEI": "JP225.cash", "XAUUSD": "XAUUSD", "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD",
      "XAGUSD": "XAGUSD", "DOW": "US30.cash", "ASX": "AUS200.cash", "EURUSD": "EURUSD", "USDJPY": "USDJPY", "AUDUSD": "AUDUSD"}
FXM = ("EURUSD", "USDJPY", "AUDUSD")
S.CCY.update({"ASX": "AUDUSD"})
S.DROP_DAX_OOT = False
ALL = VAR["X3"]


def ft_daily(m, spread):
    d = pd.read_parquet(f"D:/finance/beginner-quant-research/forex/data/{FT[m]}_D1.parquet")
    d.index = pd.to_datetime(d.time // 86400 * 86400, unit="s"); d = d[(d.index >= "2020-01-01") & (d.index < "2021-12-01")]
    return pd.DataFrame({"mark": d.close, "low": d.low, "bo": d.close, "ao": d.close + spread})


def build():
    E = {m: S.daily(S.load_mt5(m)) for m in ALL + FXM}
    F = {m: ft_daily(m, S.mt5_spread18(m) if m not in FXM else 0.0) for m in ALL + FXM}
    C = {}
    for m in ALL:
        e, h = E[m].mark, F[m].mark; C[m] = pd.concat([h * (e.iloc[0] / h.iloc[-1]), e])
    return E, F, pd.DataFrame(C).sort_index().ffill()


def main():
    E, F, C = build()
    if "--dry-run" in sys.argv:
        for m in ALL:
            print(f"{m}: MT5 OOT days {len(F[m])} ({F[m].index.min().date()}..{F[m].index.max().date()}), MT5 broker days {len(E[m])}, splice ratio {E[m].mark.iloc[0] / F[m].mark.iloc[-1]:.4f}, MT5 broker spread18 {S.mt5_spread18(m):.3f}")
        for x in (pd.Timestamp("2022-06-13"), pd.Timestamp("2025-03-03")):
            S.MK = ALL; a, _ = S.signals(C[list(ALL)], x, "D2"); b, _ = S.signals(C[C.index <= x][list(ALL)], x, "D2")
            assert np.allclose(a.fillna(0), b.fillna(0)); print("weights", x.date(), a.round(3).to_dict())
        print("truncation test passed"); return
    hold = sys.argv[sys.argv.index("--hold") + 1] if "--hold" in sys.argv else None
    rows = []; ser = {}
    for v, mk in VAR.items():
        if hold and v not in (hold, "REF_D2"): continue
        S.MK = mk
        for p, (a, b) in S.PER.items():
            if (p == "HOLD") != bool(hold): continue
            s = S.run_book(F if p == "OOT" else E, C, "D2", a, b); ser[(v, p)] = s
            st = S.stats(s); rows.append(dict(variant=v, period=p, **st, trades=s.attrs["trades"]))
            print(f"{v} {p}: mean {st['mean']:+.1f}/day per 100k, t {st['t']:+.2f}, Sharpe {st['sharpe']:+.2f}, maxDD {st['maxdd']:.0f}, worst low {st['worst_day']:.0f}, by market {({k: round(x) for k, x in s.attrs['bym'].items()})}", flush=True)
        if not hold:
            st = S.stats(pd.concat([ser[(v, 'DEV')], ser[(v, 'VAL')]])); rows.append(dict(variant=v, period="DEV+VAL", **st))
            print(f"{v} DEV+VAL: t {st['t']:+.2f} Sharpe {st['sharpe']:+.2f} (bar t >= 2.13; Sharpe above REF_D2 in DEV and VAL)")
    tag = f"HOLD_{hold}" if hold else "RUN"
    pd.DataFrame(rows).to_csv(f"D:/finance/si_ledgers/D2X_{tag}.csv", index=False)
    pd.concat({f"{k[0]}_{k[1]}": s for k, s in ser.items()}).to_parquet(f"D:/finance/si_ledgers/D2X_{tag}_series.parquet")


if __name__ == "__main__":
    main()
