"""Family I, exactly as registered in PREREG_ORB_GOLD.md (the trader 2026-10-09: "operacoes frequentes, risco de 1%, super lucrosa", ideas from the Comet search).
   python -m forex.ea_research.orb_gold --smoke | --trials | --holdout
Gold 30-minute opening-range breakout: I1 London 08:00 (Europe/London), I2 New York 09:30 (America/New_York); stop = opposite side of the box, target 1.0 R, 4-hour window, OCO stop orders, MT5 M1 bid / ask bars."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
PERIODS = {"SMOKE": ("2023-03-01", "2023-03-31"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP, BOX_MIN, WIN_MIN, TARGET_R = 0.05, 30, 240, 1.0
CLOCKS = {"I1": ("Europe/London", 8, 0), "I2": ("America/New_York", 9, 30)}


def load() -> pd.DataFrame:
    return pd.read_parquet(DATA / "XAUUSD_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").reset_index(drop=True)


def trades_for(d: pd.DataFrame, tz: str, hh: int, mm: int) -> pd.DataFrame:
    ts = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward"); ok = ts.notna().to_numpy(); d = d[ok].reset_index(drop=True); loc = ts[ok].dt.tz_convert(tz)
    hm = (loc.dt.hour * 100 + loc.dt.minute).to_numpy(); date = loc.dt.date.to_numpy(); t = d.t.to_numpy("int64"); bo, bh, bl, bc, ao, ah, al = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al")); n = len(d); rows = []; seen = set()
    for k in np.nonzero(hm == hh * 100 + mm)[0]:
        if date[k] in seen: continue
        seen.add(date[k]); tb = t[k]; b = int(np.searchsorted(t, tb + BOX_MIN * 60)); e = int(np.searchsorted(t, tb + (BOX_MIN + WIN_MIN) * 60))
        if b - k < 28 or e - b < 200 or b >= n: continue
        H, L = bh[k:b].max(), bl[k:b].min(); R = H - L
        if R <= 0: continue
        pos = 0; entry = stop = tgt = 0.0; j0 = -1; res = None
        for j in range(b, e):
            if pos == 0:
                lt, st = ah[j] >= H, bl[j] <= L
                if lt and st:
                    res = (-(1.0) - (ao[j] - bo[j] + 2 * SLIP) / R, "both", j); break
                if lt:
                    pos = 1; entry = max(H, ao[j]) + SLIP; stop = L; tgt = entry + TARGET_R * R; j0 = j; continue
                if st:
                    pos = -1; entry = min(L, bo[j]) - SLIP; stop = H; tgt = entry - TARGET_R * R; j0 = j; continue
            else:
                if pos == 1:
                    if bl[j] <= stop: res = ((min(stop, bo[j]) - SLIP - entry) / R, "stop", j); break
                    if bh[j] >= tgt: res = ((tgt - entry) / R, "tp", j); break
                else:
                    if ah[j] >= stop: res = ((entry - (max(stop, ao[j]) + SLIP)) / R, "stop", j); break
                    if al[j] <= tgt: res = ((entry - tgt) / R, "tp", j); break
        if res is None:
            if pos == 0: continue                                           # no break inside the window
            jj = min(e, n - 1); ex = bo[jj] if pos == 1 else ao[jj]; res = ((ex - entry) / R if pos == 1 else (entry - ex) / R, "time", jj)
        rows.append(dict(date=pd.Timestamp(date[k]), t_in=int(t[b]), side=pos, r=res[0], why=res[1], R=R, cost_share=(ao[b] - bo[b] + 2 * SLIP) / R))
    return pd.DataFrame(rows)


def stats(T: pd.DataFrame, a: str, b: str) -> dict:
    X = T[(T.date >= pd.Timestamp(a)) & (T.date <= pd.Timestamp(b))]
    if not len(X): return dict(trades=0, mean=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), ret=float("nan"), dd=float("nan"), cs=float("nan"))
    day = X.groupby("date").r.sum(); w, l_ = X.r[X.r > 0].sum(), -X.r[X.r <= 0].sum(); eq = np.cumprod(1 + 0.01 * X.sort_values("date").r.to_numpy()); dd = float((1 - eq / np.maximum.accumulate(eq)).max())
    return dict(trades=len(X), mean=float(X.r.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))) if len(day) > 2 and day.std(ddof=1) > 0 else float("nan"), win=float((X.r > 0).mean()), ret=float(eq[-1] - 1), dd=dd, cs=float(X.cost_share.mean()))


def fmt(tag, s):
    return f"{tag:16s} trades {s['trades']:5d} | mean {s['mean']:+.3f} R | PF {s['pf']:4.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | cost share of R {100*s['cs']:4.1f}% | 1% risk: return {100*s['ret']:+7.1f}% maxDD {100*s['dd']:4.1f}%"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},orb_gold,{trial},{period},,{s['trades']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args(); d = load()
    if a.smoke:
        T = trades_for(d, *CLOCKS["I2"]); X = T[(T.date >= PERIODS["SMOKE"][0]) & (T.date <= PERIODS["SMOKE"][1])]; pd.set_option("display.width", 200); print(X.round(3).to_string()); print(len(T), "I2 trades;", T.why.value_counts().to_dict())
    if a.trials or a.holdout:
        from forex.ea_research import clean_boot_lib as L
        s = L.series("MT5", 1.2); V = dict(zip(s["days"].tolist(), s["V"].tolist())); alld = s["days"].tolist(); pooled = []
        for trial, clk in CLOCKS.items():
            T = trades_for(d, *clk); pooled.append(T.assign(trial=trial)); print(f"\n=== {trial} {clk[0]} {clk[1]:02d}:{clk[2]:02d}: {len(T)} trades; exits {T.why.value_counts().to_dict()}; long share {(T.side > 0).mean():.2f}", flush=True)
            for per in ("DEV", "VAL", "POOL") + (("HOLD",) if a.holdout else ()):
                st = stats(T, *PERIODS[per]); print(fmt(f"{trial} {per}", st), flush=True); ledger(trial, per, st, f"{clk[0]} {clk[1]:02d}:{clk[2]:02d} box 30m target 1R; 1% risk return {100*st['ret']:.1f}% maxDD {100*st['dd']:.1f}%")
            for y in range(2022, 2027):
                st = stats(T, f"{y}-01-01", f"{y}-12-31"); print(f"   {y}: trades {st['trades']:4d} mean {st['mean']:+.3f} R PF {st['pf']:4.2f} cost share of R {100*st['cs']:4.1f}%")
            X = T[(T.date >= "2025-10-01") & (T.date <= "2026-09-30")]; day = X.assign(day=X.t_in // 86400).groupby("day").r.sum(); b = np.array([day.get(dd, 0.0) for dd in alld]); a_ = np.array([V[dd] for dd in alld])
            print(f"   12-month daily correlation with the pair: {np.corrcoef(a_, b)[0, 1]:+.3f}")
        P = pd.concat(pooled); st = stats(P.groupby(["date", "trial"], as_index=False).first().assign(r=P.groupby(["date", "trial"]).r.sum().values), *PERIODS["DEV"]); print(f"\nBoth sessions DEV: {st['trades']} trades, mean {st['mean']:+.3f} R, trades per month {st['trades']/36:.1f}")


if __name__ == "__main__":
    main()
