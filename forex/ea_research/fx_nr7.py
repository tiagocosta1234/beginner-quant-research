"""NR7 breakout rule F2 on the 28 MT5 FX pairs, exactly as registered in PREREG_FX_NR7.md.
   python -m forex.ea_research.fx_nr7 --smoke     mechanics check, EURUSD Dec 2021 (prints trades; not used for any decision)
   python -m forex.ea_research.fx_nr7 --trials    F2 pooled over the 28 pairs: DEV, VAL, POOL (+ breadth), appended to LEDGER.csv
   python -m forex.ea_research.fx_nr7 --holdout   the one-time 2026 look (only if acceptance 1-3 held)
Server clock; M1 bid / ask bars; fills on the ask for longs and the bid for shorts; stop first; costs = the bars' own spread + 0.2 bp slippage."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
PAIRS = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
         "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
SLIP = 0.2e-4                    # 0.2 bp of the price per market / stop fill
MIN_BARS, NR, HOLD_DAYS, MIN_R_SPREADS = 1000, 7, 3, 5.0
PERIODS = {"SMOKE": ("2021-12-01", "2021-12-31"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def epoch(day: str) -> int:
    return int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp())


def trades_for(pair: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{pair}_M1_rates.parquet").sort_values("t"); t = d.t.to_numpy("int64"); day = t // 86400
    bo, bh, bl, bc, ao, ah, ac, sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "ac", "sp"))
    ud, first, cnt = np.unique(day, return_index=True, return_counts=True); ok = cnt >= MIN_BARS; ud, first, cnt = ud[ok], first[ok], cnt[ok]; last = first + cnt          # trading days: start / end bar index
    H = np.array([bh[a:b].max() for a, b in zip(first, last)]); L = np.array([bl[a:b].min() for a, b in zip(first, last)]); S = np.array([sp[a:b].mean() for a, b in zip(first, last)]); rng = H - L
    rows, busy_until = [], -1
    for i in range(NR - 1, len(ud) - 1 - HOLD_DAYS + 1):
        if not rng[i] < rng[i - NR + 1:i].min() or i + 1 <= busy_until:
            continue
        e, x = i + 1, min(i + HOLD_DAYS, len(ud) - 1); a, b = first[e], last[e]
        ib = np.nonzero(ah[a:b] >= H[i])[0]; isl = np.nonzero(bl[a:b] <= L[i])[0]; kb = ib[0] if len(ib) else None; ks = isl[0] if len(isl) else None
        if kb is None and ks is None:
            continue
        if kb is not None and ks is not None and kb == ks:                                   # both orders inside one M1 bar: booked as exactly -1 R (worst case)
            ent = H[i] + 0.5 * rng[i]; rows.append(dict(pair=pair, t_in=int(t[a + kb]), t_out=int(t[a + kb]), side=0, r=-1.0, bp=-rng[i] / H[i] * 1e4, why="both-in-one-bar", day=int(ud[e]))); busy_until = e; continue
        side = 1 if (ks is None or (kb is not None and kb < ks)) else -1; k = kb if side > 0 else ks; idx = a + k
        if side > 0:
            entry = max(H[i], ao[idx]) * (1 + SLIP); stop = L[i]; R = entry - stop
        else:
            entry = min(L[i], bo[idx]) * (1 - SLIP); stop = H[i]; R = stop - entry
        if not R > MIN_R_SPREADS * S[i]:
            continue
        end = last[x]; seg = slice(idx, end)
        if side > 0:
            hit = np.nonzero(bl[seg] <= stop)[0]
            if len(hit):
                j = idx + hit[0]; ex = min(stop, bo[j]) * (1 - SLIP) if j > idx else stop * (1 - SLIP); why = "stop"
            else:
                j = end - 1; ex = bc[j]; why = "time"
            pnl = ex - entry
        else:
            hit = np.nonzero(ah[seg] >= stop)[0]
            if len(hit):
                j = idx + hit[0]; ex = max(stop, ao[j]) * (1 + SLIP) if j > idx else stop * (1 + SLIP); why = "stop"
            else:
                j = end - 1; ex = ac[j]; why = "time"
            pnl = entry - ex
        exit_day = int(t[j] // 86400); rows.append(dict(pair=pair, t_in=int(t[idx]), t_out=int(t[j]), side=side, r=pnl / R, bp=pnl / entry * 1e4, why=why, day=exit_day)); busy_until = int(np.searchsorted(ud, exit_day))
    return pd.DataFrame(rows)


def fade_trades_for(pair: str) -> pd.DataFrame:
    """Rule F2m (PREREG_FX_NR7_FADE.md): fade the NR7 breakout at the close of the trigger bar, stop one signal-day range beyond the entry, time exit at the close of day d+3."""
    d = pd.read_parquet(DATA / f"{pair}_M1_rates.parquet").sort_values("t"); t = d.t.to_numpy("int64"); day = t // 86400
    bo, bh, bl, bc, ao, ah, ac, sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "ac", "sp"))
    ud, first, cnt = np.unique(day, return_index=True, return_counts=True); ok = cnt >= MIN_BARS; ud, first, cnt = ud[ok], first[ok], cnt[ok]; last = first + cnt
    H = np.array([bh[a:b].max() for a, b in zip(first, last)]); L = np.array([bl[a:b].min() for a, b in zip(first, last)]); S = np.array([sp[a:b].mean() for a, b in zip(first, last)]); rng = H - L
    rows, busy_until = [], -1
    for i in range(NR - 1, len(ud) - 1 - HOLD_DAYS + 1):
        if not rng[i] < rng[i - NR + 1:i].min() or i + 1 <= busy_until:
            continue
        e, x = i + 1, min(i + HOLD_DAYS, len(ud) - 1); a, b = first[e], last[e]
        ib = np.nonzero(ah[a:b] >= H[i])[0]; isl = np.nonzero(bl[a:b] <= L[i])[0]; kb = ib[0] if len(ib) else None; ks = isl[0] if len(isl) else None
        if kb is None and ks is None or (kb is not None and ks is not None and kb == ks):
            continue
        up = ks is None or (kb is not None and kb < ks); k = kb if up else ks; idx = a + k; R0 = rng[i]
        if not R0 >= MIN_R_SPREADS * S[i]:
            continue
        end = last[x]; side = -1 if up else 1
        entry = bc[idx] * (1 - SLIP) if up else ac[idx] * (1 + SLIP); stop = entry + R0 if up else entry - R0; seg = slice(idx + 1, end)
        if up:
            hit = np.nonzero(ah[seg] >= stop)[0]
            if len(hit):
                j = idx + 1 + hit[0]; ex = max(stop, ao[j]) * (1 + SLIP); why = "stop"
            else:
                j = end - 1; ex = ac[j]; why = "time"
            pnl = entry - ex
        else:
            hit = np.nonzero(bl[seg] <= stop)[0]
            if len(hit):
                j = idx + 1 + hit[0]; ex = min(stop, bo[j]) * (1 - SLIP); why = "stop"
            else:
                j = end - 1; ex = bc[j]; why = "time"
            pnl = ex - entry
        exit_day = int(t[j] // 86400); rows.append(dict(pair=pair, t_in=int(t[idx]), t_out=int(t[j]), side=side, r=pnl / R0, bp=pnl / entry * 1e4, why=why, day=exit_day)); busy_until = int(np.searchsorted(ud, exit_day))
    return pd.DataFrame(rows)


def stats(T: pd.DataFrame, a: str, b: str, all_days: np.ndarray) -> dict:
    t0, t1 = epoch(a), epoch(b) + 86400; X = T[(T.t_in >= t0) & (T.t_in < t1)]; d0, d1 = t0 // 86400, t1 // 86400; days = all_days[(all_days >= d0) & (all_days < d1)]
    if not len(X):
        return dict(days=len(days), trades=0, mean=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), net=0.0, pairs_pos=0, pairs=0)
    s = pd.Series(0.0, index=days); g = X.groupby("day").r.sum(); ix = g.index.intersection(s.index); s.loc[ix] += g.loc[ix]; e = s.to_numpy(); w, l_ = X.r[X.r > 0].sum(), -X.r[X.r <= 0].sum()
    pm = X.groupby("pair").r.mean()
    return dict(days=len(days), trades=len(X), mean=float(X.r.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))) if e.std(ddof=1) > 0 else float("nan"), win=float((X.r > 0).mean()), net=float(X.r.sum()), pairs_pos=int((pm > 0).sum()), pairs=int(len(pm)))


def fmt(tag, s):
    return f"{tag:22s} days {s['days']:4d} trades {s['trades']:5d} | mean {s['mean']:+6.3f} R | PF {s['pf']:5.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | net {s['net']:+8.1f} R | pairs with mean>0: {s['pairs_pos']}/{s['pairs']}"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},fx_nr7,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser()
    for k in ("smoke", "trials", "holdout", "fade_smoke", "fade_trials", "fade_holdout"):
        ap.add_argument(f"--{k}", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        T = trades_for("EURUSD"); t0, t1 = epoch(PERIODS["SMOKE"][0]), epoch(PERIODS["SMOKE"][1]) + 86400; X = T[(T.t_in >= t0) & (T.t_in < t1)].copy()
        X["in"] = pd.to_datetime(X.t_in, unit="s").dt.strftime("%m-%d %H:%M"); X["out"] = pd.to_datetime(X.t_out, unit="s").dt.strftime("%m-%d %H:%M"); pd.set_option("display.width", 200); print(X[["in", "out", "side", "r", "bp", "why"]].round(3).to_string())
        print(f"EURUSD all {len(T)} trades 2021-12..2026-10: mean {T.r.mean():+.3f} R")
    if a.fade_smoke:
        T = fade_trades_for("EURUSD"); t0, t1 = epoch(PERIODS["SMOKE"][0]), epoch(PERIODS["SMOKE"][1]) + 86400; X = T[(T.t_in >= t0) & (T.t_in < t1)].copy()
        X["in"] = pd.to_datetime(X.t_in, unit="s").dt.strftime("%m-%d %H:%M"); X["out"] = pd.to_datetime(X.t_out, unit="s").dt.strftime("%m-%d %H:%M"); pd.set_option("display.width", 200); print(X[["in", "out", "side", "r", "bp", "why"]].round(3).to_string())
    if a.fade_trials or a.fade_holdout:
        allT = []
        for p in PAIRS:
            allT.append(fade_trades_for(p)); print(p, len(allT[-1]), flush=True)
        T = pd.concat(allT, ignore_index=True); all_days = np.unique(pd.read_parquet(DATA / "EURUSD_M1_rates.parquet", columns=["t"]).t.to_numpy("int64") // 86400)
        if a.fade_trials:
            for per in ("DEV", "VAL", "POOL"):
                s = stats(T, *PERIODS[per], all_days); print(fmt(f"F2m fade {per}", s), flush=True); ledger("F2m", per, s, "fade NR7, 28 FX pairs pooled, R units (consistency only)")
        if a.fade_holdout:
            s = stats(T, *PERIODS["HOLD"], all_days); print(fmt("F2m fade HOLD-OUT 2026", s)); ledger("F2m", "HOLD", s, "one-time look, the decision")
    if a.trials or a.holdout:
        allT = []
        for p in PAIRS:
            T = trades_for(p); allT.append(T); print(p, len(T), flush=True)
        T = pd.concat(allT, ignore_index=True); eur = pd.read_parquet(DATA / "EURUSD_M1_rates.parquet", columns=["t"]).t.to_numpy("int64") // 86400; all_days = np.unique(eur)
        if a.trials:
            for per in ("DEV", "VAL", "POOL"):
                s = stats(T, *PERIODS[per], all_days); print(fmt(f"F2 NR7 {per}", s), flush=True); ledger("F2", per, s, "28 FX pairs pooled, R units")
            # per-pair breadth on DEV+VAL (registered acceptance 3)
            s = stats(T, *PERIODS["POOL"], all_days); print(f"breadth DEV+VAL (2022-2025 pooled): pairs with mean R > 0: {s['pairs_pos']}/{s['pairs']}")
        if a.holdout:
            s = stats(T, *PERIODS["HOLD"], all_days); print(fmt("F2 NR7 HOLD-OUT 2026", s)); ledger("F2", "HOLD", s, "one-time look, 28 FX pairs pooled")


if __name__ == "__main__":
    main()
