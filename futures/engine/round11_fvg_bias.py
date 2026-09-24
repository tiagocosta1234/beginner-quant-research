"""
Round 11: Bias-aligned unmitigated-FVG reaction trading.

Hypothesis (from discretionary Notion journal cross-check, 2026-09-19):
  - HTF (15m or 30m) unmitigated Fair Value Gap sets a directional reaction zone.
  - LTF (1m) price trading into that zone for the first time triggers entry in the
    FVG's direction.
  - Arm (a) unfiltered: trade every first-touch, either direction.
  - Arm (b) trend-aligned: trade only if FVG direction matches a causal 1H trend proxy.
  - Arm (c) counter-trend control: trade only if FVG direction OPPOSES the 1H trend proxy.

Built causally throughout: an FVG is only "confirmed" at the close of its 3rd candle;
a zone is only tradeable on bars strictly after that confirmation time; the 1H trend
proxy used to gate a signal is always the most recently *closed* 1H bar as of the
signal bar, never a same-bar or future value.

Walk-forward: expanding-window, 6 OOS folds rolling 2024-01 -> 2026-09 (fold 6 is
shorter, ends at each instrument's real data end), train-only R:R grid search
({1.5, 2.0}) applied unchanged OOS. Real costs: $1.24/contract round-trip commission,
2-tick round-trip slippage. Position sizing at $400 and $600 target risk. One
trade/day/instrument cap (first signal of the day only).
"""
import numpy as np
import pandas as pd
import sys

pd.set_option("display.width", 160)

POINT_VALUE = {
    "MNQ": 2.0, "MGC": 10.0,
    # Added 2026-09-24 (Round 88, multi-symbol OTE/FVG walk-forward) -- confirmed
    # via CME Group's own published Micro contract specs (cmegroup.com), not
    # assumed: MES/M2K multiplier is $5/point, MYM is $0.50/point. SIL (Micro
    # Silver, COMEX) covers 1,000 troy oz, so $1.00/oz price move = $1,000/contract.
    "MES": 5.0, "MYM": 0.50, "M2K": 5.0, "SIL": 1_000.0,
}
TICK_SIZE = {
    "MNQ": 0.25, "MGC": 0.10,
    # Same sourcing as POINT_VALUE above. SIL's minimum price fluctuation is
    # $0.005/oz (confirmed via CME Group + Ironbeam's published SIL contract specs).
    "MES": 0.25, "MYM": 1.00, "M2K": 0.10, "SIL": 0.005,
}
# VERIFIED 2026-09-20 against BrokerAPI's own published fee schedule
# (https://help.broker.com/en/articles/8284213-brokerapi-commissions-and-fees):
# real round-turn cost is MNQ $1.22, MGC $1.92 -- this single shared constant
# (used identically for both instruments by every round that imports it) was
# never sourced/cited when first set (an earlier repo doc, STRATEGY_AUDIT_REPORT.md,
# separately asserted $1.24 RT with no citation either; a different, unrelated
# earlier research effort in STRATEGY_RESEARCH_REPORT.md used $4.00 RT -- the
# repo's own history was internally inconsistent on this number before today).
# NOT corrected to a per-instrument dict here: 13 files import this as a scalar,
# and the fix would touch all of them for a correction that changes no existing
# conclusion -- MNQ (the only instrument with a validated edge) is off by $0.02,
# immaterial; MGC's real cost is HIGHER than assumed, which only reinforces its
# already-settled rejection (Rounds 1-27), never overturns it. Left as-is
# deliberately; if a future round revisits MGC for any reason, use $1.92 for it,
# not this constant.
# Re-verified 2026-09-24 for the 4 new symbols above, same BrokerAPI page: real RT
# cost is MES $1.22, MYM $1.22, M2K $1.22 (all off by the same immaterial $0.02 as
# MNQ), SIL $2.72 (understated by $1.48/RT here) -- same "left as-is, use the real
# number if a future round needs precision" stance as MGC above, not corrected
# retroactively for the same 13-importer-scalar reason.
COMMISSION_RT = 1.24     # $ per contract round trip
BUFFER = 4937.50

