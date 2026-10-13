"""Slow fundamental bias + mechanical 15-minute pullback entries, exactly as registered in PREREG_MACRO_TA.md.
   python -m forex.ea_research.macro_ta --smoke | --trials | --holdout
M1: 28 FX pairs, bias = sign of the policy-rate differential (|d| >= 1.0 pp); M2: SP / NSDQ / DOW, bias = VIX regime. Controls: inverted bias and no bias."""
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
FX = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
      "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
IDX = ["SP", "NSDQ", "DOW"]
PERIODS = {"SMOKE": ("2023-02-01", "2023-02-28"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
STOP_ATR, TP_ATR, MAX_BARS = 1.5, 3.0, 48


def series(name: str) -> pd.Series:
    d = pd.read_csv(MACRO / f"{name}.csv"); d.columns = ["d", "v"]; d["d"] = pd.to_datetime(d.d); d["v"] = pd.to_numeric(d.v, errors="coerce"); return d.dropna().set_index("d").v.sort_index()


RATES = {"USD": series("IRSTCI01USM156N"), "GBP": series("IRSTCI01GBM156N"), "JPY": series("IRSTCI01JPM156N"), "AUD": series("IRSTCI01AUM156N"), "CAD": series("IRSTCI01CAM156N"),
         "CHF": series("IR3TIB01CHM156N"), "NZD": series("IR3TIB01NZM156N"), "EUR": series("ECBDFR")}
VIX = series("VIXCLS"); VIX20 = VIX.rolling(20).mean()


def rate(ccy: str, day: pd.Timestamp) -> float:
    s = RATES[ccy]
    if ccy == "EUR":
        return float(s.asof(day - pd.Timedelta(days=1)))
    return float(s.asof(day.replace(day=1) - pd.DateOffset(months=2)))


def fx_bias(pair: str, day: pd.Timestamp) -> int:
    d = rate(pair[:3], day) - rate(pair[3:], day)
    return 0 if not np.isfinite(d) else (1 if d >= 1.0 else (-1 if d <= -1.0 else 0))


def vix_bias(day: pd.Timestamp) -> int:
    t = day - pd.Timedelta(days=1); v, m = VIX.asof(t), VIX20.asof(t)
    return 0 if not (np.isfinite(v) and np.isfinite(m)) else (1 if v < m else -1)


def bars15(name: str):
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet").sort_values("t"); g = d.groupby(d.t // 900)
    b = pd.DataFrame({"bo": g.bo.first(), "bh": g.bh.max(), "bl": g.bl.min(), "bc": g.bc.last(), "ao": g.ao.first(), "ah": g.ah.max(), "al": g.al.min(), "ac": g.ac.last(), "sp": g.sp.mean()}); b["t"] = b.index.to_numpy() * 900; b = b.reset_index(drop=True)
    pc = b.bc.shift(1); tr = pd.concat([b.bh - b.bl, (b.bh - pc).abs(), (b.bl - pc).abs()], axis=1).max(axis=1)
    b["e20"] = b.bc.ewm(span=20, adjust=False).mean(); b["e50"] = b.bc.ewm(span=50, adjust=False).mean(); b["atr"] = tr.rolling(14).mean()
    return b


def simulate(name: str, b: pd.DataFrame, bias_of_day, mode: str, kind: str) -> pd.DataFrame:
    t = b.t.to_numpy("int64"); bo, bh, bl, bc, ao, ah, al = (b[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al")); e20, e50, atr = b.e20.to_numpy(), b.e50.to_numpy(), b.atr.to_numpy(); n = len(b)
    slip = (0.2e-4 if kind == "fx" else 0.12e-4); srv_h = (t % 86400) // 3600; srv_m = (t % 86400) // 60 % 60
    if kind == "idx":
        ny = pd.to_datetime(t, unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward").tz_convert("America/New_York"); hm = (ny.hour * 100 + ny.minute).to_numpy(); hm = np.where(pd.isna(hm), -1, hm)
    days = t // 86400; bias_cache = {}; rows = []; busy = -1; last_day = -1
    for k in range(60, n - 2):
        if k <= busy or not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        up = e20[k] > e50[k] and e50[k] > e50[k - 4] and bc[k - 1] < e20[k - 1] and bc[k] > e20[k]
        dn = e20[k] < e50[k] and e50[k] < e50[k - 4] and bc[k - 1] > e20[k - 1] and bc[k] < e20[k]
        if not (up or dn):
            continue
        d_ = 1 if up else -1
        if kind == "fx":
            if (srv_h[k] == 23 and srv_m[k] >= 30) or srv_h[k] in (0, 1) and not (srv_h[k] == 1 and srv_m[k] >= 30):
                continue
        else:
            if hm[k] < 935 or hm[k] > 1530:
                continue
        day = int(days[k])
        if day == last_day:
            continue
        if day not in bias_cache:
            bias_cache[day] = bias_of_day(pd.Timestamp(day * 86400, unit="s"))
        bsd = bias_cache[day]
        if mode == "with":
            ok = bsd != 0 and d_ == bsd
        elif mode == "against":
            ok = bsd != 0 and d_ == -bsd
        else:
            ok = True
        if not ok:
            continue
        e = k + 1; entry = ao[e] * (1 + slip) if d_ > 0 else bo[e] * (1 - slip); R = STOP_ATR * atr[k]; stop = entry - d_ * R; tp = entry + d_ * TP_ATR * atr[k]; ex = None; j = e; why = ""
        while j < n:
            if d_ > 0:
                if bl[j] <= stop: ex = min(stop, bo[j]) * (1 - slip) if j > e else stop * (1 - slip); why = "stop"; break
                if bh[j] >= tp: ex = tp; why = "tp"; break
            else:
                if ah[j] >= stop: ex = max(stop, ao[j]) * (1 + slip) if j > e else stop * (1 + slip); why = "stop"; break
                if al[j] <= tp: ex = tp; why = "tp"; break
            held = j - e + 1
            if held >= MAX_BARS or (kind == "idx" and hm[min(j + 1, n - 1)] >= 1555) or (j + 1 < n and t[j + 1] - t[j] > 3600):
                jj = min(j + 1, n - 1); ex = (bo[jj] * (1 - slip)) if d_ > 0 else (ao[jj] * (1 + slip)); why = "time"; j = jj; break
            j += 1
        if ex is None:
            break
        pnl = d_ * (ex - entry); rows.append(dict(name=name, t_in=int(t[e]), day=int(t[min(j, n - 1)] // 86400), side=d_, r=pnl / R, bp=pnl / entry * 1e4, why=why)); busy = j; last_day = day
    return pd.DataFrame(rows)


def stats(T: pd.DataFrame, a: str, b: str) -> dict:
    t0, t1 = int(pd.Timestamp(a).timestamp()), int(pd.Timestamp(b).timestamp()) + 86400; X = T[(T.t_in >= t0) & (T.t_in < t1)] if len(T) else T
    if not len(X):
        return dict(trades=0, mean=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), bp=float("nan"), npos=0, ninst=0)
    day = X.groupby("day").r.mean(); w, l_ = X.r[X.r > 0].sum(), -X.r[X.r <= 0].sum(); per = X.groupby("name").r.mean()
    return dict(trades=len(X), mean=float(X.r.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))) if len(day) > 2 and day.std(ddof=1) > 0 else float("nan"), win=float((X.r > 0).mean()), bp=float(X.bp.mean()), npos=int((per > 0).sum()), ninst=int(len(per)))


def fmt(tag, s):
    return f"{tag:24s} trades {s['trades']:5d} | mean {s['mean']:+.3f} R ({s['bp']:+6.2f} bp) | PF {s['pf']:4.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | instruments > 0: {s['npos']}/{s['ninst']}"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},macro_ta,{trial},{period},,{s['trades']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def build(family: str, modes=("with", "against", "both")):
    out = {m: [] for m in modes}
    names, kind = (FX, "fx") if family == "FX" else (IDX, "idx")
    for nm in names:
        b = bars15(nm); fn = (lambda day, nm=nm: fx_bias(nm, day)) if family == "FX" else (lambda day: vix_bias(day))
        for m in modes:
            T = simulate(nm, b, fn, m, kind)
            if len(T): out[m].append(T)
        print(f"  {family} {nm} done", flush=True)
    return {m: (pd.concat(v, ignore_index=True) if v else pd.DataFrame()) for m, v in out.items()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.smoke:
        b = bars15("USDJPY"); T = simulate("USDJPY", b, lambda day: fx_bias("USDJPY", day), "with", "fx"); t0, t1 = int(pd.Timestamp(PERIODS["SMOKE"][0]).timestamp()), int(pd.Timestamp(PERIODS["SMOKE"][1]).timestamp()); X = T[(T.t_in >= t0) & (T.t_in < t1)].copy()
        X["in"] = pd.to_datetime(X.t_in, unit="s").dt.strftime("%m-%d %H:%M"); pd.set_option("display.width", 200); print(X[["in", "side", "r", "bp", "why"]].round(3).to_string()); print("USDJPY bias on 2023-02-15:", fx_bias("USDJPY", pd.Timestamp("2023-02-15")), "| rates", {c: round(rate(c, pd.Timestamp("2023-02-15")), 2) for c in RATES}, "| VIX bias", vix_bias(pd.Timestamp("2023-02-15")))
    if a.trials or a.holdout:
        for family, trial in (("FX", "M1"), ("IDX", "M2")):
            R = build(family)
            if a.trials:
                for per in ("DEV", "VAL", "POOL"):
                    for m in ("with", "against", "both"):
                        s = stats(R[m], *PERIODS[per]); print(fmt(f"{trial} {per} {m}", s), flush=True)
                        ledger(trial if m == "with" else f"DIAG-{trial}-{m}", per, s, f"{family}; bias {m}")
            if a.holdout:
                s = stats(R["with"], *PERIODS["HOLD"]); print(fmt(f"{trial} HOLD-OUT with", s)); ledger(trial, "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
