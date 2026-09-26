"""
Round 151, batch Q: three intraday structures not yet tested here -- same-slot
persistence, the overnight session after a big day, and the 08:30 news breakout.
Pre-registered 2026-09-26, committed before any result is run.

Step 0 (the pass-speed gate's screen), stated up front: none of these has a published
effect anywhere near a daily Sharpe of 0.5. They are run because the trader asked to keep
hunting and because each is a structure the 187 earlier tests did not cover.

Data: 24-hour 1-minute MNQ and MGC (idea_harness.load_days, one contract per day,
18:00 ET start), 2022-12 .. 2026-09; split 2025-07-01. The 1-minute bars are stamped at
their END (checked in the dry run: the 2024-03-08 jobs-report burst is the bar stamped
08:31, the 09:30 open's the bar stamped 09:31); all windows below are in real minutes. $300 risk unit, whole
contracts (1..50), cost = commission + 2 ticks per contract round trip.

Q1  Same-slot persistence (Heston, Korajczyk & Sadka 2010: an asset's return in a
    given half-hour predicts its return in the same half-hour on later days). Slots:
    the 16 half-hours 08:00 -> 16:00 ET. A slot's move = the close of its last minute
    minus the close of the minute before it starts. For day d and slot s: mean and SD
    of that slot's moves over the previous 20 trading days; if |mean| / (SD / sqrt 20)
    >= 2, trade the sign of the mean for that slot on day d (enter at the slot's start
    price, exit at its end -- a pure time exit). Size: $300 per 1 SD of the slot's move.
Q2  The overnight session after a big regular session (Lou, Polk & Skouras 2019: the
    overnight and intraday legs pull against each other). If the previous day's
    09:30 -> 16:00 move was >= 1 SD (SD of the previous 20 such moves), trade AGAINST it
    from the 18:00 reopen to 09:29 -- inside Broker's trading day. Same contract only
    (skipped over rolls). Size: $300 per 1 SD of the overnight move (previous 20 nights).
Q3  08:30 news breakout: a scheduled release shows as a volume spike -- the 08:30 bar's
    volume >= 5 x the average 08:00-08:29 bar (known when that bar closes). Range =
    the high/low of the 08:30-08:34 bars. The first bar from 08:35 to 10:30 that closes
    outside it is traded in that direction (idea_harness.resolve_bracket: entry at its
    close, stop at the range's other side, 1:1 target, flat at 16:00); skipped if the
    cost would exceed 0.10R.
3 variants take the ledger from k=187 to k=190.

Candidate (as batches M-P): net and before-cost mean > 0; IS P(edge>0) >= 0.95; OOS
P(edge>0) >= 1 - 0.01/190; net mean > 0 on MNQ and on MGC; pass-speed gate
P(pass a $50K Test within 10 trading days) >= 0.50 at the best size.

Power notes (dry run, before any result):
  variant                          trades (IS / OOS)   per day  cost    gate needs
  Q1 same-slot persistence         1,497 (956 / 541)   1.6      0.045R  per-trade mean/SD >= 0.286
  Q2 overnight against a big day     526 (351 / 175)   0.56     0.011R  per-trade mean/SD >= 0.482
  Q3 08:30 news breakout, 1:1        446 (368 / 78)    0.47     0.015R  per-trade mean/SD >= 0.524 (74% wins)
Q2 and Q3 trade about every other day, so each trade would need to be near-certain for
the gate; they can pass only as ingredients of a larger portfolio, not alone.
Fixed in the dry run, before any result: bars are END-stamped, so the release minute is
the bar stamped 08:31 (the first version looked at 08:29-08:30 and found 15 news days),
and Q1's slots were shifted one minute early.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round147_batch_m import RISK, full, load, gate_row
from round149_batch_o import needed_win_rate_1to1

N_VARIANTS = 3
SLOTS = [dt.time(8 + m // 60, m % 60) for m in range(0, 480, 30)]  # 08:00 .. 15:30 starts
LOOKBACK, T_MIN = 20, 2.0
NEWS_T, NEWS_END = dt.time(8, 30), dt.time(10, 30)
MAX_COST_R = 0.10


def contracts_for(sd_pts, sym):
    return int(min(max(1, RISK // (sd_pts * H.PV[sym])), 50)) if sd_pts > 0 else 0


def trade_row(sym, t_in, t_out, d, c, e, x):
    cost = c * H.cost_per_contract(sym)
    return (t_in, t_out, d, c, d * (x - e) * H.PV[sym] * c - cost, cost, sym)


COLS = ["entry_ts", "exit_ts", "direction", "contracts", "pnl", "cost", "sym"]


def slot_table(days):
    """Per day and slot: (start_ts, start_px, end_ts, end_px) from 1-minute closes."""
    recs = []
    for d in days:
        b = full(d)
        t = b.index.time
        c = b["close"].values
        for s in SLOTS:
            e_min = (s.hour * 60 + s.minute + 30)
            end = dt.time(e_min // 60, e_min % 60) if e_min < 24 * 60 else dt.time(23, 59)
            # bars are stamped at their END: the slot [s, end) is the bars stamped (s, end]; its start price is
            # the close of the bar stamped s
            before = np.flatnonzero([(x <= s) and (x < dt.time(18, 0)) for x in t])
            inside = np.flatnonzero([(x > s) and (x <= end) and (x < dt.time(18, 0)) for x in t])
            if len(before) == 0 or len(inside) < 20:
                continue
            i0, i1 = before[-1], inside[-1]
            recs.append((d["tday"], s, b.index[i0], c[i0], b.index[i1], c[i1]))
    return pd.DataFrame(recs, columns=["tday", "slot", "t0", "p0", "t1", "p1"])


def q1(data):
    rows = []
    for sym, (days, _) in data.items():
        st = slot_table(days)
        st["mv"] = st["p1"] - st["p0"]
        st = st.sort_values(["slot", "tday"])
        g = st.groupby("slot")["mv"]
        st["m"] = g.transform(lambda x: x.shift(1).rolling(LOOKBACK, min_periods=LOOKBACK).mean())
        st["sd"] = g.transform(lambda x: x.shift(1).rolling(LOOKBACK, min_periods=LOOKBACK).std())
        st["t"] = st["m"] / (st["sd"] / np.sqrt(LOOKBACK))
        for r in st[st["t"].abs() >= T_MIN].itertuples():
            c = contracts_for(r.sd, sym)
            if c:
                rows.append(trade_row(sym, r.t0, r.t1, int(np.sign(r.m)), c, r.p0, r.p1))
    return pd.DataFrame(rows, columns=COLS)


def q2(data):
    rows = []
    for sym, (days, _) in data.items():
        rth = pd.Series([d["session"]["close"].iloc[-1] - d["session"]["open"].iloc[0] for d in days])
        on = pd.Series([d["on"]["close"].iloc[-1] - d["on"]["open"].iloc[0] for d in days])
        rth_sd, on_sd = rth.rolling(20, min_periods=20).std(), on.shift(1).rolling(20, min_periods=20).std()
        for i in range(1, len(days)):
            d, p = days[i], days[i - 1]
            if p["contract"] != d["contract"] or (d["tday"] - p["tday"]).days > 5:
                continue
            z = rth.iloc[i - 1] / rth_sd.iloc[i - 1] if rth_sd.iloc[i - 1] > 0 else np.nan
            if not abs(z) >= 1:
                continue
            c = contracts_for(on_sd.iloc[i], sym)
            if c:
                o = d["on"]
                rows.append(trade_row(sym, o.index[0], o.index[-1], -int(np.sign(z)), c, o["open"].iloc[0], o["close"].iloc[-1]))
    return pd.DataFrame(rows, columns=COLS)


def q3(data):
    parts = []
    for sym, (days, bars) in data.items():
        sig = []
        for d in days:
            b = full(d)
            t = b.index.time
            # end-stamped bars: the 08:30-08:31 minute is the bar stamped 08:31
            pre = np.flatnonzero([dt.time(8, 0) < x <= NEWS_T for x in t])
            at = np.flatnonzero([x == dt.time(8, 31) for x in t])
            if len(pre) < 20 or len(at) != 1 or b["vol"].values[at[0]] < 5 * b["vol"].values[pre].mean():
                continue
            rng = np.flatnonzero([dt.time(8, 31) <= x <= dt.time(8, 35) for x in t])
            hi, lo = b["high"].values[rng].max(), b["low"].values[rng].min()
            S = hi - lo
            if S <= 0 or H.cost_per_contract(sym) / (S * H.PV[sym]) > MAX_COST_R:
                continue
            for i in np.flatnonzero([dt.time(8, 36) <= x <= NEWS_END for x in t]):
                cl = b["close"].values[i]
                if cl > hi or cl < lo:
                    dr = 1 if cl > hi else -1
                    sig.append((b.index[i], dr, cl, lo if dr == 1 else hi, cl + dr * abs(cl - (lo if dr == 1 else hi))))
                    break
        s = pd.DataFrame(sig, columns=["ts", "direction", "entry", "sl", "tp"])
        tr = H.resolve_bracket(s, bars, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


LABELS = {"Q1": "Q1 same-slot persistence, 30-min slots 08-16 ET, |t| >= 2 over 20 days",
          "Q2": "Q2 overnight 18:00-09:29 against a >= 1 SD previous regular session",
          "Q3": "Q3 08:30 news breakout of the 08:30-08:34 range, 1:1"}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch Q = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    rows = []
    for key, fn in (("Q1", q1), ("Q2", q2), ("Q3", q3)):
        tr = fn(data)
        name = LABELS[key] + ", MNQ + MGC"
        per_day = len(tr) / len(all_days)
        cost_r = float((tr["cost"] / RISK).median())
        need = f"per-trade mean/SD >= {0.36 / np.sqrt(per_day):.3f}"
        if key == "Q3":
            need += f" (1:1 win rate >= {needed_win_rate_1to1(per_day, cost_r):.1%})"
        if dry:
            e = pd.to_datetime(tr["entry_ts"])
            print(f"{name}: {len(tr)} trades ({(e < J.OOS_START).sum()} IS / {(e >= J.OOS_START).sum()} OOS; "
                  f"MNQ {(tr['sym'] == 'MNQ').sum()}, MGC {(tr['sym'] == 'MGC').sum()}), {per_day:.2f}/day, "
                  f"median cost {cost_r:.3f}R, contracts median {tr['contracts'].median():.0f} | gate needs {need}", flush=True)
            if key == "Q1":
                print("   sample:", tr.head(3)[["entry_ts", "exit_ts", "direction", "contracts"]].to_dict("records"))
            continue
        r = H.test_idea(name, tr, all_days, "MNQ", k, risk=RISK)
        per = tr.groupby("sym")["pnl"].mean()
        g, _ = gate_row(tr, all_days)
        both = bool(len(per) == 2 and (per > 0).all())
        r.update(gate=g, both_positive=both, per_market={s: float(v) for s, v in per.items()},
                 trade_sharpe=float(tr["pnl"].mean() / tr["pnl"].std()), trade_sharpe_needed=0.36 / np.sqrt(per_day))
        r["candidate"] = bool(r["candidate"] and both and g["pass_10d"] >= 0.50)
        print(f"      per-trade mean/SD {r['trade_sharpe']:+.3f} (gate needs {r['trade_sharpe_needed']:.3f}) | "
              + ", ".join(f"{s} ${v:+.1f}" for s, v in per.items())
              + f" | gate: pass <= 10d {g['pass_10d']:.2f}, <= 21d {g['pass_21d']:.2f} | "
              f"{'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
        rows.append(r)
    if dry:
        sys.exit()
    lines = H.ledger_rows(rows, "Round 151 batch Q (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round151_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
