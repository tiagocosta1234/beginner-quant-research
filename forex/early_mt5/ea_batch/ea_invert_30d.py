"""Round 347f -- two ideas from the trader (2026-10-06) tested on the batch's 2026 results, equity-aware (floating.py), nothing tuned on the data it is scored on.

(A) INVERSION. Flipping an EA's direction at the same times and prices turns its gross P&L G into -G but charges the spread again (a mirrored buy enters at the bid and exits at the ask):
    inverted net per trade = -profit - (spread at entry + spread at exit) * volume * K + commission.
    It beats the original only when the EA loses by MORE than its round-trip costs. Per verified EA with >= MIN_POS positions: the inverted net, its t-stat, and whether it is positive in BOTH
    halves of 2026 (Jan-Jun, Jul-Sep). 200 EAs are screened, so the worst few losers are mostly unlucky, not systematically wrong: the two-halves rule is the guard.
(B) A DE-RISKED PORTFOLIO AIMED AT 30 DAYS. Every EA runs at a fraction w of its equity-capped safe size. The portfolio's daily P&L is the sum; its worst equity of each day is bounded by the sum of the
    members' worst equities (conservative). EAs and the common scale are chosen GREEDILY on the TRAIN starts only (30-day windows ending by 30 Jun) to maximise the 1-Step 30-day pass rate subject to
    breach <= 10%, then scored on TEST starts (Jul 1 - Aug 31 starts). The null: random EAs from the same pool, the same number, the scale tuned on train the same way.
    Power is small: the test is about two independent months.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import floating
from mt5broker.ea_batch.analyze_reports import INITIAL, daily_pnl

HERE = Path(__file__).resolve().parent
RES = HERE / "results_2026"
SUMMARY = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\finance\scratch\mon_out\results_summary.csv")
MIN_POS = 30
DAYS = pd.bdate_range("2026-01-01", "2026-09-30")
TRAIN = [list(pd.bdate_range(s, s + pd.Timedelta(days=30))) for s in DAYS if s + pd.Timedelta(days=30) <= pd.Timestamp("2026-06-30")]
TEST = [list(pd.bdate_range(s, s + pd.Timedelta(days=30))) for s in pd.bdate_range("2026-07-01", "2026-08-31")]
SCALES = (0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)


def inversion(st: pd.DataFrame):
    rows = []
    for r in st.itertuples():
        f = RES / f"{r.id}.csv"
        deals = pd.read_csv(f)
        fl = floating.get(r.id, 2026, f, str(r.symbol), float(r.eq_dd), "2026-01-01", "2026-09-30")
        if not fl.ok:
            continue
        kp = floating.prior_k(str(r.symbol), pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-01"))
        pos, _ = floating.pair_positions(deals, kp)
        if pos is None or len(pos) < MIN_POS:
            continue
        bars, _ = floating.bars_for(str(r.symbol), pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-01"))
        ts = bars.index.values.astype("datetime64[ns]").astype(np.int64)
        sp = (bars.ac.values - bars.bc.values)
        i0, i1 = floating._bar_idx(ts, pos.te.values), floating._bar_idx(ts, pos.tx.values)
        cost = (sp[i0] + sp[i1]) * pos.v.values * pos.k.values
        comm = deals.commission.values.sum() / len(pos)                            # commission per position, both sides
        inv = -pos.profit.values - cost + comm
        orig = pos.profit.values + comm
        half = pd.to_datetime(pos.tx.values) < pd.Timestamp("2026-07-01")
        sd = inv.std()
        rows.append(dict(id=r.id, title=str(r.title)[:34], symbol=r.symbol, period=r.period, positions=len(pos), orig_net=orig.sum(), inv_net=inv.sum(), inv_mean=inv.mean(),
                         inv_t=inv.mean() / sd * np.sqrt(len(inv)) if sd > 0 else np.nan, inv_h1=inv[half].sum(), inv_h2=inv[~half].sum(), spread_cost=cost.sum(), gross=pos.profit.sum()))
    return pd.DataFrame(rows)


def load_pool(s1: pd.DataFrame):
    pool = {}
    for r in s1[s1.rankable_e == True].itertuples():
        f = RES / f"{r.id}.csv"
        fl = floating.get(r.id, 2026, f, str(r.symbol), float(r.eq_dd), "2026-01-01", "2026-09-30")
        if not fl.ok:
            continue
        lam = float(r.lam_max_eq)
        d = pd.read_csv(f, usecols=["time", "direction"])
        ent = set(pd.to_datetime(d.time[d.direction == "in"].astype(str).str.replace(".", "-", regex=False)).dt.normalize())
        pool[r.id] = dict(title=str(r.title)[:34], v=daily_pnl(f).reindex(DAYS).fillna(0.0) * lam, m=fl.m.reindex(DAYS).fillna(0.0) * lam, ent=ent)
    return pool


def score(ids, c, windows, pool):
    v = sum(pool[i]["v"] * c for i in ids).to_dict(); m = sum(pool[i]["m"] * c for i in ids).to_dict(); ent = set().union(*[pool[i]["ent"] for i in ids])
    o = [floating.replay_1step_eq(v, m, w)[0] for w in windows]
    return float(np.mean([x == "pass" for x in o])), float(np.mean([x == "breach" for x in o]))


def best_scale(ids, pool):
    best = None
    for c in SCALES:
        p, b = score(ids, c, TRAIN, pool)
        if b <= 0.10 and (best is None or p > best[1]):
            best = (c, p)
    return best


def greedy(cands, pool, kmax=10):
    chosen, cur = [], 0.0
    while len(chosen) < kmax:
        top = None
        for i in cands:
            if i in chosen:
                continue
            bs = best_scale(chosen + [i], pool)
            if bs and (top is None or bs[1] > top[2]):
                top = (i, bs[0], bs[1])
        if top is None or top[2] < cur + 0.01:
            break
        chosen.append(top[0]); cur = top[2]
    return chosen


def main():
    st = pd.read_csv(RES / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last")
    st = st[st.deals > 0].dropna(subset=["eq_dd"])
    inv = inversion(st)
    print(f"(A) INVERSION: {len(inv)} verified EAs with >= {MIN_POS} positions")
    print(f"    originals with net > 0: {int((inv.orig_net > 0).sum())}; inverted net > 0: {int((inv.inv_net > 0).sum())}; inverted net > 0 in BOTH halves of 2026: {int(((inv.inv_h1 > 0) & (inv.inv_h2 > 0)).sum())};"
          f" inverted t >= 2: {int((inv.inv_t >= 2).sum())}; both halves and t >= 2: {int(((inv.inv_h1 > 0) & (inv.inv_h2 > 0) & (inv.inv_t >= 2)).sum())}")
    print(f"    median per-EA spread cost of a flip (mirrored trades pay it again): {inv.spread_cost.median():,.0f} $; median gross {inv.gross.median():,.0f} $")
    print(inv.sort_values("inv_t", ascending=False).head(6)[["id", "title", "symbol", "period", "positions", "orig_net", "inv_net", "inv_t", "inv_h1", "inv_h2"]].round(1).to_string(index=False))
    inv.to_csv(HERE / "ea_invert_results.csv", index=False)

    s1 = pd.read_csv(SUMMARY, dtype={"id": str})
    pool = load_pool(s1)
    train_net = {i: pool[i]["v"][pool[i]["v"].index <= "2026-06-30"].sum() for i in pool}
    cands = [i for i in pool if train_net[i] > 0]
    print(f"\n(B) DE-RISKED 30-DAY PORTFOLIO: pool {len(pool)} verified EAs, {len(cands)} with positive train P&L; {len(TRAIN)} train starts, {len(TEST)} test starts")
    ch = greedy(cands, pool)
    c, ptrain = best_scale(ch, pool)
    ptest, btest = score(ch, c, TEST, pool); pt, bt = score(ch, c, TRAIN, pool)
    print(f"    greedy picks {len(ch)} EAs at {c:.2f} of their safe size: TRAIN 30-day pass {pt:.0%} (breach {bt:.0%}); TEST {ptest:.0%} (breach {btest:.0%})")
    for i in ch:
        print(f"      {i}: {pool[i]['title']}")
    rng = np.random.default_rng(347); res = []
    for _ in range(100):
        sub = list(rng.choice(cands, size=len(ch), replace=False))
        bs = best_scale(sub, pool)
        if bs:
            res.append(score(sub, bs[0], TEST, pool)[0])
    print(f"    NULL: {len(res)} random sets of {len(ch)} EAs from the same pool, scale tuned on train: TEST 30-day pass mean {np.mean(res):.0%}, 90th percentile {np.percentile(res, 90):.0%}, max {np.max(res):.0%}")
    # equal-weight of every EA in the pool, no selection at all
    p_all, b_all = score(list(pool), 0.05, TEST, pool)
    print(f"    no selection at all: every verified EA at 5% of its size, TEST pass {p_all:.0%} (breach {b_all:.0%})")


if __name__ == "__main__":
    main()
