"""
Round 15: pure time-of-day / day-of-week directional drift, no price-structure trigger
at all. Every prior round (1-14) required SOME price condition (breakout, gap, zone
reaction, statistical extreme) to fire a signal. This tests the simplest possible
hypothesis instead: does MNQ/MGC have an unconditional directional tendency at a
specific time-of-day window or day-of-week, tradeable with a fixed stop/target and no
setup at all beyond "enter at time X"?

This category is unusually prone to multiple-comparisons false positives (many windows
scanned per fold). Handling, explicit:
  1. Per fold, rank candidate windows/days by TRAIN-only expectancy (never touches test).
  2. Apply the SAME top-1 (and, as a secondary check, top-3 tested individually) window
     unchanged to that fold's OOS data -- identical walk-forward discipline to every
     prior round.
  3. Cross-fold persistence check: record which window/day was training-rank-1 in each
     of the 6 folds. A real effect should recur; if the "best" window is different
     (and unrelated) almost every fold, that is itself evidence of noise, reported
     explicitly alongside the OOS numbers rather than left implicit.
  4. Full tail-concentration check on any config with positive aggregate OOS profit,
     same standard as every prior round, no exception for this category despite (or
     because of) its data-mined nature.

Causal throughout: a fold's "best window" is selected using only that fold's training
slice; the 15m ATR used for stop sizing at any entry time only uses 15m bars whose
close is strictly before the entry time (via resample_causal's right-closed/right-
labeled convention, reused unchanged from Round 11).
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS,
    fold_stats, tail_concentration,
)
from round14_meanreversion import atr_causal

ATR_MULT = 1.0
ATR_PERIOD = 14
BUCKET_MIN = 30          # time-of-day bucket width
RR_GRID = (1.5, 2.0)
RISK_LEVELS = (400, 600)
MIN_SIGNALS = 30         # per-fold OOS floor below which a fold is reported as "insufficient", not zero
MIN_TRAIN_PER_BUCKET = 15  # a bucket needs >= this many training-set occurrences to be ranked at all


def session_bucket_of_day(ts_index):
    """Minutes since local midnight of each timestamp, then floor to BUCKET_MIN chunks.
    Data is stored as naive local session time already (per load_1m / prior rounds'
    convention), so this is just wall-clock time-of-day, no timezone conversion needed."""
    minutes = ts_index.hour * 60 + ts_index.minute
    return (minutes // BUCKET_MIN) * BUCKET_MIN


def build_daily_bucket_table(df1m):
    """One row per (date, bucket) = the first 1m bar at/after the bucket's start each
    day. This IS the unconditional daily signal set (before any direction/ranking is
    applied) -- literally 'every day, at this time, in this direction.'"""
    idx = df1m.index
    bucket = session_bucket_of_day(idx)
    date = idx.normalize()
    tmp = pd.DataFrame({"ts": idx, "date": date, "bucket": bucket, "open": df1m["open"].values})
    # first bar of each (date, bucket) pair = the bar that "starts" that bucket-window that day
    first = tmp.sort_values("ts").groupby(["date", "bucket"], as_index=False).first()
    return first  # columns: date, bucket, ts, open


def resolve_fixed_window(entries, df1m, symbol, rr, risk_dollar, atr15, window_end_minutes):
    """entries: DataFrame[ts, direction] (direction already chosen per bucket).
    Stop = ATR_MULT * most-recently-closed 15m ATR as of ts. Target = rr*stop.
    Walk forward bar-by-bar from entry to the bucket's window-end time that SAME day
    (flatten at window end if neither stop nor target hit -- a real fixed-holding-period
    exit, not a free timeout)."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts_arr = df1m.index.values
    open_arr = df1m["open"].values
    hi = df1m["high"].values
    lo = df1m["low"].values
    close = df1m["close"].values
    n = len(df1m)
    atr_ts = atr15.index.values
    atr_vals = atr15.values
    results = []
    for r in entries.itertuples(index=False):
        pos = np.searchsorted(ts_arr, np.datetime64(r.ts), side="left")
        if pos >= n or ts_arr[pos] != np.datetime64(r.ts):
            continue
        # most recently CLOSED 15m bar strictly before entry ts
        a_pos = np.searchsorted(atr_ts, np.datetime64(r.ts), side="left") - 1
        if a_pos < 0 or a_pos >= len(atr_vals) or np.isnan(atr_vals[a_pos]) or atr_vals[a_pos] <= 0:
            continue
        stop_dist = atr_vals[a_pos] * ATR_MULT
        entry_px = open_arr[pos]
        target_dist = rr * stop_dist
        day = pd.Timestamp(r.ts).normalize()
        window_end_ts = day + pd.Timedelta(minutes=window_end_minutes)
        end_pos = np.searchsorted(ts_arr, np.datetime64(window_end_ts), side="right")
        end_pos = min(end_pos, n)
        if end_pos <= pos + 1:
            continue
        seg_hi = hi[pos + 1:end_pos]
        seg_lo = lo[pos + 1:end_pos]
        if r.direction == 1:
            stop_px = entry_px - stop_dist
            target_px = entry_px + target_dist
            hit_stop = seg_lo <= stop_px
            hit_target = seg_hi >= target_px
        else:
            stop_px = entry_px + stop_dist
            target_px = entry_px - target_dist
            hit_stop = seg_hi >= stop_px
            hit_target = seg_lo <= target_px
        first_stop = np.argmax(hit_stop) if hit_stop.any() else len(seg_hi)
        first_target = np.argmax(hit_target) if hit_target.any() else len(seg_hi)
        contracts = max(1, int(risk_dollar // (stop_dist * pv)))
        commission = COMMISSION_RT * contracts
        if first_stop == len(seg_hi) and first_target == len(seg_hi):
            exit_px = close[end_pos - 1]
            pnl = (exit_px - entry_px) * r.direction * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "flatten"
        elif first_target <= first_stop:
            pnl = target_dist * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "target"
        else:
            pnl = -stop_dist * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "stop"
        results.append((r.ts, symbol, r.direction, rr, risk_dollar, contracts, pnl, outcome))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts", "pnl", "outcome"])


def rank_buckets_on_train(daily_table, train_end, atr15, df1m, symbol, window_end_minutes):
    """Quick screen (fixed rr=1.5, $400 risk) of every (bucket, direction) using only
    ts < train_end. Returns a DataFrame sorted best-first: bucket, direction, n, exp."""
    train = daily_table[daily_table["ts"] < train_end]
    rows = []
    for bucket, grp in train.groupby("bucket"):
        if len(grp) < MIN_TRAIN_PER_BUCKET:
            continue
        for direction in (1, -1):
            ent = pd.DataFrame({"ts": grp["ts"].values, "direction": direction})
            tr = resolve_fixed_window(ent, df1m, symbol, 1.5, 400, atr15, window_end_minutes)
            if len(tr) < MIN_TRAIN_PER_BUCKET // 2:
                continue
            rows.append((bucket, direction, len(tr), tr["pnl"].mean()))
    if not rows:
        return pd.DataFrame(columns=["bucket", "direction", "n", "exp"])
    out = pd.DataFrame(rows, columns=["bucket", "direction", "n", "exp"]).sort_values("exp", ascending=False)
    return out.reset_index(drop=True)


def walk_forward_bucket(rank_key, daily_table, df1m, symbol, atr15, window_end_minutes):
    bucket, direction = rank_key
    sub = daily_table[daily_table["bucket"] == bucket]
    entries = pd.DataFrame({"ts": sub["ts"].values, "direction": direction})
    out = {}
    for risk in RISK_LEVELS:
        fold_rows = []
        for train_end, test_end in FOLDS:
            test_entries = entries[(entries["ts"] >= train_end) & (entries["ts"] < test_end)]
            if len(test_entries) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            train_entries = entries[entries["ts"] < train_end]
            best_rr, best_exp = None, -1e18
            for rr in RR_GRID:
                tr = resolve_fixed_window(train_entries, df1m, symbol, rr, risk, atr15, window_end_minutes)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_rr = exp, rr
            if best_rr is None:
                best_rr = 1.5
            te = resolve_fixed_window(test_entries, df1m, symbol, best_rr, risk, atr15, window_end_minutes)
            fold_rows.append((train_end, test_end, best_rr, te))
        out[risk] = fold_rows
    return out


def print_fold_results(label, res):
    for risk, fold_rows in res.items():
        print(f"-- {label} risk=${risk} --", flush=True)
        all_trades = []
        for train_end, test_end, rr, te in fold_rows:
            if te is None or len(te) == 0:
                print(f"  {train_end}->{test_end}: no OOS signals", flush=True)
                continue
            st = fold_stats(te)
            print(f"  {train_end}->{test_end} rr={rr} n={st['n']} win%={st['winrate']:.1%} "
                  f"exp=${st['expectancy']:.2f} total=${st['total']:.2f} maxdd=${st['maxdd']:.2f} "
                  f"breach={st['breach']}", flush=True)
            all_trades.append(te)
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            tc10 = tail_concentration(combo, 10)
            tc20 = tail_concentration(combo, 20)
            print(f"  AGGREGATE n={len(combo)} total=${combo['pnl'].sum():.2f} "
                  f"exp=${combo['pnl'].mean():.2f} win%={(combo['pnl']>0).mean():.1%} "
                  f"tail10={tc10} tail20={tc20}", flush=True)
        else:
            print("  AGGREGATE: no OOS trades across any fold", flush=True)


# ---------------- day-of-week (full-session) ----------------

def build_daily_first_bar(df1m):
    idx = df1m.index
    date = idx.normalize()
    tmp = pd.DataFrame({"ts": idx, "date": date, "open": df1m["open"].values})
    first = tmp.sort_values("ts").groupby("date", as_index=False).first()
    first["dow"] = pd.to_datetime(first["date"]).dt.dayofweek  # 0=Mon .. 6=Sun
    return first


def rank_dow_on_train(daily_first, train_end, atr15, df1m, symbol, window_end_minutes):
    train = daily_first[daily_first["ts"] < train_end]
    rows = []
    for dow, grp in train.groupby("dow"):
        if len(grp) < MIN_TRAIN_PER_BUCKET:
            continue
        for direction in (1, -1):
            ent = pd.DataFrame({"ts": grp["ts"].values, "direction": direction})
            tr = resolve_fixed_window(ent, df1m, symbol, 1.5, 400, atr15, window_end_minutes)
            if len(tr) < MIN_TRAIN_PER_BUCKET // 2:
                continue
            rows.append((dow, direction, len(tr), tr["pnl"].mean()))
    if not rows:
        return pd.DataFrame(columns=["dow", "direction", "n", "exp"])
    out = pd.DataFrame(rows, columns=["dow", "direction", "n", "exp"]).sort_values("exp", ascending=False)
    return out.reset_index(drop=True)


def walk_forward_dow(rank_key, daily_first, df1m, symbol, atr15, window_end_minutes):
    dow, direction = rank_key
    sub = daily_first[daily_first["dow"] == dow]
    entries = pd.DataFrame({"ts": sub["ts"].values, "direction": direction})
    out = {}
    for risk in RISK_LEVELS:
        fold_rows = []
        for train_end, test_end in FOLDS:
            test_entries = entries[(entries["ts"] >= train_end) & (entries["ts"] < test_end)]
            if len(test_entries) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            train_entries = entries[entries["ts"] < train_end]
            best_rr, best_exp = None, -1e18
            for rr in RR_GRID:
                tr = resolve_fixed_window(train_entries, df1m, symbol, rr, risk, atr15, window_end_minutes)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_rr = exp, rr
            if best_rr is None:
                best_rr = 1.5
            te = resolve_fixed_window(test_entries, df1m, symbol, best_rr, risk, atr15, window_end_minutes)
            fold_rows.append((train_end, test_end, best_rr, te))
        out[risk] = fold_rows
    return out


if __name__ == "__main__":
    for symbol, path in [("MNQ", "../data/MNQ_CONTINUOUS.txt"), ("MGC", "../data/MGC_CONTINUOUS.txt")]:
        print(f"\n\n################ {symbol}: Round 15 seasonality ################", flush=True)
        df1m = load_1m(path)
        print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)
        tod = df1m.index.hour * 60 + df1m.index.minute
        session_start = int(tod.min())
        session_end = int(tod.max()) + 1
        print(f"{symbol}: session time-of-day range {session_start}min -> {session_end}min "
              f"({session_start//60:02d}:{session_start%60:02d} -> {session_end//60:02d}:{session_end%60:02d})",
              flush=True)
        n_buckets = (session_end - session_start + BUCKET_MIN - 1) // BUCKET_MIN
        print(f"{symbol}: {n_buckets} time-of-day buckets scanned x 2 directions = "
              f"{n_buckets*2} hypotheses per fold (time-of-day part)", flush=True)

        bar15 = resample_causal(df1m, "15min")
        atr15 = atr_causal(bar15)
        daily_table = build_daily_bucket_table(df1m)
        window_end_minutes = session_end  # flatten at session end if unresolved

        # ---- time-of-day: per-fold train-rank, OOS test on rank-1 (and rank-2, rank-3 individually) ----
        print(f"\n---- {symbol}: TIME-OF-DAY, per-fold training rank (top-3 reported individually) ----", flush=True)
        per_fold_rank1 = []
        rankK_results = {1: [], 2: [], 3: []}
        for train_end, test_end in FOLDS:
            ranked = rank_buckets_on_train(daily_table, train_end, atr15, df1m, symbol, window_end_minutes)
            if len(ranked) == 0:
                print(f"  fold train<{train_end}: no buckets met the training-count floor", flush=True)
                per_fold_rank1.append(None)
                continue
            top3 = ranked.head(3)
            print(f"  fold train<{train_end}: top-3 by train exp -> " +
                  ", ".join(f"(bucket={int(b)}min dir={d} n={n} exp=${e:.2f})"
                            for b, d, n, e in top3.itertuples(index=False)), flush=True)
            per_fold_rank1.append((int(top3.iloc[0]["bucket"]), int(top3.iloc[0]["direction"])))

        distinct_rank1 = set(x for x in per_fold_rank1 if x is not None)
        print(f"  PERSISTENCE CHECK: rank-1 window/direction across {len(FOLDS)} folds = {per_fold_rank1}", flush=True)
        print(f"  -> {len(distinct_rank1)} distinct rank-1 picks out of {len(FOLDS)} folds "
              f"({'STABLE -- same pick recurs' if len(distinct_rank1) <= 3 else 'UNSTABLE -- different pick nearly every fold'})",
              flush=True)

        # Full walk-forward using the FINAL fold's full-history ranking's top-3 as the
        # representative config set (each tested as its own independent one-trade/day strategy)
        final_train_end = FOLDS[-1][0]
        final_ranked = rank_buckets_on_train(daily_table, final_train_end, atr15, df1m, symbol, window_end_minutes)
        for k in (1, 2, 3):
            if len(final_ranked) < k:
                print(f"\n  [{symbol} rank-{k}]: fewer than {k} qualifying buckets, skipped", flush=True)
                continue
            bucket, direction = int(final_ranked.iloc[k-1]["bucket"]), int(final_ranked.iloc[k-1]["direction"])
            label = f"{symbol} TOD rank-{k} bucket={bucket}min dir={direction}"
            res = walk_forward_bucket((bucket, direction), daily_table, df1m, symbol, atr15, window_end_minutes)
            print(f"\n  [{label}] (selected using train<{final_train_end}, applied unchanged across ALL folds' OOS windows)", flush=True)
            print_fold_results(label, res)

        # ---- day-of-week ----
        print(f"\n---- {symbol}: DAY-OF-WEEK, per-fold training rank ----", flush=True)
        daily_first = build_daily_first_bar(df1m)
        per_fold_dow_rank1 = []
        for train_end, test_end in FOLDS:
            ranked = rank_dow_on_train(daily_first, train_end, atr15, df1m, symbol, window_end_minutes)
            if len(ranked) == 0:
                print(f"  fold train<{train_end}: no days met the training-count floor", flush=True)
                per_fold_dow_rank1.append(None)
                continue
            top3 = ranked.head(3)
            dow_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
            print(f"  fold train<{train_end}: top-3 by train exp -> " +
                  ", ".join(f"({dow_names.get(int(d),'?')} dir={dr} n={n} exp=${e:.2f})"
                            for d, dr, n, e in top3.itertuples(index=False)), flush=True)
            per_fold_dow_rank1.append((int(top3.iloc[0]["dow"]), int(top3.iloc[0]["direction"])))
        distinct_dow = set(x for x in per_fold_dow_rank1 if x is not None)
        print(f"  PERSISTENCE CHECK: rank-1 day/direction across {len(FOLDS)} folds = {per_fold_dow_rank1}", flush=True)
        print(f"  -> {len(distinct_dow)} distinct rank-1 picks out of {len(FOLDS)} folds", flush=True)

        final_dow_ranked = rank_dow_on_train(daily_first, final_train_end, atr15, df1m, symbol, window_end_minutes)
        for k in (1, 2, 3):
            if len(final_dow_ranked) < k:
                print(f"\n  [{symbol} DOW rank-{k}]: fewer than {k} qualifying days, skipped", flush=True)
                continue
            dow, direction = int(final_dow_ranked.iloc[k-1]["dow"]), int(final_dow_ranked.iloc[k-1]["direction"])
            dow_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
            label = f"{symbol} DOW rank-{k} day={dow_names.get(dow,'?')} dir={direction}"
            res = walk_forward_dow((dow, direction), daily_first, df1m, symbol, atr15, window_end_minutes)
            print(f"\n  [{label}] (selected using train<{final_train_end}, applied unchanged across ALL folds' OOS windows)", flush=True)
            print_fold_results(label, res)

    print("\n\n################ Round 15 complete ################", flush=True)
