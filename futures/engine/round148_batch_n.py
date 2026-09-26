"""
Round 148, batch N: intraday breakouts through levels, held to the pass-speed gate.
Pre-registered 2026-09-26, committed before any result is run.

the trader: keep hunting, test breakouts through levels. Batch M (Round 147) found that
levels break more often than they hold: fades won 1-3 points below the random-walk
rate. Osler (2003): stop-loss orders cluster just beyond round numbers, so once a
level is crossed those stops can push price further. This batch trades WITH the break.

Data, exits, costs, split: as batch M (24-hour 1-minute MNQ and MGC, one contract per
day, 2022-12 .. 2026-09; idea_harness.resolve_bracket, entry at the signal bar's close,
one position at a time per instrument, stop before target on a tie, flat at 16:00 ET;
$300 risk, whole contracts, commission + 2 ticks; split 2025-07-01).

Entry: the first 1-minute bar in the session to CLOSE through a level after every
earlier close of the session sat on the other side (a confirmed first break, not a
touch). Up through -> long, down through -> short. Stop S behind the entry, with S =
0.15 x the average full-session range of the previous 20 days (as batch M).
Levels:
  N1  round numbers: MNQ multiples of 100 points, MGC multiples of $10; the close must
      cross a multiple beyond every earlier close of the session. Entries 18:00 -> 15:30 ET.
  N2  previous day's high and low (full 18:00 -> 16:00 session, same contract only).
      Entries 18:00 -> 15:30 ET.
  N3  overnight high and low (this session's 18:00 -> 09:29 ET range), broken during
      regular hours: entries 09:30 -> 15:30 ET. (Replaces the opening range: batch B
      already tested opening-range breakouts on MNQ.)
Exits, one variant each:
  a  target 2S (random-walk win rate 33%);
  b  no target -- ride the break with the stop to the 16:00 flat.
6 variants take the ledger from k=175 to k=181.

Candidate (all required, as batch M): net and before-cost mean > 0; IS P(edge>0) >= 0.95;
OOS P(edge>0) >= 1 - 0.01/181; net mean > 0 on MNQ and on MGC separately; pass-speed
gate P(pass a $50K Test within 10 trading days) >= 0.50 at the best size.
Descriptive: win rate against the random-walk rate (a); N1 on non-round control
levels (MNQ 100k + 37, MGC 10k + 3.7).

Power notes and what each variant needs for the gate (dry run, before any result):
  variant                       trades (IS / OOS)      per day  gate needs
  N1 round numbers, target 2S   4,907 (2,818 / 2,089)  5.2      win >= 41.9% (random walk 33%)
  N1 round numbers, no target   3,433 (2,061 / 1,372)  3.6      per-trade mean/SD >= 0.189
  N2 prior-day H/L, target 2S   1,509 (986 / 523)      1.6      win >= 48.4%
  N2 prior-day H/L, no target   1,493 (978 / 515)      1.6      per-trade mean/SD >= 0.286
  N3 overnight H/L, target 2S   1,590 (1,062 / 528)    1.7      win >= 48.0%
  N3 overnight H/L, no target   1,590 (1,062 / 528)    1.7      per-trade mean/SD >= 0.277
Median cost 0.022R per trade. "Gate needs" = what reaches a daily Sharpe of 0.36 (~50%
passes within 10 days) with independent trades: 9-15 points of win rate above the
random walk for the 2S target. Batch M's fades lost 1-3 points to the random walk, which
would put these breakouts only 1-3 points above it before costs.
Hand-checked (MNQ): an N1 short on the first close below 12,600 after every earlier close
sat above it; an N2 short on the first close below the previous day's low (12,550.5); an
N3 long at 11:33 on the first close above the overnight high (12,573.75). A close exactly
on a round number is not a break (fixed in the dry run, before any result).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round147_batch_m import (GRID, CONTROL_OFFSET, RISK, LAST_ENTRY, full, stop_sizes, load, gate_row,
                              needed_win_rate)

N_VARIANTS = 6
EXITS = {"a": ("target 2S", 2.0), "b": ("no target, stop to 16:00", np.nan)}
RTH_OPEN = dt.time(9, 30)


def in_window(idx, rth_only):
    t = idx.time
    if rth_only:
        return np.array([RTH_OPEN <= x <= LAST_ENTRY for x in t])
    return np.array([(x >= dt.time(18, 0)) or (x <= LAST_ENTRY) for x in t])


def first_breaks(b, crosses_up, crosses_dn, rth_only=False):
    """Bars whose close first crosses a level beyond every earlier close of the session.
    crosses_up(close, prev_max_close) -> bool array; likewise down."""
    c = b["close"].values
    start = b["open"].values[0]
    prev_max = np.maximum.accumulate(np.r_[start, c[:-1]])
    prev_min = np.minimum.accumulate(np.r_[start, c[:-1]])
    up, dn = crosses_up(c, prev_max), crosses_dn(c, prev_min)
    ok = in_window(b.index, rth_only)
    idx = np.flatnonzero((up | dn) & ok)
    return idx, np.where(up[idx], 1, -1)


def round_crosses(grid, offset=0.0):
    # the nearest level strictly below (above) the close must lie beyond every earlier close
    up = lambda c, pm: np.ceil((c - offset) / grid - 1) * grid + offset > pm
    dn = lambda c, pm: np.floor((c - offset) / grid + 1) * grid + offset < pm
    return up, dn


def level_crosses(levels):
    lv = np.array(levels, float)
    up = lambda c, pm: ((lv[None, :] > pm[:, None]) & (lv[None, :] < c[:, None])).any(axis=1)
    dn = lambda c, pm: ((lv[None, :] < pm[:, None]) & (lv[None, :] > c[:, None])).any(axis=1)
    return up, dn


def signals(days, sym, setup, tmult, control=False):
    S_by_day = stop_sizes(days)
    rows, prev = [], None
    for d in days:
        b = full(d)
        S = S_by_day.get(d["tday"], np.nan)
        pos, dirs = np.array([], int), np.array([], int)
        if S > 0 and setup == "N1":
            pos, dirs = first_breaks(b, *round_crosses(GRID[sym], CONTROL_OFFSET[sym] if control else 0.0))
        elif S > 0 and setup == "N2" and prev is not None and prev["contract"] == d["contract"] \
                and (d["tday"] - prev["tday"]).days <= 5:
            pb = full(prev)
            pos, dirs = first_breaks(b, *level_crosses([pb["high"].max(), pb["low"].min()]))
        elif S > 0 and setup == "N3" and len(d["on"]) >= 300:
            pos, dirs = first_breaks(b, *level_crosses([d["on"]["high"].max(), d["on"]["low"].min()]), rth_only=True)
        for i, dr in zip(pos, dirs):
            e = b["close"].values[i]
            rows.append((b.index[i], dr, e, e - dr * S, e + dr * tmult * S if tmult == tmult else np.nan))
        prev = d
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "sl", "tp"])


def run_variant(data, setup, tmult, control=False):
    parts = []
    for sym, (days, bars) in data.items():
        tr = H.resolve_bracket(signals(days, sym, setup, tmult, control), bars, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def needed_trade_sharpe(n_per_day, target_sharpe=0.36):
    return target_sharpe / np.sqrt(n_per_day)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch N = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    rows = []
    for setup, label in [("N1", "N1 round-number breakout"), ("N2", "N2 previous-day high/low breakout"),
                         ("N3", "N3 overnight high/low breakout in RTH")]:
        for key, (xname, tmult) in EXITS.items():
            name = f"{label}, {xname}, MNQ + MGC"
            tr = run_variant(data, setup, tmult)
            per_day = len(tr) / len(all_days)
            cost_r = float((tr["cost"] / RISK).median())
            base = 1 / (1 + tmult) if tmult == tmult else np.nan
            need = needed_win_rate(per_day, tmult, cost_r) if tmult == tmult else np.nan
            if dry:
                e = pd.to_datetime(tr["entry_ts"])
                need_txt = (f"random-walk win {base:.0%}; gate needs win >= {need:.1%}" if tmult == tmult else
                            f"gate needs per-trade mean/SD >= {needed_trade_sharpe(per_day):.3f}")
                print(f"{name}: {len(tr)} trades ({(e < J.OOS_START).sum()} IS / {(e >= J.OOS_START).sum()} OOS; "
                      f"MNQ {(tr['sym'] == 'MNQ').sum()}, MGC {(tr['sym'] == 'MGC').sum()}), {per_day:.2f}/day, "
                      f"median cost {cost_r:.3f}R | {need_txt}", flush=True)
                continue
            r = H.test_idea(name, tr, all_days, "MNQ", k, risk=RISK)
            per = tr.groupby("sym")["pnl"].mean()
            g, sharpe = gate_row(tr, all_days)
            both = bool(len(per) == 2 and (per > 0).all())
            r.update(win_baseline=base, win_needed=need, gate=g, both_positive=both,
                     per_market={s: float(v) for s, v in per.items()},
                     trade_sharpe=float(tr["pnl"].mean() / tr["pnl"].std()), trade_sharpe_needed=needed_trade_sharpe(per_day))
            r["candidate"] = bool(r["candidate"] and both and g["pass_10d"] >= 0.50)
            print(f"      win {r['win']:.1%}" + (f" vs random walk {base:.0%} (gate needs {need:.1%})" if tmult == tmult else "")
                  + f" | per-trade mean/SD {r['trade_sharpe']:+.3f} (gate needs {r['trade_sharpe_needed']:.3f}) | "
                  + ", ".join(f"{s} ${v:+.1f}" for s, v in per.items())
                  + f" | gate: pass <= 10d {g['pass_10d']:.2f}, <= 21d {g['pass_21d']:.2f} | "
                  f"{'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
            if setup == "N1":
                c = run_variant(data, setup, tmult, control=True)
                print(f"      control (non-round levels): n={len(c)} win {(c['pnl'] > 0).mean():.1%} "
                      f"net ${c['pnl'].mean():+.1f}/trade", flush=True)
            rows.append(r)
    if dry:
        sys.exit()
    lines = H.ledger_rows(rows, "Round 148 batch N (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round148_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
