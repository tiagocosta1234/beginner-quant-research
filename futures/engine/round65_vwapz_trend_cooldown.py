"""
Round 65: VWAP-Z trend-day cooldown filter.

2026-09-21 finding (see TRADING_JOURNAL.md): a live-logic replay of VWAP-Z against
today's real data found the edge's realized losses were all normal-sized (-$685 to
-$832, well inside the historical avg loss of -$521 / max loss of -$970 -- the ATR
trail was doing its job) but today produced FIVE consecutive same-direction losing
entries and only one small winner, because the whole session was one persistent
~700-point trend with no mean-reversion for the edge to actually profit from. VWAP-Z's
real edge (avg win $1,167 vs avg loss -$521, top 5% of wins = 25% of gross profit,
Round 64 numbers) depends on catching an eventual reversal -- a pure trend day denies
it that upside while still paying the downside repeatedly.

This tests a simple, live-implementable fix: track consecutive same-direction losses
within a calendar day: after N in a row, halt ALL new VWAP-Z entries for the rest of
that day (reset at the next session). No change to entry logic, stop distance, or
trail -- purely a "stop digging" circuit breaker.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round19_random_entry import causal_atr15_lookup, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals


def resolve_trailing_sequential_cooldown(sig_df, df1m, symbol, risk_dollar, trail_mult,
                                          max_hold_bars=390, cooldown_n=None):
    """Same mechanics as round30b's resolve_trailing_sequential (one position at a
    time, real overlap skip) plus an optional same-day circuit breaker: once
    `cooldown_n` consecutive same-direction losses land within one calendar day, all
    further entries that day are skipped (counter resets at the next day). cooldown_n
    =None disables the breaker (identical output to resolve_trailing_sequential)."""
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    skipped_overlap = 0
    skipped_cooldown = 0
    cur_day = None
    streak_dir = 0
    streak_len = 0
    day_halted = False
    for r in sig_df.itertuples(index=False):
        r_day = pd.Timestamp(r.ts).date()
        if r_day != cur_day:
            cur_day = r_day
            streak_dir = 0
            streak_len = 0
            day_halted = False
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        if pos < next_free_pos:
            skipped_overlap += 1
            continue
        if cooldown_n is not None and day_halted:
            skipped_cooldown += 1
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        cur_stop = r.entry - trail_dist if r.direction == 1 else r.entry + trail_dist
        best = r.entry; exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = max(best, bar_hi); cur_stop = max(cur_stop, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = min(best, bar_lo); cur_stop = min(cur_stop, best + trail_dist)
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, risk_dollar, contracts, pnl, outcome))
        next_free_pos = exit_i + 1

        if cooldown_n is not None:
            if pnl <= 0 and r.direction == streak_dir:
                streak_len += 1
            elif pnl <= 0:
                streak_dir = r.direction
                streak_len = 1
            else:
                streak_dir = 0
                streak_len = 0
            if streak_len >= cooldown_n:
                day_halted = True

    out = pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "contracts", "pnl", "outcome"])
    return out, skipped_overlap, skipped_cooldown


if __name__ == "__main__":
    VWAPZ_RISK = 600
    mnq_1m = load_1m("../data/MNQ_CONTINUOUS.txt")
    atr15 = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    sig_z = build_zscore_signals(mnq_z, atr15, 2.5)

    print(f"MNQ: {len(mnq_1m)} bars {mnq_1m.index.min()} -> {mnq_1m.index.max()}", flush=True)
    print(f"raw VWAP-Z signals: {len(sig_z)}\n", flush=True)

    baseline, base_skip, _ = resolve_trailing_sequential_cooldown(sig_z, mnq_1m, "MNQ", VWAPZ_RISK, TRAIL_ATR_MULT, cooldown_n=None)
    wr_b = (baseline["pnl"] > 0).mean() * 100
    print(f"BASELINE (no cooldown): trades={len(baseline)} win_rate={wr_b:.1f}% "
          f"total_pnl=${baseline['pnl'].sum():,.0f} worst_trade=${baseline['pnl'].min():,.0f}")
    peak = baseline["pnl"].cumsum().cummax(); dd = baseline["pnl"].cumsum() - peak
    print(f"  worst equity drawdown=${dd.min():,.0f}\n")

    for N in (2, 3, 4, 5):
        tr, skip_ov, skip_cd = resolve_trailing_sequential_cooldown(
            sig_z, mnq_1m, "MNQ", VWAPZ_RISK, TRAIL_ATR_MULT, cooldown_n=N)
        wr = (tr["pnl"] > 0).mean() * 100
        peak = tr["pnl"].cumsum().cummax(); dd = tr["pnl"].cumsum() - peak
        avoided_signals = skip_cd
        print(f"cooldown_n={N}: trades={len(tr)} (vs {len(baseline)} baseline, "
              f"{avoided_signals} entries blocked by cooldown) win_rate={wr:.1f}% "
              f"total_pnl=${tr['pnl'].sum():,.0f} (baseline ${baseline['pnl'].sum():,.0f}) "
              f"worst_dd=${dd.min():,.0f} (baseline ${(baseline['pnl'].cumsum()-baseline['pnl'].cumsum().cummax()).min():,.0f})")

    # per-day PnL comparison: how many days does the cooldown actually change, and by how much
    print("\n--- day-level impact at cooldown_n=3 ---")
    tr3, _, _ = resolve_trailing_sequential_cooldown(sig_z, mnq_1m, "MNQ", VWAPZ_RISK, TRAIL_ATR_MULT, cooldown_n=3)
    base_daily = baseline.copy(); base_daily["date"] = pd.to_datetime(base_daily["ts"]).dt.date
    cd_daily = tr3.copy(); cd_daily["date"] = pd.to_datetime(cd_daily["ts"]).dt.date
    base_by_day = base_daily.groupby("date")["pnl"].sum()
    cd_by_day = cd_daily.groupby("date")["pnl"].sum()
    all_days = base_by_day.index.union(cd_by_day.index)
    base_by_day = base_by_day.reindex(all_days, fill_value=0)
    cd_by_day = cd_by_day.reindex(all_days, fill_value=0)
    delta = cd_by_day - base_by_day
    changed = delta[delta != 0]
    print(f"days changed: {len(changed)} of {len(all_days)}")
    print(f"days improved (cooldown helped): {(changed > 0).sum()}, total saved=${changed[changed>0].sum():,.2f}")
    print(f"days worsened (cooldown cost a would-be recovery): {(changed < 0).sum()}, total cost=${changed[changed<0].sum():,.2f}")
    worst_baseline_days = base_by_day.sort_values().head(10)
    print("\n10 worst baseline days and what cooldown_n=3 would have done:")
    for d, v in worst_baseline_days.items():
        print(f"  {d}: baseline=${v:,.2f}  with_cooldown=${cd_by_day.loc[d]:,.2f}")

    # today specifically
    today = pd.Timestamp("2026-09-21").date()
    print(f"\n--- 2026-09-21 specifically ---")
    print(f"baseline pnl today: ${base_by_day.get(today, 0):,.2f}")
    print(f"with cooldown_n=3 pnl today: ${cd_by_day.get(today, 0):,.2f}")
    today_trades_cd = tr3[pd.to_datetime(tr3['ts']).dt.date == today]
    print(today_trades_cd[["ts", "direction", "pnl", "outcome"]].to_string())

    print("\nDONE.")
