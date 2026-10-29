"""XMKT (PREREG_XMKT.md): cross-market and daily-pattern hypotheses from the trader's list.
   python -m forex.ea_research.xmkt --dry | (run)"""
import sys

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.orb11 import H, M, PER

END = pd.Timestamp("2026-10-03").timestamp()
NY = "America/New_York"


class Mk:
    def __init__(self, sym, end=END):
        D = load(sym, end); self.D = D; self.t = D["t"]; self.lc = local_clock(self.t, NY); self.sym = sym
        self.mid = (D["bo"] + D["ao"]) / 2

    def at(self, sec, tol=5 * M):
        """index of the first minute at or after New-York-local epoch second sec (None if the gap is > tol or server hour 23 / 0)."""
        k = int(np.searchsorted(self.lc, sec))
        if k >= len(self.t) or self.lc[k] - sec > tol: return None
        if (self.t[k] % 86400) // H in (23, 0): return None
        return k

    def trade(self, k_in, k_out, side):
        D = self.D
        e = D["ao"][k_in] if side > 0 else D["bo"][k_in]; x = D["bo"][k_out] if side > 0 else D["ao"][k_out]
        g = side * (self.mid[k_out] - self.mid[k_in]); m = self.mid[k_in]
        return side * (x - e) / m * 1e4, g / m * 1e4


