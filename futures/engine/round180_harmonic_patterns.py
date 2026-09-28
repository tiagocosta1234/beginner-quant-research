"""
Round 180: formalizing the `/watch`ed video (2026-09-28, neurotrader,
"Harmonic Pattern Recognition With Python", ODHlC9YuowY). A new idea class,
never tested in this ledger: XABCD harmonic patterns (Gartley, Bat,
Butterfly, Crab, Deep Crab, Cypher, Shark) -- geometric price patterns
defined by Fibonacci-derived ratios between four consecutive swings, found
via a directional-change/zigzag segmentation. Different in kind from every
other pattern tested here: OTE/FVG use a single retracement zone, ICT/PO3
use time-of-day structure, this uses ratios across FOUR chained swings.

Unlike most videos in this ledger, the source itself already ran a real
backtest (hourly BTC-USDT, 2018-2023) and reported an honest, weak result:
combining all 7 patterns across 7 sigma values gave a profit factor of
1.026 -- barely positive, and the author says so directly. Only the Shark
pattern was profitable at every sigma tested; tighter (more "authentic")
Fibonacci tolerances performed WORSE than looser ones, which the author
reads (correctly) as evidence against the specific ratios being what
matters. Tested here for the mechanism (multi-swing ratio matching), not
because the source material oversold it -- it didn't.

Mechanics (faithful to the video, standard published ratios used for the
6 patterns not shown on screen -- only Gartley's exact ratios were visible
[07:47]: XA->AB 0.618, AB->BC 0.382-0.886, BC->CD 1.13-1.618, XA->AD 0.786):
  1. Directional change: confirm a top/bottom once price retraces `sigma`
     from the running extreme since the last confirmed one.
  2. After a top/bottom (C) confirms, track the running opposite extreme
     bar-by-bar as a candidate D point. At each bar, compute the three
     ratios (XA->AB, AB->BC, BC->CD) and the overall XA->AD ratio using the
     last 4 confirmed swings (X, A, B, C) plus the candidate D.
  3. Compare against all 7 patterns' ideal ratios (log-ratio error, ranges
     scored 0 inside / distance*2 outside, matching the video's get_error).
     Best-matching pattern under the error threshold triggers an entry at
     that bar's close, direction opposite the D extreme (buy a confirmed
     low, sell a confirmed high).
  4. Exit at the close of the bar where the directional-change algorithm
     confirms the NEXT opposite extreme -- no fixed target or stop, exactly
     as shown; entries are non-overlapping by construction.

Data: hourly bars aggregated from the Databento 1-minute ES/NQ/GC/SI data
(continuous, not RTH-restricted -- testing the ratio hypothesis itself
first, the same way the video tested it on 24-hour BTC; Broker-legality
of a hold that can span the session close is a SEPARATE question to check
only if this shows anything worth trading). Position sized to $300 risk
against each instrument's own trailing 20-hour realized volatility (no
explicit stop is defined in the source; sizing to a volatility unit is
this repo's standard way to size open-ended, no-stop trades).

Step 0, honest before running: the source's own result was barely positive
overall (PF 1.026) on a different market (BTC) and a different, longer
history (2018-2023) than what's available here (2019-2026). A weak result
somewhere else is not evidence for a strong result here -- tested because
the mechanism is new to this ledger, not because the video's own number was
compelling.

Sigma in {0.01, 0.02, 0.03} (the video's own most-tested range, not
cherry-picked), error threshold 0.2 (the video's stated default), all 7
patterns combined into one signal per instrument (matches the video's
primary "combined" approach, avoiding the multiple-comparison risk of
picking whichever single pattern looks best after the fact).

Changed after the dry-run, before any result was seen (counts only, not
performance -- the same "hand-check before the real run" step every round
in this ledger uses): per-(symbol, sigma) sample sizes were far too thin
to test at all (1 to 76 trades over 7 years; several cells single-digit).
Pooled all 3 sigma values into ONE combined sample per symbol instead of
12 separate cells -- matching the video's own stated preference for
combining across scales rather than picking one, and turning an untestable
design into a real one (32-113 trades per symbol instead of 1-31 per
sigma-cell).

4 symbols (sigma pooled). Ledger k=292 -> 296; OOS bar 1 - 0.01/296 at the
last variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento

ERROR_THRESHOLD = 0.2
SIGMAS = [0.01, 0.02, 0.03]

# ratio1 = |AB|/|XA|, ratio2 = |BC|/|AB|, ratio3 = |CD|/|BC|, ratio4 = |AD|/|XA|
# float = exact target; [lo, hi] = acceptable range; None = ignored.
# Gartley's values are screen-confirmed [07:47]; the rest are the standard
# published harmonic-pattern ratio table (Carney), not independently
# re-derived from the video's own (unseen) source for those six.
PATTERNS = {
    "Gartley":   (0.618,          [0.382, 0.886], [1.13, 1.618], 0.786),
    "Bat":       ([0.382, 0.50],  [0.382, 0.886], [1.618, 2.618], 0.886),
    "Butterfly": (0.786,          [0.382, 0.886], [1.618, 2.24],  [1.27, 1.618]),
    "Crab":      ([0.382, 0.618], [0.382, 0.886], [2.24, 3.618],  1.618),
    "DeepCrab":  (0.886,          [0.382, 0.886], [2.0, 3.618],   1.618),
    "Cypher":    ([0.382, 0.618], [1.13, 1.414],  [1.272, 2.0],   0.786),
    "Shark":     (None,           [1.13, 1.618],  [1.618, 2.24],  [0.886, 1.13]),
}


def hourly_bars(sym):
    days = load_days_databento(sym)
    b = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    h = b.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
    return h


def zigzag(close, sigma):
    """Returns arrays: confirmed_idx (bar index where confirmed), extreme_idx
    (bar index of the actual extreme), price, kind (+1 top, -1 bottom)."""
    n = len(close)
    out = []
    up_zig = True  # arbitrary start; first leg is provisional until a real move confirms
    last_extreme_i, last_extreme_p = 0, close[0]
    run_i, run_p = 0, close[0]
    for i in range(1, n):
        p = close[i]
        if up_zig:
            if p > run_p:
                run_i, run_p = i, p
            elif p <= run_p * (1 - sigma):
                out.append((i, run_i, run_p, 1))
                last_extreme_i, last_extreme_p = run_i, run_p
                up_zig = False
                run_i, run_p = i, p
        else:
            if p < run_p:
                run_i, run_p = i, p
            elif p >= run_p * (1 + sigma):
                out.append((i, run_i, run_p, -1))
                last_extreme_i, last_extreme_p = run_i, run_p
                up_zig = True
                run_i, run_p = i, p
    return out


def log_err(obs, ideal):
    if ideal is None:
        return 0.0
    lobs = np.log(obs)
    if isinstance(ideal, (list, tuple)):
        lo, hi = np.log(ideal[0]), np.log(ideal[1])
        if lo <= lobs <= hi:
            return 0.0
        return 2 * (lo - lobs if lobs < lo else lobs - hi)
    return abs(lobs - np.log(ideal))


def find_signals_with_x(bars, sigma, err_thresh):
    """Returns the pattern's own X price alongside each signal, so the
    |entry-X| DISTANCE can be used as the risk magnitude for a real stop
    (the textbook invalidation distance for these patterns) instead of a
    volatility-window proxy that doesn't account for how long a trade might
    actually stay open. X's own price can fall on either side of the entry
    for deep-retracement patterns (D past X), so only the distance is used
    here -- the stop itself is placed on the correct (losing) side in
    build_trades, not literally at X's price level."""
    close, high, low = bars["close"].values, bars["high"].values, bars["low"].values
    zz = zigzag(close, sigma)
    out = []
    for zi in range(3, len(zz)):
        conf_i, ext_i, ext_p, kind = zz[zi]
        cX, cA, cB = zz[zi - 3][2], zz[zi - 2][2], zz[zi - 1][2]
        xa, ab, bc = abs(cA - cX), abs(cB - cA), abs(ext_p - cB)
        if xa == 0 or ab == 0 or bc == 0:
            continue
        c_conf_i = conf_i
        next_conf_i = zz[zi + 1][0] if zi + 1 < len(zz) else len(close)
        want_low = kind == 1
        run_extreme = ext_p
        for j in range(c_conf_i, min(next_conf_i, len(close))):
            px = low[j] if want_low else high[j]
            run_extreme = min(run_extreme, px) if want_low else max(run_extreme, px)
            cd = abs(run_extreme - cB)
            ad = abs(run_extreme - cA)
            if cd == 0 or ad == 0:
                continue
            r1, r2, r3, r4 = ab / xa, bc / ab, cd / bc, ad / xa
            local_best = None
            for name, (i1, i2, i3, i4) in PATTERNS.items():
                if name == "Shark" and i1 is None:
                    e = log_err(r2, i2) + log_err(r3, i3) + log_err(r4, i4)
                else:
                    e = log_err(r1, i1) + log_err(r2, i2) + log_err(r3, i3) + log_err(r4, i4)
                if local_best is None or e < local_best[0]:
                    local_best = (e, name)
            if local_best[0] <= err_thresh:
                direction = 1 if want_low else -1
                out.append((j, direction, cX))
                break
    return out