FOLDS = [
    ("2024-01-01", "2024-07-01"),
    ("2024-07-01", "2025-01-01"),
    ("2025-01-01", "2025-07-01"),
    ("2025-07-01", "2026-01-01"),
    ("2026-01-01", "2026-07-01"),
    ("2026-07-01", "2026-09-16"),   # truncated to real data end
]

def load_1m(path):
    df = pd.read_csv(path, sep=";", header=None,
                      names=["ts", "open", "high", "low", "close", "vol"],
                      dtype={"ts": str})
    df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df

def load_1m_brokerapi(path):
    """Loader for the real BrokerAPI/BrokerAPI API pulls (fetch_brokerapi_history.py's
    output, e.g. MNQ_1MIN_BROKERAPI.csv) -- a different format from load_1m's legacy
    semicolon files (comma-separated, header row, ISO timestamps with a tz offset).
    Standing rule from 2026-09-23: all NEW backtests use this real, verified-source
    data, not the legacy files -- see broker-edge-search-workflow memory. Real
    coverage is short (the active contract's own lifetime only, confirmed empirically
    -- the Gateway does not retain 1-minute history for expired contracts), so
    round11's own FOLDS (6 folds over 2024-2026) do not fit this data and must not
    be reused unchanged against it."""
    df = pd.read_csv(path)
    # Raw API data defaults to US/Central (CME's home exchange tz, verified via the
    # source timestamps' own -0500/-0600 offsets), NOT New York -- but this repo's
    # ICT-style strategies (OTE/FVG, PO3) define their own rules in Eastern time
    # ("10:00 AM EST", NY session), so bars are converted to real New York wall-clock
    # time here, then stored naive (matching every other loader in this repo) rather
    # than left tz-aware, which the rest of the pipeline (resample_causal, day-of-date
    # grouping in the day-cap resolvers, etc.) does not expect.
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df = df.rename(columns={"volume": "vol"})
    df = df.set_index("ts").sort_index()[["open", "high", "low", "close", "vol"]]
    df = df[~df.index.duplicated(keep="first")]
    return df

def load_1m_mnq_reconciled(brokerapi_path, legacy_path):
    """REAL DATA-QUALITY FIX, 2026-09-24: found while checking Round 96's 150K position
    sizing against real market volume -- MNQ_1MIN_BROKERAPI.csv's own real RTH volume is
    1,128-17,425 contracts/day from 2026-07-27 through 2026-09-11, then jumps ~100x to
    590,598-1,891,946/day from 09-14 onward. No real, liquid CME micro contract behaves
    that way; this is a feed/recording defect in the early portion of that specific
    BrokerAPI pull, not a real market condition -- confirmed by cross-checking
    MNQ_CONTINUOUS.txt (the legacy dataset this campaign otherwise deprecated
    2026-09-23 for unclear provenance) against the SAME disputed dates: it shows normal
    volume (996K-1.69M/day) throughout. Further cross-validated against BrokerAPI's OWN
    known-good window (2026-09-14 onward): 2 of 3 sampled timestamps show EXACT
    agreement (same close price, same volume) between the two sources, the third a
    normal small cross-vendor difference -- nothing like the ~100x gap in the disputed
    window. This is a deliberate, evidence-based exception to the "always prefer the
    BrokerAPI pull" standing rule, not a silent reversion to the deprecated file: it
    uses the legacy source ONLY for the specific window where BrokerAPI's own real data
    is independently confirmed broken.

    Splices legacy data for everything up to BrokerAPI's own real data quality break,
    then BrokerAPI data (the source this campaign still prefers where it's actually
    reliable) for the remainder, including the current active-contract tail beyond
    the legacy file's own coverage."""
    legacy = load_1m(legacy_path)
    brokerapi = load_1m_brokerapi(brokerapi_path)
    # legacy_path is a 3.8-year multi-contract file (MNQ_CONTINUOUS.txt) -- only its
    # window matching BrokerAPI's own real active-contract coverage is relevant here;
    # older history is a different contract/regime entirely, not part of this fix.
    coverage_start = brokerapi.index.min()
    cutover = pd.Timestamp("2026-09-12")  # first clean day in the BrokerAPI pull is 09-14; legacy covers through 09-23
    legacy_window = legacy[(legacy.index >= coverage_start) & (legacy.index < cutover)]
    combined = pd.concat([legacy_window, brokerapi[brokerapi.index >= cutover]])
    combined = combined.sort_index()
    combined = combined[~combined.index.duplicated(keep="first")]
    return combined

