"""
Round 150, batch P: fair value gaps (FVG), plain and with the popular "secrets",
1:1 target, held to the pass-speed gate. Pre-registered 2026-09-26, committed before
any result is run.

Source: Revelio Trading, "How to identify the best Fair Value Gaps (backed by data)"
(YouTube qkzJknH5IJk, 2026-09-25). YouTube blocked the video and captions here; the
description says it tested 1,736,521 gaps, the basic FVG plus 5 "secrets" taught by
ICT, TJR, PB Patty, PB Blake, Casper Trading and Justin Bennett (96 combinations),
on 7 markets and 4 timeframes with costs. The secrets are not named in the
description, so the ones below are this repo's choice of the most commonly taught
rules -- not a reproduction of the video. Earlier FVG work here (Rounds 10-13, 46, 52,
76-82) predates the honest harness; the live bot's OTE/FVG has no edge (Rounds 76, 130).

Data: 24-hour 1-minute MNQ and MGC (idea_harness.load_days, one contract per day),
2022-12 .. 2026-09, grouped into 5- and 15-minute candles on the 18:00 ET session clock.
FVG: three consecutive candles where candle 1's high < candle 3's low (bullish gap
[c1 high, c3 low]) or candle 1's low > candle 3's high (bearish), gap >= 1 tick. It is
known when candle 3 completes.
Entry: a limit order at the gap's near edge (bullish: c3 low; bearish: c3 high), live
for the next 20 candles, one fill attempt per gap (first retrace only). Filled on the
first later 1-minute bar that trades 1 tick through the limit; entry price = the limit.
Stop: 1 tick beyond candle 1's far extreme (bullish: c1 low - 1 tick). Target: 1:1.
Gaps whose cost would exceed 0.10R at $300 risk are skipped (tiny stops). One position
at a time per instrument; an order can fill only when flat. On the fill bar only the
stop is checked (its order vs the target is unknown); after that stop first on a tie.
Flat at 16:00 ET; no fills after 15:30 ET. Costs: commission + 2 ticks per contract.
Split 2025-07-01.

Variants (5- and 15-minute candles, each):
  P1  plain FVG, as above.
  P2  with the secrets: (a) displacement -- candle 2's body >= 1.5 x the median body of
      the previous 20 candles of the session; (b) with the session VWAP -- bullish only
      if candle 3 closes above the VWAP from 18:00, bearish only below; (c) killzones --
      candle 3 completes 02:00-05:00 ET (London) or 09:30-11:30 ET (New York AM);
      (d) entry at the gap's 50% ("consequent encroachment") instead of its edge.
4 variants take the ledger from k=183 to k=187.

Candidate (as batches M-O): net and before-cost mean > 0; IS P(edge>0) >= 0.95; OOS
P(edge>0) >= 1 - 0.01/187; net mean > 0 on MNQ and on MGC; pass-speed gate
P(pass a $50K Test within 10 trading days) >= 0.50 at the best size.
Descriptive: win rate vs 50% and vs the ~48-49% a random 1:1 bracket gets here
(Round 149's placebo, same-bar ties counted as stops).

Power notes (dry run, before any result):
  variant                    trades (IS / OOS)        per day  cost   gate needs (1:1 win rate)
  P1 plain, 5-min            24,215 (12,946 / 11,269)  25.7    0.045R  55.8%
  P2 secrets, 5-min           4,740 (2,762 / 1,978)     5.0    0.043R  60.0%
  P1 plain, 15-min           11,427 (7,050 / 4,377)    12.1    0.032R  56.7%
  P2 secrets, 15-min          2,891 (1,889 / 1,002)     3.1    0.032R  61.6%
Cost break-even at 1:1 is ~51.6-52.3%; the OOS bar (0.99995, z ~3.9) needs roughly 54%
(P1 5-min) to 58% (P2 15-min). Resolver fixed in the dry run, before any result: fills are
taken in time order (an older gap touched later no longer blocks a newer gap touched
first), and a fill on an early-close day's last bar exits at its close; both covered by
the self-test.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round147_batch_m import RISK, full, load, gate_row
from round149_batch_o import needed_win_rate_1to1

N_VARIANTS = 4
LIVE_CANDLES = 20
MAX_COST_R = 0.10
LAST_FILL = dt.time(15, 30)
KILLZONES = [(dt.time(2, 0), dt.time(5, 0)), (dt.time(9, 30), dt.time(11, 30))]


def session_minute(ts):
    return ((ts.hour * 60 + ts.minute) - 18 * 60) % 1440


def candles(b, tf):
    """Group a session's 1-minute bars into tf-minute candles on the 18:00 clock.
    Returns a frame with o/h/l/c and `last` = index (in b) of the candle's final 1-min bar."""
    sm = np.array([session_minute(t) for t in b.index])
    bucket = sm // tf
    g = pd.DataFrame({"bucket": bucket, "i": np.arange(len(b)), "o": b["open"].values, "h": b["high"].values,
                      "l": b["low"].values, "c": b["close"].values})
    agg = g.groupby("bucket").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                                  last=("i", "last"), n=("i", "size"))
    return agg[agg["n"] >= max(2, tf // 2)].reset_index(drop=True)


def fvg_orders(b, sym, tf, secrets):
    k = candles(b, tf)
    tick = H.TK[sym]
    tp_ = (b["high"].values + b["low"].values + b["close"].values) / 3
    vwap = np.cumsum(tp_ * b["vol"].values) / np.maximum(np.cumsum(b["vol"].values), 1e-9)
    body = (k["c"] - k["o"]).abs().values
    med_body = pd.Series(body).shift(1).rolling(20, min_periods=20).median().values
    out = []
    for j in range(2, len(k)):
        c1, c2, c3 = k.iloc[j - 2], k.iloc[j - 1], k.iloc[j]
        if c1["h"] + tick <= c3["l"]:
            d, near, far, stop = 1, c3["l"], c1["h"], c1["l"] - tick
        elif c1["l"] - tick >= c3["h"]:
            d, near, far, stop = -1, c3["h"], c1["l"], c1["h"] + tick
        else:
            continue
        done = int(c3["last"])
        if secrets:
            if not (med_body[j - 1] == med_body[j - 1] and body[j - 1] >= 1.5 * med_body[j - 1]):
                continue
            if (d == 1 and not c3["c"] > vwap[done]) or (d == -1 and not c3["c"] < vwap[done]):
                continue
            t = b.index[done].time()
            if not any(a <= t < z for a, z in KILLZONES):
                continue
            entry = (near + far) / 2
        else:
            entry = near
        entry = round(entry / tick) * tick
        risk_pts = abs(entry - stop)
        if risk_pts <= 0 or H.cost_per_contract(sym) / (risk_pts * H.PV[sym]) > MAX_COST_R:
            continue
        expiry = int(k.iloc[min(j + LIVE_CANDLES, len(k) - 1)]["last"])
        out.append((done, expiry, d, entry, stop, entry + d * risk_pts))
    return out


def resolve_limit(b, orders, sym, risk=RISK, max_contracts=50):
    """One position at a time, in time order. orders: (formed_idx, expiry_idx, dir, entry, stop, target).
    Each gap gets one chance: its first retrace (1 tick through the limit, by 15:30 and before expiry).
    If that first retrace comes while a position is open, the gap is dropped."""
    hi, lo, cl = b["high"].values, b["low"].values, b["close"].values
    tick, pv, cpc = H.TK[sym], H.PV[sym], H.cost_per_contract(sym)
    ok_fill = np.array([(t.time() >= dt.time(18, 0)) or (t.time() <= LAST_FILL) for t in b.index])
    touched = []
    for formed, expiry, d, e, s, tgt in orders:
        for i in range(formed + 1, min(expiry, len(b) - 1) + 1):
            if not ok_fill[i]:
                break
            if (d == 1 and lo[i] <= e - tick) or (d == -1 and hi[i] >= e + tick):
                touched.append((i, formed, d, e, s, tgt))
                break
    free_from, trades = 0, []
    for fill, formed, d, e, s, tgt in sorted(touched):
        if fill < free_from:
            continue  # its first retrace came while a position was open
        c = min(max(1, int(risk // (abs(e - s) * pv))), max_contracts)
        px, i = None, fill
        if (d == 1 and lo[i] <= s) or (d == -1 and hi[i] >= s):
            px = s  # the fill bar also reached the stop: counted as a loss
        while px is None:
            i += 1
            if i >= len(b):  # filled on the session's last bar (early-close days): out at its close
                i, px = len(b) - 1, cl[-1]
                break
            if (d == 1 and lo[i] <= s) or (d == -1 and hi[i] >= s):
                px = s
            elif (d == 1 and hi[i] >= tgt) or (d == -1 and lo[i] <= tgt):
                px = tgt
            elif i == len(b) - 1:
                px = cl[i]
        trades.append((b.index[fill], b.index[i], d, c, d * (px - e) * pv * c - c * cpc, d * (px - e) / abs(e - s)))
        free_from = i + 1
    return trades


def run_variant(data, tf, secrets):
    parts = []
    for sym, (days, _) in data.items():
        rows = []
        for d in days:
            b = full(d)
            rows += resolve_limit(b, fvg_orders(b, sym, tf, secrets), sym)
        tr = pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r"])
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def selftest():
    """Synthetic session: a bullish FVG, a retrace fill, then the target; and a fill bar that hits the stop."""
    idx = pd.date_range("2024-01-02 09:30", periods=12, freq="min")
    base = dict(vol=np.ones(12))
    hi = np.array([101, 102, 106, 107, 106, 105, 104, 106, 108, 109, 110, 110.0])
    lo = np.array([100, 101, 104, 105, 104, 102.5, 102, 104, 106, 107, 108, 108.0])
    b = pd.DataFrame(dict(open=lo + 0.5, high=hi, low=lo, close=hi - 0.5, **base), index=idx)
    # FVG on 1-minute "candles": c1 = bar 1 (high 102), c3 = bar 3 (low 105) -> gap [102, 105]
    orders = [(3, 11, 1, 105.0, 100.9, 109.1)]
    t = resolve_limit(b, orders, "MNQ", risk=300)
    assert len(t) == 1 and t[0][0] == idx[4] and abs(t[0][5] - 1.0) < 1e-9, t   # fills at bar 4 (low 104 <= 104.75), target 109.1 hit at bar 10
    lo2 = lo.copy(); lo2[4] = 100.0  # the fill bar also trades through the stop -> a loss
    b2 = b.assign(low=lo2)
    t2 = resolve_limit(b2, orders, "MNQ", risk=300)
    assert len(t2) == 1 and abs(t2[0][5] + 1.0) < 1e-9, t2
    # time order: an older gap touched later must not block a newer gap touched first
    later = (1, 11, 1, 103.0, 100.9, 105.1)    # formed at bar 1, first touched at bar 5 (low 102.5)
    sooner = (3, 11, 1, 105.0, 100.9, 109.1)   # formed at bar 3, first touched at bar 4
    t3 = resolve_limit(b, [later, sooner], "MNQ", risk=300)
    assert len(t3) == 1 and t3[0][0] == idx[4], t3  # bar-4 fill taken; the other's first touch comes while in it
    print("selftest OK: limit fill, 1:1 target, a stop on the fill bar, fills in time order")


if __name__ == "__main__":
    selftest()
    if "--selftest" in sys.argv:
        sys.exit()
    dry = "--dry-run" in sys.argv
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch P = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    rows = []
    for tf in (5, 15):
        for secrets, label in [(False, "P1 plain FVG retest"), (True, "P2 FVG with displacement, VWAP side, killzone, 50% entry")]:
            name = f"{label}, {tf}-min, 1:1, MNQ + MGC"
            tr = run_variant(data, tf, secrets)
            per_day = len(tr) / len(all_days)
            cost_r = float((tr["cost"] / RISK).median()) if len(tr) else np.nan
            need = needed_win_rate_1to1(per_day, cost_r) if len(tr) else np.nan
            if dry:
                e = pd.to_datetime(tr["entry_ts"])
                print(f"{name}: {len(tr)} trades ({(e < J.OOS_START).sum()} IS / {(e >= J.OOS_START).sum()} OOS; "
                      f"MNQ {(tr['sym'] == 'MNQ').sum()}, MGC {(tr['sym'] == 'MGC').sum()}), {per_day:.2f}/day, "
                      f"median cost {cost_r:.3f}R, contracts median {tr['contracts'].median():.0f} | "
                      f"gate needs a 1:1 win rate >= {need:.1%}", flush=True)
                continue
            r = H.test_idea(name, tr, all_days, "MNQ", k, risk=RISK)
            per = tr.groupby("sym")["pnl"].mean()
            g, _ = gate_row(tr, all_days)
            both = bool(len(per) == 2 and (per > 0).all())
            r.update(win_needed=need, gate=g, both_positive=both, per_market={s: float(v) for s, v in per.items()})
            r["candidate"] = bool(r["candidate"] and both and g["pass_10d"] >= 0.50)
            e = pd.to_datetime(tr["entry_ts"])
            print(f"      win {r['win']:.1%} (IS {(tr.loc[e < J.OOS_START, 'pnl'] > 0).mean():.1%}, OOS "
                  f"{(tr.loc[e >= J.OOS_START, 'pnl'] > 0).mean():.1%}; gate needs {need:.1%} at {per_day:.1f}/day) | "
                  + ", ".join(f"{s} ${v:+.1f}" for s, v in per.items())
                  + f" | gate: pass <= 10d {g['pass_10d']:.2f} | {'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
            rows.append(r)
    if dry:
        sys.exit()
    lines = H.ledger_rows(rows, "Round 150 batch P (pre-registered; video qkzJknH5IJk)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round150_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
