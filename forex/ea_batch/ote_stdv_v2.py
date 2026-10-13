"""Round 347i -- "make it trade discretionally like him" (the trader, 2026-10-06): version 2 of the OTE / STDV rules with the judgment calls Dutchy actually describes in the video turned into FIXED rules.
Literal discretion cannot be backtested; every rule below is my encoding of something he says, written BEFORE any v2 result was looked at. Nothing is tuned; the ablation table is reported in full.

WHAT HE DESCRIBES (youtube M6rIs6kR7wQ, auto-generated captions)            ->  HOW IT IS ENCODED
  "six entries" on one move, a new entry on every re-balanced leg [03:35, 10:51]  ->  up to N entries a day, one position at a time; after an exit the scan restarts from the bar after it
  OTE still works with no deviation tap, "that's when OTE comes in clutch" [06:33] ->  CONTINUATION legs: a break of structure + retracement entry with no tap needed, in the bias direction
  at all-time highs "I just expect it to keep pumping" [01:25]                     ->  BIAS = +1 if the previous 16:00 close is above its 20-day mean, else -1; continuation legs only in the bias direction;
                                                                                    reversal legs (a tap of the 2x-range deviation, as v1) stay allowed in both directions ("you can still short ATH")
  a leg that does not break structure is not taken [05:35]                          ->  already the v1 rule (the break of structure is required)
  lower-risk 0.5 entry is "far better" than the first-leg entry [02:53]             ->  v2 primary entry at 0.5 of the leg (v1's grid also looked best at 0.5, so v2's primary is NOT independent of v1; 0.62 / 0.79 are in the table)
  a choppy day, "perfect day to just not trade" [08:21]                              ->  stop trading for the day after 2 losing trades
  SMT divergence, "works for your entries but not the best" [04:45], and the "valid leg" / "too discretionary" calls [08:39] are NOT encoded: they need a second index feed / eyeballing.
Everything else is as in ote_stdv_eval.py (range 18:00-00:00 NY, tap at k = 2.0 x range, 5-minute structure, stop at the leg extreme but not closer than 0.05%, target m x stop, flat at 16:00 NY, entries until 11:00).

CONFIGS (ablation, all reported):  A rev only, 1 entry (= v1)   B rev only, 3   C continuation only, 3   D rev + continuation, 3 (PRIMARY)   E rev + continuation, 6.   f in {0.5, 0.62, 0.79}, m in {1, 2}.
INSTRUMENTS: MT5 broker index CFDs US100 / US500 / US30 (real bid / ask, 2022-2026) and Broker futures NQ / ES / GC / SI (1-minute, 2020-2026, MNQ / MES / MGC / SIL sizing, repo costs).
BENCHMARKS: NULL-COIN = the same entry minutes, stops and reward multiple with a coin-flip side; NULL-LONG = the same with every trade long (what the drift of a bull market pays for entering at those minutes).

  python -m forex.ea_batch.ote_stdv_v2 --grid
  python -m forex.ea_batch.ote_stdv_v2 --primary
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import ote_stdv_eval as O
from forex.ea_batch import ote_stdv_broker as TS
from forex.ea_batch import trendline_eval as T

HERE = Path(__file__).resolve().parent
MT5BROKER_SYMS, FUT_SYMS = ("US100.cash", "US500.cash", "US30.cash"), ("NQ", "ES", "GC", "SI")
CONFIGS = {"A": dict(rev=True, cont=False, n=1), "B": dict(rev=True, cont=False, n=3), "C": dict(rev=False, cont=True, n=3), "D": dict(rev=True, cont=True, n=3), "E": dict(rev=True, cont=True, n=6)}
STOP_AFTER = 2


class V2(O.Data):
    OFF = (-360, 0, 660, 960)                  # minutes from NY midnight: range start (18:00 the day before), range end / tap window start, last entry (11:00), flat time (16:00)
    MIN_RANGE_MIN = 60                         # fewest minutes the range window must contain

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        # previous 16:00 close per trading day and the 20-day mean -> bias
        d_all = np.unique(self.nym // 1440)
        cl = {}
        for d in d_all:
            i = int(np.searchsorted(self.nym, int(d) * 1440 + 960))
            if i > 0 and self.nym[i - 1] >= int(d) * 1440 + 930:
                cl[int(d)] = self.A[1]["mc"][i - 1]
        ds = sorted(cl)
        vals = np.array([cl[x] for x in ds])
        self.bias = {}
        for j in range(20, len(ds)):
            # the bias of the day AFTER ds[j] uses closes up to ds[j]
            nxt = ds[j + 1] if j + 1 < len(ds) else ds[j] + 1
            self.bias[nxt] = 1 if vals[j] > vals[j - 19:j + 1].mean() else -1
        self.last_bias = None

    def bias_for(self, d):
        for x in (d, ):
            if x in self.bias:
                return self.bias[x]
        ds = [k for k in self.bias if k <= d]
        return self.bias[max(ds)] if ds and d - max(ds) <= 5 else 0

    def seek(self, s, B, st, en, a1, b1, c, t0, f, mult):
        bh5, bl5, bc5 = B[s]; A = self.A[s]; nb = len(st); t = t0
        while t < nb - 1:
            jl = t0 + int(np.argmin(bl5[t0:t + 1])); ll = bl5[jl]
            S = None
            for j in range(min(jl - 1, t - 2), 1, -1):
                if bh5[j] > max(bh5[j - 2], bh5[j - 1], bh5[j + 1], bh5[j + 2]):
                    S = bh5[j]; break
            if S is None:
                S = bh5[max(0, jl - 6):jl + 1].max()
            if t > jl and bc5[t] > S:
                lh = bh5[jl:t + 1].max()
                q, fill, void = a1 + int(en[t]), None, False
                while q < b1:
                    level = lh - f * (lh - ll)
                    if A["al"][q] <= level - self.through:
                        fill = q; pe = min(level, A["ao"][q]); break
                    if A["ml"][q] < ll:
                        t = int(np.searchsorted(st, q - a1, side="right")) - 1; void = True; break
                    lh = max(lh, A["mh"][q]); q += 1
                if void:
                    continue
                if fill is None:
                    return None
                stop = min(ll, pe - O.MIN_STOP * abs(pe)); dist = pe - stop
                ix, px = self.run_exit(s, fill, pe, stop, pe + mult * dist, c)
                lots = T.RISK_REF / dist
                spr = 0.5 * ((self.m1.ask_open.values[fill] - self.m1.open.values[fill]) + (self.m1.ask_open.values[ix] - self.m1.open.values[ix])) * lots
                return dict(i0=fill, i1=ix, side=s, pe=s * pe, px=s * px, lots=lots, k=1.0, gross=(px - pe) * lots, comm=0.0, spread=spr, dist=dist, c=c, day=None)
            t += 1
        return None

    def day_trades(self, d, k, f, mult, cfg):
        nym = self.nym
        rs, re_, ee, fl = self.OFF
        a0, a1, b1, c = (self.ix(d * 1440 + x) for x in (rs, re_, ee, fl))
        if a1 - a0 < self.MIN_RANGE_MIN or b1 - a1 < 15 or c <= b1:
            return []
        A1 = self.A[1]
        H, L = A1["mh"][a0:a1].max(), A1["ml"][a0:a1].min(); R = H - L
        if R < O.MIN_RANGE * A1["mc"][a1 - 1]:
            return []
        key = nym[a1:b1] // 5
        st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], b1 - a1]
        B = {}
        for s in (1, -1):
            A = self.A[s]
            B[s] = (np.maximum.reduceat(A["mh"][a1:b1], st), np.minimum.reduceat(A["ml"][a1:b1], st), A["mc"][a1:b1][en - 1])
        lvl = {1: L - k * R, -1: -(H + k * R)}
        tap = {s: (int(np.flatnonzero(B[s][1] <= lvl[s])[0]) if (B[s][1] <= lvl[s]).any() else None) for s in (1, -1)}
        s_rev = None
        if tap[1] is not None or tap[-1] is not None:
            if tap[1] is not None and tap[-1] is not None:
                s_rev = None if tap[1] == tap[-1] else (1 if tap[1] < tap[-1] else -1)
            else:
                s_rev = 1 if tap[-1] is None else -1
        bias = self.bias_for(d)
        out, min_bar, losses = [], 0, 0
        while len(out) < cfg["n"]:
            cands = []
            if cfg["rev"] and s_rev is not None:
                t0 = max(tap[s_rev], min_bar)
                if t0 < len(st) - 1:
                    r = self.seek(s_rev, B, st, en, a1, b1, c, t0, f, mult)
                    if r:
                        cands.append(r)
            if cfg["cont"] and bias != 0 and min_bar < len(st) - 1:
                r = self.seek(bias, B, st, en, a1, b1, c, min_bar, f, mult)
                if r:
                    cands.append(r)
            if not cands:
                break
            r = min(cands, key=lambda x: x["i0"]); r["day"] = d
            out.append(r)
            min_bar = int(np.searchsorted(st, min(r["i1"], b1 - 1) - a1, side="right"))             # first 5-minute bar after the one in which the exit happened
            if r["gross"] < 0:
                losses += 1
                if losses >= STOP_AFTER:
                    break
        return out

    def simulate2(self, k, f, mult, cfg):
        rows = [r for d in self.days for r in self.day_trades(d, k, f, mult, cfg)]
        return pd.DataFrame(rows)

    def null2(self, ref, mult, mode, rng=None):
        rows = []
        for r in ref.itertuples():
            s = (1 if rng.random() < 0.5 else -1) if mode == "coin" else 1
            A = self.A[s]
            pe = A["ao"][r.i0]; stop = pe - r.dist
            ix, px = self.run_exit(s, r.i0, pe, stop, pe + mult * r.dist, r.c)
            lots = T.RISK_REF / r.dist
            rows.append(dict(i0=r.i0, i1=ix, side=s, pe=s * pe, px=s * px, lots=lots, k=1.0, gross=(px - pe) * lots, comm=0.0, spread=0.0, dist=r.dist, c=r.c, day=r.day))
        return pd.DataFrame(rows)


def build(sym):
    if sym in MT5BROKER_SYMS:
        O.START, O.END = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-09-30")
        return V2(sym), "mt5broker"
    O.START, O.END = pd.Timestamp("2020-01-01"), pd.Timestamp("2026-09-24")
    return V2(sym, m1=TS.load_fut(sym), through=TS.PRODUCT[sym]["tick"]), "fut"


def rmult(tr, D, kind, sym):
    if tr.empty:
        return np.array([])
    if kind == "mt5broker":
        return (tr.gross / T.RISK_REF).values
    p = TS.PRODUCT[sym]
    tt = TS.trade_table(D, tr)
    return ((tt.pts.values * p["pv"] - p["cost"]) / (tt.dist.values * p["pv"]))


def tstat(x):
    return float(x.mean() / (x.std() / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else float("nan")


def day_series_multi(tt, prod, risk, days):
    """Broker day series for several trades a day: closed P&L adds; the worst equity is the sequential worst (earlier closed P&L + the current trade's worst excursion)."""
    n = np.clip(np.floor(risk / (tt.dist.values * prod["pv"])), 1, TS.MAXC)
    net = n * (tt.pts.values * prod["pv"] - prod["cost"])
    worst = n * (tt.adv.values * prod["pv"] - prod["cost"])
    v, m = {}, {}
    for d, a, w in zip(tt.index.values, net, worst):
        c = v.get(d, 0.0)
        m[d] = min(m.get(d, 0.0), c + min(w, a)); v[d] = c + a
    idx = lambda dd: pd.DatetimeIndex([pd.Timestamp(int(x) * 86400, unit="s") for x in dd])
    vv = pd.Series(list(v.values()), index=idx(list(v))).reindex(days).fillna(0.0).values
    mm = pd.Series(list(m.values()), index=idx(list(m))).reindex(days).fillna(0.0).values
    return vv, np.minimum(mm, vv)


def evaluate_any(tr, D, kind, sym, W=None, days=None):
    if kind == "mt5broker":
        v, m, ent = T.day_frames(tr, D.m1)
        return T.evaluate(v, m, ent, W)
    tt = TS.trade_table(D, tr)
    return TS.evaluate_fn(lambda r: day_series_multi(tt, TS.PRODUCT[sym], r, days), days)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--grid", action="store_true"); ap.add_argument("--primary", action="store_true"); ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--symbols", default=",".join(MT5BROKER_SYMS + FUT_SYMS))
    a = ap.parse_args(argv)
    rows = []
    for sym in a.symbols.split(","):
        D, kind = build(sym)
        W = T.windows("B") if kind == "mt5broker" else None
        days = pd.bdate_range(O.START, O.END)
        cfgs = list(CONFIGS) if a.grid else ["D"]
        for cname, f, mult in itertools.product(cfgs, (0.5, 0.62, 0.79) if a.grid else (0.5,), (1.0, 2.0) if a.grid else (2.0,)):
            tr = D.simulate2(2.0, f, mult, CONFIGS[cname])
            if len(tr) < 20:
                print(f"{sym} {cname} f={f} m={mult:g}: too few trades ({len(tr)})", flush=True); continue
            R = rmult(tr, D, kind, sym)
            yrs = (O.END - O.START).days / 365.25
            Rl = rmult(D.null2(tr, mult, "long"), D, kind, sym)
            rs = [rmult(D.null2(tr, mult, "coin", np.random.default_rng(sd)), D, kind, sym).mean() for sd in range(a.seeds if not a.grid else 8)]
            row = dict(symbol=sym, cfg=cname, f=f, m=mult, trades=len(tr), per_year=len(tr) / yrs, long_share=float((tr.side == 1).mean()), win_pct=100 * float((R > 0).mean()), mean_R=float(R.mean()), t=tstat(R),
                       alllong_R=float(Rl.mean()), coin_R=float(np.mean(rs)), beats_coin=float(np.mean(np.array(rs) < R.mean())))
            print(f"{sym} cfg {cname} f={f} m={mult:g}: {row['trades']} trades ({row['per_year']:.0f}/yr, long {row['long_share']:.0%}) win {row['win_pct']:.0f}% meanR {row['mean_R']:+.3f} (t {row['t']:+.1f}) | same minutes all-long {row['alllong_R']:+.3f}, coin-flip {row['coin_R']:+.3f}, real beats {row['beats_coin']:.0%} of coin runs", flush=True)
            if a.primary:
                ev = evaluate_any(tr, D, kind, sym, W, days)
                if kind == "mt5broker":
                    for H in T.HORIZONS:
                        e = ev[ev.horizon == H].set_index("rule")
                        print(f"    within {H:>2} days: " + " | ".join(f"{r} {e.loc[r, 'pass_pct']:.0f}% (breach {e.loc[r, 'breach_pct']:.0f}%, loyo {e.loc[r, 'loyo_pass_pct']:.0f}%)" for r in e.index if pd.notna(e.loc[r, 'pass_pct'])), flush=True)
                    nev = [evaluate_any(D.null2(tr, mult, "long"), D, kind, sym, W, days)]
                    print("    NULL-LONG: " + " | ".join(f"{H}d MT5 1-Step {x[x.horizon == H].set_index('rule').loc['MT5 1-Step', 'pass_pct']:.0f}%" for x in nev for H in T.HORIZONS), flush=True)
                else:
                    print("    Broker $50K Test pass (in-sample / leave-1-yr-out, breach): " + ", ".join(f"{H}d {ev[H]['pass_pct']:.0f}/{ev[H]['loyo_pass_pct']:.0f}% ({ev[H]['breach_pct']:.0f}%, r=${ev[H]['best_risk']})" for H in TS.HORIZONS), flush=True)
                    nl = evaluate_any(D.null2(tr, mult, "long"), D, kind, sym, W, days)
                    print("    NULL-LONG (same minutes, all long): " + ", ".join(f"{H}d {nl[H]['pass_pct']:.0f}/{nl[H]['loyo_pass_pct']:.0f}%" for H in TS.HORIZONS), flush=True)
                    row.update({f"pass_{H}": ev[H]["pass_pct"] for H in TS.HORIZONS})
            rows.append(row)
    pd.DataFrame(rows).to_csv(HERE / ("ote_stdv_v2_grid.csv" if a.grid else "ote_stdv_v2_primary.csv"), index=False)


if __name__ == "__main__":
    main()
