"""
Round 185: robustness pass on Round 184's NQ Value Area rejection lead
(OOS P=0.972, the second-closest miss in this ledger). Same discipline as
Round 183 (which stress-tested the POC lead and found it robust): perturb
one parameter at a time, holding the other at Round 184's original value,
and look for a smooth curve or a cliff.

Two tunable parameters in the Value Area rule (unlike Round 178/183's POC
rule, there is no separate rolling lookback window here -- the value area
is built entirely from that session's own volume profile):
  bin size     -- the tick-multiple used to bin volume into the profile
                  (1x is Round 184's original).
  VA percentage -- the fraction of session volume the value area must
                  capture around POC (0.70 is Round 184's original, and
                  the standard textbook Market Profile convention).

Step 0, honest before running: same as every robustness pass in this
ledger -- a real, structural effect should perform similarly across nearby
parameter values; a result that only appears at one exact setting and
reverses nearby is the "sharp drop" signature of overfitting (the /watched
validation video's own diagnostic, qcUCBLRcGLA), the same one that flagged
Round 167's ORB volume lead before Round 169 killed it, and the one Round
183 showed the POC lead does NOT have.

4 variants (2 bin sizes + 2 VA percentages). NQ, rejection direction only
(the side of Round 184 that showed anything). Ledger k=317 -> 321; OOS bar
1 - 0.01/321 at the last variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento

FLAT_TIME = dt.time(16, 0)
BASELINE = dict(tick_mult=1, va_pct=0.70)


def session_value_area(session, tick, va_pct):
    if session.empty:
        return np.nan, np.nan, np.nan
    px = np.round(session["close"] / tick).astype(int) * tick
    profile = pd.Series(session["vol"].values, index=px.values).groupby(level=0).sum().sort_index()
    if len(profile) < 2:
        v = float(profile.index[0])
        return v, v, v
    poc = profile.idxmax()
    levels = profile.index.to_list()
    poc_idx = levels.index(poc)
    target = va_pct * profile.sum()
    lo = hi = poc_idx
    vol_sum = profile.iloc[poc_idx]
    while vol_sum < target and (lo > 0 or hi < len(levels) - 1):
        vol_below = profile.iloc[lo - 1] if lo > 0 else -1
        vol_above = profile.iloc[hi + 1] if hi < len(levels) - 1 else -1
        if vol_below >= vol_above:
            lo -= 1
            vol_sum += profile.iloc[lo]
        else:
            hi += 1
            vol_sum += profile.iloc[hi]
    return float(poc), float(levels[lo]), float(levels[hi])


def build_signals_df(days, tick, va_pct):
    """Rejection only: bet AGAINST a breakout beyond yesterday's value area."""
    rows, prev = [], None
    for d in days:
        s = d["session"]
        if s.empty:
            continue
        if prev is not None:
            poc, val, vah = prev
            open_px = s["open"].iloc[0]
            if vah - val > 0:
                if open_px > vah:
                    sl = open_px + (open_px - vah)
                    rows.append((s.index[0], -1, open_px, sl, poc))
                elif open_px < val:
                    sl = open_px - (val - open_px)
                    rows.append((s.index[0], 1, open_px, sl, poc))
        prev = session_value_area(s, tick, va_pct)
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(sym, tick_mult, va_pct):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    tick = H.TK[sym] * tick_mult
    sig = build_signals_df(days, tick, va_pct)
    tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sym = "NQ"
    grid = []
    for tm in (2, 4):
        grid.append((dict(BASELINE, tick_mult=tm), f"bin size x{tm}"))
    for vp in (0.60, 0.80):
        grid.append((dict(BASELINE, va_pct=vp), f"VA {vp:.0%}"))

    if dry:
        for params, label in grid:
            tr, days = build_trades(sym, **params)
            print(f"{label} ({params}): {len(tr)} trades")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for params, label in grid:
        k = H.ledger_count() + 1
        tr, days = build_trades(sym, **params)
        all_days = [d["tday"] for d in days]
        name = f"Value Area rejection, NQ, {label} (robustness pass on Round 184), Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 185 (pre-registered, robustness pass on Round 184's NQ Value Area rejection lead)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round185_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
