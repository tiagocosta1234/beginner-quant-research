"""Round 347j -- the OTE / STDV rules on MT5 STOCK CFDs (the trader: "why dont we just try to trade stocks? would this be profitable on MT5?").

UNIVERSE: planned as 12 liquid names fixed by liquidity before any result (AAPL MSFT NVDA AMZN GOOG META TSLA AMD NFLX AVGO JPM PLTR); the terminal serves history for only MSFT and NVDA (Oct 2021+), AMD and INTC (Jan 2026+) -- chosen by availability, not performance. Data: MT5 broker tick history -> 1-minute BID / ASK bars
(forex/early_mt5/stock_pull.py, the same builder as the index files), 2021-10 .. 2026-10; evaluation 2022-01-01 .. 2026-09-30.

ADAPTATION (the index routine needs an overnight session that stocks do not have; these are the fixed substitutes, written before any result):
  range     the opening range 09:30-10:00 New York (what exists of it: the CFD's first quote is ~09:35); R = high - low (mid); days with R < 0.10% of price skipped
  tap       k x R beyond the range, k in {0.5, 1.0, 1.5} (a stock's day is a few opening ranges wide, so the index's 2.0 would almost never print); structure / entry / stop / target exactly as ote_stdv_eval.py
  entries   10:00 .. 14:00 NY; everything is flat at 15:55 NY (no overnight: no earnings gaps, no swap)
  CONFIGS   A = reversal only, 1 entry a day (v1);  D = reversal + continuation (trend bias), up to 3 entries, stop after 2 losses (v2).   f in {0.5, 0.62}, m in {1, 2}: 3 x 2 x 2 x 2 = 24 runs per stock.
  PRIMARY   A: k = 1.0, f = 0.62, m = 2 (the v1 primary, scaled to the opening range)   and   D: k = 1.0, f = 0.5, m = 2 (the v2 primary).
COSTS     the real bid / ask of MT5 broker's feed (3-8 bp of spread for a stock, ~0.5 bp for US100) + commission 0.004% of the notional per side (the rate review sites quote for MT5 broker stock CFDs; NOT verified
          against MT5 broker's own page -- spread dominates it anyway).
LEVERAGE  read from the terminal (order_calc_margin): stock CFDs carry 30% margin = 3.3x leverage on the MT5-Demo server. The position notional is capped at 3.3 x $100K per position (single stock) and
          at 3.3 x $100K / 4 per position when 12 stocks trade as ONE account (assumes at most ~4 open at once).
RULES     MT5 1-Step / 2-Step and Broker 1-Step / 2-Step exactly as trendline_eval.py (equity-aware: floating losses at the worst bid / ask of every minute), 30 / 60 / 86 days from every start.
NULLS     same entry minutes, stops and reward multiple: coin-flip side, and all-long.

  python -m mt5broker.ea_batch.ote_stdv_stocks --grid
  python -m mt5broker.ea_batch.ote_stdv_stocks --primary
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import ote_stdv_eval as O
from mt5broker.ea_batch import ote_stdv_v2 as V
from mt5broker.ea_batch import trendline_eval as T
from mt5broker.ea_batch.firm_compare import attempt

HERE = Path(__file__).resolve().parent
STOCKS = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "AMD", "NFLX", "AVGO", "JPM", "PLTR", "INTC")
COMM, LEV = 0.00004, 10 / 3
for _s in STOCKS:
    T.SYMBOLS[_s] = (f"{_s}_M1_ticks_full.parquet", lambda p: 1.0, 0.0, "B")
CONFIGS = {"A": dict(rev=True, cont=False, n=1), "D": dict(rev=True, cont=True, n=3)}
RISKS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0)
YEARS, HORIZONS, RULES = tuple(T.YEARS), T.HORIZONS, T.RULES


class StockV2(V.V2):
    OFF = (570, 600, 840, 955)
    MIN_RANGE_MIN = 20


def build(sym):
    O.START, O.END = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-09-30")
    return StockV2(sym)


def net_R(tr):
    """R per trade after the spread (already in the fills) and the round-trip commission."""
    if tr.empty:
        return np.array([])
    pts = tr.side.values * (tr.px.values - tr.pe.values) - 2 * COMM * np.abs(tr.pe.values)
    return pts / tr.dist.values


def scaled(tr, r, per_pos_cap):
    """The trades at risk r% of $100K per trade, notional capped; returns the frame day_frames() wants (gross and commission in $, lots = shares)."""
    lots = np.minimum(tr.lots.values * r, per_pos_cap * T.INITIAL / np.abs(tr.pe.values))
    out = tr.copy()
    out["lots"] = lots
    out["gross"] = tr.side.values * (tr.px.values - tr.pe.values) * lots
    out["comm"] = COMM * np.abs(tr.pe.values) * lots
    if "swap" in tr.columns:                                                       # financing of positions held overnight, scaled with the position
        out["gross"] = out["gross"] - tr.swap.values * lots / tr.lots.values
    return out


def evaluate_capped(parts, W, per_pos_cap, max_breach=0.10):
    """parts = [(D, trades)] (one or several stocks as one account). Same pass / breach replay and best-risk logic as T.evaluate, with the risk and the notional cap applied per risk level."""
    res = {}
    for r in RISKS:
        v = m = None; ent = set()
        for D, tr in parts:
            if tr.empty:
                continue
            a, b, e = T.day_frames(scaled(tr, r, per_pos_cap), D.m1)
            v = a if v is None else v.add(a, fill_value=0.0); m = b if m is None else m.add(b, fill_value=0.0); ent |= e
        if v is None:
            continue
        m = np.minimum(m, v)                                                       # the sum of the stocks' worst equities is a conservative bound
        pnl, mm = v.to_dict(), m.to_dict()
        for y in YEARS:
            for R in RULES:
                for H in HORIZONS:
                    n = p = bb = 0
                    for days in W[(y, H)]:
                        o, _ = attempt(days, pnl, mm, ent, R)
                        n += 1; p += o == "pass"; bb += o == "breach"
                    res[(R.name, H, r, y)] = (n, p, bb)
    out = []
    for R in RULES:
        for H in HORIZONS:
            def pick(ys):
                best = None
                for r in RISKS:
                    k = (R.name, H, r, ys[0])
                    if k not in res:
                        continue
                    n = sum(res[(R.name, H, r, y)][0] for y in ys); p = sum(res[(R.name, H, r, y)][1] for y in ys); b = sum(res[(R.name, H, r, y)][2] for y in ys)
                    if n and b / n <= max_breach and (best is None or (p / n, -r) > best[0]):
                        best = ((p / n, -r), r)
                return None if best is None else best[1]
            r = pick(YEARS)
            row = dict(rule=R.name, horizon=H, best_risk_pct=r, pass_pct=np.nan, breach_pct=np.nan)
            if r is not None:
                n = sum(res[(R.name, H, r, y)][0] for y in YEARS)
                row.update(pass_pct=100 * sum(res[(R.name, H, r, y)][1] for y in YEARS) / n, breach_pct=100 * sum(res[(R.name, H, r, y)][2] for y in YEARS) / n)
            n = p = b = 0
            for hy in YEARS:
                r2 = pick(tuple(y for y in YEARS if y != hy))
                if r2 is not None:
                    a = res[(R.name, H, r2, hy)]; n += a[0]; p += a[1]; b += a[2]
            row.update(loyo_pass_pct=100 * p / n if n else np.nan, loyo_breach_pct=100 * b / n if n else np.nan)
            out.append(row)
    return pd.DataFrame(out)


def fmt(ev, tag):
    for H in HORIZONS:
        e = ev[ev.horizon == H].set_index("rule")
        print(f"    {tag} within {H:>2} days: " + " | ".join(f"{r} {e.loc[r, 'pass_pct']:.0f}% (breach {e.loc[r, 'breach_pct']:.0f}%, r={e.loc[r, 'best_risk_pct']}%; loyo {e.loc[r, 'loyo_pass_pct']:.0f}%)" for r in e.index if pd.notna(e.loc[r, 'pass_pct'])), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--grid", action="store_true"); ap.add_argument("--primary", action="store_true"); ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--symbols", default=",".join(STOCKS))
    a = ap.parse_args(argv)
    syms = [s for s in a.symbols.split(",") if (T.DATA / T.SYMBOLS[s][0]).exists()]
    print("symbols with data:", syms, flush=True)
    Ds = {s: build(s) for s in syms}
    if a.grid:
        rows = []
        for s in syms:
            D = Ds[s]
            for cname, k, f, m in itertools.product(("A", "D"), (0.5, 1.0, 1.5), (0.5, 0.62), (1.0, 2.0)):
                tr = D.simulate2(k, f, m, CONFIGS[cname])
                if len(tr) < 20:
                    continue
                R = net_R(tr)
                Rl = net_R(D.null2(tr, m, "long"))
                rs = [net_R(D.null2(tr, m, "coin", np.random.default_rng(sd))).mean() for sd in range(6)]
                row = dict(symbol=s, cfg=cname, k=k, f=f, m=m, trades=len(tr), per_year=len(tr) / 4.75, win_pct=100 * float((R > 0).mean()), mean_R=float(R.mean()), t=V.tstat(R), alllong_R=float(Rl.mean()), coin_R=float(np.mean(rs)),
                           spread_bp=float((tr.spread / (tr.lots * tr.pe.abs())).mean() * 1e4), stop_pct=float((tr.dist / tr.pe.abs()).mean() * 100))
                rows.append(row)
                print(f"{s} {cname} k={k} f={f} m={m:g}: {row['trades']} trades ({row['per_year']:.0f}/yr) win {row['win_pct']:.0f}% meanR {row['mean_R']:+.3f} (t {row['t']:+.1f}) | all-long {row['alllong_R']:+.3f}, coin {row['coin_R']:+.3f} | stop {row['stop_pct']:.2f}%, spread {row['spread_bp']:.1f}bp", flush=True)
        pd.DataFrame(rows).to_csv(HERE / "ote_stdv_stocks_grid.csv", index=False)
    if a.primary:
        W = T.windows("B"); out = []
        for cname, k, f, m in (("A", 1.0, 0.62, 2.0), ("D", 1.0, 0.5, 2.0)):
            trs = {s: Ds[s].simulate2(k, f, m, CONFIGS[cname]) for s in syms}
            allR = np.concatenate([net_R(t) for t in trs.values() if len(t)])
            print(f"\nPRIMARY {cname} (k={k}, f={f}, m={m:g}) on {len(syms)} stocks: {sum(len(t) for t in trs.values())} trades ({sum(len(t) for t in trs.values()) / 4.75:.0f}/yr), win {100 * (allR > 0).mean():.0f}%, mean R {allR.mean():+.3f} (t {V.tstat(allR):+.1f})", flush=True)
            for tag, parts, cap in (("ONE ACCOUNT, all stocks", [(Ds[s], trs[s]) for s in syms], LEV / 4),):
                ev = evaluate_capped(parts, W, cap); fmt(ev, tag); ev["cfg"] = cname; ev["kind"] = "real"; out.append(ev)
                nl = [(Ds[s], Ds[s].null2(trs[s], m, "long")) for s in syms if len(trs[s])]
                fmt(evaluate_capped(nl, W, cap), "NULL-LONG one account")
                nc = [(Ds[s], Ds[s].null2(trs[s], m, "coin", np.random.default_rng(1))) for s in syms if len(trs[s])]
                fmt(evaluate_capped(nc, W, cap), "NULL-COIN one account (seed 1)")
            for s in syms[:4]:
                if len(trs[s]) > 20:
                    ev = evaluate_capped([(Ds[s], trs[s])], W, LEV)
                    e = ev[ev.horizon == 30].set_index("rule")
                    print(f"    {s} alone: {len(trs[s])} trades, mean R {net_R(trs[s]).mean():+.3f}; 30d pass " + ", ".join(f"{r} {e.loc[r, 'pass_pct']:.0f}%" for r in e.index if pd.notna(e.loc[r, 'pass_pct'])), flush=True)
        pd.concat(out).to_csv(HERE / "ote_stdv_stocks_primary.csv", index=False)


if __name__ == "__main__":
    main()
