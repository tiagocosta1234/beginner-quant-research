"""
Round 145, batch L: a currency month-end flow, a classic daily breakout, a
close-location bounce, and a lunar-cycle anomaly. Pre-registered 2026-09-26,
committed before any result is run. Legal window (daily 18:00 ET open -> settlement),
R units, real costs, batch D's frames and judge; split 2000-12 / 2013-26, plus 2020-26.

New data: daily high and low from the same Yahoo chart API as the open/close
(cached in data/daily_ohlc). A day's high/low is used only if the new download's
open and close match batch D's cached ones and high >= max(open, close),
low <= min(open, close), high > low. "Previous day" = the previous clean row, at most
5 calendar days earlier.

L1  Month-end currency hedging flows (Melvin & Prins 2015, "Equity hedging and
    exchange rates at the London 4 p.m. fix"): investors who hedge foreign equity
    holdings adjust hedges at month end, so when US stocks beat foreign stocks during
    the month, dollars are sold at the fix. Signal at the settlement before the
    month's last NYSE trading day: ES's month-to-date sum of open->close returns
    minus the DAX's (^GDAXI closes, known by 11:30 ET) month-to-date log return.
    > 0 -> long 6E (euro up, dollar down) on the last trading day; < 0 -> short.
L2  Volatility breakout (Larry Williams): buy stop at the open + k x the previous
    day's range (high - low), sell stop at the open - k x range; hold to settlement,
    no stop. If both levels trade the same day (13% of days at k=0.5, 3% at 1.0 in the
    dry run), the order is unknown: the headline counts the average of the two
    outcomes (a 50/50 order); a candidate must ALSO pass with the worse of the two
    counted (changed after the dry run's count, before any result -- worst-case alone
    would drag k=0.5 by ~0.1R). 10 markets. Variants: k in {0.5, 1.0}.
    Costs as elsewhere (commission + 2 ticks); stop entries can slip more, so a
    candidate would need that checked on intraday data.
L3  Internal bar strength (Pagonidis 2014): IBS = (close - low) / (high - low) of the
    previous day; long ES, NQ, YM, RTY the next day when IBS < 0.2.
L4  Lunar cycle (Dichev & Janes 2003; Yuan, Zheng & Zhu 2006: returns are lower around
    full moons): long ES, NQ, YM, RTY within 7 days of a new moon, short within 7 days
    of a full moon. Moon age from the mean synodic month (29.530589 days) since the
    new moon of 2000-01-06 18:14 UTC (error < 1 day), taken at noon UTC.

5 variants take the ledger from k=163 to k=168. Candidate: net and before-cost mean
R > 0; P(edge>0) >= 0.95 on 2000-12; >= 1 - 0.01/168 on 2013-26; 2020-26 mean R > 0;
then (stricter only) the same thresholds again on daily sums of its trades, and for
L2 again with both-triggered days counted at their worse outcome.
Descriptive: L1 by side and against long 6E every month end; L2 by side and the
share of both-triggered days; L3 against long every day.

Power notes (dry-run counts, before any result): trades (2000-12 / 2013-26): L1 306 (142 / 164;
one a month); L2a 36,136 (14,674 / 21,462); L2b 15,876 (6,462 / 9,414); L3 3,896 (1,754 /
2,142); L4 20,251 (8,327 / 11,924). Same-day trades are correlated, so effective
samples are nearer the number of distinct days. Reaching the 2013-26 bar (~3.85
standard errors) needs roughly: L1 >= +0.3R per trade (only a large effect can pass --
one trade a month); L3 >= +0.1R; L4 >= +0.07R; L2 >= +0.04-0.05R.
Dry-run checks: moon age 2024-04-08 = 29.1 and 2020-12-14 = 28.8 (new moons),
2024-04-23 = 14.6 and 2020-12-30 = 15.3 (full moons); clean high/low on 96-100% of days
(SI 87%); L1's last signals 2026-06-30, 07-31, 08-31.
"""
import os, sys, json, subprocess, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
import round136_batch_e as E
from round122b_tom_long_history import load_daily
from round144_batch_k import nyse_calendar

N_VARIANTS = 5
OHLC = os.path.join(H.HERE, "..", "data", "daily_ohlc")
MOON_EPOCH, SYNODIC = pd.Timestamp("2000-01-06 18:14"), 29.530588853


