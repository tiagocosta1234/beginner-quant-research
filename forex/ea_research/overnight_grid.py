"""Family N2: the overnight try-everything grid, exactly as registered in PREREG_OVERNIGHT_GRID.md.
   python -m forex.ea_research.overnight_grid --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research import event_macro as V

HERE = Path(__file__).resolve().parent
STATE = HERE / "OVERNIGHT_GRID_STATE.json"
MK = {"SP": ("America/New_York", (16, 0), (9, 30)), "NSDQ": ("America/New_York", (16, 0), (9, 30)), "DOW": ("America/New_York", (16, 0), (9, 30)),
      "DAX": ("Europe/Berlin", (17, 30), (9, 0)), "NIKKEI": ("Asia/Tokyo", (15, 0), (9, 0)), "ASX": ("Australia/Sydney", (16, 0), (10, 0)), "XAUUSD": ("America/New_York", (16, 0), (9, 30))}
TIMING = {"T5": (5, 5), "T2": (2, 2), "T60": (5, 60)}
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def srv(day: str, tz: str, hh: int, mm: int, add_min: int) -> int:
    ts = (pd.Timestamp(f"{day} {hh:02d}:{mm:02d}").tz_localize(tz) + pd.Timedelta(minutes=add_min)).tz_convert("Europe/Athens").tz_localize(None)
    return int((ts - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def nights(m: str, timing: str, last: str) -> pd.DataFrame:
    tz, (ch, cm), (oh, om) = MK[m]; e, x = TIMING[timing]; days = pd.bdate_range("2021-06-01", last); rows = []
    for i, D in enumerate(days[:-1]):
        N = days[i + 1]; d, n = str(D.date()), str(N.date())
        qe, qx, qo = V.quote(m, srv(d, tz, ch, cm, -e)), V.quote(m, srv(n, tz, oh, om, x)), V.quote(m, srv(d, tz, oh, om, 5))
        if qe is None or qx is None: continue
        rows.append(dict(date=D, wk=(N - D).days > 1, dow=D.dayofweek, net=(qx[0] / qe[1] - 1.0) * 1e4 - 2 * V.SLIP * 1e4, px=(qe[0] + qe[1]) / 2,
                         day=np.nan if qo is None else ((qe[0] + qe[1]) / (qo[0] + qo[1]) - 1.0) * 1e4))
    return pd.DataFrame(rows).set_index("date")


def frame(m: str, timing: str, last: str) -> pd.DataFrame:
    if m != "US-EW": return nights(m, timing, last)
    parts = [nights(k, timing, last) for k in ("SP", "NSDQ", "DOW")]; idx = parts[0].index.intersection(parts[1].index).intersection(parts[2].index)
    F = parts[0].loc[idx].copy(); F["net"] = sum(p.loc[idx, "net"] for p in parts) / 3; F["day"] = sum(p.loc[idx, "day"] for p in parts) / 3
    F["px"] = np.exp(sum(np.log(p.loc[idx, "px"]) for p in parts) / 3); return F


def filters(F: pd.DataFrame) -> dict:
    px = F.px; s200, s50 = px.rolling(200, min_periods=150).mean(), px.rolling(50, min_periods=40).mean()
    vol = F.net.rolling(20).std().shift(1); vmed = vol.rolling(250, min_periods=120).median()
    return {"none": pd.Series(True, index=F.index), "trend200": px > s200, "trend50": px > s50, "below200": px < s200, "lowvol": vol < vmed, "highvol": vol > vmed,
            "afterdown": F.day < 0, "afterup": F.day > 0, "montue": F.dow.isin([0, 1]), "trend200_lowvol": (px > s200) & (vol < vmed)}


def grid(last="2025-12-31") -> pd.DataFrame:
    cols = {}
    for m in ("US-EW",) + tuple(MK):
        for tm in TIMING:
            F = frame(m, tm, last)
            for fn, ok in filters(F).items():
                for wkend in ("monthu", "all"):
                    act = ok.fillna(False) & (~F.wk if wkend == "monthu" else True)
                    cols[f"{m}|{tm}|{fn}|{wkend}"] = F.net.where(act, 0.0)
    G = pd.DataFrame(cols).fillna(0.0); return G[G.index >= "2022-01-01"]


def sl(G, p): return G[(G.index >= p[0]) & (G.index <= p[1])]


def tstat(X): return X.mean() / (X.std(ddof=1) / np.sqrt(len(X)))


def dev():
    G = grid(); G.to_parquet("D:/finance/tmp/overnight_grid.parquet"); d, v = sl(G, PER["DEV"]), sl(G, PER["VAL"]); T = tstat(d)
    print(f"variants {G.shape[1]} | DEV nights {len(d)} | DEV t: median {T.median():+.2f}, share > 0 {100*(T > 0).mean():.0f}%, share >= 2 {100*(T >= 2).mean():.1f}%, best {T.max():+.2f} ({T.idxmax()})")
    rng = np.random.default_rng(5); X = (d - d.mean()).to_numpy(); n = len(X); mx = []
    for _ in range(300):
        idx = np.empty(n, int); idx[0] = rng.integers(n)
        for j in range(1, n): idx[j] = rng.integers(n) if rng.random() < 0.2 else (idx[j - 1] + 1) % n
        Y = X[idx]; sd = Y.std(0, ddof=1); mx.append(np.nanmax(np.where(sd > 0, Y.mean(0) / (sd / np.sqrt(n)), np.nan)))
    q95 = float(np.percentile(mx, 95)); print(f"reality check: best DEV t under the null median {np.median(mx):+.2f}, 95th pct {q95:+.2f}; real best {T.max():+.2f}, p = {np.mean(np.array(mx) >= T.max()):.3f}")
    top = T.sort_values(ascending=False).head(15); print("top 15 by DEV t (with VAL 2025):")
    for k, t in top.items(): print(f"   {k:34s} DEV t {t:+.2f} mean {d[k].mean():+6.2f} bp/night | VAL mean {v[k].mean():+6.2f} t {tstat(v[k]):+.2f}")
    print("by filter (median DEV t over markets/timings):", T.groupby(T.index.str.split("|").str[2]).median().round(2).to_dict())
    print("by market (median DEV t):", T.groupby(T.index.str.split("|").str[0]).median().round(2).to_dict())
    surv = [k for k in T.index if T[k] > q95 and v[k].mean() > 0]; print(f"variants above the null 95th pct: {int((T > q95).sum())}; of those positive in VAL 2025: {len(surv)} -> {surv}")
    with open(V.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},overnight_grid,GRID,DEV,{len(d)},{G.shape[1]},,,,{T.max():.2f},,best {T.idxmax()}; null95 {q95:.2f}; survivors {len(surv)}\n")
    STATE.write_text(json.dumps(dict(survivors=surv, q95=q95, best=float(T.max()))))


def holdout():
    st = json.loads(STATE.read_text()); s = st["survivors"]
    if not s: print("No variant beat the reality check and 2025: the 2026 hold-out stays CLOSED."); return
    G = grid("2026-09-30"); h = sl(G, PER["HOLD"])[s].mean(axis=1); print(f"HOLD 2026 portfolio of {len(s)}: mean {h.mean():+.2f} bp/night t {tstat(h):+.2f} worst {h.min():+.1f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev: dev()
    if a.holdout: holdout()