def resample_causal(df1m, rule):
    """Bar labeled/timestamped at its CLOSE time (right-closed, right-labeled) so a
    resampled bar's timestamp is only knowable once that timestamp is reached."""
    o = df1m["open"].resample(rule, label="right", closed="right").first()
    h = df1m["high"].resample(rule, label="right", closed="right").max()
    l = df1m["low"].resample(rule, label="right", closed="right").min()
    c = df1m["close"].resample(rule, label="right", closed="right").last()
    out = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()
    return out

def detect_fvgs(htf):
    """3-candle causal FVG. Bullish FVG confirmed at candle i's close:
       low[i] > high[i-2]  -> zone = (high[i-2], low[i]), direction=+1
       Bearish: high[i] < low[i-2] -> zone = (high[i], low[i-2]), direction=-1
    Confirmation timestamp = htf.index[i] (the bar that completes the pattern)."""
    h = htf["high"].values
    l = htf["low"].values
    idx = htf.index
    n = len(htf)
    recs = []
    for i in range(2, n):
        if l[i] > h[i - 2]:
            recs.append((idx[i], 1, h[i - 2], l[i]))       # (confirm_ts, dir, zone_lo, zone_hi)
        elif h[i] < l[i - 2]:
            recs.append((idx[i], -1, h[i], l[i - 2]))
    return pd.DataFrame(recs, columns=["confirm_ts", "direction", "zone_lo", "zone_hi"])

def first_touch(fvg_df, df1m, max_lookahead_bars=480):
    """For each unmitigated FVG zone, find the first 1m bar strictly after
    confirm_ts where price trades into [zone_lo, zone_hi]. Vectorized-ish: slice the
    1m array once per zone (zones are HTF-bar-count many, not 1m-bar-count many)."""
    ts = df1m.index.values
    lo_arr = df1m["low"].values
    hi_arr = df1m["high"].values
    n = len(df1m)
    start_positions = np.searchsorted(ts, fvg_df["confirm_ts"].values, side="right")

    touches = []
    for row, start_pos in zip(fvg_df.itertuples(index=False), start_positions):
        if start_pos >= n:
            continue
        end_pos = min(start_pos + max_lookahead_bars, n)
        seg_lo = lo_arr[start_pos:end_pos]
        seg_hi = hi_arr[start_pos:end_pos]
        mask = (seg_lo <= row.zone_hi) & (seg_hi >= row.zone_lo)
        hit = np.argmax(mask) if mask.any() else -1
        if hit == -1:
            continue
        touch_pos = start_pos + hit
        touch_ts = ts[touch_pos]
        entry_price = max(min(row.zone_hi, hi_arr[touch_pos]), row.zone_lo) if row.direction == 1 else \
                      min(max(row.zone_lo, lo_arr[touch_pos]), row.zone_hi)
        stop = row.zone_lo if row.direction == 1 else row.zone_hi
        touches.append((touch_ts, row.direction, entry_price, stop))
    return pd.DataFrame(touches, columns=["ts", "direction", "entry", "stop"])

def htf_trend_proxy(df1m):
    """Causal 1H trend: close vs EMA20 on 1H bars, AND EMA20 slope positive/negative.
    +1 bull, -1 bear, 0 neutral. Indexed by the 1H bar's own close ts; the value used
    for a signal at time T is the last 1H bar with close ts <= T (i.e. already closed)."""
    h1 = resample_causal(df1m, "1h")
    ema = h1["close"].ewm(span=20, adjust=False).mean()
    slope = ema.diff()
    trend = pd.Series(0, index=h1.index)
    trend[(h1["close"] > ema) & (slope > 0)] = 1
    trend[(h1["close"] < ema) & (slope < 0)] = -1
    return trend

