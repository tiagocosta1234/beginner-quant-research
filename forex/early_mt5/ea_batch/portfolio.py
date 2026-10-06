"""Round 347 stage 3 -- PORTFOLIO BUILDER (written 2026-10-05 at the trader's request: "10 EAs returning 1% each a month" -- many independent small edges instead of one EA that must do it all).

WHY: for independent edges the combined Sharpe grows with the square root of their number, so a handful of smooth EAs that cannot pass alone can pass together (a Monte Carlo of ten
independent Sharpe-2 EAs at +1% a month each passed 58% of 1-Step attempts in 30 days with 3% breach, against 0% for one). Correlation destroys that (rho 0.3: 55% breach), and so does a
member that is not real, so only stage-2 CONFIRMED EAs (confirmed_summary.csv) are eligible; Market EAs tested by hand join through register_market_ea.py.
DATA: each member's daily closed P&L in 2026 (stage 1), 2025 and 2024 (stage 2) at its frozen stage-1 safe size (confirm.load_year), the three years replayed separately; when every member's floating-loss
rebuild is verified (floating.py) the floors are tested on equity (the sum of the members' worst equity of each day, the conservative bound), else on closed P&L.
SIZING: member i runs at the fraction w_i = min(1, c / D_i) of its own safe size, D_i = its largest equity drawdown ($) over the years at that size, so every member contributes at most the
same drawdown c and none exceeds its own safe size. The combined tester equity drawdown is ESTIMATED (the tester runs one EA at a time, so there is no combined curve) as sqrt(d' R d),
d = each member's equity drawdown at its weight, R = the daily-P&L correlation matrix of that year with negative entries set to 0 and every pair floored at RHO_FLOOR = 0.25 (drawdowns
cluster in stress). c is the largest value with that estimate <= EQ_BUDGET = 8% of $100K in every year.
SELECTION (greedy, fixed now): start from the best single EA and keep adding the EA that raises the objective most, while the gain is at least MIN_GAIN = 1 point, up to MAX_MEMBERS = 10.
OBJECTIVE: mean over the years of p1_30 + 0.5 p1_60 + 0.25 p1_86 (1-Step pass within 30 / 60 / 86 calendar days, closed-deal replay of every weekday start); a portfolio whose 86-day breach rate
exceeds 10% in any year is infeasible.
CHECK: leave-one-year-out -- the same greedy on two years, weights frozen, scored on the third -- shows how much of the in-sample result survives. With three years and a handful of
members this is still optimistic: it removes EAs that do not diversify, it does not prove the survivors have an edge.

  python -m mt5broker.ea_batch.portfolio                    # confirmed EAs -> portfolio_members.csv + portfolio_summary.json
  python -m mt5broker.ea_batch.portfolio --members id1,id2  # force a member list from the stage-1 results (a test; nothing is written)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch.floating import replay_1step_eq, replay_2step_eq
from mt5broker.ea_batch.analyze_reports import INITIAL
from mt5broker.ea_batch.confirm import HERE, _W, load_year, stage1

ALL_YEARS = (2026, 2025, 2024)
EQ_BUDGET = 0.08 * INITIAL
RHO_FLOOR = 0.25
MAX_MEMBERS, MIN_GAIN, MAX_BREACH86 = 10, 0.01, 0.10
OUT_CSV, OUT_JSON = HERE / "portfolio_members.csv", HERE / "portfolio_summary.json"


def load_members(rows: pd.DataFrame, base_dir: Path | None = None) -> dict:
    """id -> dict(row, data={year: load_year data}) for the EAs whose three years all load."""
    M = {}
    for _, r in rows.iterrows():
        data = {}
        for y in ALL_YEARS:
            status, d = load_year(r, y, base_dir)
            if d is None:
                break
            data[y] = d
        else:
            M[r.id] = dict(row=r, data=data)
    return M


def est_dd(M: dict, ids: list, y: int, w: dict) -> float:
    dd = np.array([M[i]["data"][y]["eq_dd"] * w[i] for i in ids])
    if len(ids) == 1:
        return float(dd[0])
    P = pd.DataFrame({i: M[i]["data"][y]["pnl"] for i in ids})
    R = np.maximum(P.corr().fillna(0.0).clip(lower=0.0).to_numpy(), RHO_FLOOR)
    np.fill_diagonal(R, 1.0)
    return float(np.sqrt(dd @ R @ dd))


def weights(M: dict, ids: list, years) -> dict:
    """w_i = min(1, c / D_i), c the largest drawdown unit ($) keeping the estimated combined equity drawdown within EQ_BUDGET in every year (bisection)."""
    D = {i: max(M[i]["data"][y]["eq_dd"] for y in years) for i in ids}
    def w_of(c):
        return {i: min(1.0, c / D[i]) if D[i] > 0 else 1.0 for i in ids}
    ok = lambda c: max(est_dd(M, ids, y, w_of(c)) for y in years) <= EQ_BUDGET
    hi = max(D.values())
    if ok(hi):
        return w_of(hi)
    lo = 0.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return w_of(lo)


def evaluate(M: dict, ids: list, w: dict, years) -> dict:
    out = {}
    for y in years:
        pnl = sum(M[i]["data"][y]["pnl"] * w[i] for i in ids)
        d = pnl.to_dict(); ent = set().union(*[M[i]["data"][y]["ent"] for i in ids]); wins = _W[y][1]
        # floating losses: when every member's rebuild is verified, the portfolio's worst equity of a day is bounded by the SUM of the members' worst equities (their worst minutes need not
        # coincide, so this is the conservative side); otherwise the closed P&L is tested, as before
        mm = sum(M[i]["data"][y]["m"] * w[i] for i in ids).to_dict() if all(M[i]["data"][y].get("m") is not None for i in ids) else None
        o = dict(floating=mm is not None)
        for H, dls in wins.items():
            r1 = [replay_1step_eq(d, mm, dl)[0] for dl in dls]; r2 = [replay_2step_eq(d, mm, ent, dl) for dl in dls]
            o[f"p1_{H}"] = float(np.mean([x == "pass" for x in r1])); o[f"b1_{H}"] = float(np.mean([x == "breach" for x in r1]))
            o[f"p2_{H}"] = float(np.mean([x == "pass" for x in r2]))
        o["ret30"] = float(np.mean([sum(d.get(x, 0.0) for x in dl) for dl in wins[30]]) / INITIAL * 100)
        sd = float(pnl.std()); o["sharpe"] = float(pnl.mean() / sd * np.sqrt(252)) if sd > 0 else float("nan")
        o["est_dd_pct"] = est_dd(M, ids, y, w) / INITIAL * 100
        o["net"] = float(pnl.sum())
        out[y] = o
    return out


def objective(ev: dict) -> tuple:
    ys = list(ev)
    m = lambda k: float(np.mean([ev[y][k] for y in ys]))
    feasible = max(ev[y]["b1_86"] for y in ys) <= MAX_BREACH86
    return (feasible, m("p1_30") + 0.5 * m("p1_60") + 0.25 * m("p1_86"), m("p1_30"), m("p1_60"), m("p1_86"))


def build(M: dict, years) -> tuple:
    """Greedy forward selection on `years`; returns (member ids, w, evaluation on those years)."""
    chosen, best = [], None
    while len(chosen) < MAX_MEMBERS:
        cands = []
        for i in M:
            if i in chosen:
                continue
            ids = chosen + [i]; w = weights(M, ids, years); ev = evaluate(M, ids, w, years)
            cands.append((objective(ev), i, w, ev))
        if not cands:
            break
        key, i, w, ev = max(cands, key=lambda c: c[0])
        if chosen and not (key[0] and key[1] >= best[1] + MIN_GAIN):
            break
        chosen.append(i); best = key; best_w, best_ev = w, ev
    return chosen, best_w, best_ev


def diversification(M: dict, ids: list, w: dict) -> dict:
    P = pd.concat([pd.DataFrame({i: M[i]["data"][y]["pnl"] * w[i] for i in ids}) for y in ALL_YEARS])
    sd = P.std()
    port_sd = float(P.sum(axis=1).std())
    corr = P.corr().to_numpy(); off = corr[np.triu_indices(len(ids), 1)] if len(ids) > 1 else np.array([])
    return dict(avg_pairwise_corr=float(np.nanmean(off)) if off.size else float("nan"), max_pairwise_corr=float(np.nanmax(off)) if off.size else float("nan"), diversification_ratio=float(sd.sum() / port_sd) if port_sd > 0 else float("nan"),
                member_sharpes={i: M[i]["row"].get("avg_sharpe", float("nan")) for i in ids})


def main(argv=None) -> dict | None:
    ap = argparse.ArgumentParser(); ap.add_argument("--members", default="")
    a = ap.parse_args(argv)
    if a.members:
        s1 = stage1(); rows = s1[s1.id.isin(a.members.split(","))]
    else:
        f = HERE / "confirmed_summary.csv"
        if not f.exists():
            print("stage 3: no confirmed_summary.csv yet (run stage 2 first)"); return None
        c = pd.read_csv(f, dtype={"id": str}); rows = c[c.verdict == "CONFIRMED"]
    M = load_members(rows)
    if not M:
        print("stage 3: no confirmed EAs with all three years yet"); return None
    ids, w, ev = build(M, ALL_YEARS)
    print(f"stage 3: {len(M)} eligible EAs -> portfolio of {len(ids)}", flush=True)
    div = diversification(M, ids, w)
    rows_out = []
    for i in ids:
        r = M[i]["row"]; lf = r.get("lam_frozen"); lot_mult = float(lf if pd.notna(lf) else r.lam_max) * w[i]
        rows_out.append(dict(id=i, title=r.title, symbol=r.symbol, period=r.period, weight_of_safe_size=w[i], lot_multiple_of_default=lot_mult,
                             **{f"eq_dd_pct_{y}": M[i]["data"][y]["eq_dd"] * w[i] / INITIAL * 100 for y in ALL_YEARS}))
        print(f"  {str(r.title)[:40]} {r.symbol} {r.period}: {w[i]:.2f} of its safe size = {lot_mult:.2f} x its default lot", flush=True)
    print(f"  diversification: average pairwise correlation {div['avg_pairwise_corr']:.2f}, highest {div['max_pairwise_corr']:.2f}, diversification ratio {div['diversification_ratio']:.1f} (sum of member vols / portfolio vol)", flush=True)
    for y in ALL_YEARS:
        e = ev[y]
        print(f"  {y}{'' if e.get('floating') else ' (closed deals only)'}: 1-Step 30d {e['p1_30']:.0%} ({e['b1_30']:.0%} breach) | 60d {e['p1_60']:.0%} ({e['b1_60']:.0%}) | Dec 31 {e['p1_86']:.0%} ({e['b1_86']:.0%}) | 2-Step both phases 30d {e['p2_30']:.0%} / 60d {e['p2_60']:.0%} / Dec 31 {e['p2_86']:.0%} "
              f"| Sharpe {e['sharpe']:.1f}, avg 30d return {e['ret30']:+.1f}%, est. equity drawdown {e['est_dd_pct']:.1f}%", flush=True)
    loyo = {}
    if len(M) >= 2:
        for h in ALL_YEARS:
            fit = tuple(y for y in ALL_YEARS if y != h)
            ids_h, w_h, _ = build(M, fit)
            loyo[h] = dict(members=ids_h, **evaluate(M, ids_h, w_h, (h,))[h])
        print("  leave-one-year-out (selected on the other two years, weights frozen):", " | ".join(
            f"{h}: {len(loyo[h]['members'])} members, 30d {loyo[h]['p1_30']:.0%}, Dec 31 {loyo[h]['p1_86']:.0%} ({loyo[h]['b1_86']:.0%} breach), est. drawdown {loyo[h]['est_dd_pct']:.1f}%" for h in ALL_YEARS), flush=True)
    summary = dict(members=ids, weight_of_safe_size=w, per_year={str(y): ev[y] for y in ALL_YEARS}, diversification=div, leave_one_year_out={str(h): v for h, v in loyo.items()})
    if not a.members:
        pd.DataFrame(rows_out).to_csv(OUT_CSV, index=False)
        json.dump(summary, open(OUT_JSON, "w"), indent=1, default=float)
    return summary


if __name__ == "__main__":
    main()