def days(mk):
    return np.unique(mk.lc // 86400)


def rec(out, hyp, mk, k_in, k_out, side):
    if k_in is None or k_out is None or k_out <= k_in or side == 0: return
    n, g = mk.trade(k_in, k_out, side)
    out.append((hyp, mk.sym, pd.Timestamp(int(mk.t[k_in]) // 86400 * 86400, unit="s"), int(mk.t[k_in]), side, n, g))


def x10(out, M_):
    for mk in M_:
        for d in days(mk):
            b = d * 86400
            kp, k0, k1, k2 = mk.at(b - 86400 + 15 * H + 55 * M), mk.at(b + 9 * H + 30 * M), mk.at(b + 10 * H), mk.at(b + 15 * H + 55 * M)
            if None in (kp, k0, k1, k2) or pd.Timestamp(d * 86400, unit="s").weekday() == 0: continue
            on, rx = mk.mid[k0] - mk.mid[kp], mk.mid[k1] - mk.mid[k0]
            if np.sign(on) * np.sign(rx) < 0: rec(out, "X10", mk, k1, k2, int(np.sign(rx)))


def leadlag(out, hyp, L, F):
    hist = {}
    dl = days(F)
    for d in dl:
        b = d * 86400; grid = [b + 9 * H + 30 * M + 5 * M * i for i in range(19)]
        ks = [(L.at(s, 2 * M), F.at(s, 2 * M)) for s in grid]
        if any(a is None or c is None for a, c in ks): continue
        rl = np.diff([L.mid[a] for a, _ in ks]) / L.mid[ks[0][0]]; rf = np.diff([F.mid[c] for _, c in ks]) / F.mid[ks[0][1]]
        past = [v for dd in sorted(hist)[-20:] for v in hist[dd]]
        if len(past) >= 20 * 10:
            sl = np.std([p[0] for p in past]); sf = np.std([p[1] for p in past]); busy = -1
            for i in range(len(rl)):
                if i <= busy: continue
                zl, zf = rl[i] / sl, rf[i] / sf
                if abs(zl) > 1.5 and zf * np.sign(zl) < 0.5 * abs(zl):
                    s = int(np.sign(zl)); k_in = ks[i + 1][1] + 1 if i + 1 < len(ks) else None
                    k_out = F.at(F.lc[k_in] + 15 * M, 3 * M) if k_in is not None and k_in < len(F.t) else None
                    rec(out, hyp, F, k_in, k_out, s); busy = i + 3
        hist[d] = list(zip(rl, rf))


def signal_window(out, hyp, L, F, a, b, c, e, same=True, prev_day=False):
    for d in days(F):
        base = d * 86400
        la, lb = L.at(base - (86400 if prev_day else 0) + a), L.at(base + b)
        fi, fo = F.at(base + c), F.at(base + e)
        if None in (la, lb, fi, fo): continue
        s = int(np.sign(L.mid[lb] - L.mid[la])) * (1 if same else -1)
        rec(out, hyp, F, fi, fo, s)


def x15(out, W, C):
    cal = pd.read_csv("data/data_macro/mt5_calendar.csv", encoding="latin-1")
    ev = cal[cal.event_id == 840200001].time.drop_duplicates()
    tu = pd.to_datetime(ev, format="%Y.%m.%d %H:%M:%S").dt.tz_localize("UTC").dt.tz_convert("Europe/Athens").dt.tz_localize(None)
    for ts in tu.astype("datetime64[s]").astype("int64"):
        k0 = int(np.searchsorted(W.t, ts)); k1 = int(np.searchsorted(W.t, ts + 15 * M))
        if k1 >= len(W.t) or W.t[k0] - ts > 2 * M or W.t[k1] - ts - 15 * M > 2 * M: continue
        r = W.mid[k1] / W.mid[k0] - 1
        if abs(r) <= 0.003: continue
        ci, co = int(np.searchsorted(C.t, ts + 16 * M)), int(np.searchsorted(C.t, ts + 90 * M))
        if co >= len(C.t) or C.t[ci] - ts - 16 * M > 2 * M or (C.t[co] % 86400) // H in (23, 0): continue
        rec(out, "X15", C, ci, co, -int(np.sign(r)))


def x19(out, EJ, EU, UJ):
    df = pd.DataFrame({"t": EJ.t, "ej": EJ.mid, "sp": EJ.D["ao"] - EJ.D["bo"], "i": np.arange(len(EJ.t))})
    df = df.merge(pd.DataFrame({"t": EU.t, "eu": EU.mid}), on="t").merge(pd.DataFrame({"t": UJ.t, "uj": UJ.mid}), on="t")
    df["res"] = df.ej - df.eu * df.uj
    hr = (df.t % 86400) // H
    sig = df[(df.res.abs() > df.sp) & ~hr.isin([23, 0])]
    busy = 0
    for r in sig.itertuples():
        if r.t < busy: continue
        k_in = int(r.i) + 1
        k_out = int(np.searchsorted(EJ.t, r.t + 6 * M))
        if k_out >= len(EJ.t) or EJ.t[k_out] - r.t > 10 * M: continue
        rec(out, "X19", EJ, k_in, k_out, -int(np.sign(r.res))); busy = r.t + 6 * M


def x20(out, S, U, G):
    for d in days(S):
        b = d * 86400; ks = [S.at(b + 9 * H + 30 * M + i * M, 2 * M) for i in range(0, 331)]
        for i in range(30, len(ks)):
            if ks[i] is None or ks[i - 30] is None: continue
            if S.mid[ks[i]] / S.mid[ks[i - 30]] - 1 < -0.01:
                s0 = S.lc[ks[i]] + M
                for hyp, mk, side in (("X20a", U, -1), ("X20b", G, 1)):
                    ki = mk.at(s0, 2 * M); ko = mk.at(s0 + 60 * M, 3 * M) if ki is not None else None
                    rec(out, hyp, mk, ki, ko, side)
                break


def x34(out, M_):
    for mk in M_:
        t = mk.t; sd, sod = t // 86400, t % 86400
        ok = (sod >= H) & (sod < 22 * H + 55 * M)
        g = pd.DataFrame({"d": sd[ok], "h": mk.D["mh"][ok], "l": mk.D["ml"][ok], "c": mk.mid[ok], "i": np.flatnonzero(ok)}).groupby("d").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
        dl = g.index.to_numpy()
        for j in range(len(dl) - 1):
            rng_ = g.h.iloc[j] - g.l.iloc[j]
            if not rng_ > 0: continue
            pos = (g.c.iloc[j] - g.l.iloc[j]) / rng_
            s = 1 if pos >= 0.9 else (-1 if pos <= 0.1 else 0)
            if s == 0: continue
            nd = dl[j + 1]
            ki, ko = int(np.searchsorted(t, nd * 86400 + H + 5 * M)), int(np.searchsorted(t, nd * 86400 + 22 * H + 45 * M))
            if ko >= len(t) or t[ki] // 86400 != nd or t[ko] // 86400 != nd: continue
            rec(out, "X34", mk, ki, ko, s)


def run(end=END):
    mk = {s: Mk(s, end) for s in ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "USDJPY", "WTI", "USDCAD", "XAUUSD", "EURJPY", "EURUSD")}
    out = []
    x10(out, [mk["SP"], mk["NSDQ"], mk["DOW"]])
    leadlag(out, "X11", mk["SP"], mk["NSDQ"]); leadlag(out, "X12", mk["NSDQ"], mk["SP"])
    signal_window(out, "X13", mk["DAX"], mk["SP"], 3 * H, 9 * H + 25 * M, 9 * H + 35 * M, 11 * H + 30 * M)
    signal_window(out, "X14", mk["NIKKEI"], mk["USDJPY"], 20 * H, 2 * H, 3 * H, 7 * H, prev_day=True)
    x15(out, mk["WTI"], mk["USDCAD"])
    signal_window(out, "X18", mk["DAX"], mk["SP"], 3 * H, 11 * H + 30 * M, 11 * H + 35 * M, 15 * H + 55 * M)
    x19(out, mk["EURJPY"], mk["EURUSD"], mk["USDJPY"])
    x20(out, mk["SP"], mk["USDJPY"], mk["XAUUSD"])
    x34(out, [mk[s] for s in ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "XAUUSD")])
    return pd.DataFrame(out, columns=["hyp", "mkt", "day", "t_entry", "side", "net_bp", "gross_bp"])


def tstat(x):
    x = np.asarray(x, float); return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def main():
    pd.set_option("display.width", 250)
    if "--dry" in sys.argv:
        T = run(); print(T.groupby("hyp").size().to_string())
        print(T.groupby("hyp").head(1)[["hyp", "mkt", "day", "t_entry", "side"]].assign(srv=lambda x: pd.to_datetime(x.t_entry, unit="s")).to_string(index=False))
        cut = pd.Timestamp("2024-06-01").timestamp(); Tc = run(cut)
        sel = lambda X: X[X.t_entry < cut - 2 * 86400].sort_values(["hyp", "mkt", "t_entry"]).reset_index(drop=True)[["hyp", "mkt", "t_entry", "side", "net_bp"]]
        a, b = sel(T), sel(Tc)
        same = len(a) == len(b) and np.allclose(a.net_bp, b.net_bp) and (a.side.values == b.side.values).all()
        print("truncation:", len(a), len(b), "identical" if same else "DIFFERENT")
        if not same:
            m = a.merge(b, on=["hyp", "mkt", "t_entry"], how="outer", indicator=True); print(m[m._merge != "both"].groupby("hyp").size())
        return
    T = run(); T.to_parquet("data/si_ledgers/XMKT.parquet")
    rows = []
    for h, g in T.groupby("hyp"):
        p = {k: g[(g.day >= a) & (g.day <= b)] for k, (a, b) in PER.items()}
        dv = pd.concat([p["DEV"], p["VAL"]])
        r = dict(hyp=h, n=len(dv), gross=dv.gross_bp.mean(), net=dv.net_bp.mean(), win=(dv.net_bp > 0).mean(), t=tstat(dv.net_bp),
                 DEV=p["DEV"].net_bp.mean(), VAL=p["VAL"].net_bp.mean(), Y26=p["Y26"].net_bp.mean(), n26=len(p["Y26"]))
        r["pass"] = bool(r["n"] >= 100 and r["t"] >= 2.61 and r["DEV"] > 0 and r["VAL"] > 0 and r["Y26"] > 0)
        rows.append(r)
    R = pd.DataFrame(rows)
    print("net / gross in basis points per trade (DEV 2022-24 + VAL 2025), by period:")
    print(R.round(2).to_string(index=False))
    print("\nby market, net bp 2022-25:", T[(T.day <= "2025-12-31")].groupby(["hyp", "mkt"]).net_bp.agg(["size", "mean"]).round(2).to_string())
    R.to_csv("data/si_ledgers/XMKT.csv", index=False)


if __name__ == "__main__":
    main()
