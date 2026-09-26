"""
Round 144, batch K: institutional flows, the RSI(2) mechanism beyond equity longs,
calendar and volatility regimes, and cross-sectional momentum. Pre-registered
2026-09-26, committed before any result is run. Legal window (daily 18:00 ET open ->
settlement), R units, real costs, data-quality rule, as in batch D; split 2000-12 /
2013-26, plus 2020-26.

K1  Month-end rebalancing flows (idea: Harvey, Mazzoleni & Melone 2025, "The
    Unintended Consequences of Rebalancing": funds holding fixed stock/bond weights
    must sell stocks at month end after stocks beat bonds). My version: at the
    settlement 4 NYSE trading days before month end, spread = ES's month-to-date sum
    of open->close log returns minus ZN's. Spread > 0 -> short ES, NQ, YM, RTY on
    each of the month's last 3 trading days; spread < 0 -> long. Complete months only.
K2  Connors RSI(2) beyond equity longs (the one lead with 1990s support, Round 143).
    Same state machine as Round 142 J3 (roll-free price rebuilt from open->close
    returns; exit after a settlement back across the 5-day average, or 10 days).
      K2a both sides on the 6 non-equity markets (GC, SI, CL, HG, 6E, ZN): long when
          RSI(2) < 10 above the 200-day average; short when RSI(2) > 90 below it.
      K2b short side on ES, NQ, YM, RTY: RSI(2) > 90 below the 200-day average.
K3  Santa Claus rally (Hirsch 1972): long ES, NQ, YM, RTY on the last 5 NYSE
    trading days of December and the first 2 of January. Relevant: the goal's
    deadline is Dec 31.
K4  Volatility-managed exposure (Moreira & Muir 2017: risk rises less than
    volatility, so calm periods pay more per unit of risk): long ES, NQ, YM, RTY on
    days whose 20-day SD is below the median of the previous 250 days' 20-day SD.
K5  Cross-sectional momentum across asset classes (Asness, Moskowitz & Pedersen
    2013): score = sum of R (open->close return / 20-day SD) over days t-250 .. t-21
    (>= 200 days present); each day with >= 6 scored markets, long the top 3 and short
    the bottom 3 of batch D's 10 markets, each a separate 1R trade.

6 variants take the ledger from k=157 to k=163. Candidate (batch D's judge): net and
before-cost mean R > 0; P(edge>0) >= 0.95 on 2000-12; >= 1 - 0.01/163 on 2013-26;
2020-26 mean R > 0. Descriptive: long-only variants against long every day; K2b against short every
day; K1, K2a and K5 split by side.

Power notes (dry-run counts, before any result): trades (2000-12 / 2013-26):
K1 3,045 (1,249 / 1,796; 1,163 long, 1,882 short -- stocks beat bonds more often);
K2a 4,651 (1,824 / 2,827; SI contributes 3); K2b 891 (487 / 404); K3 590 (250 / 340,
but only ~26 seasons x 7 days = ~180 distinct days); K4 11,042; K5 34,914 (6 a day from
2003-03-26). Trades on the same day are correlated, so the effective sample is closer
to the number of distinct days. Reaching the 2013-26 bar (~3.85 standard errors) then
needs roughly: K3 >= +0.3R per day (implausible -- K3 can hardly pass at
this bar and is here because of the Dec 31 deadline); K1 >= +0.15R; K2b >= +0.2R;
K4 and K5 >= +0.05-0.1R.
Extra check, stricter only (fixed now): a variant that passes is re-bootstrapped on
daily sums of its trades (one number per day); it must pass the same thresholds again.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
import round136_batch_e as E
from round122b_tom_long_history import load_daily
from round141_batch_i import vs_every_day
from round142_batch_j import rsi2

N_VARIANTS = 6
NON_EQUITY = [s for s in D.MARKETS if s not in D.EQUITY]


def nyse_calendar():
    nyse = load_daily("SPY").index
    ym = pd.Series(nyse.year * 12 + nyse.month, index=nyse)
    from_end = ym[::-1].groupby(ym[::-1].values).cumcount()[::-1]
    from_start = ym.groupby(ym.values).cumcount()
    complete = ym != ym.iloc[-1]  # the data's final month is incomplete
    return pd.DataFrame({"ym": ym, "from_end": from_end, "from_start": from_start, "complete": complete})


def rebalance_direction(es, zn):
    cal = nyse_calendar()
    out = {}
    for ym, m in cal[cal["complete"]].groupby("ym"):
        sig_day = m.index[m["from_end"] == 3]
        if len(sig_day) == 0:
            continue
        lo, hi = m.index[0], sig_day[0]
        spread = es["r"][(es.index >= lo) & (es.index <= hi)].sum() - zn["r"][(zn.index >= lo) & (zn.index <= hi)].sum()
        for d in m.index[m["from_end"] <= 2]:
            out[d] = -np.sign(spread)
    return pd.Series(out).sort_index()


def connors_side(frame, long_x=None, short_x=None):
    """+1 / -1 / 0 per day. Long: RSI(2) < long_x above the 200-day, out after a close
    above the 5-day average or 10 days. Short: mirror image with RSI(2) > short_x."""
    px = np.exp(frame["r"].cumsum())
    rsi, ma200, ma5 = rsi2(px), px.rolling(200).mean(), px.rolling(5).mean()
    go_long = ((rsi < long_x) & (px > ma200)).values if long_x else np.zeros(len(px), bool)
    go_short = ((rsi > short_x) & (px < ma200)).values if short_x else np.zeros(len(px), bool)
    above, below = (px > ma5).values, (px < ma5).values
    pos, side, days = np.zeros(len(px)), 0, 0
    for i in range(1, len(px)):
        if side:
            days += 1
            if (side > 0 and above[i - 1]) or (side < 0 and below[i - 1]) or days > 10:
                side = 0
        if not side:
            if go_long[i - 1]:
                side, days = 1, 1
            elif go_short[i - 1]:
                side, days = -1, 1
        pos[i] = side
    return pd.Series(pos, index=frame.index)


def santa_days():
    cal = nyse_calendar()
    dec = cal[(cal.index.month == 12) & (cal["from_end"] <= 4) & cal["complete"]]
    jan = cal[(cal.index.month == 1) & (cal["from_start"] <= 1)]
    jan = jan[jan.index.year - 1 >= dec.index.year.min()]  # Januaries that follow a December in the data
    return dec.index.union(jan.index)


def calm(frame):
    ref = frame["sd"].shift(1).rolling(250, min_periods=200).median()
    return pd.Series(np.where(frame["sd"] < ref, 1, 0), index=frame.index)


def xs_momentum(frames):
    score = pd.DataFrame({s: (d["r"] / d["sd"]).shift(21).rolling(230, min_periods=200).sum() for s, d in frames.items()})
    rank = score.rank(axis=1)
    n = score.notna().sum(axis=1)
    top = rank.ge(n - 2, axis=0) & score.notna()
    bot = rank.le(3, axis=0) & score.notna()
    ok = n >= 6
    pos = (top.astype(int) - bot.astype(int)).where(ok, 0)
    return {s: pos[s].reindex(frames[s].index).fillna(0) for s in frames}, n


def on_days(frame, days, direction=1):
    return pd.Series(np.where(frame.index.isin(days), direction, 0), index=frame.index)


def trades(frame, direction, sym):
    """batch D's trades_from, plus each trade's side (+1 long / -1 short)."""
    tr = D.trades_from(frame, direction, sym)
    tr["side"] = direction[direction != 0].values
    return tr


def build(eq, frames):
    rb = rebalance_direction(eq["ES=F"], frames["ZN=F"])
    sd = santa_days()
    xs, n_scored = xs_momentum(frames)
    cat = lambda parts: pd.concat(parts, ignore_index=True)
    t = {"K1": cat([trades(eq[s], rb.reindex(eq[s].index).fillna(0), s) for s in D.EQUITY]),
         "K2a": cat([trades(frames[s], connors_side(frames[s], 10, 90), s) for s in NON_EQUITY]),
         "K2b": cat([trades(eq[s], connors_side(eq[s], None, 90), s) for s in D.EQUITY]),
         "K3": cat([trades(eq[s], on_days(eq[s], sd), s) for s in D.EQUITY]),
         "K4": cat([trades(eq[s], calm(eq[s]), s) for s in D.EQUITY]),
         "K5": cat([trades(frames[s], xs[s], s) for s in frames])}
    return t, rb, sd, n_scored


LABELS = {"K1": "K1 month-end rebalancing: fade stocks-minus-bonds MTD, last 3 days",
          "K2a": "K2a Connors RSI(2) both sides, 6 non-equity markets",
          "K2b": "K2b Connors RSI(2) > 90 short below 200-day, 4 indices",
          "K3": "K3 Santa Claus rally, last 5 Dec + first 2 Jan days, 4 indices",
          "K4": "K4 long 4 indices when 20-day SD is below its 250-day median",
          "K5": "K5 cross-sectional momentum 12-1, top 3 / bottom 3 of 10 markets"}


def dry_run():
    frames = {s: D.market_frame(s) for s in D.MARKETS}
    eq = {s: frames[s] for s in D.EQUITY}
    t, rb, sd, n_scored = build(eq, frames)
    print(f"K1: {rb.index.to_period('M').nunique()} months, window days {len(rb)}; short share {(rb < 0).mean():.2f}; "
          f"e.g. Aug 2026 window {[str(d.date()) for d in rb[rb.index.to_period('M') == '2026-08'].index]}")
    print(f"K3: Santa days {len(sd)}; 2019-20: {[str(d.date()) for d in sd[(sd >= '2019-12-01') & (sd <= '2020-01-31')]]}")
    print(f"K5: days with >= 6 scored markets {(n_scored >= 6).sum()} (first {n_scored[n_scored >= 6].index[0].date()})")
    for key, tr in t.items():
        yrs = tr["date"].dt.year
        print(f"{key}: {len(tr)} trades ({(yrs <= 2012).sum()} in 2000-12, {(yrs >= 2013).sum()} in 2013-26; "
              f"{(tr['side'] > 0).sum()} long / {(tr['side'] < 0).sum()} short) | "
              + ", ".join(f"{m} {c}" for m, c in tr.groupby("market").size().items()))


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        dry_run()
        sys.exit()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch K = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    frames = {s: D.market_frame(s) for s in D.MARKETS}
    eq = {s: frames[s] for s in D.EQUITY}
    t, rb, sd, _ = build(eq, frames)
    rows = []
    for key, label in LABELS.items():
        tr = t[key]
        print(f"\n{key}: {len(tr)} trades")
        r = D.judge_variant(label, tr, k)
        if r["candidate"]:  # stricter re-check on daily sums (same-day trades are correlated)
            day = tr.groupby("date")[["pnl", "gross"]].sum().reset_index()
            r2 = D.judge_variant(label + " [daily sums]", day.assign(market="portfolio"), k)
            r["candidate"] = r2["candidate"]
        rows.append(r)
        if key in ("K1", "K2a", "K5"):
            for lab, v in [("long", 1), ("short", -1)]:
                x = tr[tr["side"] == v]
                print(f"      {lab} side: n={len(x)} {x['pnl'].mean():+.3f}R (gross {x['gross'].mean():+.3f}R)")
        if key in ("K3", "K4"):
            E.excess_vs_long(eq, tr)
        if key == "K2b":
            vs_every_day(tr, eq, -1)

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 144 batch K (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round144_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
