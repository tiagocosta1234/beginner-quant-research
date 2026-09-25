"""
Round 122b: is the turn-of-month lead from Round 122 real? Check it on ~30 years
of independent daily history before trusting 180 MNQ trades.

Round 122 found long MNQ from the 09:30 bar to the close on turn-of-month days
(last trading day + first three of the month) made +$44/trade vs -$4.6 on other
days -- but only 180 trades, the pre-registered bar was missed (IS P(edge>0)
0.81), and the TOM-vs-other comparison was made after seeing results.

Test fixed before running: open->close return (the part Broker lets you hold)
on TOM days vs all other days, for SPY (1993-) and QQQ (1999-), whose opens are
real traded prices. Split at 2023-01-01 so the early period is fully independent
of the MNQ file. Reports mean daily open->close return in basis points, Welch t
of the difference, and a bootstrap P(TOM > other). Daily bars from Yahoo's chart
API, cached under data/daily/.
"""
import os, sys, json, urllib.request
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "data", "daily")
SPLIT = pd.Timestamp("2023-01-01")


def load_daily(sym):
    path = os.path.join(CACHE, f"{sym}_yahoo_daily.csv")
    if not os.path.exists(path):
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
               f"?period1=0&period2=1790000000&interval=1d")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = json.load(urllib.request.urlopen(req, timeout=60))["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        df = pd.DataFrame({"open": q["open"], "close": q["close"]},
                          index=pd.to_datetime(res["timestamp"], unit="s").normalize())
        os.makedirs(CACHE, exist_ok=True)
        df.dropna().to_csv(path, index_label="date")
    return pd.read_csv(path, index_col="date", parse_dates=True)


def tom_flags(idx):
    ym = idx.year * 12 + idx.month
    s = pd.Series(1, index=idx)
    from_start = s.groupby(ym).cumcount().values
    from_end = s[::-1].groupby(ym[::-1]).cumcount()[::-1].values
    flag = ((from_start <= 2) & (ym != ym[0])) | ((from_end == 0) & (ym != ym[-1]))
    return pd.Series(flag, index=idx)


def compare(r, flag, label, rng):
    a, b = r[flag].to_numpy(), r[~flag].to_numpy()
    diff = a.mean() - b.mean()
    t = diff / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    boot = np.array([rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(4000)])
    print(f"  {label:<22} TOM n={len(a):>4} {a.mean()*1e4:+6.1f} bp | other n={len(b):>5} {b.mean()*1e4:+6.1f} bp | "
          f"diff {diff*1e4:+6.1f} bp  t={t:+.2f}  P(TOM>other)={np.mean(boot > 0):.3f}", flush=True)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    for sym in ["SPY", "QQQ"]:
        d = load_daily(sym)
        d = d[(d["open"] > 0) & (d["close"] > 0)]
        stale = (d["open"] == d["close"].shift(1)).mean()
        r = d["close"] / d["open"] - 1.0
        flag = tom_flags(d.index)
        print(f"\n{sym} {d.index[0].date()}..{d.index[-1].date()}, {len(d)} days "
              f"(open == prior close on {stale:.1%} of days)")
        compare(r, flag, "all years", rng)
        compare(r[r.index < SPLIT], flag[flag.index < SPLIT], f"before {SPLIT.year}", rng)
        compare(r[r.index >= SPLIT], flag[flag.index >= SPLIT], f"{SPLIT.year} on (MNQ era)", rng)
        for lo, hi in [(1993, 2002), (2003, 2012), (2013, 2022)]:
            m = (r.index.year >= lo) & (r.index.year <= hi)
            if m.sum() > 500:
                compare(r[m], flag[m], f"{lo}-{hi}", rng)
