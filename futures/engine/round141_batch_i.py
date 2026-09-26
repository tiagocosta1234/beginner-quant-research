"""
Round 141, batch I: flow-driven calendar effects -- Treasury supply, month-end
index extension, and options expiration. Pre-registered 2026-09-26, committed
before any result is run. Legal window: the daily 18:00 ET open -> settlement
(batch D's frames, R units, costs, data-quality rule; split 2000-12 / 2013-26,
plus 2020-26).

I1  Treasury auction cycle (Lou, Yan & Zhang 2013: prices sag before large
    auctions as dealers make room for supply, then recover). Auctions of nominal
    notes/bonds with >= 4 years to maturity (data/events/treasury_coupon_auctions.csv,
    1,085 auctions 2000-2026, TreasuryDirect). Auction days no more than 2 ZN
    trading days apart form one supply cluster.
      I1a short ZN on the 2 trading days before each cluster
      I1b long ZN on the 2 trading days after each cluster
    A day that is both "before" one cluster and "after" another is skipped by both.
I2  Month-end Treasury rally (bond index funds extend duration at month end):
    long ZN on the last NYSE trading day of each month (SPY's trading calendar).
I3  Options expiration (monthly OPEX = the third Friday, or the trading day before
    it if that Friday is a holiday), equity indices ES, NQ, YM, RTY:
      I3a long on each trading day of OPEX week (Monday -> OPEX day)
      I3b short on each trading day of the following week

5 variants take the ledger from k=145 to k=150. Candidate (batch D's judge): net
and before-cost mean R > 0; P(edge>0) >= 0.95 on 2000-12; >= 1 - 0.01/150 on
2013-26; 2020-26 mean R > 0. Descriptive: each variant against the same
direction taken every day (same market, same units).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
from round122b_tom_long_history import load_daily

AUCTIONS = os.path.join(H.HERE, "..", "data", "events", "treasury_coupon_auctions.csv")
N_VARIANTS = 5


def auction_windows(zn_days):
    days = pd.DatetimeIndex(zn_days)
    auct = pd.DatetimeIndex(pd.read_csv(AUCTIONS, parse_dates=["date"])["date"].unique()).sort_values()
    pos = np.unique(np.searchsorted(days.values, auct.values))
    pos = pos[pos < len(days)]
    clusters, cur = [], [pos[0]]
    for p in pos[1:]:
        if p - cur[-1] <= 2:
            cur.append(p)
        else:
            clusters.append((cur[0], cur[-1])); cur = [p]
    clusters.append((cur[0], cur[-1]))
    pre, post = set(), set()
    for a, b in clusters:
        pre.update(i for i in (a - 2, a - 1) if i >= 0)
        post.update(i for i in (b + 1, b + 2) if i < len(days))
    both = pre & post
    return days[sorted(pre - both)], days[sorted(post - both)], len(clusters)


def month_ends():
    nyse = load_daily("SPY").index
    ym = nyse.year * 12 + nyse.month
    last = pd.Series(1, index=nyse)[::-1].groupby(ym[::-1]).cumcount()[::-1]
    return nyse[(last.values == 0) & (ym != ym[-1])]  # the data's final month is incomplete


def opex_weeks():
    nyse = load_daily("SPY").index
    s = set(nyse)
    opex_week, after_week = set(), set()
    for y in range(2000, 2027):
        for m in range(1, 13):
            first = pd.Timestamp(y, m, 1)
            fri = first + pd.Timedelta(days=(4 - first.weekday()) % 7) + pd.Timedelta(weeks=2)
            day = fri
            while day not in s and day > fri - pd.Timedelta(days=4):
                day -= pd.Timedelta(days=1)
            if day not in s:
                continue
            monday = fri - pd.Timedelta(days=4)
            opex_week.update(d for d in pd.date_range(monday, day) if d in s)
            after_week.update(d for d in pd.date_range(fri + pd.Timedelta(days=3), fri + pd.Timedelta(days=7)) if d in s)
    return pd.DatetimeIndex(sorted(opex_week)), pd.DatetimeIndex(sorted(after_week - opex_week))


def vs_every_day(tr, frames, direction):
    base = pd.concat([D.trades_from(frames[m], pd.Series(direction, index=frames[m].index), m) for m in tr["market"].unique()])
    for lab, lo, hi in [("2000-12", "2000", "2012-12-31"), ("2013-26", "2013", "2026-12-31")]:
        a = base[(base["date"] >= lo) & (base["date"] <= hi)]["pnl"].values
        e = tr[(tr["date"] >= lo) & (tr["date"] <= hi)]["pnl"].values
        rng = np.random.default_rng(0)
        boot = np.array([rng.choice(e, len(e)).mean() - rng.choice(a, len(a)).mean() for _ in range(4000)])
        print(f"      {lab}: signal days {e.mean():+.3f}R vs {'long' if direction > 0 else 'short'} every day "
              f"{a.mean():+.3f}R -> excess {e.mean() - a.mean():+.3f}R, P(excess>0) {(boot > 0).mean():.3f}")


def on_days(frame, days, direction):
    return pd.Series(np.where(frame.index.isin(days), direction, 0), index=frame.index)


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch I = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    zn = {"ZN=F": D.market_frame("ZN=F")}
    eq = {s: D.market_frame(s) for s in D.EQUITY}
    rows = []

    pre, post, n_cl = auction_windows(zn["ZN=F"].index)
    print(f"I1 Treasury auction cycle: {n_cl} supply clusters; {len(pre)} pre-auction days, {len(post)} post-auction days")
    t = D.trades_from(zn["ZN=F"], on_days(zn["ZN=F"], pre, -1), "ZN=F")
    rows.append(D.judge_variant("I1a short ZN 2 days before auctions", t, k)); vs_every_day(t, zn, -1)
    t = D.trades_from(zn["ZN=F"], on_days(zn["ZN=F"], post, 1), "ZN=F")
    rows.append(D.judge_variant("I1b long ZN 2 days after auctions", t, k)); vs_every_day(t, zn, 1)

    print("\nI2 month-end Treasury rally")
    t = D.trades_from(zn["ZN=F"], on_days(zn["ZN=F"], month_ends(), 1), "ZN=F")
    rows.append(D.judge_variant("I2 long ZN on the last trading day of the month", t, k)); vs_every_day(t, zn, 1)

    ow, aw = opex_weeks()
    print(f"\nI3 options expiration: {len(ow)} OPEX-week days, {len(aw)} following-week days")
    t = pd.concat([D.trades_from(eq[s], on_days(eq[s], ow, 1), s) for s in D.EQUITY], ignore_index=True)
    rows.append(D.judge_variant("I3a long indices in OPEX week", t, k)); vs_every_day(t, eq, 1)
    t = pd.concat([D.trades_from(eq[s], on_days(eq[s], aw, -1), s) for s in D.EQUITY], ignore_index=True)
    rows.append(D.judge_variant("I3b short indices the week after OPEX", t, k)); vs_every_day(t, eq, -1)

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 141 batch I (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round141_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
