"""
Round 142, batch J: weekend gaps, a classic multi-day mean-reversion system, and
index relative value. Pre-registered 2026-09-26, committed before any result is
run. Legal window (daily 18:00 ET open -> settlement), R units, real costs, as in
batches D and H.

J1  Crypto "CME gap fill" (trader folklore: the weekend gap in CME bitcoin futures
    gets filled). Crypto trades all weekend, CME futures don't, so the first
    session after a break (Sunday 18:00 open) gaps versus Friday's settlement.
    Fade it: on that session, trade against the gap's sign when |gap| >= 0.5 x the
    20-day SD of open->close returns. BTC (MBT) and ETH (MET), real fees; split
    before / from 2023-01-01; must be positive on BTC and on ETH separately.
J2  Weekend gaps in equity index futures: same rule on ES, NQ, YM, RTY (the first
    session after a break of >= 3 calendar days). Split 2000-12 / 2013-26, plus 2020-26.
J3  Connors RSI(2) (Connors & Alvarez 2008): long ES/NQ/YM/RTY when the 2-day RSI
    of the previous settlement is < X and that settlement is above its 200-day
    average; stay long day by day (each day a separate open->close trade -- Broker
    requires flat daily) until a settlement closes above its 5-day average, or 10
    days. Prices for RSI/averages are rebuilt from the open->close returns (so futures
    rolls don't distort them). Variants: X in {10, 5}. Split as J2.
J4  Nasdaq vs S&P relative value: spread move s = NQ's R minus ES's R on a day
    (each in its own SD units); if s >= +2 x the SD of s over the prior 60 days,
    next session short NQ / long ES (half the risk on each leg); if s <= -2 SD, the
    reverse. Costs on both legs. Split as J2.

5 variants take the ledger from k=150 to k=155. Candidate: net and before-cost mean
R > 0; in-sample P(edge>0) >= 0.95; out-of-sample P(edge>0) >= 1 - 0.01/155;
equity variants also 2020-26 mean R > 0; J1 also positive on BTC and ETH separately.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
import round139_batch_h as HH
from round122b_tom_long_history import load_daily

N_VARIANTS = 5
GAP_Z = 0.5


def with_prev_close(frame, sym):
    """Adds the previous settlement (same quality-filtered days) and the break length."""
    raw = load_daily(sym)["close"]
    f = frame.copy()
    prev = raw.shift(1).reindex(f.index)
    prev_date = pd.Series(raw.index, index=raw.index).shift(1).reindex(f.index)
    f["gap"] = np.log(f["open"] / prev)
    f["break_days"] = (f.index - pd.to_datetime(prev_date)).dt.days
    return f


def gap_fade(frame, sym):
    f = with_prev_close(frame, sym)
    first_after_break = f["break_days"] >= 3
    big = f["gap"].abs() >= GAP_Z * f["sd"]
    return pd.Series(np.where(first_after_break & big, -np.sign(f["gap"]), 0), index=f.index).fillna(0)


def rsi2(price):
    d = price.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    au, ad = up.ewm(alpha=1 / 2, adjust=False).mean(), dn.ewm(alpha=1 / 2, adjust=False).mean()
    return 100 - 100 / (1 + au / ad.replace(0, np.nan))


def connors(frame, x, px=None):
    if px is None:
        px = np.exp(frame["r"].cumsum())  # roll-free price rebuilt from open->close returns
    rsi, ma200, ma5 = rsi2(px), px.rolling(200).mean(), px.rolling(5).mean()
    enter = (rsi < x) & (px > ma200)          # known at that settlement -> trade from the next open
    exit_ = px > ma5
    pos, held, days = np.zeros(len(px)), False, 0
    e, xo = enter.values, exit_.values
    for i in range(1, len(px)):
        if held:
            days += 1
            if xo[i - 1] or days > 10:
                held = False
        if not held and e[i - 1]:
            held, days = True, 1
        pos[i] = 1 if held else 0
    return pd.Series(pos, index=frame.index)


def relative_value(frames):
    nq, es = frames["NQ=F"], frames["ES=F"]
    j = pd.DataFrame({"nq": nq["r"] / nq["sd"], "es": es["r"] / es["sd"],
                      "c_nq": nq["cost_r"], "c_es": es["cost_r"]}).dropna()
    s = j["nq"] - j["es"]
    band = s.shift(1).rolling(60).std()
    z = (s / band).shift(1)                      # yesterday's spread move, in units of its prior SD
    d = pd.Series(np.where(z >= 2, -1, np.where(z <= -2, 1, 0)), index=j.index)  # +1 = long NQ / short ES
    t = j[d != 0]
    dd = d[d != 0]
    gross = 0.5 * dd * t["nq"] - 0.5 * dd * t["es"]
    pnl = gross - 0.5 * t["c_nq"] - 0.5 * t["c_es"]
    return pd.DataFrame({"date": t.index, "market": "NQ-ES", "gross": gross.values, "pnl": pnl.values})


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch J = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    rows = []

    cf = {s: HH.crypto_frame(s) for s in HH.CRYPTO}
    t = pd.concat([D.trades_from(cf[s], gap_fade(cf[s], s), HH.CRYPTO[s]) for s in HH.CRYPTO], ignore_index=True)
    print(f"J1 crypto weekend-gap fade: {len(t)} trades")
    rows.append(HH.judge_split("J1 crypto CME weekend-gap fade, BTC + ETH", t, HH.H2_SPLIT, k))

    eq = {s: D.market_frame(s) for s in D.EQUITY}
    t = pd.concat([D.trades_from(eq[s], gap_fade(eq[s], s), s) for s in D.EQUITY], ignore_index=True)
    print(f"\nJ2 equity-index weekend-gap fade: {len(t)} trades")
    rows.append(D.judge_variant("J2 index weekend-gap fade, 4 indices", t, k))

    for x in [10, 5]:
        t = pd.concat([D.trades_from(eq[s], connors(eq[s], x), s) for s in D.EQUITY], ignore_index=True)
        print(f"\nJ3 Connors RSI(2) < {x}: {len(t)} daily trades")
        rows.append(D.judge_variant(f"J3 Connors RSI(2) < {x} above 200-day, 4 indices", t, k))

    t = relative_value(eq)
    print(f"\nJ4 NQ vs ES relative value: {len(t)} trades")
    rows.append(D.judge_variant("J4 NQ-ES spread reversal after a 2 SD day", t, k))

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 142 batch J (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round142_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