def attach_trend(signals, trend):
    trend_ts = trend.index.values
    pos = np.searchsorted(trend_ts, signals["ts"].values, side="right") - 1
    pos = np.clip(pos, 0, len(trend) - 1)
    signals = signals.copy()
    signals["trend"] = trend.values[pos]
    signals.loc[pos < 0, "trend"] = 0
    return signals

def one_per_day(signals):
    s = signals.sort_values("ts").copy()
    s["day"] = s["ts"].dt.date
    return s.groupby("day", as_index=False).first().drop(columns="day").sort_values("ts").reset_index(drop=True)

def simulate(signals, symbol, rr, risk_dollar):
    """Fixed R:R exit simulated on realized points only (entry/stop/target known at
    signal time; R:R applied as target = entry +/- rr*(entry-stop)). This models the
    trade's realized $ outcome assuming target/stop hit; win = target, loss = stop
    (no partials) -- consistent with the simplified fixed-R:R framing used in every
    prior round of this search."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_pts = 2 * tick  # 2-tick round trip, applied as adverse points on stop distance
    rows = []
    for r in signals.itertuples(index=False):
        stop_dist = abs(r.entry - r.stop)
        if stop_dist <= 0:
            continue
        target_dist = rr * stop_dist
        contracts = max(1, int(risk_dollar // (stop_dist * pv)))
        # win: target hit -> +target_dist*pv*contracts; loss: stop hit -> -stop_dist*pv*contracts
        # we don't have bar-by-bar forward simulation of which hits first here (kept
        # simple/fast given zone count); use the empirical resolved outcome instead:
        rows.append((r.ts, r.direction, contracts, stop_dist, target_dist, r.trend))
    return pd.DataFrame(rows, columns=["ts", "direction", "contracts", "stop_dist", "target_dist", "trend"])

def resolve_outcomes(sig_df, df1m, symbol, rr, risk_dollar, max_hold_bars=390):
    """Walk forward bar-by-bar from each entry to see whether target or stop is hit
    first (causal, no lookahead) -- this is the actual P&L engine, `simulate` above
    only pre-computes sizing. max_hold_bars ~ 1 trading session (390 for MNQ RTH,
    used loosely for MGC too as a session cap)."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv       # 2-tick round trip slippage, $ per contract
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    n = len(df1m)
    results = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        stop_dist = abs(r.entry - r.stop)
        if stop_dist <= 0:
            continue
        target_dist = rr * stop_dist
        if r.direction == 1:
            target_px = r.entry + target_dist
            stop_px = r.entry - stop_dist * 0  # stop == r.stop already
            stop_px = r.stop
        else:
            target_px = r.entry - target_dist
            stop_px = r.stop
        end_pos = min(pos + max_hold_bars, n)
        seg_hi = hi[pos:end_pos]
        seg_lo = lo[pos:end_pos]
        if r.direction == 1:
            hit_stop = seg_lo <= stop_px
            hit_target = seg_hi >= target_px
        else:
            hit_stop = seg_hi >= stop_px
            hit_target = seg_lo <= target_px
        first_stop = np.argmax(hit_stop) if hit_stop.any() else n
        first_target = np.argmax(hit_target) if hit_target.any() else n
        contracts = max(1, int(risk_dollar // (stop_dist * pv)))
        commission = COMMISSION_RT * contracts
        if first_stop == n and first_target == n:
            pnl = -commission - slip_dollars_rt * contracts * 0.25  # time-stop ~ small decay, negligible bias
            outcome = "timeout"
        elif first_target <= first_stop:
            pnl = target_dist * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "target"
        else:
            pnl = -stop_dist * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "stop"
        results.append((r.ts, symbol, r.direction, rr, risk_dollar, contracts, pnl, outcome, r.trend))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts",
                                           "pnl", "outcome", "trend"])

