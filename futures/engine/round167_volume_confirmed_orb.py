"""
Round 167: "build a strategy from scratch." Round 166 showed combining
already-found small effects has a hard, computed ceiling (inverse-variance
reweighting: 0.048 -> 0.050 daily Sharpe; even a hypothetical 5th fully
independent same-quality signal would only reach ~0.054 via sqrt(N)). That
rules out portfolio construction as the path to the pass-speed gate. This
round instead builds a genuinely new SIGNAL, using a dimension nothing in
this ledger has used as a filter: real traded VOLUME (the "vol" column
already present in every 1-minute bar this repo has, from Rounds 147/148/
159/160's price-only breakout/level tests through the ICT/mean-reversion/
cross-asset/calendar families -- never once used to confirm or reject a
setup).

Checked IDEA_LEDGER.md first (k=225): Round 148's un-filtered breakouts
(round numbers, prior-day H/L, overnight H/L) found a REAL, small edge
above the random-walk baseline (36.0% break-and-hold vs 33.3% expected) --
real but too small after costs (net $0-18/trade, Sharpe 0.029 vs 0.29
needed). Round 147's opening-range level itself was never isolated as its
own breakout test (it appeared only as a level-FADE target, and lost).
Never tested: whether a breakout's real (not random-walk) probability of
continuing depends on how much genuine participation confirmed it --
a textbook technical-analysis claim (a breakout on light volume is more
likely a false move) that, unlike ICT/SMC concepts already tested here, is
mechanically checkable against something OTHER than price alone.

The strategy: Volume-Confirmed Opening Range Breakout (VCORB). Opening
range = first 15 minutes of RTH (09:30-09:45 ET). First 1-minute close
after 09:45 that breaks the range, WHOSE OWN BAR VOLUME is at least K times
the opening range's own average per-bar volume, triggers entry at that
close; stop at the opposite side of the range. Compared directly against
the SAME breakout rule with no volume filter (K effectively 0) -- an
ablation, not just a new rule in isolation, so the volume filter's own
marginal contribution is visible rather than blended into "yet another new
rule that may or may not work."

Step 0, honest before running: light-volume-breakouts-are-false is one of
the most repeated claims in retail technical analysis, so if it were a
clean exploitable rule on liquid index/metal futures, it would likely
already be priced in. Tested because it's mechanically different from
every price-only test in this ledger (it uses information -- participation
-- that ICT/SMC-style price patterns explicitly do not), not because prior
odds are good.

MNQ + MGC (both have full multi-year 1-minute-equivalent history via
`idea_harness.load_days`), first setup per day, $300 risk, real commission
+ 2-tick slippage, flat by 16:00 ET (Broker-legal). Grid: R-multiple in
{1, 2, 3, hold-to-close} x volume filter in {none (baseline), >=1.5x OR
avg, >=2.5x OR avg} = 12 variants.

12 variants. Ledger k=225 -> 237; OOS bar 1 - 0.01/237 at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H

OR_START, OR_END = dt.time(9, 30), dt.time(9, 45)
FLAT_TIME = dt.time(16, 0)

_DAYS_CACHE, _BARS_CACHE = {}, {}


def cached_days(sym):
    if sym not in _DAYS_CACHE:
        _DAYS_CACHE[sym] = H.load_days(sym)
    return _DAYS_CACHE[sym]


def cached_bars(sym):
    if sym not in _BARS_CACHE:
        _BARS_CACHE[sym] = H.bars_from_days(cached_days(sym), "all")
    return _BARS_CACHE[sym]


def orb_signals(days, symbol, vol_mult, rr):
    """vol_mult: minimum breakout-bar volume as a multiple of the opening
    range's own average bar volume (0 = no filter, take the first breakout
    regardless of volume). rr: R-multiple for the target, or None = hold to
    the session close (tp stays NaN, flat_time in resolve_bracket exits it)."""
    tick = H.TK[symbol]
    out = []
    for d in days:
        s = d["session"]
        t = s.index.time
        orw = s[(t >= OR_START) & (t < OR_END)]
        if orw.empty:
            continue
        or_hi, or_lo, avg_vol = orw["high"].max(), orw["low"].min(), orw["vol"].mean()
        if avg_vol <= 0 or or_hi <= or_lo:
            continue
        after = s[t >= OR_END]
        for ts, c, v in zip(after.index, after["close"].values, after["vol"].values):
            if c > or_hi and v >= vol_mult * avg_vol:
                dd, entry, sl = 1, c, or_lo - tick
            elif c < or_lo and v >= vol_mult * avg_vol:
                dd, entry, sl = -1, c, or_hi + tick
            else:
                continue
            tp = entry + dd * rr * abs(entry - sl) if rr is not None else np.nan
            out.append((ts, dd, entry, sl, tp))
            break
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(vol_mult, rr):
    parts = []
    for sym in ("MNQ", "MGC"):
        days = cached_days(sym)
        bars = cached_bars(sym)
        sig = orb_signals(days, sym, vol_mult, rr)
        tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = []
    for rr, rr_label in [(1.0, "1R"), (2.0, "2R"), (3.0, "3R"), (None, "hold-to-close")]:
        for vm, vm_label in [(0.0, "no filter"), (1.5, ">=1.5x OR-avg vol"), (2.5, ">=2.5x OR-avg vol")]:
            grid.append((rr, vm, f"VCORB {rr_label}, {vm_label}, MNQ+MGC"))

    if dry:
        for rr, vm, label in grid:
            tr = build_trades(vm, rr)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))

    rows = []
    for rr, vm, label in grid:
        k = H.ledger_count() + 1
        tr = build_trades(vm, rr)
        r = H.test_idea(label, tr, all_days_mnq_mgc, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round167_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
