"""
Round 183: robustness pass on Round 178's NQ Volume Profile / POC lead, per
CURRENT_STATE.md's own note ("worth a robustness pass... before trusting it
further"). NQ was the one symbol of four where POC reversion looked real
(IS P=0.98, Sharpe 0.054, OOS P=0.85) -- not yet stress-tested the way the
ORB volume lead was (Rounds 168-169) before it was retired. Same discipline
applied here, and directly informed by the /watched validation-methodology
video (qcUCBLRcGLA): perturb ONE parameter at a time, holding the others at
Round 178's original values, and look for a smooth curve (robust) or a
cliff (overfit to one specific setting).

Three parameters, each varied alone:
  bin size   -- the tick-multiple used to bin volume into the profile
                (1x is Round 178's original, i.e. bin width = one tick).
  lookback   -- the window (in days) for the average-session-range stop
                sizing (20 is Round 178's original).
  threshold  -- the |open-POC| distance, in units of that stop size,
                required to trade at all (0.15 is Round 178's original).

Step 0, honest before running: a real, structural effect should perform
similarly across nearby parameter values (the video's own "smooth curve"
signature); a result that only appears at one exact setting and reverses or
collapses nearby is the "sharp drop" signature of overfitting, the same
diagnostic that flagged Round 167's ORB volume lead before Round 169 killed
it by extending its own threshold grid. Tested to find out which this is,
not because either outcome is expected.

8 variants (2 bin sizes + 3 lookbacks + 3 thresholds, minus the shared
baseline already in the ledger as Round 178's NQ row -- not re-run here).
NQ only. Ledger k=301 -> 309; OOS bar 1 - 0.01/309 at the last variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento
from round178_volume_profile_poc import session_poc, FLAT_TIME

BASELINE = dict(tick_mult=1, window=20, stop_mult=0.15)


def build_signals(days, tick, window, stop_mult):
    ranges = pd.Series({d["tday"]: (d["session"]["high"].max() - d["session"]["low"].min())
                        for d in days if not d["session"].empty})
    avg_range = ranges.rolling(window, min_periods=max(5, window // 2)).mean().shift(1)

    out, prev_poc = [], None
    for d in days:
        s = d["session"]
        S = avg_range.get(d["tday"], np.nan)
        if s.empty or prev_poc is None or not (S > 0):
            prev_poc = session_poc(s, tick)
            continue
        open_px = s["open"].iloc[0]
        dist = prev_poc - open_px
        if abs(dist) >= stop_mult * S:
            direction = int(np.sign(dist))
            sl = open_px - direction * stop_mult * S
            out.append((s.index[0], direction, open_px, sl, prev_poc))
        prev_poc = session_poc(s, tick)
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(sym, tick_mult, window, stop_mult):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    tick = H.TK[sym] * tick_mult
    sig = build_signals(days, tick, window, stop_mult)
    tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sym = "NQ"
    grid = []
    for tm in (2, 4):
        grid.append((dict(BASELINE, tick_mult=tm), f"bin size x{tm}"))
    for w in (10, 30, 40):
        grid.append((dict(BASELINE, window=w), f"lookback {w}d"))
    for sm in (0.10, 0.20, 0.25):
        grid.append((dict(BASELINE, stop_mult=sm), f"threshold {sm}x"))

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
        name = f"Volume Profile POC reversion, NQ, {label} (robustness pass on Round 178), Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round183_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
