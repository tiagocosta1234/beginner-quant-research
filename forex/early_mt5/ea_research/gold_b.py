"""Three gold trials exactly as registered in PREREG_GOLD_B.md (the trader 2026-10-09, "faz A e B", item B).
   python -m mt5broker.ea_research.gold_b --smoke | --g1 | --g23 | --holdout
G1 range fade on XAUUSD M15 (Bollinger 20/2 + ADX < 20); G2 / G3 SDB entries confirmed by a USD proxy / the 10-year real yield."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
MACRO = Path(r"D:\finance\data_macro")
LEDGER = HERE / "LEDGER.csv"
RES = HERE.parent / "ea_batch" / "mt5data"
PERIODS = {"SMOKE": ("2023-02-01", "2023-02-28"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP, STOP_ATR, MAX_BARS = 0.25, 1.5, 24


def bars15(name: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet").sort_values("t"); g = d.groupby(d.t // 900)
    b = pd.DataFrame({"bo": g.bo.first(), "bh": g.bh.max(), "bl": g.bl.min(), "bc": g.bc.last(), "ao": g.ao.first(), "ah": g.ah.max(), "al": g.al.min(), "ac": g.ac.last()}); b["t"] = b.index.to_numpy() * 900; b = b.reset_index(drop=True)
    pc = b.bc.shift(1); tr = pd.concat([b.bh - b.bl, (b.bh - pc).abs(), (b.bl - pc).abs()], axis=1).max(axis=1); b["atr"] = tr.rolling(14).mean()
    b["sma"] = b.bc.rolling(20).mean(); sd = b.bc.rolling(20).std(ddof=0); b["up"] = b.sma + 2 * sd; b["lo"] = b.sma - 2 * sd
    up, dn = b.bh.diff(), -b.bl.diff(); pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0); a = 1.0 / 14
    trs = tr.ewm(alpha=a, adjust=False).mean(); pdi = 100 * pd.Series(pdm).ewm(alpha=a, adjust=False).mean() / trs; mdi = 100 * pd.Series(mdm).ewm(alpha=a, adjust=False).mean() / trs
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi); b["adx"] = dx.ewm(alpha=a, adjust=False).mean()
    return b


def simulate(b: pd.DataFrame) -> pd.DataFrame:
    t = b.t.to_numpy("int64"); bo, bh, bl, bc, ao, ah, al = (b[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al")); atr, sma, up, lo, adx = (b[k].to_numpy() for k in ("atr", "sma", "up", "lo", "adx")); n = len(b)
    srv_h = (t % 86400) // 3600; srv_m = (t % 86400) // 60 % 60; days = t // 86400; rows = []; busy = -1; per_day = {}
    for k in range(60, n - 2):
        if k <= busy or not (np.isfinite(atr[k]) and np.isfinite(adx[k]) and np.isfinite(up[k])) or atr[k] <= 0 or adx[k] >= 20:
            continue
        s = 1 if bc[k] < lo[k] else (-1 if bc[k] > up[k] else 0)
        if s == 0:
            continue
        if (srv_h[k] == 23 and srv_m[k] >= 30) or srv_h[k] == 0 or (srv_h[k] == 1 and srv_m[k] < 30):
            continue
        if t[k + 1] - t[k] > 3600 or per_day.get(int(days[k]), 0) >= 2:
            continue
        e = k + 1; entry = ao[e] + SLIP if s > 0 else bo[e] - SLIP; R = STOP_ATR * atr[k]; stop = entry - s * R; tp = sma[k]; ex = None; j = e; why = ""
        while j < n:
            if s > 0:
                if bl[j] <= stop: ex = (min(stop, bo[j]) if j > e else stop) - SLIP; why = "stop"; break
                if bh[j] >= tp: ex = tp; why = "tp"; break
            else:
                if ah[j] >= stop: ex = (max(stop, ao[j]) if j > e else stop) + SLIP; why = "stop"; break
                if al[j] <= tp: ex = tp; why = "tp"; break
            if j - e + 1 >= MAX_BARS or (j + 1 < n and t[j + 1] - t[j] > 3600):
                jj = min(j + 1, n - 1); ex = (bo[jj] - SLIP) if s > 0 else (ao[jj] + SLIP); why = "time"; j = jj; break
            j += 1
        if ex is None:
            break
        pnl = s * (ex - entry); per_day[int(days[k])] = per_day.get(int(days[k]), 0) + 1
        rows.append(dict(t_in=int(t[e]), day=int(t[min(j, n - 1)] // 86400), side=s, pnl=pnl, r=pnl / R, bp=pnl / entry * 1e4, why=why)); busy = j
    return pd.DataFrame(rows)


def stats(T: pd.DataFrame, a: str, b: str) -> dict:
    t0, t1 = int(pd.Timestamp(a).timestamp()), int(pd.Timestamp(b).timestamp()) + 86400; X = T[(T.t_in >= t0) & (T.t_in < t1)] if len(T) else T
    if not len(X):
        return dict(trades=0, mean=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), bp=float("nan"))
    day = X.groupby("day").r.mean(); w, l_ = X.r[X.r > 0].sum(), -X.r[X.r <= 0].sum()
    return dict(trades=len(X), mean=float(X.r.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))) if len(day) > 2 and day.std(ddof=1) > 0 else float("nan"), win=float((X.r > 0).mean()), bp=float(X.bp.mean()))


def fmt(tag, s):
    return f"{tag:22s} trades {s['trades']:5d} | mean {s['mean']:+.3f} R ({s['bp']:+6.2f} bp) | PF {s['pf']:4.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}%"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gold_b,{trial},{period},,{s['trades']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def run_g1(holdout: bool):
    T = simulate(bars15("XAUUSD")); print(len(T), "trades in total; exits:", T.why.value_counts().to_dict(), "| long share", round((T.side > 0).mean(), 2), flush=True)
    for per in ("DEV", "VAL", "POOL"):
        s = stats(T, *PERIODS[per]); print(fmt(f"G1 {per}", s), flush=True); ledger("G1", per, s, "XAUUSD M15 BB20/2 + ADX<20 fade to SMA20")
    # control: the same signals in the opposite direction would be a breakout; not a trial, descriptive only (mirror by sign flip is NOT exact because stops/targets differ, so none is reported)
    # correlation with the live pair (12-month clean series)
    from mt5broker.ea_research import clean_boot_lib as L
    ser = L.series("MT5", 1.2); days = ser["days"]; V = dict(zip(days.tolist(), ser["V"].tolist()))
    X = T[(T.t_in >= int(pd.Timestamp("2025-10-01").timestamp())) & (T.t_in < int(pd.Timestamp("2026-10-01").timestamp()))]; g = X.groupby("day").pnl.sum()
    common = sorted(set(g.index.tolist()) & set(V)); allv = np.array([V.get(d, 0.0) for d in days.tolist()]); gg = np.array([g.get(d, 0.0) for d in days.tolist()])
    print(f"12-month daily correlation of G1 (USD per oz, all days, 0 when flat) with the pair's guarded daily P&L: {np.corrcoef(gg, allv)[0, 1]:+.3f} ({len(days)} days, {len(g)} with a G1 trade)")
    if holdout:
        s = stats(T, *PERIODS["HOLD"]); print(fmt("G1 HOLD-OUT", s)); ledger("G1", "HOLD", s, "one-time look")


def sdb_trades() -> pd.DataFrame:
    parts = []
    for y in ("2022", "2023", "2024", "2025", "2026"):
        d = pd.read_csv(RES / f"results_{y}" / "77900.csv"); d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S"); i = d[d.direction == "in"].reset_index(drop=True); o = d[d.direction == "out"].reset_index(drop=True); n = min(len(i), len(o))
        parts.append(pd.DataFrame({"t_in": i.time[:n], "entry": i.price[:n], "exit": o.price[:n], "pl": o.profit[:n]}))
    T = pd.concat(parts, ignore_index=True); mv = T.exit - T.entry
    T["side"] = np.where(mv == 0, 1.0, np.where(T.pl * mv >= 0, 1.0, -1.0)); T["bp"] = T.pl / T.entry * 1e4; T["day"] = T.t_in.dt.floor("D"); return T


def daily_close(name: str) -> pd.Series:
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet", columns=["t", "bc"]).sort_values("t"); s = d.groupby(d.t // 86400).bc.last(); s.index = pd.to_datetime(s.index * 86400, unit="s"); return s


def r5_before(close: pd.Series, day: pd.Timestamp) -> float:
    pos = int(close.index.searchsorted(day)) - 1
    return float((close.iloc[pos] / close.iloc[pos - 5] - 1) * 100) if pos >= 5 else float("nan")


def dy_before(y: pd.Series, day: pd.Timestamp) -> float:
    pos = int(y.index.searchsorted(day)) - 1
    return float(y.iloc[pos] - y.iloc[pos - 5]) if pos >= 5 else float("nan")


def perm_p(bp: np.ndarray, conf: np.ndarray, reps=20000, seed=7) -> tuple[float, float]:
    rng = np.random.default_rng(seed); obs = bp[conf].mean() - bp[~conf].mean(); k = conf.sum(); cnt = 0
    for _ in range(reps):
        p = rng.permutation(len(bp)); m = bp[p[:k]].mean() - bp[p[k:]].mean(); cnt += m >= obs
    return float(obs), (cnt + 1) / (reps + 1)


def run_filters(holdout: bool):
    T = sdb_trades(); print(len(T), "SDB trades 2022-26 on MT5 broker data; long share", round((T.side > 0).mean(), 2), "| mean bp", round(T.bp.mean(), 1), flush=True)
    eu, uj = daily_close("EURUSD"), daily_close("USDJPY"); y = pd.read_csv(MACRO / "DFII10.csv"); y.columns = ["d", "v"]; y["d"] = pd.to_datetime(y.d); y["v"] = pd.to_numeric(y.v, errors="coerce"); y = y.dropna().set_index("d").v.sort_index()
    T["S"] = [-r5_before(eu, d) + r5_before(uj, d) for d in T.day]; T["dy"] = [dy_before(y, d) for d in T.day]
    T["c2"] = np.where(T.side > 0, T.S <= 0, T.S >= 0); T["c3"] = np.where(T.side > 0, T.dy <= 0, T.dy >= 0)
    for trial, col, lab in (("G2", "c2", "USD proxy"), ("G3", "c3", "real yield")):
        print(f"\n=== {trial}: SDB confirmed by {lab}", flush=True)
        ok_all = True
        for per in ("DEV", "VAL", "POOL", "HOLD"):
            a, b = pd.Timestamp(PERIODS[per][0]), pd.Timestamp(PERIODS[per][1]) + pd.Timedelta(days=1); X = T[(T.t_in >= a) & (T.t_in < b) & T[col].notna()]
            if per == "HOLD" and not holdout:
                continue
            c, u = X[X[col]], X[~X[col]]; pf = lambda Z: (Z.bp[Z.bp > 0].sum() / -Z.bp[Z.bp <= 0].sum()) if (Z.bp <= 0).any() else float("inf")
            print(f"  {per:5s} confirmed {len(c):3d} ({100*len(c)/max(len(X),1):4.1f}%) mean {c.bp.mean():+7.1f} bp PF {pf(c):4.2f} | unconfirmed {len(u):3d} mean {u.bp.mean():+7.1f} bp PF {pf(u):4.2f} | diff {c.bp.mean() - u.bp.mean():+7.1f} bp", flush=True)
            s = dict(trades=len(c), mean=float(c.bp.mean()), pf=float(pf(c)), t=float("nan"), win=float((c.bp > 0).mean()))
            ledger(trial, per, s, f"confirmed n={len(c)} mean bp; unconfirmed n={len(u)} mean {u.bp.mean():+.1f} bp; diff {c.bp.mean() - u.bp.mean():+.1f}")
        X = T[(T.t_in >= pd.Timestamp(PERIODS["POOL"][0])) & (T.t_in < pd.Timestamp(PERIODS["POOL"][1]) + pd.Timedelta(days=1)) & T[col].notna()]; obs, p = perm_p(X.bp.to_numpy(), X[col].to_numpy())
        print(f"  pooled 2022-25 permutation test (one-sided): diff {obs:+.1f} bp, p = {p:.3f}  (bar 0.05; single test of this trial)")
        ledger(trial, "PERM", dict(trades=len(X), mean=obs, pf=float("nan"), t=float("nan"), win=float("nan")), f"permutation p {p:.3f}")
    # descriptive: does the relation gold vs real yield / USD proxy exist at all in this sample (5-day non-overlapping windows)
    g = daily_close("XAUUSD"); idx = g.index; rows = []
    for k in range(10, len(idx) - 5, 5):
        d0 = idx[k]; rows.append((float((g.iloc[k + 5] / g.iloc[k] - 1) * 100), dy_before(y, idx[k]), -r5_before(eu, idx[k]) + r5_before(uj, idx[k])))
    R = pd.DataFrame(rows, columns=["gold_fwd5", "dy_prev5", "S_prev5"]).dropna()
    print(f"\nDescriptive (non-overlapping 5-session windows, {len(R)}): corr(gold NEXT-5d return, previous-5d real-yield change) = {R.gold_fwd5.corr(R.dy_prev5):+.3f}; corr(gold next-5d, previous-5d USD proxy) = {R.gold_fwd5.corr(R.S_prev5):+.3f}  (|corr| < 0.12 is noise at this size)")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--g1", action="store_true"); ap.add_argument("--g23", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.smoke:
        b = bars15("XAUUSD"); T = simulate(b); t0, t1 = int(pd.Timestamp(PERIODS["SMOKE"][0]).timestamp()), int(pd.Timestamp(PERIODS["SMOKE"][1]).timestamp()); X = T[(T.t_in >= t0) & (T.t_in < t1)].copy(); X["in"] = pd.to_datetime(X.t_in, unit="s").dt.strftime("%m-%d %H:%M")
        pd.set_option("display.width", 200); print(X[["in", "side", "pnl", "r", "why"]].round(3).to_string()); print("bars with ADX<20:", round(float((b.adx < 20).mean()), 3), "| sample row:", b.iloc[5000][["bc", "sma", "up", "lo", "atr", "adx"]].round(2).to_dict())
        T2 = sdb_trades(); print(T2.head(3).to_string()); print(T2.groupby(T2.t_in.dt.year).size().to_dict(), "| side counts", T2.side.value_counts().to_dict())
    if a.g1:
        run_g1(a.holdout)
    if a.g23:
        run_filters(a.holdout)


if __name__ == "__main__":
    main()
