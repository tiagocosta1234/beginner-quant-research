"""Family H, exactly as registered in PREREG_EDGE_H.md (the trader 2026-10-09 evening: "we need another edge, far greater than our current one").
   python -m mt5broker.ea_research.edge_h --smoke | --trials | --holdout
H1 gold / silver ratio mean reversion, H2 Brent / WTI ratio mean reversion (daily, two legs), H3 overnight index drift (cash close -> next cash open) on six index CFDs; control for H3: open -> close."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
PERIODS = {"SMOKE": ("2023-03-01", "2023-04-30"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP_PAIR = {"XAUUSD": 0.25, "XAGUSD": 0.02, "BRENT": 0.04, "WTI": 0.04}
SESS = {"SP": ("America/New_York", 930, 1600), "NSDQ": ("America/New_York", 930, 1600), "DOW": ("America/New_York", 930, 1600),
        "DAX": ("Europe/Berlin", 900, 1730), "NIKKEI": ("Asia/Tokyo", 900, 1500), "ASX": ("Australia/Sydney", 1000, 1600)}
IDX_SLIP = 0.12e-4


def load(name: str, cols=("t", "bo", "bc", "ao", "ac", "sp")) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}_M1_rates.parquet", columns=list(cols)).sort_values("t").reset_index(drop=True)


def daily(name: str) -> pd.DataFrame:
    d = load(name); g = d.groupby(d.t // 86400)
    o = pd.DataFrame({"ob": g.bo.first(), "oa": g.ao.first(), "cb": g.bc.last()}); o["sp"] = o.oa - o.ob; return o


def spread_trial(n1: str, n2: str, z_in=2.0, z_out=0.5, z_stop=4.0, win=60, max_days=30):
    a, b = daily(n1), daily(n2); idx = a.index.intersection(b.index); a, b = a.loc[idx], b.loc[idx]; days = idx.to_numpy(); n = len(days)
    lr = np.log(a.cb.to_numpy() / b.cb.to_numpy()); m = pd.Series(lr).rolling(win).mean().to_numpy(); s = pd.Series(lr).rolling(win).std(ddof=0).to_numpy(); z = (lr - m) / s
    o1, c1, sp1 = a.ob.to_numpy(), a.cb.to_numpy(), a.sp.to_numpy(); o2, c2, sp2 = b.ob.to_numpy(), b.cb.to_numpy(), b.sp.to_numpy(); k1, k2 = SLIP_PAIR[n1], SLIP_PAIR[n2]
    pnl = np.zeros(n); trades = []; i = win
    while i < n - 2:
        if not np.isfinite(z[i]) or abs(z[i]) < z_in:
            i += 1; continue
        side = -1 if z[i] > 0 else 1                                     # z high -> ratio too high -> short the ratio (short leg 1, long leg 2)
        e = i + 1; cost_in = (sp1[e] / o1[e] if side > 0 else sp2[e] / o2[e]) + k1 / o1[e] + k2 / o2[e]
        tot = side * ((c1[e] / o1[e] - 1) - (c2[e] / o2[e] - 1)) - cost_in; pnl[e] += side * ((c1[e] / o1[e] - 1) - (c2[e] / o2[e] - 1)) - cost_in; d = e; x = None
        while d < n - 1:
            ex = (z[d] * side >= -z_out) or (d - e + 1 >= max_days) or (z[d] * side <= -z_stop)    # z*side: for a long ratio (side +1) entry z <= -2 -> exit when z >= -0.5 ; stop when z <= -4
            if ex:
                x = d + 1; g = side * ((o1[x] / c1[x - 1] - 1) - (o2[x] / c2[x - 1] - 1)); cost_out = (sp2[x] / o2[x] if side > 0 else sp1[x] / o1[x]) + k1 / o1[x] + k2 / o2[x]
                pnl[x] += g - cost_out; tot += g - cost_out; break
            d += 1; step = side * ((c1[d] / c1[d - 1] - 1) - (c2[d] / c2[d - 1] - 1)); pnl[d] += step; tot += step
        if x is None:
            break
        trades.append(dict(day_in=int(days[e]), day_out=int(days[x]), side=side, bp=tot * 1e4, held=int(x - e))); i = x
    return pd.DataFrame(dict(day=days, bp=pnl * 1e4)), pd.DataFrame(trades)


def index_trial(name: str, overnight: bool = True) -> pd.DataFrame:
    tz, op, cl = SESS[name]; d = load(name, ("t", "bo", "ao")); ts = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward")
    ok = ts.notna().to_numpy(); d = d[ok].reset_index(drop=True); loc = ts[ok].dt.tz_convert(tz); hm = (loc.dt.hour * 100 + loc.dt.minute).to_numpy(); date = loc.dt.date.to_numpy(); t = d.t.to_numpy()
    bo, ao = d.bo.to_numpy(), d.ao.to_numpy(); s_open, s_close = {}, {}
    for k in np.nonzero(hm == op)[0]:
        s_open.setdefault(date[k], k)
    for k in np.nonzero(hm == cl)[0]:
        s_close.setdefault(date[k], k)
    rows = []; dates = sorted(s_close if overnight else s_open); odates = sorted(s_open)
    for dd in dates:
        if overnight:
            k_in = s_close[dd]; nxt = [x for x in odates if x > dd]
            if not nxt or (nxt[0] - dd).days > 5: continue
            k_out = s_open[nxt[0]]; gap = (nxt[0] - dd).days
        else:
            if dd not in s_close: continue
            k_in = s_open[dd]; k_out = s_close[dd]; gap = 0
        entry = ao[k_in] * (1 + IDX_SLIP); exit_ = bo[k_out] * (1 - IDX_SLIP)
        rows.append(dict(name=name, date=pd.Timestamp(dd), t_in=int(t[k_in]), bp=(exit_ / entry - 1) * 1e4, nights=gap))
    return pd.DataFrame(rows)


def t_stat(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def period_slice(df: pd.DataFrame, col: str, a: str, b: str) -> pd.DataFrame:
    lo, hi = int(pd.Timestamp(a).timestamp()) // 86400, int(pd.Timestamp(b).timestamp()) // 86400
    return df[(df[col] >= lo) & (df[col] <= hi)]


def pair_series():
    from mt5broker.ea_research import clean_boot_lib as L
    s = L.series("MT5", 1.2); return dict(zip(s["days"].tolist(), s["V"].tolist()))


def ledger(trial, period, trades, mean, pf, t, win, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},edge_h,{trial},{period},,{trades},,{mean:.4f},{pf:.3f},{t:.2f},{win:.3f},{note}\n")


def pf_of(x: np.ndarray) -> float:
    w, l_ = x[x > 0].sum(), -x[x <= 0].sum(); return float(w / l_) if l_ > 0 else float("inf")


def run_pair(trial: str, n1: str, n2: str, holdout: bool, pairV: dict):
    ser, tr = spread_trial(n1, n2); print(f"\n=== {trial}: {n1}/{n2} ratio mean reversion; {len(tr)} trades in total, mean held {tr.held.mean():.1f} days, long-ratio share {(tr.side > 0).mean():.2f}", flush=True)
    for per in ("DEV", "VAL", "POOL") + (("HOLD",) if holdout else ()):
        S = period_slice(ser, "day", *PERIODS[per]); T = period_slice(tr, "day_in", *PERIODS[per]); x = S.bp.to_numpy(); tt = t_stat(x); sh = x.mean() / x.std(ddof=1) * np.sqrt(252) if x.std(ddof=1) > 0 else float("nan")
        print(f"  {per:5s} trades {len(T):3d} | mean/trade {T.bp.mean():+7.1f} bp | PF {pf_of(T.bp.to_numpy()) if len(T) else float('nan'):4.2f} | win {100*(T.bp > 0).mean() if len(T) else float('nan'):4.1f}% | daily t (all days) {tt:+5.2f} | Sharpe {sh:+5.2f} | mean/day {x.mean():+6.2f} bp", flush=True)
        ledger(trial, per, len(T), float(T.bp.mean()) if len(T) else float("nan"), pf_of(T.bp.to_numpy()) if len(T) else float("nan"), tt, float((T.bp > 0).mean()) if len(T) else float("nan"), f"{n1}/{n2}; bp per trade; Sharpe {sh:.2f}")
    S = period_slice(ser, "day", "2025-10-01", "2026-09-30"); a = np.array([pairV.get(int(d), 0.0) for d in S.day]); b = S.bp.to_numpy()
    print(f"  12-month daily correlation with the pair: {np.corrcoef(a, b)[0, 1]:+.3f} (the pair's own daily t over the same days: {t_stat(a):+.2f})")


def run_index(holdout: bool, pairV: dict):
    for trial, over in (("H3", True), ("DIAG-H3-daytime", False)):
        R = pd.concat([index_trial(n, over) for n in SESS], ignore_index=True); print(f"\n=== {trial}: {'overnight (cash close -> next open)' if over else 'daytime control (open -> close)'}; {len(R)} index-trades", flush=True)
        R["day"] = R.t_in // 86400
        for per in ("DEV", "VAL", "POOL") + (("HOLD",) if holdout and over else ()):
            X = period_slice(R, "day", *PERIODS[per]); D = X.groupby("day").bp.mean(); x = D.to_numpy(); tt = t_stat(x); sh = x.mean() / x.std(ddof=1) * np.sqrt(252) if x.std(ddof=1) > 0 else float("nan")
            per_ix = " ".join(f"{k} {v:+.1f}" for k, v in X.groupby("name").bp.mean().items())
            print(f"  {per:5s} index-trades {len(X):5d} | mean {X.bp.mean():+6.2f} bp | PF {pf_of(X.bp.to_numpy()):4.2f} | win {100*(X.bp > 0).mean():4.1f}% | daily t {tt:+5.2f} | Sharpe {sh:+5.2f} | per index bp: {per_ix}", flush=True)
            ledger(trial, per, len(X), float(X.bp.mean()), pf_of(X.bp.to_numpy()), tt, float((X.bp > 0).mean()), f"equal-weight daily mean of 6 indices; Sharpe {sh:.2f}")
        if over:
            X = R[R.nights >= 3]; W = R[R.nights < 3]; print(f"  split (POOL not shown): weekend nights (3+) {len(X)} trades mean {X.bp.mean():+.2f} bp | one-night {len(W)} trades mean {W.bp.mean():+.2f} bp")
            S = period_slice(R, "day", "2025-10-01", "2026-09-30").groupby("day").bp.mean(); a = np.array([pairV.get(int(d), 0.0) for d in S.index]); print(f"  12-month daily correlation with the pair: {np.corrcoef(a, S.to_numpy())[0, 1]:+.3f}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.smoke:
        ser, tr = spread_trial("XAUUSD", "XAGUSD"); lo, hi = [int(pd.Timestamp(x).timestamp()) // 86400 for x in PERIODS["SMOKE"]]; pd.set_option("display.width", 200)
        print(tr[(tr.day_in >= lo - 400) & (tr.day_in <= hi + 400)].head(8).round(1).to_string()); print(len(tr), "trades; series days", len(ser), "sum bp", round(float(ser.bp.sum()), 1), "| sum of trade bp", round(float(tr.bp.sum()), 1))
        for nm in ("DAX", "NIKKEI"):
            R = index_trial(nm); print(nm, len(R), "overnight trades, mean bp", round(float(R.bp.mean()), 2), R.tail(3).to_string())
    if a.trials or a.holdout:
        pairV = pair_series(); run_pair("H1", "XAUUSD", "XAGUSD", a.holdout, pairV); run_pair("H2", "BRENT", "WTI", a.holdout, pairV); run_index(a.holdout, pairV)


if __name__ == "__main__":
    main()
