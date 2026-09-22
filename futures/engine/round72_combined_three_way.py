"""
Round 72: combine TOD + VWAP-Z + Round 71's two-stage breakout into ONE portfolio
with a single SHARED daily cap (not three independent $3,000 caps that could
stack to $9,000 of combined daily risk) and shared one-position-at-a-time gating,
then run the real deadline Monte Carlo against the account's current true state.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import datetime as dt
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round19_random_entry import causal_atr15_lookup, attach_atr, generate_random_entries, build_stop_signals, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round70_breakout_momentum import build_breakout_signals
from round31_combined_portfolio import block_bootstrap

INIT_MULT, BE_TRIGGER, TRAIL_MULT_BREAKOUT = 0.75, 2.0, 4.0


def resolve_combined_shared_cap(sig_df, df1m, symbol, day_cap, max_hold_bars=390):
    """sig_df rows need: ts, direction, entry, risk, source ('tod'/'vwapz' use plain
    trailing-stop mechanics with trail_dist=TRAIL_ATR_MULT*init_dist and stop column;
    'breakout' uses the two-stage mechanic with an atr column instead of stop).
    ONE shared day_cum/day_halted state across all three sources -- the real
    combined-portfolio promise ("no day loses more than day_cap total"), not three
    independent caps stacking."""
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    cur_day = None; day_cum = 0.0; day_halted = False
    for r in sig_df.itertuples(index=False):
        r_day = pd.Timestamp(r.ts).date()
        if r_day != cur_day:
            cur_day = r_day; day_cum = 0.0; day_halted = False
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n or pos < next_free_pos or day_halted:
            continue
        # 30% margin on the halt threshold: known commission/slippage/contract-
        # rounding overshoot on both mechanics, verified empirically in Round 69/71
        if day_cum <= -(day_cap - r.risk * 1.3):
            day_halted = True
            continue

        entry = r.entry
        if r.source == "breakout":
            init_dist = INIT_MULT * r.atr
            if init_dist <= 0:
                continue
            trail_dist = TRAIL_MULT_BREAKOUT * r.atr
            contracts = max(1, int(r.risk // (init_dist * pv)))
            cur_stop = entry - init_dist if r.direction == 1 else entry + init_dist
            best = entry; trailing_active = False
            end_pos = min(pos + max_hold_bars, n - 1)
            exit_px = None; outcome = "timeout"; exit_i = end_pos
            for i in range(pos, end_pos + 1):
                bar_hi, bar_lo = hi[i], lo[i]
                if r.direction == 1:
                    if bar_lo <= cur_stop:
                        exit_px = cur_stop; outcome = "trail_stop" if trailing_active else "initial_stop"; exit_i = i; break
                    best = max(best, bar_hi); favorable = best - entry
                    if favorable >= BE_TRIGGER * init_dist:
                        trailing_active = True; cur_stop = max(cur_stop, entry, best - trail_dist)
                else:
                    if bar_hi >= cur_stop:
                        exit_px = cur_stop; outcome = "trail_stop" if trailing_active else "initial_stop"; exit_i = i; break
                    best = min(best, bar_lo); favorable = entry - best
                    if favorable >= BE_TRIGGER * init_dist:
                        trailing_active = True; cur_stop = min(cur_stop, entry, best + trail_dist)
        else:  # tod / vwapz: plain trailing-stop mechanic, sized against TRUE trail_dist (Round 69 fix)
            init_dist = abs(r.entry - r.stop)
            if init_dist <= 0:
                continue
            trail_dist = TRAIL_ATR_MULT * init_dist
            contracts = max(1, int(r.risk // (trail_dist * pv)))
            cur_stop = entry - trail_dist if r.direction == 1 else entry + trail_dist
            best = entry
            end_pos = min(pos + max_hold_bars, n - 1)
            exit_px = None; outcome = "timeout"; exit_i = end_pos
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
        move = (exit_px - entry) if r.direction == 1 else (entry - exit_px)
        commission = COMMISSION_RT * contracts
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, r.source, r.direction, r.risk, contracts, pnl, outcome))
        next_free_pos = exit_i + 1
        day_cum += pnl
        if day_cum <= -(day_cap - r.risk * 1.3):
            day_halted = True
    return pd.DataFrame(results, columns=["ts", "source", "direction", "risk", "contracts", "pnl", "outcome"])


if __name__ == "__main__":
    TOD_RISK, VWAPZ_RISK, BREAKOUT_RISK, DAY_CAP = 2100, 1500, 900, 3000.0

    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    _T2 = dt.time(13, 50); _CLOSE = dt.time(16, 0); SEED = 0
    raw = generate_random_entries(mnq_1m, SEED)
    sig_base = build_stop_signals(raw, atr15)
    t = sig_base["ts"].dt.time
    sig_tod = sig_base[(t >= _T2) & (t < _CLOSE)].copy()
    sig_tod["risk"] = TOD_RISK; sig_tod["source"] = "tod"; sig_tod["atr"] = np.nan

    sig_z = build_zscore_signals(mnq_z, atr15, 2.5).copy()
    sig_z["risk"] = VWAPZ_RISK; sig_z["source"] = "vwapz"; sig_z["atr"] = np.nan

    raw_bo = build_breakout_signals(mnq_1m, atr15, 15)[["ts", "direction", "entry"]]
    sig_bo = attach_atr(raw_bo, atr15)
    sig_bo = sig_bo[sig_bo["atr"] > 0].copy()
    sig_bo["risk"] = BREAKOUT_RISK; sig_bo["source"] = "breakout"; sig_bo["stop"] = np.nan

    combined = pd.concat([sig_tod, sig_z, sig_bo], ignore_index=True).sort_values("ts").reset_index(drop=True)
    print(f"raw combined signals: {len(combined)} (tod={len(sig_tod)} vwapz={len(sig_z)} breakout={len(sig_bo)})", flush=True)

    trades = resolve_combined_shared_cap(combined, mnq_1m, "MNQ", DAY_CAP)
    trades["date"] = pd.to_datetime(trades["ts"]).dt.date
    daily = trades.groupby("date")["pnl"].sum()
    print(f"accepted trades: {len(trades)}  by source: {trades['source'].value_counts().to_dict()}")
    print(f"n_days={len(daily)} total=${daily.sum():,.0f} ev/day=${daily.sum()/len(daily):,.2f} "
          f"worst_day=${daily.min():,.2f} worst_dd=${(daily.cumsum()-daily.cumsum().cummax()).min():,.2f}")
    print(f"pct losing days: {(daily<0).mean()*100:.1f}%  pct winning days: {(daily>0).mean()*100:.1f}%")

    daily.to_csv("round72_daily_pnl.csv")
    print("wrote round72_daily_pnl.csv")

    # --- deadline Monte Carlo, real current account state ---
    REAL_CURRENT_BALANCE = 247_937.86
    HWM = 250_877.88
    TRAILING_FLOOR = HWM - 10_000.0
    REAL_BUFFER = REAL_CURRENT_BALANCE - TRAILING_FLOOR
    REAL_TARGET_GAP = 265_000.0 - REAL_CURRENT_BALANCE
    N_EVAL_DAYS = 18  # recomputed from today 2026-09-22, see journal
    BLOCK_SIZE = 10
    N_MC_PATHS = 8000
    MC_SEED = 0

    rng = np.random.default_rng(MC_SEED)
    floor = REAL_CURRENT_BALANCE - REAL_BUFFER
    n_success = n_ruin = n_neither = 0
    for _ in range(N_MC_PATHS):
        path = block_bootstrap([daily], N_EVAL_DAYS, BLOCK_SIZE, rng)
        cum = np.cumsum(path)
        equity = REAL_CURRENT_BALANCE + cum
        trailing_breach = equity <= floor
        daily_breach = path <= -5000.0
        target_cross = np.argmax(cum >= REAL_TARGET_GAP) if (cum >= REAL_TARGET_GAP).any() else None
        ruin_idx = None
        if trailing_breach.any() or daily_breach.any():
            idx_t = int(np.argmax(trailing_breach)) if trailing_breach.any() else N_EVAL_DAYS
            idx_d = int(np.argmax(daily_breach)) if daily_breach.any() else N_EVAL_DAYS
            ruin_idx = min(idx_t, idx_d)
        if target_cross is not None and (ruin_idx is None or target_cross <= ruin_idx):
            n_success += 1
        elif ruin_idx is not None:
            n_ruin += 1
        else:
            n_neither += 1
    print(f"\nDEADLINE MONTE CARLO (N_EVAL_DAYS={N_EVAL_DAYS}, balance=${REAL_CURRENT_BALANCE:,.2f}, "
          f"buffer=${REAL_BUFFER:,.2f}, target_gap=${REAL_TARGET_GAP:,.2f}):")
    print(f"  P(success)={n_success/N_MC_PATHS:.1%}  P(ruin)={n_ruin/N_MC_PATHS:.1%}  P(neither)={n_neither/N_MC_PATHS:.1%}")
    print("\nDONE.")
