"""
Round 139, batch H: two data types never used before -- implied volatility (VIX)
and crypto futures. Pre-registered 2026-09-26 -- signals, splits, costs and the
verdict rule committed before any result is run.

Legal window throughout: the daily bar's open (the 18:00 ET Globex reopen) to its
close (the 16:00 ET settlement) -- inside Broker's 18:00 -> 16:10 trading day.
Checked for crypto this session: BTC=F / ETH=F daily open = the hourly 18:00 open
(0.0000% median gap), daily close within 0.03% of the hourly 16:00 close.
Broker permits MBT/MET in standard Tests (Knowledge_Base rules file, checked
2026-09-26); round-trip fees MBT $2.82, MET $0.72 (used here instead of $1.24).

H1  VIX signals, long ES/NQ/YM/RTY open -> close (batch D's frames, R units, costs,
    data-quality rule; split 2000-12 / 2013-26, plus 2020-26). Each signal uses VIX
    closes from the previous trading day or earlier (the VIX closes at 16:15 ET,
    before the 18:00 open).
    H1a variance risk premium (Bollerslev, Tauchen & Zhou 2009): VRP = (VIX/100)^2
        - 252 x the variance of ES's last 20 open->close returns; long when VRP is at
        or above the 2/3 quantile of all earlier VRP values (expanding, >= 250 days).
    H1b term structure (Johnson 2017): long the day after VIX > VIX3M (backwardation).
        VIX3M starts 2006-07, so its "in-sample" slot is 2006-12.
    H1c spike reversal: long the day after VIX >= 1.2 x its average of the 20
        trading days before that.
    Long-only, so each is also shown against being long every day (descriptive).
H2  Crypto futures (MBT, MET), R units, costs with the real fees.
    H2a time-series momentum: sign of the sum of the previous N open->close returns,
        N in {20, 60}; BTC and ETH pooled; split before / from 2023-01-01.
    H2b intraday momentum (Wen et al. 2022): on the hourly bars, the 18:00 -> 10:00 ET
        return's sign is traded 10:00 -> 16:00; BTC and ETH pooled; split at 2025-07-01.

6 variants take the ledger from k=138 to k=144. Candidate: net and before-cost
mean R > 0; in-sample P(edge>0) >= 0.95; out-of-sample P(edge>0) >= 1 - 0.01/144;
H1 also 2020-26 mean R > 0; H2 also mean R > 0 on BTC and on ETH separately.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D
import round136_batch_e as E
from round134_batch_c import segment_moves
from round122b_tom_long_history import load_daily

T = dt.time
H.PV.update({"MBT": 0.1, "MET": 0.1})
H.TK.update({"MBT": 5.0, "MET": 0.5})
COMM = {"MBT": 2.82, "MET": 0.72}
CRYPTO = {"BTC=F": "MBT", "ETH=F": "MET"}
H2_SPLIT, H2B_SPLIT = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-07-01")
N_VARIANTS = 6


def prior(series, dates):
    """Value of `series` on the last date strictly before each of `dates`."""
    s = series.sort_index()
    pos = np.searchsorted(s.index.values, np.asarray(dates, dtype="datetime64[ns]"), side="left") - 1
    out = np.where(pos >= 0, s.values[np.clip(pos, 0, None)], np.nan)
    return pd.Series(out, index=dates)


def h1_signals(frames):
    vix = load_daily("^VIX")["close"]
    vix3m = load_daily("^VIX3M")["close"]
    es = frames["ES=F"]
    rv = es["r"].rolling(20).var() * 252  # through day t (used for day t+1 below)
    vrp_daily = (vix.reindex(es.index).ffill() / 100) ** 2 - rv
    thresh = vrp_daily.expanding(min_periods=250).quantile(2 / 3)
    vix_avg = vix.shift(1).rolling(20).mean()
    spike = vix / vix_avg
    sig = {}
    for sym, d in frames.items():
        idx = d.index
        vrp_prev, thr_prev = prior(vrp_daily.dropna(), idx), prior(thresh.dropna(), idx)
        backw = prior(vix, idx) > prior(vix3m, idx)
        spk = prior(spike.dropna(), idx) >= 1.2
        sig[sym] = {"H1a": (vrp_prev >= thr_prev).astype(int), "H1b": backw.astype(int), "H1c": spk.astype(int)}
    return sig


def crypto_frame(sym):
    micro = CRYPTO[sym]
    d = load_daily(sym)
    d = d[(d["open"] > 0) & (d["close"] > 0) & (d["open"] != d["close"])].copy()
    d["r"] = np.log(d["close"] / d["open"])
    d["sd"] = d["r"].shift(1).rolling(20).std()
    d = d[~(d["r"].abs() > 10 * d["sd"])]
    d["sd"] = d["r"].shift(1).rolling(20).std()
    d = d[d["sd"] > 0]
    d["cost_r"] = (COMM[micro] + 2 * H.TK[micro] * H.PV[micro]) / (d["sd"] * d["open"] * H.PV[micro])
    return d


def judge_split(name, tr, split, k):
    a = J.edge_stats(tr, n_boot=40_000)
    i = J.edge_stats(tr[tr["date"] < split])
    o = J.edge_stats(tr[tr["date"] >= split], n_boot=40_000)
    per = tr.groupby("market")["pnl"].mean()
    bar = H.oos_bar(k)
    daily = tr.groupby("date")["pnl"].sum()
    both = bool((per > 0).all() and len(per) == 2)
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar and both)
    print(f"  {name:<44} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | before {split.date()} "
          f"{i['exp']:+.3f}R P {i['p_pos']:.3f} | from {o['exp']:+.3f}R P {o['p_pos']:.4f} (bar {bar:.5f}) | "
          f"{', '.join(f'{m} {v:+.3f}' for m, v in per.items())} | Sharpe/day {daily.mean() / daily.std():+.3f} | "
          f"{'CANDIDATE' if cand else 'no'}", flush=True)
    return dict(name=name, n=a["n"], exp=a["exp"], exp_gross=float(tr["gross"].mean()), p_is=i["p_pos"],
                p_oos=o["p_pos"], exp_is=i["exp"], exp_oos=o["exp"], k=k, bar=bar, candidate=cand)


def h2b_trades(sym):
    micro = CRYPTO[sym]
    h = H.load_yahoo_hourly(sym)
    first = segment_moves(h, T(18, 0), T(10, 0))
    rest = segment_moves(h, T(10, 0), T(16, 0))
    m = first[["entry", "exit", "n"]].join(rest[["entry", "exit", "n"]], rsuffix="_2", how="inner")
    m = m[(m["n"] >= 14) & (m["n_2"] >= 5)].copy()
    m["sig"] = np.sign(np.log(m["exit"] / m["entry"]))
    m["r"] = np.log(m["exit_2"] / m["entry_2"])
    m["sd"] = m["r"].shift(1).rolling(20).std()
    m = m[(m["sd"] > 0) & (m["sig"] != 0)]
    cost_r = (COMM[micro] + 2 * H.TK[micro] * H.PV[micro]) / (m["sd"] * m["entry_2"] * H.PV[micro])
    gross = m["sig"] * m["r"] / m["sd"]
    return pd.DataFrame({"date": m.index, "market": micro, "gross": gross.values, "pnl": (gross - cost_r).values})


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch H = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    rows = []

    frames = {s: D.market_frame(s) for s in D.EQUITY}
    sig = h1_signals(frames)
    print("H1 VIX signals, long ES/NQ/YM/RTY open -> close")
    labels = {"H1a": "H1a variance risk premium in top third", "H1b": "H1b VIX term structure in backwardation",
              "H1c": "H1c VIX spike >= 20% above 20-day average"}
    for key, label in labels.items():
        tr = pd.concat([D.trades_from(frames[s], sig[s][key].reindex(frames[s].index).fillna(0), s) for s in D.EQUITY],
                       ignore_index=True)
        rows.append(D.judge_variant(label, tr, k))
        E.excess_vs_long(frames, tr)

    print("\nH2 crypto futures (MBT, MET)")
    cf = {s: crypto_frame(s) for s in CRYPTO}
    for s, d in cf.items():
        print(f"   {s}: {d.index[0].date()}..{d.index[-1].date()} days={len(d)} median cost {d['cost_r'].median():.3f}R")
    for n in [20, 60]:
        parts = []
        for s, d in cf.items():
            trend = d["r"].shift(1).rolling(n, min_periods=int(0.9 * n)).sum()
            parts.append(D.trades_from(d, np.sign(trend).fillna(0), CRYPTO[s]))
        rows.append(judge_split(f"H2a crypto TSMOM {n}-day, BTC + ETH", pd.concat(parts, ignore_index=True), H2_SPLIT, k))
    rows.append(judge_split("H2b crypto intraday momentum 18-10 -> 10-16", pd.concat([h2b_trades(s) for s in CRYPTO],
                                                                                   ignore_index=True), H2B_SPLIT, k))

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 139 batch H (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round139_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
