"""Family R (intraday pairs stat-arb on linked MT5 broker instruments), exactly as registered in PREREG_STATARB_INTRADAY.md (the trader 2026-10-10 goal: "um novo sistema, 70% chance de passar o desafio este mes").
   python -m mt5broker.ea_research.statarb_intraday --dry-run | --trials | --holdout
--dry-run prints counts, betas, costs and a hand check: NO P&L."""
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
STATE = HERE / "STATARB_INTRADAY_STATE.json"
PAIRS = {"R1": ("SP", "DOW"), "R2": ("SP", "NSDQ"), "R3": ("XAUUSD", "XAGUSD"), "R4": ("BRENT", "WTI"), "R5": ("AUDUSD", "NZDUSD"), "R6": ("EURUSD", "GBPUSD")}
PERIODS = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
WIN, ZIN, TSTOP, BDAYS = 48, 2.0, 24, 20
SLIP = 1e-5
NOTIONAL = 100_000.0


def load(m: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao", "bc", "ac"]).sort_values("t").drop_duplicates("t")
    return d[(d.bo > 0) & (d.ao >= d.bo) & (d.ac >= d.bc) & (d.bc > 0)].reset_index(drop=True)


def pair_frame(a: str, b: str) -> pd.DataFrame:
    A, B = load(a), load(b); M = A.merge(B, on="t", suffixes=("_a", "_b"))
    M["ma"] = (M.bc_a + M.ac_a) / 2; M["mb"] = (M.bc_b + M.ac_b) / 2
    M = M[(np.abs(np.log(M.ma / ((M.bo_a + M.ao_a) / 2))) < 0.05) & (np.abs(np.log(M.mb / ((M.bo_b + M.ao_b) / 2))) < 0.05)].reset_index(drop=True)    # quote glitches
    return M


def bars(M: pd.DataFrame) -> pd.DataFrame:
    key = (M.t // 300).to_numpy(); g = M.groupby(key, sort=True)
    B = pd.DataFrame({"T": g.t.first().index.to_numpy() * 300, "tl": g.t.last().to_numpy(), "n": g.size().to_numpy(), "la": np.log(g.ma.last().to_numpy()), "lb": np.log(g.mb.last().to_numpy())})
    B = B[B.n >= 3].reset_index(drop=True); B["day"] = B["T"] // 86400; B["hhmm"] = ((B["T"] + 300) % 86400) // 60          # minutes after midnight of the bar CLOSE (end of bar)
    return B


def betas(B: pd.DataFrame) -> pd.Series:
    ra = B.la.diff(); rb = B.lb.diff(); ok = (B["T"].diff() == 300) & (B.day == B.day.shift())
    x = pd.DataFrame({"day": B.day, "ab": (ra * rb).where(ok), "bb": (rb * rb).where(ok), "a": ra.where(ok), "b": rb.where(ok), "n": ok.astype(float)}).groupby("day").sum(min_count=1).fillna(0.0)
    r = x.rolling(BDAYS, min_periods=BDAYS).sum().shift(1)                                          # previous 20 server days only
    cov = r.ab / r.n - (r.a / r.n) * (r.b / r.n); var = r.bb / r.n - (r.b / r.n) ** 2; beta = (cov / var).where(r.n >= 1000)
    return beta


def zscore(B: pd.DataFrame, beta_by_day: pd.Series) -> np.ndarray:
    beta = B.day.map(beta_by_day).to_numpy(); la, lb = B.la, B.lb
    mA, mB = la.rolling(WIN).mean(), lb.rolling(WIN).mean(); vA, vB = la.rolling(WIN).var(ddof=0), lb.rolling(WIN).var(ddof=0); cAB = la.rolling(WIN).cov(lb, ddof=0)
    den = np.sqrt(np.maximum(vA + beta ** 2 * vB - 2 * beta * cAB, 0.0)); z = ((la - mA) - beta * (lb - mB)) / den
    return np.where((den > 0) & np.isfinite(beta) & (beta > 0.2), z, np.nan), beta


def exec_index(Mt: np.ndarray, target: int) -> int:
    i = int(np.searchsorted(Mt, target))
    return i if i < len(Mt) and Mt[i] <= target + 300 else -1


def trade_pair(M: pd.DataFrame, B: pd.DataFrame, z: np.ndarray, beta: np.ndarray, dry=False) -> pd.DataFrame:
    Mt = M.t.to_numpy("int64"); boa, aoa, bob, aob = (M[k].to_numpy("float64") for k in ("bo_a", "ao_a", "bo_b", "ao_b")); T = B["T"].to_numpy("int64"); hm = B.hhmm.to_numpy(); n = len(B)
    rows = []; pos = 0; k0 = -1; ie = -1; be = 0.0
    for k in range(WIN, n):
        if pos == 0:
            if not (60 <= hm[k] <= 21 * 60 + 30) or not np.isfinite(z[k]): continue
            if z[k] <= -ZIN or z[k] >= ZIN:
                i = exec_index(Mt, int(T[k] + 300 + 120))
                if i < 0: continue
                pos = 1 if z[k] <= -ZIN else -1; k0 = k; ie = i; be = float(beta[k])
            continue
        why = None
        if (pos == 1 and z[k] >= 0) or (pos == -1 and z[k] <= 0): why = "zcross"
        elif k - k0 >= TSTOP: why = "time"
        elif hm[k] >= 21 * 60 + 50 or (T[k] // 86400) != (T[k0] // 86400): why = "session"
        nxt_gap = (k + 1 < n) and (T[k + 1] - T[k] > 3600)
        if why is None and not nxt_gap and np.isfinite(z[k]): continue
        if why is None: why = "closure"
        i = exec_index(Mt, int(T[k] + 300 + 120))
        if i < 0: i = int(np.searchsorted(Mt, T[k] + 300)) - 1                                       # last common minute: closure
        if pos == 1:   # long A, short B
            ra = boa[i] / aoa[ie] - 1.0; rb = (bob[ie] - aob[i]) / bob[ie]
        else:
            ra = (boa[ie] - aoa[i]) / boa[ie]; rb = bob[i] / aob[ie] - 1.0
        mid_a_e, mid_a_x = (boa[ie] + aoa[ie]) / 2, (boa[i] + aoa[i]) / 2; mid_b_e, mid_b_x = (bob[ie] + aob[ie]) / 2, (bob[i] + aob[i]) / 2
        ga = pos * (mid_a_x / mid_a_e - 1.0); gb = -pos * (mid_b_x / mid_b_e - 1.0)
        net = NOTIONAL * (ra + be * rb) - SLIP * 2 * NOTIONAL * (1 + be); gross = NOTIONAL * (ga + be * gb)
        cost_rt = 1e4 * ((aoa[ie] - boa[ie]) / mid_a_e + (aoa[i] - boa[i]) / mid_a_x + be * ((aob[ie] - bob[ie]) / mid_b_e + (aob[i] - bob[i]) / mid_b_x)) / 2
        rows.append(dict(t_in=int(Mt[ie]), t_out=int(Mt[i]), side=pos, beta=be, bars=k - k0, why=why, net=net, gross=gross, net_bp=net / NOTIONAL * 1e4, gross_bp=gross / NOTIONAL * 1e4, cost_bp=cost_rt))
        pos = 0
    return pd.DataFrame(rows)


def daily(T: pd.DataFrame, B: pd.DataFrame, a: str, b: str):
    days = pd.to_datetime(np.unique(B.day.to_numpy()) * 86400, unit="s"); days = days[days.dayofweek < 5]
    s = pd.Series(0.0, index=days)
    if len(T):
        x = T.groupby(pd.to_datetime(T.t_out // 86400 * 86400, unit="s")).net.sum(); s = s.add(x, fill_value=0.0)
    return s


def stat(T: pd.DataFrame, s: pd.Series, per: str) -> dict:
    a, b = PERIODS[per]; dd_ = pd.to_datetime(T.t_out // 86400 * 86400, unit="s") if len(T) else None; X = T[(dd_ >= a) & (dd_ <= b)] if len(T) else T
    d = s[(s.index >= a) & (s.index <= b)]; n = len(d); sd = d.std(ddof=1)
    w, l_ = X.net[X.net > 0].sum() if len(X) else 0.0, -X.net[X.net < 0].sum() if len(X) else 0.0; eq = d.cumsum()
    return dict(trades=len(X), tpd=len(X) / max(1, n), win=float((X.net > 0).mean()) if len(X) else float("nan"), net_bp=float(X.net_bp.mean()) if len(X) else float("nan"), gross_bp=float(X.gross_bp.mean()) if len(X) else float("nan"),
                cost_bp=float(X.cost_bp.mean()) if len(X) else float("nan"), pf=float(w / l_) if l_ > 0 else float("nan"), days=n, mean_day=float(d.mean()), t=float(d.mean() / (sd / np.sqrt(n))) if sd > 0 else float("nan"),
                sh_d=float(d.mean() / sd) if sd > 0 else float("nan"), dd=float((eq.cummax() - eq).max()) if n else float("nan"), why=X.why.value_counts(normalize=True).round(2).to_dict() if len(X) else {})


def fmt(tag, s):
    return (f"{tag:10s} trades {s['trades']:5d} ({s['tpd']:.2f}/day) | win {100*s['win']:4.1f}% | net {s['net_bp']:+6.2f} bp/trade (gross {s['gross_bp']:+6.2f}, round-trip spread {s['cost_bp']:5.2f}) | PF {s['pf']:4.2f} | "
            f"day {s['mean_day']:+7.1f} USD per 100K leg-A | daily t {s['t']:+5.2f} | daily Sharpe {s['sh_d']:+5.2f} | maxDD {s['dd']:,.0f} | exits {s['why']}")


def ledger(trial, per, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},statarb_intraday,{trial},{per},{s['days']},{s['trades']},,{s['net_bp']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def build(trial):
    a, b = PAIRS[trial]; M = pair_frame(a, b); B = bars(M); bd = betas(B); z, beta = zscore(B, bd); return a, b, M, B, z, beta, bd


def dry_run():
    for trial in PAIRS:
        a, b, M, B, z, beta, bd = build(trial)
        sig = np.zeros(len(B), bool); hm = B.hhmm.to_numpy(); sig = np.isfinite(z) & (np.abs(z) >= ZIN) & (hm >= 60) & (hm <= 21 * 60 + 30)
        yrs = pd.to_datetime(B["T"], unit="s").dt.year
        print(f"== {trial} {a}/{b}: common minutes {len(M):,} | M5 bars {len(B):,} | beta: median {np.nanmedian(bd):.2f}, 5-95% {np.nanpercentile(bd, 5):.2f}..{np.nanpercentile(bd, 95):.2f}, days with beta {int(bd.notna().sum())} | bars with |z|>=2 in trading hours by year {pd.Series(sig).groupby(yrs).sum().to_dict()}")
        sp = ((M.ao_a - M.bo_a) / ((M.ao_a + M.bo_a) / 2) + np.nanmedian(bd) * (M.ao_b - M.bo_b) / ((M.ao_b + M.bo_b) / 2)) * 1e4
        print(f"   round-trip spread cost (both legs, beta-weighted, bp of leg A) median {sp.median():.2f} + slippage {4*SLIP*1e4*(1+np.nanmedian(bd))/2:.2f}")
    # causality: z at a bar must not change when later bars are removed
    a, b, M, B, z, beta, bd = build("R1"); k = len(B) - 500; cut = B.iloc[:k + 1].copy(); bd2 = betas(cut); z2, _ = zscore(cut, bd2)
    print(f"causality test R1: z at bar {k} full {z[k]:+.6f} vs truncated {z2[k]:+.6f}; beta of that day full {bd.get(B.day.iloc[k], np.nan):.6f} vs truncated {bd2.get(B.day.iloc[k], np.nan):.6f}")
    # hand check of one bar
    i = k; T0 = int(B["T"].iloc[i]); mm = M[(M.t >= T0) & (M.t < T0 + 300)]
    print(f"hand check R1 bar {T0}: last-minute mid A table {np.exp(B.la.iloc[i]):.4f} vs raw {mm.ma.iloc[-1]:.4f}; execution minute for a signal here = first common minute >= {T0 + 420} -> {int(M.t.to_numpy()[np.searchsorted(M.t.to_numpy(), T0 + 420)])}")
    print("no P&L computed")


def accept(dev, val):
    a1 = dev["t"] >= 2.4 and dev["net_bp"] > 0 and dev["trades"] >= 300; a2 = val["t"] >= 1.0 and val["net_bp"] > 0; return dict(a1=bool(a1), a2=bool(a2), passed=bool(a1 and a2))


def run_trials():
    res = {}
    for trial in PAIRS:
        a, b, M, B, z, beta, bd = build(trial); T = trade_pair(M, B, z, beta); s = daily(T, B, a, b)
        st = {per: stat(T, s, per) for per in ("DEV", "VAL")}
        print(f"\n=== {trial} {a}/{b} ===", flush=True)
        for per in ("DEV", "VAL"):
            print(fmt(f"{trial} {per}", st[per]), flush=True); ledger(trial, per, st[per], f"{a}/{b}; net {st[per]['net_bp']:+.2f} bp/trade; gross {st[per]['gross_bp']:+.2f}; daily Sharpe {st[per]['sh_d']:+.2f}")
        for y in (2022, 2023, 2024, 2025):
            X = T[pd.to_datetime(T.t_out, unit="s").dt.year == y] if len(T) else T
            print(f"   {y}: trades {len(X):5d} net {X.net_bp.mean() if len(X) else float('nan'):+6.2f} bp gross {X.gross_bp.mean() if len(X) else float('nan'):+6.2f} bp")
        acc = accept(st["DEV"], st["VAL"]); res[trial] = dict(acc=acc, dev=st["DEV"], val=st["VAL"]); print("   acceptance 1:", acc["a1"], "| 2:", acc["a2"], "=>", "hold-out may be opened" if acc["passed"] else "closed")
    STATE.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); print("\n== acceptance ==", {k: v["acc"] for k, v in res.items()})


def run_holdout():
    res = json.loads(STATE.read_text()) if STATE.exists() else {}; live = [k for k, v in res.items() if v["acc"]["passed"]]
    if not live: print("No pair passed acceptance 1-2: the 2026 hold-out stays CLOSED (registered rule)."); return
    for trial in live:
        a, b, M, B, z, beta, bd = build(trial); T = trade_pair(M, B, z, beta); s = daily(T, B, a, b); st = stat(T, s, "HOLD"); print(fmt(f"{trial} HOLD", st)); ledger(trial, "HOLD", st, f"{a}/{b}; daily Sharpe {st['sh_d']:+.2f}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); x = ap.parse_args()
    if x.dry_run: dry_run()
    if x.trials: run_trials()
    if x.holdout: run_holdout()


if __name__ == "__main__":
    main()
