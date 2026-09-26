"""
Round 147, batch M: high win-rate intraday level fades, held to the pass-speed gate.
Pre-registered 2026-09-26, committed before any result is run.

the trader: keep hunting, focus on high win-rate intraday ideas -- and (standing rule) the
edge must comply with Broker's rules and be big enough to pass a Test in few
days. A high win rate alone is not an edge: a bracket with a target T and a stop S
wins S / (S + T) of the time on a random walk (67% at T = S/2, 75% at T = S/3) and
still loses the costs. What matters is the win rate ABOVE that baseline, and whether
it is large enough, often enough, to clear the gate.

Data: 24-hour 1-minute MNQ and MGC (idea_harness.load_days, one contract per day,
18:00 ET start), 2022-12 .. 2026-09. Exits: idea_harness.resolve_bracket -- entry at
the signal bar's close, one position at a time per instrument, stop checked before
target on each bar, flat at the day's last bar (16:00 ET, inside Broker's 16:10 ET
cutoff); no new entries after 15:30 ET. $300 risk per trade, whole contracts, cost =
commission + 2 ticks per contract. Split at 2025-07-01.

Each setup fades a price level on its first touch in the session: approached from
below -> short, from above -> long; stop S beyond the entry, target T back. A bar
that touches levels in both directions is skipped.
M1  Round numbers (Osler 2003: take-profit orders cluster at round numbers, so prices
    tend to reverse there): MNQ multiples of 100 points, MGC multiples of $10. A level
    is "touched first from below" when the bar's high reaches a multiple above every
    earlier high of the session (session start = the first bar's open); mirror image
    from above. S = 0.15 x the average full-session range of the previous 20 days
    (~45 MNQ points, ~$6 gold).
M2  Previous day's high and low (full 18:00 -> 16:00 session of the previous trading
    day, same contract only -- skipped on roll days, where contracts differ by ~1%).
    Same touch rule and S as M1.
M3  Opening-range fade: the opening range is MNQ 09:30-09:44 ET, MGC 08:20-08:34 ET
    (COMEX open). The first bar after it trading beyond the range is faded;
    S = the range's width (at least 8 ticks).
Variants: each setup at T = S/2 and T = S/3 (random-walk win rates 67% and 75%).
6 variants take the ledger from k=169 to k=175.

Candidate (all required): net and before-cost mean > 0; IS P(edge>0) >= 0.95;
OOS P(edge>0) >= 1 - 0.01/175; net mean > 0 on MNQ and on MGC separately; AND the
pass-speed gate (pass_speed_gate.gate on its daily results, all trading days,
days without trades = 0): P(pass a $50K Test within 10 trading days) >= 0.50 at
the best size (a zero-edge coin flip sized up: 0.20).

Descriptive: win rate against the random-walk baseline; M1 on "non-round" control
levels (MNQ 100k + 37, MGC 10k + 3.7) -- Osler's claim is specific to round numbers.

Power notes and the win rate each variant needs for the gate (dry run, before any
result):
  variant                  trades (IS / OOS)      per day  random-walk win  gate needs win
  M1 round numbers, S/2    6,898 (3,699 / 3,199)  7.3      67%              74.0%
  M1 round numbers, S/3    7,051 (3,728 / 3,323)  7.5      75%              81.8%
  M2 prior-day H/L, S/2    1,686 (1,119 / 567)    1.8      67%              79.2%
  M2 prior-day H/L, S/3    1,686                  1.8      75%              86.1%
  M3 opening range, S/2    1,818 (1,230 / 588)    1.9      67%              78.4%
  M3 opening range, S/3    1,818                  1.9      75%              85.4%
Median cost 0.015-0.022R per trade. "Gate needs" = the win rate at which (per-trade
mean / SD) x sqrt(trades per day) reaches a daily Sharpe of 0.36 (~50% passes within
10 days), assuming independent trades -- 7 to 12 points above the random-walk
baseline. Osler's round-number effect in FX was a few points, so M1 would need a much
larger effect in futures than was published for currencies.
Hand-checked in the dry run (MNQ): an M1 short at a first touch of 12,800 from below,
an M2 long at the first touch of the previous day's low (12,550.5, same contract), an
M3 long fading the first break below the 09:30-09:44 range (width 62, stop 62 away).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from pass_speed_gate import gate

N_VARIANTS = 6
RISK = 300.0
GRID = {"MNQ": 100.0, "MGC": 10.0}
CONTROL_OFFSET = {"MNQ": 37.0, "MGC": 3.7}
OR_WINDOW = {"MNQ": (dt.time(9, 30), dt.time(9, 45)), "MGC": (dt.time(8, 20), dt.time(8, 35))}
LAST_ENTRY = dt.time(15, 30)
S_FRAC = 0.15
RATIOS = {"T=S/2": 0.5, "T=S/3": 1 / 3}


def full(d):
    return pd.concat([d["on"], d["session"]])


def entry_ok(idx):
    t = idx.time
    return np.array([(x >= dt.time(18, 0)) or (x <= LAST_ENTRY) for x in t])


def stop_sizes(days):
    rng = pd.Series([full(d)["high"].max() - full(d)["low"].min() for d in days], index=[d["tday"] for d in days])
    return (S_FRAC * rng.shift(1).rolling(20, min_periods=15).mean()).to_dict()


def first_touches(b, levels_up, levels_dn):
    """Bars where the high first reaches one of levels_up (fn: high -> level or NaN, the
    highest level <= high) above all earlier highs, or the low first reaches a level
    below all earlier lows. Returns (bar positions, directions): -1 = fade from below."""
    hi, lo = b["high"].values, b["low"].values
    prev_max = np.maximum.accumulate(np.r_[b["open"].values[0], hi[:-1]])
    prev_min = np.minimum.accumulate(np.r_[b["open"].values[0], lo[:-1]])
    up = levels_up(hi, prev_max)   # a level in (prev_max, hi]
    dn = levels_dn(lo, prev_min)   # a level in [lo, prev_min)
    ok = entry_ok(b.index)
    pos, dirs = [], []
    for i in np.flatnonzero((up | dn) & ~(up & dn) & ok):
        pos.append(i); dirs.append(-1 if up[i] else 1)
    return np.array(pos, int), np.array(dirs, int)


def round_levels(grid, offset=0.0):
    up = lambda hi, pm: np.floor((hi - offset) / grid) * grid + offset > pm
    dn = lambda lo, pm: np.ceil((lo - offset) / grid) * grid + offset < pm
    return up, dn


def fixed_levels(levels):
    lv = np.array(levels)
    up = lambda hi, pm: ((lv[None, :] > pm[:, None]) & (lv[None, :] <= hi[:, None])).any(axis=1)
    dn = lambda lo, pm: ((lv[None, :] < pm[:, None]) & (lv[None, :] >= lo[:, None])).any(axis=1)
    return up, dn


def signals(days, sym, setup, ratio, control=False):
    S_by_day = stop_sizes(days)
    rows = []
    prev = None
    for d in days:
        b = full(d)
        S = S_by_day.get(d["tday"], np.nan)
        pos, dirs = np.array([], int), np.array([], int)
        if setup == "M1" and S > 0:
            pos, dirs = first_touches(b, *round_levels(GRID[sym], CONTROL_OFFSET[sym] if control else 0.0))
        elif setup == "M2" and S > 0 and prev is not None and prev["contract"] == d["contract"] \
                and (d["tday"] - prev["tday"]).days <= 5:
            pb = full(prev)
            pos, dirs = first_touches(b, *fixed_levels([pb["high"].max(), pb["low"].min()]))
        elif setup == "M3":
            t = b.index.time
            a, z = OR_WINDOW[sym]
            in_or = np.array([(x >= a) and (x < z) for x in t])
            after = np.array([x >= z and x <= LAST_ENTRY for x in t])
            if in_or.sum() >= 10:
                orh, orl = b["high"].values[in_or].max(), b["low"].values[in_or].min()
                S = max(orh - orl, 8 * H.TK[sym])
                brk_up, brk_dn = after & (b["high"].values > orh), after & (b["low"].values < orl)
                first = np.flatnonzero(brk_up | brk_dn)
                if len(first) and not (brk_up[first[0]] and brk_dn[first[0]]):
                    pos, dirs = first[:1], np.array([-1 if brk_up[first[0]] else 1])
        for i, dr in zip(pos, dirs):
            e = b["close"].values[i]
            rows.append((b.index[i], dr, e, e - dr * S, e + dr * ratio * S))
        prev = d
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "sl", "tp"])


def run_variant(data, setup, ratio, control=False):
    parts = []
    for sym, (days, bars) in data.items():
        sig = signals(days, sym, setup, ratio, control)
        tr = H.resolve_bracket(sig, bars, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def gate_row(tr, all_days):
    daily = tr.groupby(pd.to_datetime(tr["exit_ts"]).dt.normalize())["pnl"].sum() / RISK
    daily = daily.reindex(pd.DatetimeIndex(sorted(set(all_days))), fill_value=0.0)
    return gate(daily.values), float(daily.mean() / daily.std())


def load():
    data = {}
    for sym in GRID:
        days = H.load_days(sym)
        data[sym] = (days, H.bars_from_days(days, "all"))
    return data


def needed_win_rate(n_per_day, ratio, cost_r, target_sharpe=0.36):
    """Win rate at which (per-trade mean / SD) x sqrt(trades per day) reaches the daily
    Sharpe that gives ~50% passes within 10 days (requirement table: 0.3 -> 0.42, 0.5 -> 0.65)."""
    for p in np.arange(0.30, 0.9999, 0.0005):
        m, sd = p * ratio - (1 - p) - cost_r, np.sqrt(p * (1 - p)) * (1 + ratio)
        if m / sd * np.sqrt(n_per_day) >= target_sharpe:
            return p
    return np.nan


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch M = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    rows = []
    for setup, label in [("M1", "M1 round-number fade"), ("M2", "M2 previous-day high/low fade"),
                         ("M3", "M3 opening-range fade")]:
        for rname, ratio in RATIOS.items():
            name = f"{label}, {rname}, MNQ + MGC"
            tr = run_variant(data, setup, ratio)
            per_day = len(tr) / len(all_days)
            cost_r = float((tr["cost"] / RISK).median())
            base = 1 / (1 + ratio)
            if dry:
                e = pd.to_datetime(tr["entry_ts"])
                print(f"{name}: {len(tr)} trades ({(e < J.OOS_START).sum()} IS / {(e >= J.OOS_START).sum()} OOS; "
                      f"MNQ {(tr['sym'] == 'MNQ').sum()}, MGC {(tr['sym'] == 'MGC').sum()}), {per_day:.2f}/day, "
                      f"median cost {cost_r:.3f}R, contracts median {tr['contracts'].median():.0f} | random-walk win "
                      f"{base:.0%}; gate needs win >= {needed_win_rate(per_day, ratio, cost_r):.1%}", flush=True)
                continue
            r = H.test_idea(name, tr, all_days, "MNQ", k, risk=RISK)
            per = tr.groupby("sym")["pnl"].mean()
            g, sharpe = gate_row(tr, all_days)
            both = bool(len(per) == 2 and (per > 0).all())
            r.update(win_baseline=base, win_needed=needed_win_rate(per_day, ratio, cost_r), gate=g,
                     both_positive=both, per_market={s: float(v) for s, v in per.items()})
            r["candidate"] = bool(r["candidate"] and both and g["pass_10d"] >= 0.50)
            print(f"      win {r['win']:.1%} vs random walk {base:.0%} (gate needs {r['win_needed']:.1%}) | "
                  + ", ".join(f"{s} ${v:+.1f}" for s, v in per.items())
                  + f" | gate: pass <= 10d {g['pass_10d']:.2f}, <= 21d {g['pass_21d']:.2f} at ${g['dollars_per_R']}/R | "
                  f"{'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
            if setup == "M1":
                c = run_variant(data, setup, ratio, control=True)
                print(f"      control (non-round levels): n={len(c)} win {(c['pnl'] > 0).mean():.1%} "
                      f"net ${c['pnl'].mean():+.1f}/trade", flush=True)
            rows.append(r)
    if dry:
        sys.exit()
    lines = H.ledger_rows(rows, "Round 147 batch M (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round147_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
