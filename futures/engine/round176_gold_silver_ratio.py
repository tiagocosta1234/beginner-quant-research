"""
Round 176: the Gold/Silver ratio (GSR), a genuinely new METHODOLOGY for
this ledger -- relative value / pairs trading, not a directional lead-lag
or a single-instrument signal. Metals traders have watched GSR extremes for
decades as a mean-reversion signal (gold rich vs silver -> short gold/long
silver, expecting convergence, and the mirror). Never testable in this
ledger before: Yahoo's SI=F daily data is only usable in 2011 (this repo's
own documented gotcha, round135_batch_d's market_frame quality filter) --
not a methodology problem, a DATA problem, solved by the same Databento
GC/SI files Round 171 already verified clean (2019-06 -- 2026-09-25).

Rule: daily RTH (09:30-16:00 ET) open->close return per instrument, sized
in R-units by each instrument's own 20-day rolling SD (same convention as
round135_batch_d.market_frame and round142_batch_j.relative_value, which
tested the same idea for NQ-ES). ratio = GC close / SI close; z = 60-day
z-score of the ratio, using only the PRIOR day's close (causal). z >=
z_thresh (gold rich) -> short GC / long SI, half risk each leg; z <=
-z_thresh (gold cheap) -> the mirror. Split: IS = 2019-06 through
2022-12-31 (Databento's own start through 3.5 years), OOS = 2023-01-01
onward (~2.75 years) -- a bespoke split, not round135's global 2013 one,
since Databento's own range doesn't reach back that far; matches Round
171's own pre-2023 cutoff convention for this same data.

Step 0, honest before running: GSR mean reversion is one of the most
widely followed relationships in metals trading (real GSR-based ETF and
options products exist), so if there were a clean daily exploitable signal
here it would likely already be priced into the futures spread itself.
Tested for the methodology (this ledger's first real pairs trade), not
because prior odds are good.

2 variants (z_thresh in {1.5, 2.0}, the standard textbook thresholds, not
picked after seeing anything here). Ledger k=283 -> 285; OOS bar
1 - 0.01/285 at the last variant.

Candidate: net AND before-cost mean > 0; IS P(edge>0) >= 0.95; OOS
P(edge>0) >= the bar at that variant's k.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round171_databento_orb_replication import load_days_databento  # also adds GC/SI PV/TK to H.PV/H.TK

OOS_START = pd.Timestamp("2023-01-01")
WINDOW = 60


def daily_frame_databento(sym):
    days = load_days_databento(sym)
    rows = [(d["tday"], d["session"]["open"].iloc[0], d["session"]["close"].iloc[-1])
            for d in days if not d["session"].empty]
    df = pd.DataFrame(rows, columns=["tday", "open", "close"]).set_index("tday")
    df["r"] = np.log(df["close"] / df["open"])
    df["sd"] = df["r"].shift(1).rolling(20).std()
    df["cost_r"] = H.cost_per_contract(sym) / (df["sd"] * df["open"] * H.PV[sym])
    return df.dropna(subset=["sd"])


def build_trades(z_thresh):
    gc, si = daily_frame_databento("GC"), daily_frame_databento("SI")
    common = gc.index.intersection(si.index)
    gc, si = gc.loc[common], si.loc[common]
    ratio = gc["close"] / si["close"]
    z = ((ratio - ratio.rolling(WINDOW).mean()) / ratio.rolling(WINDOW).std()).shift(1)
    d = pd.Series(np.where(z >= z_thresh, -1, np.where(z <= -z_thresh, 1, 0)), index=common)  # +1 = long GC/short SI
    t = d[d != 0]
    if t.empty:
        return pd.DataFrame(columns=["date", "market", "gross", "pnl"])
    gc_r, si_r = (gc["r"] / gc["sd"]).loc[t.index], (si["r"] / si["sd"]).loc[t.index]
    gross = 0.5 * t * gc_r - 0.5 * t * si_r
    pnl = gross - 0.5 * gc["cost_r"].loc[t.index] - 0.5 * si["cost_r"].loc[t.index]
    return pd.DataFrame({"date": t.index, "market": "GC-SI", "gross": gross.values, "pnl": pnl.values})


def judge(name, tr, k):
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    bar = H.oos_bar(k)
    daily = tr.groupby("date")["pnl"].sum()
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar)
    print(f"  {name:<55} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"IS(<2023) {i['exp']:+.3f}R P {i['p_pos']:.3f} | OOS(>=2023) {o['exp']:+.3f}R P {o['p_pos']:.4f} "
          f"(bar {bar:.5f}) | Sharpe/day {daily.mean() / daily.std():+.3f} | {'CANDIDATE' if cand else 'no'}",
          flush=True)
    return dict(name=name, n=a["n"], exp=a["exp"], exp_gross=float(tr["gross"].mean()), p_is=i["p_pos"],
                p_oos=o["p_pos"], exp_is=i["exp"], exp_oos=o["exp"], k=k, bar=bar,
                trade_sharpe_daily=float(daily.mean() / daily.std()) if daily.std() > 0 else np.nan, candidate=cand)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for z in (1.5, 2.0):
            tr = build_trades(z)
            print(f"z>={z}: {len(tr)} trades, {tr['date'].min()} -> {tr['date'].max() if len(tr) else 'n/a'}")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for z in (1.5, 2.0):
        k = H.ledger_count() + 1
        tr = build_trades(z)
        r = judge(f"GC/SI ratio z>={z} -> fade (short rich leg/long cheap leg)", tr, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 176 (pre-registered, new methodology: Gold/Silver ratio pairs trade)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round176_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
