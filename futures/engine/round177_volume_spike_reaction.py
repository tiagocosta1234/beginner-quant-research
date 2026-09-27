"""
Round 177: formalizing the exploratory scan's standout finding (unregistered
diagnostic pass over all 4 Databento symbols, not itself a ledger entry).
Looked at every 1-minute bar with volume >= 4x its own trailing 30-bar
average, and what happened next in the direction that bar moved: metals
(GC, SI) reverse hard and fast (t=-7.73/-7.12 at +1 bar, still t=-4.18/-2.06
at +15), Nasdaq (NQ) continues and gets stronger over time (t=+0.80 at +1
bar growing to t=+2.66 at +15). ES showed no clear pattern and is dropped.
This is a genuinely different question from Rounds 167-172 (does volume
CONFIRM a price-level breakout) -- this is the market's UNCONDITIONAL
reaction to a volume spike, anywhere, no price level involved at all.

Rule, unchanged from the exploratory scan (no new tuning): volume >= 4x the
trailing 30-bar average (causal), entering at the spike bar's close.
  GC, SI: FADE the spike bar's own direction (bet on reversal).
  NQ: CONTINUE the spike bar's own direction (bet on continuation).
Exit after a fixed hold, chosen from the scan's own horizon breakdown, not
re-tuned here: GC/SI hold 5 bars (the reversal is front-loaded and decaying
by +15, so a shorter hold should capture more of it); NQ holds 15 bars (the
continuation effect was still strengthening at that horizon in the scan).
No stop-loss -- this is a direct, honest replication of the exact effect
the scan measured (raw forward price change), not a new risk-managed
version of it; a follow-up round would add real risk control only if this
one shows something real. Position sized to $300 risk per trade using each
trade's own trailing 30-bar realized volatility (in dollars), the same
"size to a volatility unit" principle round135_batch_d uses for daily bars,
applied here to 1-minute bars since there's no stop distance to size against.

Step 0, honest before running: t-stats of 4-7 on samples of 37,000-66,000
spikes look decisive, but that scan ran dozens of implicit comparisons
(4 symbols x multiple lag horizons) without a multiple-testing correction --
exactly the situation this ledger's own OOS bar exists to correct for. This
round applies that correction for real, on FRESH structure (real costs, a
real IS/OOS split, real position sizing) the exploratory pass didn't have.
A strong exploratory t-stat is a reason to test, not a reason to expect a
pass.

3 variants (GC fade, SI fade, NQ continuation). Ledger k=285 -> 288; OOS
bar 1 - 0.01/288 at the last variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento

VOL_MULT = 4.0
TRAIL = 30
CONFIGS = {
    "GC": dict(hold=5, fade=True),
    "SI": dict(hold=5, fade=True),
    "NQ": dict(hold=15, fade=False),
}

_BARS_CACHE = {}


def full_bars(sym):
    if sym not in _BARS_CACHE:
        days = load_days_databento(sym)
        b = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
        _BARS_CACHE[sym] = b[~b.index.duplicated(keep="first")]
    return _BARS_CACHE[sym]


def build_trades(sym, hold, fade, risk=H.RISK, max_contracts=H.MAX_CONTRACTS):
    b = full_bars(sym)
    close, vol = b["close"].values, b["vol"].values
    ret = np.diff(close, prepend=close[0]) / np.r_[close[0], close[:-1]]
    trail_vol = pd.Series(vol).rolling(TRAIL, min_periods=15).mean().shift(1).values
    trail_sd = pd.Series(ret).rolling(TRAIL, min_periods=15).std().shift(1).values
    spike = (vol >= VOL_MULT * trail_vol) & (np.sign(ret) != 0) & ~np.isnan(trail_sd) & (trail_sd > 0)
    idx = np.flatnonzero(spike)
    idx = idx[(idx > TRAIL) & (idx < len(close) - hold)]

    pv = H.PV[sym]
    dirs = -np.sign(ret[idx]) if fade else np.sign(ret[idx])
    entry, exitp = close[idx], close[idx + hold]
    sigma_dollars = trail_sd[idx] * entry * pv
    contracts = np.clip(np.round(risk / sigma_dollars), 1, max_contracts)
    gross = dirs * (exitp - entry) * pv * contracts
    cost = contracts * H.cost_per_contract(sym)
    pnl = gross - cost
    entry_ts, exit_ts = b.index[idx], b.index[idx + hold]
    return pd.DataFrame({"entry_ts": entry_ts, "exit_ts": exit_ts, "direction": dirs.astype(int),
                         "contracts": contracts.astype(int), "pnl": pnl, "cost": cost})


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for sym, cfg in CONFIGS.items():
            tr = build_trades(sym, cfg["hold"], cfg["fade"])
            print(f"{sym} ({'fade' if cfg['fade'] else 'continue'}, hold={cfg['hold']}): {len(tr)} trades")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym, cfg in CONFIGS.items():
        k = H.ledger_count() + 1
        tr = build_trades(sym, cfg["hold"], cfg["fade"])
        days = load_days_databento(sym)
        all_days = [d["tday"] for d in days]
        label = "fade" if cfg["fade"] else "continue"
        name = f"Volume-spike {label} (>=4x trailing 30-bar vol), {sym}, hold {cfg['hold']} bars, Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 177 (pre-registered, formalizing an exploratory volume-spike scan)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round177_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
