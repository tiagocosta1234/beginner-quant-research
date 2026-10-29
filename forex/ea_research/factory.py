"""Family F: strategy factory for the 70%-this-month goal, as registered in PREREG_FACTORY.md.
   python -m forex.ea_research.factory --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
STATE = HERE / "FACTORY_STATE.json"
CACHE = Path("data/tmp/factory_daily.parquet")
MKTS = ("XAUUSD", "NSDQ", "SP", "DOW", "DAX", "EURUSD", "GBPUSD", "USDJPY")
TFS = {"M15": 900, "H1": 3600}
RISK = 1000.0
SLIP = 2e-5
DEV, VAL, HOLD = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-09-30")


def bars(m: str, sec: int) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bh", "bl", "bc", "ah", "al", "ac"]).sort_values("t")
    d = d[(d.bc > 0) & (d.ac >= d.bc)]; sp = ((d.ac - d.bc) / ((d.ac + d.bc) / 2)).median()
    g = d.groupby(d.t // sec); B = pd.DataFrame({"T": g.t.first().index.to_numpy() * sec, "c": ((g.bc.last() + g.ac.last()) / 2).to_numpy(), "h": ((g.bh.max() + g.ah.max()) / 2).to_numpy(), "l": ((g.bl.min() + g.al.min()) / 2).to_numpy()})
    B = B[pd.to_datetime(B["T"], unit="s").dt.dayofweek < 5].reset_index(drop=True); return B, float(sp)


def state(entry_l, exit_l, entry_s, exit_s) -> np.ndarray:
    L = pd.Series(np.where(entry_l, 1.0, np.where(exit_l, 0.0, np.nan))).ffill().fillna(0.0).to_numpy()
    S = pd.Series(np.where(entry_s, 1.0, np.where(exit_s, 0.0, np.nan))).ffill().fillna(0.0).to_numpy()
    return L - S


def variants(B: pd.DataFrame):
    c, h, l = B.c, B.h, B.l; out = {}
    for N in (10, 20, 50, 100):
        hi, lo = h.rolling(N).max().shift(1), l.rolling(N).min().shift(1); hi2, lo2 = h.rolling(N // 2).max().shift(1), l.rolling(N // 2).min().shift(1)
        out[f"D{N}"] = state(c > hi, c < lo2, c < lo, c > hi2)
    for f, s in ((10, 50), (20, 100), (50, 200)):
        out[f"M{f}_{s}"] = np.sign(c.ewm(span=f, adjust=False).mean() - c.ewm(span=s, adjust=False).mean()).fillna(0).to_numpy()
    de = c.diff(); up = de.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-de.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean(); rsi = 100 - 100 / (1 + up / dn)
    for a in (20, 25, 30):
        out[f"R{a}"] = state(rsi < a, rsi > 50, rsi > 100 - a, rsi < 50)
    for N in (20, 50):
        mu, sd = c.rolling(N).mean(), c.rolling(N).std()
        for k in (2.0, 2.5):
            out[f"B{N}_{k}"] = state(c < mu - k * sd, c > mu, c > mu + k * sd, c < mu)
    day = B["T"] // 86400; hrs = (B["T"] % 86400) / 3600.0; dopen = c.groupby(day).transform("first")
    for hh in (2, 4, 6):
        sig = np.where((hrs >= 1.25 + hh) & (hrs < 1.25 + hh + 1e-9 + (B["T"].diff().fillna(900) / 3600.0)), np.sign(c - dopen), np.nan)
        out[f"O{hh}"] = pd.Series(sig).groupby(day.to_numpy()).ffill().fillna(0.0).to_numpy()
    return out


def run_market(m: str, tf: str) -> pd.DataFrame:
    B, sp = bars(m, TFS[tf]); c = B.c.to_numpy(); hrs = (B["T"] % 86400) / 3600.0; fri = pd.to_datetime(B["T"], unit="s").dt.dayofweek == 4
    flat = ((hrs >= 21.75) | (hrs < 1.25) | (fri & (hrs >= 21.0))).to_numpy()
    tr = pd.concat([B.h - B.l, (B.h - B.c.shift()).abs(), (B.l - B.c.shift()).abs()], axis=1).max(axis=1); atr = tr.rolling(14).mean().to_numpy()
    w = np.where(atr > 0, RISK / (atr / c), 0.0)                                    # notional so that 1 ATR = 1,000 USD
    ret = np.r_[0.0, c[1:] / c[:-1] - 1.0]; day = pd.to_datetime(B["T"] // 86400 * 86400, unit="s"); cols = {}
    for name, pos in variants(B).items():
        p = np.where(flat, 0.0, np.nan_to_num(pos)); N = p * w                       # decided at bar k
        held = np.r_[0.0, 0.0, N[:-2]]                                             # executed at the close of k+1, earns bar k+2
        trade = np.abs(np.diff(np.r_[0.0, N[:-1]])); cost = np.r_[0.0, trade] * (sp / 2 + SLIP)
        cols[f"{m}_{tf}_{name}"] = pd.Series(held * ret - cost).groupby(day.to_numpy()).sum()
    return pd.DataFrame(cols)


def build():
    if CACHE.exists(): return pd.read_parquet(CACHE)
    D = pd.concat([run_market(m, tf) for m in MKTS for tf in TFS], axis=1).fillna(0.0); D = D[D.index.dayofweek < 5]
    CACHE.parent.mkdir(parents=True, exist_ok=True); D.to_parquet(CACHE); return D


def sl(D, p): return D[(D.index >= p[0]) & (D.index <= p[1])]


def sharpe(x): return x.mean() / x.std(ddof=1) if x.std(ddof=1) > 0 else np.nan


def ledger(trial, per, n, mean, t, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},factory,{trial},{per},{n},,,{mean:.4f},,{t:.2f},,{note}\n")


def dev():
    D = build(); d = sl(D, DEV); v = sl(D, VAL); n = len(d)
    S = d.mean() / d.std(ddof=1); T = S * np.sqrt(n)
    print(f"variants {D.shape[1]} | DEV days {n} | DEV daily Sharpe: median {S.median():+.3f}, best {S.max():+.3f} ({S.idxmax()}), share > 0 {100*(S > 0).mean():.0f}%")
    rng = np.random.default_rng(11); X = (d - d.mean()).to_numpy(); mx = []
    for _ in range(200):
        idx = np.empty(n, int); idx[0] = rng.integers(n)
        for j in range(1, n): idx[j] = rng.integers(n) if rng.random() < 0.2 else (idx[j - 1] + 1) % n
        Y = X[idx]; mx.append(np.nanmax(Y.mean(0) / Y.std(0, ddof=1)))
    print(f"reality check: best DEV daily Sharpe under the null (no edge, same search) median {np.median(mx):+.3f}, 95th pct {np.percentile(mx, 95):+.3f}; real best {S.max():+.3f} -> p = {np.mean(np.array(mx) >= S.max()):.3f}")
    top = S[(T >= 2.0)].sort_values(ascending=False).head(20)
    print("top by DEV daily Sharpe (t >= 2):"); res = {}
    for k, s in top.items():
        sv = sharpe(v[k]); res[k] = dict(dev=float(s), val=float(sv), dev_mean=float(d[k].mean()), val_mean=float(v[k].mean()))
        print(f"   {k:22s} DEV Sharpe {s:+.3f} mean {d[k].mean():+7.1f} USD/day | VAL Sharpe {sv:+.3f} mean {v[k].mean():+7.1f}"); ledger(k, "DEV", n, d[k].mean(), s * np.sqrt(n), f"VAL Sharpe {sv:+.3f}")
    surv = [k for k, r in res.items() if r["val"] > 0]
    if surv:
        P = d[surv].sum(axis=1); scale = min(1.0, 900.0 / P.std(ddof=1)); Pd, Pv = P * scale, v[surv].sum(axis=1) * scale
        print(f"portfolio of {len(surv)} survivors, scale {scale:.2f}: DEV mean {Pd.mean():+.1f} USD/day daily Sharpe {sharpe(Pd):+.3f} | VAL mean {Pv.mean():+.1f} daily Sharpe {sharpe(Pv):+.3f} | corr of components DEV median {np.nanmedian(np.corrcoef(d[surv].T.to_numpy())[np.triu_indices(len(surv), 1)]) if len(surv) > 1 else float('nan'):+.2f}")
    STATE.write_text(json.dumps(dict(survivors=surv, res=res, null95=float(np.percentile(mx, 95)), best=float(S.max())), indent=1))


def holdout():
    st = json.loads(STATE.read_text()); surv = st["survivors"]
    if not surv: print("no survivor: hold-out stays closed"); return
    D = build(); d, h = sl(D, DEV), sl(D, HOLD); scale = min(1.0, 900.0 / d[surv].sum(axis=1).std(ddof=1)); Ph = h[surv].sum(axis=1) * scale
    print(f"HOLD-OUT 2026 portfolio ({len(surv)} variants): mean {Ph.mean():+.1f} USD/day | daily Sharpe {sharpe(Ph):+.3f} | t {sharpe(Ph)*np.sqrt(len(Ph)):+.2f} | goal needs mean >= 500 and Sharpe >= 0.5")
    for k in surv: print(f"   {k:22s} 2026 mean {h[k].mean():+7.1f} Sharpe {sharpe(h[k]):+.3f}")
    ledger("portfolio", "HOLD", len(Ph), Ph.mean(), sharpe(Ph) * np.sqrt(len(Ph)), f"{len(surv)} variants")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev: dev()
    if a.holdout: holdout()
