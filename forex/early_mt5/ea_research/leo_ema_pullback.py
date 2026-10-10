"""Rule E1: the LeoTrades morning pullback setup, mechanical version, exactly as registered in PREREG_LEO_EMA_PULLBACK.md (SP, NSDQ, DOW; MT5 M1 bars).
   python -m mt5broker.ea_research.leo_ema_pullback --smoke | --trials | --holdout
New York time derived from the MT5 broker server clock (Europe/Athens); window 09:35-12:00 NY; bias = M5 EMA20 (completed bars), trigger = touch and bounce of the M1 EMA20; two legs (1 R and 2 R), stop 0.10%."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
SLIP = 0.12e-4
RPCT = 0.001
NAMES = ["SP", "NSDQ", "DOW"]
PERIODS = {"SMOKE": ("2023-03-06", "2023-03-10"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def prep(name: str):
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet").sort_values("t").reset_index(drop=True)
    ny = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("America/New_York")
    d["hm"] = (ny.dt.hour * 100 + ny.dt.minute).where(ny.notna(), -1).astype(int); d["date"] = ny.dt.date; d["e1"] = d.bc.ewm(span=20, adjust=False).mean()
    blk = d.t // 300; g = d.groupby(blk); m5 = pd.DataFrame({"c": g.bc.last()}); m5["ema"] = m5.c.ewm(span=20, adjust=False).mean(); m5["up"] = (m5.c > m5.ema) & (m5.ema > m5.ema.shift(3)); m5["dn"] = (m5.c < m5.ema) & (m5.ema < m5.ema.shift(3))
    bias5 = (m5.up.astype(int) - m5.dn.astype(int)); prev = bias5.shift(1)                       # the previous COMPLETED M5 block only
    d["bias"] = blk.map(prev).fillna(0).astype(int).to_numpy()
    return d


def trades_for(name: str) -> pd.DataFrame:
    d = prep(name); rows = []
    for date, day in d.groupby("date", sort=True):
        w = day[(day.hm >= 935) & (day.hm <= 1200)]
        if len(w) < 100:
            continue
        t, hm = w.t.to_numpy(), w.hm.to_numpy(); bo, bh, bl, bc, ao, ah, al, ac = (w[k].to_numpy() for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")); e1, bias = w.e1.to_numpy(), w.bias.to_numpy(); n = len(w)
        trades_today = 0; k = 0
        while k < n - 2:
            if hm[k] >= 1158 or trades_today >= 2:
                break
            s = 0
            if bias[k] > 0 and bl[k] <= e1[k] < bc[k]:
                s = 1
            elif bias[k] < 0 and bh[k] >= e1[k] > bc[k]:
                s = -1
            if s == 0:
                k += 1; continue
            e = k + 1; entry = ao[e] * (1 + SLIP) if s > 0 else bo[e] * (1 - SLIP); R = RPCT * entry; stop = entry - s * R; tpA, tpB = entry + s * R, entry + 2 * s * R; stopB = stop; legA = legB = True; pnlA = pnlB = 0.0; j = e; exit_t = t[e]; why = ""
            while j < n:
                hitA = False
                if s > 0:
                    if legA and bl[j] <= stop:
                        pnlA = (min(stop, bo[j]) * (1 - SLIP) - entry); legA = False
                    if legB and bl[j] <= stopB:
                        pnlB = (min(stopB, bo[j]) * (1 - SLIP) - entry); legB = False
                    if legA and bh[j] >= tpA:
                        pnlA = tpA - entry; legA = False; hitA = True
                    if legB and bh[j] >= tpB:
                        pnlB = tpB - entry; legB = False
                else:
                    if legA and ah[j] >= stop:
                        pnlA = (entry - max(stop, ao[j]) * (1 + SLIP)); legA = False
                    if legB and ah[j] >= stopB:
                        pnlB = (entry - max(stopB, ao[j]) * (1 + SLIP)); legB = False
                    if legA and al[j] <= tpA:
                        pnlA = entry - tpA; legA = False; hitA = True
                    if legB and al[j] <= tpB:
                        pnlB = entry - tpB; legB = False
                if hitA and legB:
                    stopB = entry                                              # breakeven for leg B from the NEXT bar
                exit_t = t[j]
                if not legA and not legB:
                    why = "legs"; break
                if hm[j] >= 1200 or j == n - 1:
                    if legA:
                        pnlA = (bo[j] * (1 - SLIP) - entry) if s > 0 else (entry - ao[j] * (1 + SLIP)); legA = False
                    if legB:
                        pnlB = (bo[j] * (1 - SLIP) - entry) if s > 0 else (entry - ao[j] * (1 + SLIP)); legB = False
                    why = "time"; break
                j += 1
            r = 0.5 * (pnlA + pnlB) / R; rows.append(dict(name=name, date=pd.Timestamp(date), side=s, entry=entry, r=r, bp=0.5 * (pnlA + pnlB) / entry * 1e4, why=why, hold_min=(exit_t - t[e]) / 60)); trades_today += 1
            k = max(j, e) + 1
    return pd.DataFrame(rows)


def stats(T: pd.DataFrame, a: str, b: str) -> dict:
    X = T[(T.date >= pd.Timestamp(a)) & (T.date <= pd.Timestamp(b))]
    if not len(X):
        return dict(days=0, trades=0, mean=float("nan"), bp=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), per="", npos=0, tm=float("nan"))
    day = X.groupby("date").r.mean(); w, l_ = X.r[X.r > 0].sum(), -X.r[X.r <= 0].sum(); per = X.groupby("name").r.mean()
    return dict(days=len(day), trades=len(X), mean=float(X.r.mean()), bp=float(X.bp.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))), win=float((X.r > 0).mean()), per=" ".join(f"{k} {v:+.3f}" for k, v in per.items()), npos=int((per > 0).sum()), tm=float((X.why == "time").mean()))


def fmt(tag, s):
    return f"{tag:18s} days {s['days']:4d} trades {s['trades']:5d} | mean {s['mean']:+.3f} R ({s['bp']:+.2f} bp) | PF {s['pf']:4.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | time exits {100*s['tm']:4.1f}% | per index (R): {s['per']}"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},leo_ema_pullback,{trial},{period},{s['days']},{s['trades']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    T = pd.concat([trades_for(n) for n in NAMES], ignore_index=True)
    if a.smoke:
        pd.set_option("display.width", 200); X = T[(T.date >= pd.Timestamp(PERIODS["SMOKE"][0])) & (T.date <= pd.Timestamp(PERIODS["SMOKE"][1])) & (T.name == "SP")]; print(X.round(3).to_string()); print(len(T), "trades in total; per index:", T.groupby("name").size().to_dict(), "| exits:", T.why.value_counts().to_dict())
    if a.trials:
        for per in ("DEV", "VAL", "POOL"):
            s = stats(T, *PERIODS[per]); print(fmt(f"E1 {per}", s), flush=True); ledger("E1", per, s, "SP NSDQ DOW pooled, R units; " + s["per"])
    if a.holdout:
        s = stats(T, *PERIODS["HOLD"]); print(fmt("E1 HOLD-OUT 2026", s)); ledger("E1", "HOLD", s, "one-time look; " + s["per"])


if __name__ == "__main__":
    main()
