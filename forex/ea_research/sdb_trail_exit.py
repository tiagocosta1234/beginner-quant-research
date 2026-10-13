"""Variant X1: the SDB entries (frozen rule, MT5 broker gold) with a trailing exit instead of the fixed 1.9% target, exactly as registered in PREREG_SDB_TRAIL_EXIT.md.
   python -m forex.ea_research.sdb_trail_exit --smoke | --trials | --holdout
Entries from forex/intraday_lab/sdb.py (frozen rule); fills / exits on MT5 broker's M1 bid / ask bars; no commission."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab.sdb import h1_bars, daily_hl, stoch_signal, bands

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
PCT, EXPIRY, K, D, S, BP = 1.9, 9, 23, 3, 7, 9
PERIODS = {"SMOKE": ("2022-01-01", "2022-06-30"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def load_mt5():
    m = pd.read_parquet(DATA / "XAUUSD_M1_rates.parquet").sort_values("t"); return {k: m[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")} | {"t": m.t.to_numpy("int64")}


def simulate(m1, exit_mode: str, start="2021-12-15", end="2026-10-02") -> pd.DataFrame:
    """exit_mode 'frozen' (stop = target = 1.9%) or 'trail' (initial stop 1.9%, no target, trailing 1.9% from the best price up to the previous bar)."""
    t1 = m1["t"]; ht, ho, hh, hl, hc = h1_bars(m1); sig = stoch_signal(hc, K, D, S); up, lo_b = bands(ho, hh, hl, hc, BP); dd, dH, dL = daily_hl(m1)
    t_lo, t_hi = int(pd.Timestamp(start).timestamp()), int(pd.Timestamp(end).timestamp()) + 86400; trades = []; pend = {1: None, -1: None}; busy_until = -1; i0 = int(np.searchsorted(ht, t_lo)); n = len(ht)
    for i in range(max(i0, 30), n):
        t0 = int(ht[i])
        if t0 > t_hi:
            break
        for sd_ in (1, -1):
            if pend[sd_] is not None and i - pend[sd_]["i"] >= EXPIRY:
                pend[sd_] = None
        if t0 >= busy_until and i >= 5:
            s3, s2, s1 = sig[i - 3], sig[i - 2], sig[i - 1]; turn_down = s3 < s2 and s2 > s1; turn_up = s3 > s2 and s2 < s1; open3 = ho[i - 3]
            buy = open3 < up[i - 4] and turn_down; sell = open3 > lo_b[i - 4] and turn_up
            if buy or sell:
                d = int(np.searchsorted(dd, t0 // 86400)) - 1
                if d >= 0:
                    j0 = int(np.searchsorted(t1, t0))
                    if buy and dH[d] > m1["ao"][j0]:
                        pend[1] = dict(i=i, level=float(dH[d]))
                    elif sell and not buy and dL[d] < m1["bo"][j0]:
                        pend[-1] = dict(i=i, level=float(dL[d]))
        j0 = int(np.searchsorted(t1, t0)); j1 = int(np.searchsorted(t1, t0 + 3600))
        for side in (1, -1):
            pd_ = pend[side]
            if pd_ is None or j1 <= j0:
                continue
            L = pd_["level"]; hit = (m1["ah"][j0:j1] >= L) if side > 0 else (m1["bl"][j0:j1] <= L)
            if not hit.any():
                continue
            jf = j0 + int(np.argmax(hit)); pend[side] = None; p_fill = max(L, m1["ao"][jf]) if side > 0 else min(L, m1["bo"][jf]); sd = L * PCT / 100.0; sl = L - side * sd
            if exit_mode == "frozen":
                tp = L + side * sd
                if side > 0:
                    stop_hit = m1["bl"][jf:] <= sl; tp_hit = m1["bh"][jf:] >= tp
                else:
                    stop_hit = m1["ah"][jf:] >= sl; tp_hit = m1["al"][jf:] <= tp
                a = int(np.argmax(stop_hit)) if stop_hit.any() else 10 ** 12; b = int(np.argmax(tp_hit)) if tp_hit.any() else 10 ** 12
                if a == b == 10 ** 12:
                    busy_until = int(t1[-1]) + 1; continue
                if a <= b:
                    je = jf + a; op = m1["bo"][je] if side > 0 else m1["ao"][je]; px = min(sl, op) if side > 0 else max(sl, op)
                else:
                    je = jf + b; px = tp
            else:
                if side > 0:
                    best = np.maximum.accumulate(np.maximum(m1["bh"][jf:], p_fill)); prev = np.r_[p_fill, best[:-1]]; stop = np.maximum(sl, prev - sd); hitv = m1["bl"][jf:] <= stop
                else:
                    best = np.minimum.accumulate(np.minimum(m1["al"][jf:], p_fill)); prev = np.r_[p_fill, best[:-1]]; stop = np.minimum(sl, prev + sd); hitv = m1["ah"][jf:] >= stop
                if not hitv.any():
                    busy_until = int(t1[-1]) + 1; continue
                a = int(np.argmax(hitv)); je = jf + a; op = m1["bo"][je] if side > 0 else m1["ao"][je]; px = min(stop[a], op) if side > 0 else max(stop[a], op)
            pnl = (px - p_fill) * side
            trades.append(dict(t_entry=int(t1[jf]), t_exit=int(t1[je]), side=side, entry=p_fill, exit=px, sd=sd, R=pnl / sd, pnl=pnl, hold_d=(int(t1[je]) - int(t1[jf])) / 86400)); busy_until = max(busy_until, int(t1[je]) + 60)
    return pd.DataFrame(trades)


def pf(R):
    w, l = R[R > 0].sum(), -R[R <= 0].sum(); return float(w / l) if l > 0 else float("inf")


def stats(B: pd.DataFrame, X: pd.DataFrame, a: str, b: str) -> dict:
    t0, t1 = int(pd.Timestamp(a).timestamp()), int(pd.Timestamp(b).timestamp()) + 86400; Bp = B[(B.t_entry >= t0) & (B.t_entry < t1)]; Xp = X[(X.t_entry >= t0) & (X.t_entry < t1)]
    com = Bp.merge(Xp, on="t_entry", suffixes=("_b", "_x")); dlt = (com.R_x - com.R_b).to_numpy(); n = len(dlt)
    t = float(dlt.mean() / (dlt.std(ddof=1) / np.sqrt(n))) if n > 2 and dlt.std(ddof=1) > 0 else float("nan")
    return dict(nb=len(Bp), nx=len(Xp), rb=float(Bp.R.mean()), rx=float(Xp.R.mean()), nb_net=float(Bp.R.sum()), nx_net=float(Xp.R.sum()), pfb=pf(Bp.R), pfx=pf(Xp.R), common=n, dmean=float(dlt.mean()) if n else float("nan"), dt=t, holdb=float(Bp.hold_d.mean()), holdx=float(Xp.hold_d.mean()), maxx=float(Xp.R.max()) if len(Xp) else float("nan"))


def fmt(tag, s):
    return (f"{tag:10s} B0: n {s['nb']:3d} mean {s['rb']:+.3f} R net {s['nb_net']:+7.1f} R PF {s['pfb']:4.2f} hold {s['holdb']:4.1f} d | X1: n {s['nx']:3d} mean {s['rx']:+.3f} R net {s['nx_net']:+7.1f} R PF {s['pfx']:4.2f} hold {s['holdx']:4.1f} d max {s['maxx']:+.1f} R"
            f" | common {s['common']:3d} paired dR {s['dmean']:+.3f} t {s['dt']:+5.2f}")


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},sdb_trail_exit,{trial},{period},,{s['nx']},{s['nx_net']:.1f},{s['rx']:.3f},{s['pfx']:.3f},{s['dt']:.2f},,{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    m1 = load_mt5(); B = simulate(m1, "frozen"); X = simulate(m1, "trail")
    if a.smoke:
        pd.set_option("display.width", 200); t0, t1 = int(pd.Timestamp(PERIODS["SMOKE"][0]).timestamp()), int(pd.Timestamp(PERIODS["SMOKE"][1]).timestamp())
        for nm, T in (("B0 frozen", B), ("X1 trail", X)):
            Y = T[(T.t_entry >= t0) & (T.t_entry < t1)].copy(); Y["in"] = pd.to_datetime(Y.t_entry, unit="s").dt.strftime("%Y-%m-%d %H:%M"); print(f"--- {nm}: {len(T)} trades in total, first of 2022 H1"); print(Y[["in", "side", "entry", "exit", "R", "hold_d"]].head(6).round(3).to_string())
        print("trades per year B0:", B.groupby(pd.to_datetime(B.t_entry, unit="s").dt.year).size().to_dict(), "| X1:", X.groupby(pd.to_datetime(X.t_entry, unit="s").dt.year).size().to_dict())
    if a.trials:
        for per in ("DEV", "VAL", "POOL"):
            s = stats(B, X, *PERIODS[per]); print(fmt(per, s), flush=True); ledger("X1", per, s, f"paired dR {s['dmean']:+.3f}; B0 net {s['nb_net']:+.1f} R PF {s['pfb']:.2f}")
    if a.holdout:
        s = stats(B, X, *PERIODS["HOLD"]); print(fmt("HOLD", s)); ledger("X1", "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
