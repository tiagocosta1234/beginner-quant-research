"""
Round 136, batch E: currencies by trading hours, and scheduled-event days.
Pre-registered 2026-09-26 -- rules, variants and verdict rules committed before
any result is run. All holds sit inside Broker's 18:00 -> 16:10 ET trading day.

E1  FX local-hours effect (Breedon & Ranaldo 2013: a currency tends to weaken
    during its own country's trading hours and strengthen in foreign hours).
    Yahoo hourly (close-stamped ET, May 2024 - Sep 2026), micro contracts:
    6E -> M6E, 6B -> M6B, 6J -> MJY, 6A -> M6A.
      (a) LONG each currency during US hours, 09:00 -> 16:00 ET
      (b) SHORT each currency during its own hours: Europe 03:00 -> 08:00 ET
          (6E, 6B); Asia 19:00 -> 02:00 ET (6J, 6A)
    Entry = the first bar's open after the window start, exit = the last close by
    its end. Split: before / from 2025-07-01. Replication: at least 3 of the 4
    currencies positive on their own.
E2  FOMC statement day, long equity indices (Lucca & Moench 2015 pre-FOMC drift):
    ES, NQ, YM, RTY from the 18:00 ET reopen to settlement on each scheduled
    statement day (data/events/fomc_statement_dates.csv, 215 days 2000-2026, from
    federalreserve.gov). The daily close comes after the 14:00 statement, so this
    includes the reaction, not only the pre-announcement drift.
E3  Jobs-report day, long equity indices (Savor & Wilson 2013 announcement
    premium). BLS blocks automated access, so dates follow BLS's timing rule --
    the third Friday after the week containing the 12th of the previous month --
    which misdates some holiday-shifted or shutdown-delayed releases (noise,
    biasing toward zero, not toward a false positive).
E2 and E3 use batch D's daily data, risk units, costs and data-quality rule
(round135_batch_d.market_frame) and its split: 2000-12 / 2013-26 / 2020-26.

4 variants take the ledger from k=132 to k=136. Candidate: net and before-cost
mean R > 0; in-sample P(edge>0) >= 0.95; out-of-sample P(edge>0) >= 1 - 0.01/136;
for E2/E3 also 2020-26 mean R > 0; for E1 also the 3-of-4 replication.
Descriptive only (not in the ledger): excess over being long every day for E2/E3,
and the exact pre-statement window 18:00 -> 14:00 on the hourly data for E2.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datetime as dt
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D
from round134_batch_c import segment_moves

T = dt.time
H.PV.update({"M6B": 6250.0, "MJY": 1_250_000.0, "M6A": 10_000.0})
H.TK.update({"M6B": 0.0001, "MJY": 0.000001, "M6A": 0.0001})
FX = {"6E=F": ("M6E", (T(3, 0), T(8, 0))), "6B=F": ("M6B", (T(3, 0), T(8, 0))),
      "6J=F": ("MJY", (T(19, 0), T(2, 0))), "6A=F": ("M6A", (T(19, 0), T(2, 0)))}
US = (T(9, 0), T(16, 0))
EVENTS = os.path.join(H.HERE, "..", "data", "events", "fomc_statement_dates.csv")
N_VARIANTS = 4


def fx_window_trades(sym, micro, window, direction):
    mv = segment_moves(H.load_yahoo_hourly(sym), *window)
    hours = ((window[1].hour - window[0].hour) % 24)
    mv = mv[mv["n"] >= hours - 1].copy()
    mv["r"] = np.log(mv["exit"] / mv["entry"])
    mv["sd"] = mv["r"].shift(1).rolling(20).std()
    mv = mv[mv["sd"] > 0]
    cost_r = H.cost_per_contract(micro) / (mv["sd"] * mv["entry"] * H.PV[micro])
    gross = direction * mv["r"] / mv["sd"]
    return pd.DataFrame({"date": mv.index, "market": micro, "gross": gross.values, "pnl": (gross - cost_r).values})


def judge_fx(name, tr, k):
    split = J.OOS_START
    a, i, o = J.edge_stats(tr, n_boot=40_000), J.edge_stats(tr[tr["date"] < split]), J.edge_stats(tr[tr["date"] >= split], n_boot=40_000)
    per = tr.groupby("market")["pnl"].mean()
    n_pos = int((per > 0).sum())
    bar = H.oos_bar(k)
    daily = tr.groupby("date")["pnl"].sum()
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar and n_pos >= 3)
    print(f"  {name:<50} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | to 2025-06 {i['exp']:+.3f}R "
          f"P {i['p_pos']:.3f} | from 2025-07 {o['exp']:+.3f}R P {o['p_pos']:.4f} (bar {bar:.5f}) | "
          f"{n_pos}/4 currencies positive | Sharpe/day {daily.mean() / daily.std():+.3f} | {'CANDIDATE' if cand else 'no'}")
    print("      by currency: " + ", ".join(f"{m} {v:+.3f}" for m, v in per.items()), flush=True)
    return dict(name=name, n=a["n"], exp=a["exp"], exp_gross=float(tr["gross"].mean()), p_is=i["p_pos"],
                p_oos=o["p_pos"], exp_is=i["exp"], exp_oos=o["exp"], positive_markets=n_pos, k=k, bar=bar,
                sharpe=float(daily.mean() / daily.std()), candidate=cand)


def jobs_report_dates(start=2000, end=2026):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            ref = pd.Timestamp(y, m, 1) - pd.DateOffset(months=1) + pd.Timedelta(days=11)  # the 12th of last month
            week_end = ref + pd.Timedelta(days=(5 - ref.weekday()) % 7)  # Saturday ending that week
            first_fri = week_end + pd.Timedelta(days=6)                 # Saturday + 6 = Friday
            out.append(first_fri + pd.Timedelta(weeks=2))               # the third Friday after
    return pd.DatetimeIndex(out)


def event_trades(frames, dates):
    out = []
    for sym in D.EQUITY:
        d = frames[sym]
        out.append(D.trades_from(d, pd.Series(np.where(d.index.isin(dates), 1, 0), index=d.index), sym))
    return pd.concat(out, ignore_index=True)


def excess_vs_long(frames, tr):
    allong = pd.concat([D.trades_from(frames[s], pd.Series(1, index=frames[s].index), s) for s in D.EQUITY])
    for lab, lo, hi in [("2000-12", "2000", "2012-12-31"), ("2013-26", "2013", "2026-12-31")]:
        a = allong[(allong["date"] >= lo) & (allong["date"] <= hi)]["pnl"].values
        e = tr[(tr["date"] >= lo) & (tr["date"] <= hi)]["pnl"].values
        rng = np.random.default_rng(0)
        boot = np.array([rng.choice(e, len(e)).mean() - rng.choice(a, len(a)).mean() for _ in range(4000)])
        print(f"      {lab}: event days {e.mean():+.3f}R vs long every day {a.mean():+.3f}R -> excess "
              f"{e.mean() - a.mean():+.3f}R, P(excess>0) {(boot > 0).mean():.3f}")


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch E = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    rows = []

    print("E1 FX local-hours effect (Yahoo hourly, 4 currencies)")
    us = pd.concat([fx_window_trades(s, micro, US, 1) for s, (micro, _) in FX.items()], ignore_index=True)
    rows.append(judge_fx("E1a long each currency in US hours 09-16", us, k))
    loc = pd.concat([fx_window_trades(s, micro, win, -1) for s, (micro, win) in FX.items()], ignore_index=True)
    rows.append(judge_fx("E1b short each currency in its own hours", loc, k))

    frames = {s: D.market_frame(s) for s in D.EQUITY}
    fomc = pd.DatetimeIndex(pd.read_csv(EVENTS, parse_dates=["date"])["date"])
    print("\nE2 FOMC statement day, long 4 equity indices (18:00 reopen -> settlement)")
    t2 = event_trades(frames, fomc)
    rows.append(D.judge_variant("E2 FOMC statement day long, 4 indices", t2, k))
    excess_vs_long(frames, t2)
    hh = []
    for y, micro in [("ES=F", "MES"), ("NQ=F", "MNQ"), ("YM=F", "MYM"), ("RTY=F", "M2K")]:
        mv = segment_moves(H.load_yahoo_hourly(y), T(18, 0), T(14, 0))
        mv = mv[mv.index.isin(fomc)]
        hh.append(np.log(mv["exit"] / mv["entry"]))
    pre = pd.concat(hh)
    print(f"      hourly exact pre-statement window 18:00 -> 14:00 (2024-26, descriptive): {len(pre)} index-days, "
          f"mean {pre.mean() * 1e4:+.1f} bp, share up {(pre > 0).mean():.0%}")

    jobs = jobs_report_dates()
    print("\nE3 jobs-report day (BLS timing rule), long 4 equity indices")
    t3 = event_trades(frames, jobs)
    rows.append(D.judge_variant("E3 jobs-report day long, 4 indices", t3, k))
    excess_vs_long(frames, t3)

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 136 batch E (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round136_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
