"""
Round 20: does a REAL entry beat Round 19's random-entry baseline, holding the exit
fixed at Round 19's validated ATR-trailing style? MNQ only (MGC's base effect from
Round 19 didn't replicate, so not retested here).

Round 19 found: random entries (zero skill) + ATR trailing stop (1.5x ATR(14@15m),
no fixed target) beat costs on 8/8 seeds -- mean +$66.27/trade @$400 risk (+$103.31
@$600), tail10/20 = 11.9%/21.5% (21.6% @$600), but worst single-fold drawdown
$10,404-$16,053, 2-3x this account's real $4,937.50 buffer.

This round pairs that SAME exit mechanism (imported unchanged from
round19_random_entry.resolve_trailing) with two deterministic (non-random) entries:

  Entry 1: Round 18's Level B -- base confirmation-candle FVG entry (0.60 body-ratio,
           0.0 beyond-zone-edge, round13's confirmed_entries_v2) + weekly-open bias
           filter (round17's apply_weekly_bias_filter). This was Round 18's simplest
           fixed-parameter stack (not the per-fold grid-searched Level C/D, to keep
           the entry identical across all folds -- grid-searching the entry AND
           swapping the exit simultaneously would confound this comparison).
  Entry 2: a deliberately simple, distinct 1H-EMA(20)-slope trend entry, one per day
           at a fixed daily decision time, no other filter -- direction = sign of the
           EMA's change over the prior 3 completed 1H bars, causal throughout.

Both entries' own stop columns are DISCARDED and replaced with Round 19's ATR-based
stop (1.0x ATR(14@15m)), so the exit mechanism is byte-for-byte identical to Round 19's
-- this isolates entry-timing skill as the only variable, which is the whole point.

Part 2: since real entries are deterministic (no seed distribution needed, unlike
random entries), whichever entry wins Part 1 is then re-run at progressively smaller
risk levels to find the smallest position size whose worst-fold maxdd clears the real
$4,937.50 buffer with real margin (target: worst maxdd <= 70% of buffer, i.e. <=$3,456,
not cut to the wire), and that risk level's expectancy/trade is reported against the
$767-1,279/trade pace Round 18's Campaign Synthesis established as what's actually
needed before the October deadline.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, detect_fvgs, POINT_VALUE, TICK_SIZE,
    COMMISSION_RT, BUFFER, FOLDS, one_per_day, fold_stats, tail_concentration,
)
from round13_fvg_refinements import confirmed_entries_v2
from round17_prior_ref import weekly_open_series, apply_weekly_bias_filter
from round19_random_entry import (
    causal_atr15_lookup, attach_atr, resolve_trailing, walk_forward_fixed,
    STOP_ATR_MULT, TRAIL_ATR_MULT,
)

SYMBOL = "MNQ"
RISK_LEVELS = (400, 600)
DAILY_DECISION_TIME = "10:00"  # local exchange time already implied by the data's own tz


def build_atr_stop_signals(entries_ts_dir, atr_series):
    """entries_ts_dir: DataFrame with at least [ts, direction, entry]. Discards any
    existing 'stop' column and attaches Round 19's ATR-based stop instead, so the exit
    mechanism downstream is identical to Round 19's for a fair comparison."""
    base = entries_ts_dir[["ts", "direction", "entry"]].copy()
    s = attach_atr(base, atr_series)
    s = s[s["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * s["atr"]
    s["stop"] = np.where(s["direction"] == 1, s["entry"] - stop_dist, s["entry"] + stop_dist)
    return s[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def build_ema_trend_entries(df1m):
    """One entry/day at DAILY_DECISION_TIME, direction = sign of causal 1H EMA(20)'s
    change over the prior 3 completed 1H bars. No other filter, deliberately simple."""
    h1 = resample_causal(df1m, "60min")
    ema = h1["close"].ewm(span=20, adjust=False).mean()
    slope = ema - ema.shift(3)

    dates = pd.Series(df1m.index.date, index=df1m.index)
    rows = []
    for day, day_idx in df1m.groupby(dates).groups.items():
        day_bars = df1m.loc[day_idx]
        target_time = pd.Timestamp.combine(day, pd.Timestamp(DAILY_DECISION_TIME).time())
        candidates = day_bars.index[day_bars.index >= target_time]
        if len(candidates) == 0:
            continue
        entry_ts = candidates[0]
        pos = np.searchsorted(slope.index.values, np.datetime64(entry_ts), side="right") - 1
        if pos < 0:
            continue
        s = slope.iloc[pos]
        if pd.isna(s) or s == 0:
            continue
        direction = 1 if s > 0 else -1
        entry_px = df1m.loc[entry_ts, "close"]
        rows.append((entry_ts, direction, entry_px))
    return pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)


def run_entry(label, sig_df, df1m, symbol, risk_levels=RISK_LEVELS):
    print(f"\n=== {label}: {len(sig_df)} entries ===", flush=True)
    results = {}
    for risk in risk_levels:
        res = walk_forward_fixed(sig_df, df1m, symbol, resolve_trailing, {"trail_mult": TRAIL_ATR_MULT},
                                  risk_levels=(risk,))[risk]
        all_trades = []
        fold_breaches = []
        for train_end, test_end, _sel, te in res:
            if te is None or len(te) == 0:
                print(f"  {train_end}->{test_end}: no trades", flush=True)
                continue
            st = fold_stats(te)
            print(f"  {train_end}->{test_end} n={st['n']} win%={st['winrate']:.1%} "
                  f"exp=${st['expectancy']:.2f} total=${st['total']:.2f} maxdd=${st['maxdd']:.2f} "
                  f"breach={st['breach']}", flush=True)
            all_trades.append(te)
            fold_breaches.append((train_end, test_end, st["maxdd"], st["breach"]))
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            n_breach = sum(1 for f in fold_breaches if f[3])
            worst = max(fold_breaches, key=lambda x: x[2])
            out = dict(n=len(combo), exp=combo["pnl"].mean(), total=combo["pnl"].sum(),
                       winrate=(combo["pnl"] > 0).mean(), n_breach=n_breach, n_folds=len(fold_breaches),
                       worst_maxdd=worst[2], worst_fold=(worst[0], worst[1]))
            if combo["pnl"].sum() > 0:
                out["tail10"] = tail_concentration(combo, 10)
                out["tail20"] = tail_concentration(combo, 20)
            print(f"  AGGREGATE risk=${risk} n={out['n']} exp=${out['exp']:.2f} total=${out['total']:.2f} "
                  f"win%={out['winrate']:.1%} folds_breaching={out['n_breach']}/{out['n_folds']} "
                  f"worst_maxdd=${out['worst_maxdd']:.2f} " +
                  (f"tail10={out.get('tail10'):.1f}% tail20={out.get('tail20'):.1f}%"
                   if "tail10" in out else "(no tail check: aggregate not positive)"), flush=True)
            results[risk] = out
        else:
            results[risk] = None
    return results


def find_buffer_safe_risk(sig_df, df1m, symbol, candidate_risks, margin_frac=0.70):
    """Re-run resolve_trailing at progressively smaller risk levels; return the largest
    one whose worst-fold maxdd stays within margin_frac * BUFFER (real margin, not cut
    to the wire)."""
    target = margin_frac * BUFFER
    print(f"\n=== Buffer-safe sizing search (target worst maxdd <= ${target:.2f} = "
          f"{margin_frac:.0%} of ${BUFFER:.2f} buffer) ===", flush=True)
    best = None
    for risk in candidate_risks:
        res = walk_forward_fixed(sig_df, df1m, symbol, resolve_trailing, {"trail_mult": TRAIL_ATR_MULT},
                                  risk_levels=(risk,))[risk]
        all_trades = []
        worst_dd = 0.0
        for train_end, test_end, _sel, te in res:
            if te is None or len(te) == 0:
                continue
            st = fold_stats(te)
            worst_dd = max(worst_dd, st["maxdd"])
            all_trades.append(te)
        if not all_trades:
            print(f"  risk=${risk}: no trades", flush=True)
            continue
        combo = pd.concat(all_trades, ignore_index=True)
        exp = combo["pnl"].mean()
        ok = worst_dd <= target
        print(f"  risk=${risk}: n={len(combo)} exp=${exp:.2f} worst_maxdd=${worst_dd:.2f} "
              f"within_target={ok}", flush=True)
        if ok and (best is None or risk > best[0]):
            best = (risk, exp, worst_dd, len(combo))
    return best


def main():
    print(f"Loading {SYMBOL}...", flush=True)
    df1m = load_1m(os.path.join(os.path.dirname(__file__), "..", "data", f"{SYMBOL}_CONTINUOUS.txt"))
    print(f"{SYMBOL}: {len(df1m)} 1m bars, {df1m.index[0]} -> {df1m.index[-1]}", flush=True)

    atr15 = causal_atr15_lookup(df1m)

    # --- Entry 1: Round 18 Level B (base FVG confirmation + weekly-bias filter) ---
    htf = resample_causal(df1m, "15min")
    fvgs = detect_fvgs(htf)
    sig_fvg = confirmed_entries_v2(fvgs, df1m, 0.60, 0.0, SYMBOL, tight_stop=False)
    sig_fvg = one_per_day(sig_fvg)
    week_open = weekly_open_series(df1m)
    sig_fvg_biased = apply_weekly_bias_filter(sig_fvg, df1m, week_open)
    entry1 = build_atr_stop_signals(sig_fvg_biased, atr15)
    print(f"Entry 1 (FVG-confirm + weekly-bias): {len(sig_fvg_biased)} raw -> {len(entry1)} with valid ATR stop",
          flush=True)

    # --- Entry 2: simple 1H EMA-slope trend, one per day ---
    raw_ema = build_ema_trend_entries(df1m)
    entry2 = build_atr_stop_signals(raw_ema, atr15)
    print(f"Entry 2 (1H EMA slope): {len(raw_ema)} raw -> {len(entry2)} with valid ATR stop", flush=True)

    results_1 = run_entry("ENTRY 1: FVG-confirmation + weekly-bias (Round 18 Level B) + ATR-trailing exit",
                           entry1, df1m, SYMBOL)
    results_2 = run_entry("ENTRY 2: 1H EMA-slope trend (simple) + ATR-trailing exit",
                           entry2, df1m, SYMBOL)

    print("\n\n### PART 1 SUMMARY: real entries vs Round 19's random-entry baseline ###", flush=True)
    print("Round 19 random baseline (8-seed mean): risk=$400 exp=$66.27 std=$21.15 tail10=11.9% tail20=21.5% "
          "worst_maxdd~$10,404-16,053 (range across seeds/folds)", flush=True)
    print("Round 19 random baseline (8-seed mean): risk=$600 exp=$103.31 tail10=12.0% tail20=21.6%", flush=True)
    for label, res in [("Entry 1 (FVG+weekly-bias)", results_1), ("Entry 2 (1H EMA slope)", results_2)]:
        for risk in RISK_LEVELS:
            r = res.get(risk)
            if r:
                print(f"  {label} risk=${risk}: n={r['n']} exp=${r['exp']:.2f} win%={r['winrate']:.1%} "
                      f"worst_maxdd=${r['worst_maxdd']:.2f} folds_breaching={r['n_breach']}/{r['n_folds']}", flush=True)
            else:
                print(f"  {label} risk=${risk}: no trades", flush=True)

    # --- Part 2: buffer-safe sizing on whichever performed better (or random if neither beats it) ---
    best_label, best_sig, best_exp_400 = None, None, -1e18
    for label, sig, res in [("Entry 1 (FVG+weekly-bias)", entry1, results_1),
                             ("Entry 2 (1H EMA slope)", entry2, results_2)]:
        r = res.get(400)
        if r and r["exp"] > best_exp_400:
            best_exp_400, best_label, best_sig = r["exp"], label, sig

    print(f"\n\n### PART 2: buffer-safe sizing for best-performing config: {best_label} "
          f"(exp@$400=${best_exp_400:.2f}) ###", flush=True)
    if best_exp_400 <= 0:
        print("Best real-entry config is non-positive at $400 risk -- buffer-safe sizing search skipped; "
              "Round 19's random-entry baseline remains the only positive candidate found this campaign, "
              "and its own buffer-safe sizing (if wanted) would need the same treatment applied to a random "
              "signal set instead.", flush=True)
    else:
        candidates = [400, 300, 250, 200, 150, 125, 100, 75, 50]
        best = find_buffer_safe_risk(best_sig, df1m, SYMBOL, candidates)
        if best:
            risk, exp, worst_dd, n = best
            required_low, required_high = 767, 1279
            frac_low = exp / required_low * 100
            frac_high = exp / required_high * 100
            print(f"\nBuffer-safe size: risk=${risk}/trade, n={n} trades over 2024-01->2026-09, "
                  f"exp=${exp:.2f}/trade, worst_maxdd=${worst_dd:.2f} (within 70% margin of ${BUFFER:.2f} buffer)",
                  flush=True)
            print(f"Required pace (Round 18 Campaign Synthesis): $767-1,279/trade to close the account gap "
                  f"before the October deadline at 1 trade/day.", flush=True)
            print(f"This buffer-safe, validated result closes {frac_low:.1f}%-{frac_high:.1f}% of that "
                  f"required pace.", flush=True)
        else:
            print("No candidate risk level found whose worst-fold maxdd clears the buffer-safe target even "
                  "at very small size -- worth noting explicitly rather than silently failing.", flush=True)

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
