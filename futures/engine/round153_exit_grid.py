"""
Round 153: stop-loss and take-profit tuning, done so it can't fool us -- choose the
exit on the in-sample years only, judge that one choice out-of-sample. Pre-registered
2026-09-26, committed before any result is run.

the trader: "try to mess with stop loss and take profit".

What exits can and cannot do: with an entry that has no predictive power, every
stop/target combination has zero expectancy before costs (a martingale stopped at any
rule stays a martingale); exits only trade win rate against payoff. And at a fixed $300
risk, tighter stops mean more contracts and higher costs. So exit tuning can only help
an entry that already predicts something about how far or how fast price moves next --
and a grid of 20 exits fitted on the same data will always find one that looks good.

Entries (unchanged from their rounds; MNQ + MGC 1-minute, 2022-12 .. 2026-09):
  E1  FVG plain, 5-minute candles, limit entry at the gap's edge (Round 150 P1); base
      stop distance S = entry to candle 1's far extreme + 1 tick.
  E2  08:30 news fade (Round 152); S = distance to the far side of the 08:30-08:34 range.
  E3  round-number breakout (Round 148 N1); S = 0.15 x the 20-day average range.
  E4  previous-day high/low breakout (Round 148 N2); S as E3.
Exit grid, 20 combinations per entry: stop at {0.5, 1, 1.5, 2} x S; target at
{0.5, 1, 2, 3} x S from the entry, or none (hold to 16:00 with the stop). Everything
else as the entry's round: one position at a time per instrument, stop first on a tie,
flat at 16:00 ET, $300 risk at the stop, whole contracts (1..50), commission + 2 ticks.

Selection rule (fixed now): for each entry, the exit with the highest mean net $ per
trade on 2022-12 .. 2025-06 (in-sample) is THE exit. Only that exit is judged on
2025-07 .. 2026-09. Its ledger row is one variant per entry: 4 variants, k=191 -> 195.
Candidate: the selected exit's out-of-sample net and before-cost mean > 0 with
P(edge>0) >= 1 - 0.01/195; in-sample P(edge>0) >= 0.95 (inflated by the selection, so
not relied on); net mean > 0 on MNQ and MGC over the whole sample; pass-speed gate
P(pass within 10 trading days) >= 0.50 on the whole sample.
Descriptive (no verdicts): every exit's out-of-sample mean, to show how far the
in-sample choice sits from the best exit in hindsight.

Power notes (dry run, before any result): signals / orders per entry (MNQ, MGC):
E1 FVG 5-min 33,712 / 18,893 limit orders (~24,000 fill at the base exit); E2 news fade
239 / 207; E3 round-number breakout 2,844 / 4,125; E4 previous-day high/low breakout
787 / 722. Check: E2 at stop 1S / target 1S reproduces Round 152's 446 trades. With 20
exits per entry the in-sample choice is the best of 20 correlated tries, so its
in-sample P is optimistic by construction; only its out-of-sample result counts.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round147_batch_m import RISK, full, load, gate_row
import round148_batch_n as N
import round150_batch_p as P
from round151_batch_q import NEWS_T, NEWS_END, MAX_COST_R

N_VARIANTS = 4
STOPS = (0.5, 1.0, 1.5, 2.0)
TARGETS = (0.5, 1.0, 2.0, 3.0, None)
COMBOS = [(s, t) for s in STOPS for t in TARGETS]


def news_fade_signals(days, sym):
    sig = []
    for d in days:
        b = full(d)
        t = b.index.time
        pre = np.flatnonzero([dt.time(8, 0) < x <= NEWS_T for x in t])
        at = np.flatnonzero([x == dt.time(8, 31) for x in t])
        if len(pre) < 20 or len(at) != 1 or b["vol"].values[at[0]] < 5 * b["vol"].values[pre].mean():
            continue
        rng = np.flatnonzero([dt.time(8, 31) <= x <= dt.time(8, 35) for x in t])
        hi, lo = b["high"].values[rng].max(), b["low"].values[rng].min()
        if hi - lo <= 0 or H.cost_per_contract(sym) / ((hi - lo) * H.PV[sym]) > MAX_COST_R:
            continue
        for i in np.flatnonzero([dt.time(8, 36) <= x <= NEWS_END for x in t]):
            cl = b["close"].values[i]
            if cl > hi or cl < lo:
                q3 = 1 if cl > hi else -1
                sig.append((b.index[i], -q3, cl, abs(cl - (lo if q3 == 1 else hi))))
                break
    return pd.DataFrame(sig, columns=["ts", "direction", "entry", "S"])


def base_signals(data):
    """Per entry and instrument: market-entry signals (ts, direction, entry, S), or FVG limit orders."""
    out = {}
    for sym, (days, bars) in data.items():
        n1 = N.signals(days, sym, "N1", 2.0)
        n2 = N.signals(days, sym, "N2", 2.0)
        for key, s in (("E3", n1), ("E4", n2)):
            s = s.assign(S=(s["entry"] - s["sl"]).abs())[["ts", "direction", "entry", "S"]]
            out[(key, sym)] = s
        out[("E2", sym)] = news_fade_signals(days, sym)
        out[("E1", sym)] = [(d, P.fvg_orders(full(d), sym, 5, False)) for d in days]
    return out


def resolve_combo(data, sigs, key, stop_m, tgt_m):
    parts = []
    for sym, (days, bars) in data.items():
        if key == "E1":
            rows = []
            for d, orders in sigs[(key, sym)]:
                b = full(d)
                o2 = []
                for formed, expiry, dr, e, s, _ in orders:
                    S = abs(e - s)
                    o2.append((formed, expiry, dr, e, e - dr * stop_m * S,
                               e + dr * tgt_m * S if tgt_m is not None else np.nan))
                rows += P.resolve_limit(b, o2, sym)
            tr = pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r"])
        else:
            s = sigs[(key, sym)]
            sig = pd.DataFrame({"ts": s["ts"], "direction": s["direction"], "entry": s["entry"],
                                "sl": s["entry"] - s["direction"] * stop_m * s["S"],
                                "tp": s["entry"] + s["direction"] * tgt_m * s["S"] if tgt_m is not None else np.nan})
            b = bars[bars["tday"].isin(set((pd.to_datetime(s["ts"]) + pd.Timedelta(hours=6)).dt.normalize()))]
            tr = H.resolve_bracket(sig, b, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


LABELS = {"E1": "FVG plain 5-min", "E2": "08:30 news fade", "E3": "round-number breakout", "E4": "previous-day high/low breakout"}


def tname(t):
    return "hold" if t is None else f"{t:g}S"


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after Round 153 = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    sigs = base_signals(data)
    if dry:
        for key in LABELS:
            for sym in data:
                s = sigs[(key, sym)]
                n = sum(len(o) for _, o in s) if key == "E1" else len(s)
                print(f"{key} {LABELS[key]:<32} {sym}: {n} signals/orders", flush=True)
        tr = resolve_combo(data, sigs, "E2", 1.0, 1.0)
        print(f"check: E2 at stop 1S / target 1S reproduces Round 152's trade count: {len(tr)} (Round 152: 446)")
        sys.exit()
    rows, grids = [], {}
    for key, label in LABELS.items():
        grid = []
        for sm, tm in COMBOS:
            tr = resolve_combo(data, sigs, key, sm, tm)
            e = pd.to_datetime(tr["entry_ts"])
            grid.append(dict(stop=sm, target=tname(tm), n=len(tr), is_mean=float(tr.loc[e < J.OOS_START, "pnl"].mean()),
                             oos_mean=float(tr.loc[e >= J.OOS_START, "pnl"].mean()), win=float((tr["pnl"] > 0).mean()), tr=tr))
            print(f"  {key} stop {sm:g}S target {tname(tm):>5}: n={len(tr):>5} win {grid[-1]['win']:.0%} "
                  f"IS ${grid[-1]['is_mean']:+7.1f}", flush=True)
        best = max(grid, key=lambda g: g["is_mean"])
        hind = max(grid, key=lambda g: g["oos_mean"])
        name = f"{label}, exit chosen in-sample: stop {best['stop']:g}S target {best['target']}, MNQ + MGC"
        tr = best["tr"]
        r = H.test_idea(name, tr, all_days, "MNQ", k, risk=RISK)
        per = tr.groupby("sym")["pnl"].mean()
        g, _ = gate_row(tr, all_days)
        both = bool(len(per) == 2 and (per > 0).all())
        e = pd.to_datetime(tr["entry_ts"])
        oos = tr[e >= J.OOS_START]
        oos_gross = float((oos["pnl"] + oos["cost"]).mean())
        r.update(gate=g, both_positive=both, per_market={s: float(v) for s, v in per.items()}, stop=best["stop"],
                 target=best["target"], oos_gross=oos_gross,
                 grid=[{k2: v for k2, v in x.items() if k2 != "tr"} for x in grid])
        r["candidate"] = bool(r["exp_oos"] > 0 and oos_gross > 0 and r["p_oos"] >= r["bar"] and r["p_is"] >= 0.95
                              and both and g["pass_10d"] >= 0.50)
        print(f"   => {key}: in-sample choice stop {best['stop']:g}S / {best['target']} (IS ${best['is_mean']:+.1f}) -> "
              f"OOS ${best['oos_mean']:+.1f}; best exit in hindsight stop {hind['stop']:g}S / {hind['target']} OOS "
              f"${hind['oos_mean']:+.1f}; OOS mean over all 20 exits ${np.mean([x['oos_mean'] for x in grid]):+.1f} | "
              f"gate pass <= 10d {g['pass_10d']:.2f} | {'CANDIDATE' if r['candidate'] else 'no'}\n", flush=True)
        rows.append(r)
    lines = H.ledger_rows(rows, "Round 153 exit grid, chosen in-sample (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round153_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