def build_trades(sym, sigma, err_thresh=ERROR_THRESHOLD, risk=H.RISK, max_contracts=H.MAX_CONTRACTS):
    bars = hourly_bars(sym)
    close, high, low = bars["close"].values, bars["high"].values, bars["low"].values
    sigs = find_signals_with_x(bars, sigma, err_thresh)
    pv = H.PV[sym]
    trades = []
    for j, direction, x_price in sigs:
        entry = close[j]
        stop_dist = abs(entry - x_price)
        if stop_dist == 0:
            continue
        # the stop must sit on the LOSING side of entry, using |entry-X| only
        # as the risk magnitude -- X's own price can be on either side of D
        # for deep-retracement patterns (Crab, Deep Crab, Butterfly), so
        # placing the stop literally at X's price was backwards for those
        # (it fell on the winning side and triggered as a near-guaranteed
        # profitable exit on the very next bar -- caught by inspecting real
        # trades before trusting the first corrected run's results).
        stop_price = entry - direction * stop_dist
        zz_tail = zigzag(close[j:], sigma)
        exit_off = None
        for conf_i, ext_i, ext_p, kind in zz_tail:
            if (direction == 1 and kind == 1) or (direction == -1 and kind == -1):
                exit_off = conf_i
                break
        target_exit_j = j + exit_off if exit_off is not None else len(close) - 1
        # walk forward bar-by-bar: exit at the stop if hit first, otherwise at
        # the zigzag-confirmed opposite extreme, exactly as the video does
        # when the stop is never touched.
        exit_j, exit_price, stopped = target_exit_j, close[target_exit_j], False
        for i in range(j + 1, target_exit_j + 1):
            if (direction == 1 and low[i] <= stop_price) or (direction == -1 and high[i] >= stop_price):
                exit_j, exit_price, stopped = i, stop_price, True
                break
        contracts = int(np.clip(round(risk / (stop_dist * pv)), 1, max_contracts))
        gross = direction * (exit_price - entry) * pv * contracts
        cost = contracts * H.cost_per_contract(sym)
        trades.append((bars.index[j], bars.index[exit_j], direction, contracts, gross - cost, stopped))
    return pd.DataFrame(trades, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "stopped"]), bars


def build_trades_pooled(sym):
    parts, bars_ref = [], None
    for sigma in SIGMAS:
        tr, bars = build_trades(sym, sigma)
        parts.append(tr)
        bars_ref = bars
    return pd.concat(parts, ignore_index=True).sort_values("entry_ts").reset_index(drop=True), bars_ref


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for sym in ("ES", "NQ", "GC", "SI"):
            tr, bars = build_trades_pooled(sym)
            print(f"{sym} sigma-pooled {SIGMAS}: {len(tr)} trades, {bars.index.min()} -> {bars.index.max()}")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym in ("ES", "NQ", "GC", "SI"):
        k = H.ledger_count() + 1
        tr, bars = build_trades_pooled(sym)
        all_days = sorted(set(bars.index.normalize()))
        name = f"Harmonic XABCD patterns (7 combined, sigma pooled {SIGMAS}), {sym}, hourly Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 180 (pre-registered, formalizing a /watched video: harmonic XABCD patterns)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round180_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