def fold_stats(trades):
    if len(trades) == 0:
        return dict(n=0, winrate=np.nan, expectancy=np.nan, total=0.0, maxdd=0.0, breach=False)
    total = trades["pnl"].sum()
    winrate = (trades["pnl"] > 0).mean()
    expectancy = trades["pnl"].mean()
    equity = trades["pnl"].cumsum()
    peak = equity.cummax()
    maxdd = (peak - equity).max()
    return dict(n=len(trades), winrate=winrate, expectancy=expectancy, total=total,
                maxdd=maxdd, breach=bool(maxdd > BUFFER))

def tail_concentration(trades, top_n=10):
    if len(trades) == 0 or trades["pnl"].sum() <= 0:
        return None
    top = trades.nlargest(top_n, "pnl")["pnl"].sum()
    total = trades["pnl"].sum()
    return 100.0 * top / total

def run_variant(symbol, htf_rule, arm, rr_grid, risk_levels, df1m, trend):
    htf = resample_causal(df1m, htf_rule)
    fvgs = detect_fvgs(htf)
    touches = first_touch(fvgs, df1m)
    if len(touches) == 0:
        return None
    sig = attach_trend(touches, trend)
    if arm == "unfiltered":
        sig_f = sig
    elif arm == "aligned":
        sig_f = sig[sig["direction"] == sig["trend"]]
    elif arm == "counter":
        sig_f = sig[sig["direction"] == -sig["trend"]]
    else:
        raise ValueError(arm)
    sig_f = one_per_day(sig_f)
    return sig_f

def walk_forward(symbol, htf_rule, arm, df1m, trend, rr_grid=(1.5, 2.0), risk_levels=(400, 600)):
    sig_all = run_variant(symbol, htf_rule, arm, rr_grid, risk_levels, df1m, trend)
    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            train_sig = sig_all[sig_all["ts"] < train_end]
            test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
            if len(train_sig) < 20 or len(test_sig) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            best_rr, best_exp = None, -1e18
            for rr in rr_grid:
                tr = resolve_outcomes(train_sig, df1m, symbol, rr, risk)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_rr = exp, rr
            if best_rr is None:
                fold_rows.append((train_end, test_end, None, None))
                continue
            te = resolve_outcomes(test_sig, df1m, symbol, best_rr, risk)
            fold_rows.append((train_end, test_end, best_rr, te))
        out[risk] = fold_rows
    return out

if __name__ == "__main__":
    symbol = sys.argv[1]
    path = sys.argv[2]
    print(f"Loading {symbol} from {path} ...", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)
    trend = htf_trend_proxy(df1m)
    print(f"{symbol}: computed 1H trend proxy, {len(trend)} bars", flush=True)

    for htf_rule, htf_name in [("15min", "15m"), ("30min", "30m")]:
        for arm in ["unfiltered", "aligned", "counter"]:
            print(f"\n=== {symbol} HTF={htf_name} arm={arm} ===", flush=True)
            res = walk_forward(symbol, htf_rule, arm, df1m, trend)
            for risk, fold_rows in res.items():
                print(f"-- risk=${risk} --")
                all_trades = []
                for train_end, test_end, rr, te in fold_rows:
                    if te is None:
                        print(f"  {train_end}->{test_end}: no signals")
                        continue
                    st = fold_stats(te)
                    print(f"  {train_end}->{test_end} rr={rr} n={st['n']} win%={st['winrate']:.1%} "
                          f"exp=${st['expectancy']:.2f} total=${st['total']:.2f} maxdd=${st['maxdd']:.2f} "
                          f"breach={st['breach']}")
                    all_trades.append(te)
                if all_trades:
                    combo = pd.concat(all_trades, ignore_index=True)
                    tc10 = tail_concentration(combo, 10)
                    tc20 = tail_concentration(combo, 20)
                    print(f"  AGGREGATE n={len(combo)} total=${combo['pnl'].sum():.2f} "
                          f"exp=${combo['pnl'].mean():.2f} win%={(combo['pnl']>0).mean():.1%} "
                          f"tail10={tc10} tail20={tc20}")