def load_ohlc(sym):
    path = os.path.join(OHLC, f"{sym}_yahoo_ohlc.csv")
    if not os.path.exists(path):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2=1790000000&interval=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = json.load(urllib.request.urlopen(req, timeout=60))["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                          index=pd.to_datetime(res["timestamp"], unit="s").normalize())
        os.makedirs(OHLC, exist_ok=True)
        df.dropna().to_csv(path, index_label="date")
    return pd.read_csv(path, index_col="date", parse_dates=True)


def ohlc_frame(sym):
    d = D.market_frame(sym)
    o = load_ohlc(sym)
    o = o[~o.index.duplicated(keep="last")]
    d = d.join(o, rsuffix="_x", how="left")
    same = ((d["open"] - d["open_x"]).abs() <= 1e-6 * d["open"]) & ((d["close"] - d["close_x"]).abs() <= 1e-6 * d["close"])
    d["ok"] = (same & (d["high"] >= d[["open", "close"]].max(axis=1)) & (d["low"] <= d[["open", "close"]].min(axis=1))
               & (d["high"] > d["low"]))
    gap = pd.Series(d.index, index=d.index).diff().dt.days
    for c in ("high", "low", "close"):
        d[f"p_{c}"] = d[c].shift(1)
    d["p_ok"] = d["ok"].shift(1, fill_value=False).astype(bool) & (gap <= 5)
    return d


def breakout(d, k, sym, worst=False):
    rng = d["p_high"] - d["p_low"]
    up, dn = d["open"] + k * rng, d["open"] - k * rng
    use = d["ok"] & d["p_ok"] & (rng > 0)
    lh, sh = use & (d["high"] >= up), use & (d["low"] <= dn)
    r_long, r_short = np.log(d["close"] / up), -np.log(d["close"] / dn)
    both = lh & sh
    r_both = np.minimum(r_long, r_short) if worst else (r_long + r_short) / 2
    r = np.where(both, r_both, np.where(lh, r_long, np.where(sh, r_short, np.nan)))
    side = np.where(both, 0, np.where(lh, 1, np.where(sh, -1, 0)))  # 0 = both levels traded
    m = ~np.isnan(r)
    gross = r[m] / d["sd"].values[m]
    return pd.DataFrame({"date": d.index[m], "market": sym, "gross": gross, "pnl": gross - d["cost_r"].values[m],
                         "side": side[m], "both": both.values[m]})


def ibs_long(d):
    ibs = (d["p_close"] - d["p_low"]) / (d["p_high"] - d["p_low"])
    return pd.Series(np.where(d["p_ok"] & (ibs < 0.2), 1, 0), index=d.index)


def moon_age(idx):
    t = pd.DatetimeIndex(idx) + pd.Timedelta(hours=12)
    return pd.Series(((t - MOON_EPOCH).total_seconds() / 86400) % SYNODIC, index=idx)


def lunar(d):
    age = moon_age(d.index)
    new = (age <= 7) | (age >= SYNODIC - 7)
    full = (age - SYNODIC / 2).abs() <= 7
    return pd.Series(np.where(new, 1, np.where(full, -1, 0)), index=d.index)


def fx_month_end(es, dax):
    cal = nyse_calendar()
    out = {}
    for _, m in cal[cal["complete"]].groupby("ym"):
        last, prev = m.index[m["from_end"] == 0], m.index[m["from_end"] == 1]
        if len(last) == 0 or len(prev) == 0:
            continue
        lo, hi = m.index[0], prev[0]
        es_mtd = es["r"][(es.index >= lo) & (es.index <= hi)].sum()
        d0, d1 = dax[dax.index < lo], dax[dax.index <= hi]
        if len(d0) == 0 or len(d1) == 0 or len(es["r"][(es.index >= lo) & (es.index <= hi)]) == 0:
            continue
        out[last[0]] = np.sign(es_mtd - np.log(d1.iloc[-1] / d0.iloc[-1]))
    return pd.Series(out).sort_index()


def trades(frame, direction, sym):
    tr = D.trades_from(frame, direction, sym)
    tr["side"] = direction[direction != 0].values
    return tr


def build(frames):
    eq = {s: frames[s] for s in D.EQUITY}
    dax = load_daily("^GDAXI")["close"]
    fx = fx_month_end(eq["ES=F"], dax)
    six = frames["6E=F"]
    cat = lambda parts: pd.concat(parts, ignore_index=True)
    t = {"L1": trades(six, fx.reindex(six.index).fillna(0), "6E=F"),
         "L2a": cat([breakout(frames[s], 0.5, s) for s in frames]),
         "L2b": cat([breakout(frames[s], 1.0, s) for s in frames]),
         "L3": cat([trades(eq[s], ibs_long(eq[s]), s) for s in D.EQUITY]),
         "L4": cat([trades(eq[s], lunar(eq[s]), s) for s in D.EQUITY])}
    return t, fx


LABELS = {"L1": "L1 month-end hedging flow: 6E with US-minus-DAX MTD, last day",
          "L2a": "L2a volatility breakout 0.5 x prior range, 10 markets",
          "L2b": "L2b volatility breakout 1.0 x prior range, 10 markets",
          "L3": "L3 IBS < 0.2 long next day, 4 indices",
          "L4": "L4 lunar: long near new moon, short near full moon, 4 indices"}


def dry_run():
    frames = {s: ohlc_frame(s) for s in D.MARKETS}
    for s, d in frames.items():
        print(f"  {s}: {len(d)} days, clean high/low {d['ok'].mean():.3f}, usable previous day {d['p_ok'].mean():.3f}")
    age = moon_age(pd.DatetimeIndex(["2024-04-08", "2024-04-23", "2020-12-14", "2020-12-30"]))
    print("moon age (expect ~0, ~15, ~0, ~15):", np.round(age.values, 1))
    t, fx = build(frames)
    print(f"L1: {len(fx)} month ends with a signal ({(fx > 0).mean():.2f} long 6E); last "
          f"{[str(d.date()) for d in fx.index[-3:]]}")
    for key, tr in t.items():
        yrs = tr["date"].dt.year
        extra = f"; both triggered {tr['both'].mean():.3f}" if "both" in tr else ""
        print(f"{key}: {len(tr)} trades ({(yrs <= 2012).sum()} in 2000-12, {(yrs >= 2013).sum()} in 2013-26; "
              f"{(tr['side'] > 0).sum()} long / {(tr['side'] < 0).sum()} short{extra}) | "
              + ", ".join(f"{m} {c}" for m, c in tr.groupby("market").size().items()))


def order_bias(days=20_000, steps=390, k=0.5, seed=0):
    """Added AFTER the results (diagnostic, not part of any verdict): the breakout rule on
    a pure random walk (no edge by construction), scored with the true order of
    triggers, the 50/50 headline, and the worst case. It measures how much the unknown
    order on both-triggered days flatters the 50/50 headline."""
    rng = np.random.default_rng(seed)
    paths = np.cumsum(rng.standard_normal((days + 1, steps)) / np.sqrt(steps), axis=1)
    paths = np.concatenate([np.zeros((days + 1, 1)), paths], axis=1)  # open at 0, open->close SD = 1
    prev_range = paths.max(1) - paths.min(1)
    true, avg, worst, single = [], [], [], []
    for i in range(1, days + 1):
        p, up, dn, c = paths[i], k * prev_range[i - 1], -k * prev_range[i - 1], paths[i][-1]
        hit_up, hit_dn = (p >= up).any(), (p <= dn).any()
        if not (hit_up or hit_dn):
            continue
        rl, rs = c - up, dn - c
        if hit_up and hit_dn:
            true.append(rl if np.argmax(p >= up) < np.argmax(p <= dn) else rs)
            avg.append((rl + rs) / 2); worst.append(min(rl, rs))
        else:
            v = rl if hit_up else rs
            true.append(v); avg.append(v); worst.append(v); single.append(v)
    print(f"random walk, k={k}: {len(true)} trades, both triggered {1 - len(single) / len(true):.3f}")
    print(f"  true order {np.mean(true):+.3f}R (above 0 only from the {steps}-step grid overshooting the level) | "
          f"50/50 {np.mean(avg):+.3f}R | worst {np.mean(worst):+.3f}R | single-trigger days only {np.mean(single):+.3f}R")


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        dry_run()
        sys.exit()
    if "--order-bias" in sys.argv:
        order_bias()
        sys.exit()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch L = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    frames = {s: ohlc_frame(s) for s in D.MARKETS}
    eq = {s: frames[s] for s in D.EQUITY}
    t, fx = build(frames)
    rows = []
    for key, label in LABELS.items():
        tr = t[key]
        print(f"\n{key}: {len(tr)} trades")
        r = D.judge_variant(label, tr, k)
        if r["candidate"]:  # stricter re-check on daily sums (same-day trades are correlated)
            day = tr.groupby("date")[["pnl", "gross"]].sum().reset_index()
            r["candidate"] = D.judge_variant(label + " [daily sums]", day.assign(market="portfolio"), k)["candidate"]
            if key.startswith("L2") and r["candidate"]:
                kk = {"L2a": 0.5, "L2b": 1.0}[key]
                w = pd.concat([breakout(frames[s], kk, s, worst=True) for s in frames], ignore_index=True)
                r["candidate"] = D.judge_variant(label + " [worst case]", w, k)["candidate"]
        rows.append(r)
        if key in ("L1", "L2a", "L2b"):
            for lab, v in [("long", 1), ("short", -1)]:
                x = tr[tr["side"] == v]
                print(f"      {lab} side: n={len(x)} {x['pnl'].mean():+.3f}R (gross {x['gross'].mean():+.3f}R)")
        if key == "L1":
            base = trades(frames["6E=F"], pd.Series(1.0, index=fx.index).reindex(frames["6E=F"].index).fillna(0), "6E=F")
            print(f"      long 6E every month end: n={len(base)} {base['pnl'].mean():+.3f}R")
        if key in ("L2a", "L2b"):
            print(f"      both-triggered days {tr['both'].mean():.3f}; excluding them: {tr.loc[~tr['both'], 'pnl'].mean():+.3f}R")
        if key == "L3":
            E.excess_vs_long(eq, tr)

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 145 batch L (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round145_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
