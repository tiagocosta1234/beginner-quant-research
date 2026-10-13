"""
Round 311 (2026-10-02, PRE-REGISTERED): the trader: "analyze the current strategy applied to the chart, invert it and try to optimize its profitability". The strategy on the chart (1-minute OANDA:XAUUSD) is the trader's own
Pine indicator "Reversal Prediction Indicator with 2:1 RR" (saved as "Reversal Signal Detector"), read from the editor:
  RSI(14), MACD(12, 26, 9) histogram, ATR(14); candleSpread = high - low; atrSpike = candleSpread > ATR x 1.0 (input "ATR Spike Threshold").
  bullishDivergence = lowest(close, 3) < lowest(close[1], 3) AND lowest(rsi, 3) > lowest(rsi[1], 3) AND change(macdHist) > -0.01;  bearish: mirror with highest and < +0.01.
  LONG = bullishDivergence AND macdHist > macdHist[1] AND atrSpike; SHORT = bearishDivergence AND macdHist < macdHist[1] AND atrSpike.
  Stop = close -/+ ATR, take profit = close +/- 2 x ATR (rrRatio 2.0). It is a signals-only indicator (plotshape labels); no position handling, no session filter, no costs.

Step 0 (ledger checked first, k = 1995): RSI/MACD divergence and ATR-spike reversal have not been tested as such; the 1-minute fades of Rounds 309-310 (exhaustion, RSI(2), Bollinger, VWAP stretch) found no edge at
1-minute scale on ES/NQ/GC (costs 0.12-0.19R a trade, skill at most +0.045R). Honest expectation (stated before the run): the signal is a 3-bar divergence on a 1-minute chart, so it is close to a coin flip and a
gold 1-minute stop of 1 ATR makes the spread a large share of R; I expect the original to lose, its inversion to lose by about as much, and an optimized parameter set to look good in training and decay on unseen data.

DATA: MT5 XAUUSD M1 bid/ask (forex/data/XAUUSD_M1_ticks_full.parquet via round271.load, server time -> New York), 2021-10-04 .. 2026-09-30 (the CFD a MT5 broker account trades; no commission on MT5 broker gold, real spread
in the data; the indicator is computed on bid candles, like the OANDA chart). Entries at the signal bar's close: long at the ASK, short at the BID; long stops / targets / timeouts fill on the BID book (bid low / high / close), short ones on the ASK
book (ask high / low / close); stop wins a tie on a bar; stops and targets fill at their level. Max hold 120 bars (2 hours) then exit at the close; no position carried through a data gap (> 10 minutes); one position at a time
(a signal while a position is open is skipped). R = the stop distance; P&L in R, shown as dollars at the repo's $300 risk for the ledger.
Splits (fixed): TRAIN 2021-10-04..2023-12-31, VALID 2024-01-01..2025-06-30, TEST 2025-07-01..2026-09-30 (the repo's OOS start).

THE TESTS
  (1) ORIGINAL as written: ATR spike 1.0, divergence lookback 3, all sessions, stop 1 ATR, target 2 ATR (RR 2), both sides.
  (2) INVERTED: the same signals traded the other way with the same geometry (a "bullish" signal -> SHORT with stop +1 ATR / target -2 ATR; a "bearish" signal -> LONG): the exact mirror, same fills book logic.
  (3) OPTIMIZATION (exploratory, TRAIN period only): grid over ATR-spike threshold {0, 1.0, 1.5, 2.0}, divergence lookback {3, 5, 10}, session {all, 03:00-12:00 New York}, stop ATR multiple {1, 1.5, 2, 3},
      RR {0.5, 1, 2, 3}, direction {original, inverted} = 768 configurations. Selection rule, fixed now: per direction, among configurations with >= 400 TRAIN trades pick the highest TRAIN mean net R; that single
      configuration per direction is then read on VALID and on TEST (once). It counts as "profitable" only if its VALID and TEST net R are both > 0 AND it passes idea_harness.test_idea's candidate bar at the new k on VALID+TEST.
      The whole grid's TRAIN table (and how many TRAIN winners stay positive on VALID) is reported as the selection-decay evidence. Nothing else is tuned after seeing VALID/TEST.
  Ledger rows (4): ORIGINAL (full period), INVERTED (full period), OPTIMIZED-original and OPTIMIZED-inverted (each on VALID+TEST only, VALID as the in-sample part, TEST as OOS). k -> 1999.
  Also reported (diagnostics, not ledger): signals per day, long/short split, win rate vs the 1/3 of a random 1:2 geometry, by year, by hour, cost share (spread in R).
  CANDIDATE (idea_harness.test_idea): positive before AND after costs, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/k.

DRY-RUN COUNTS (no P&L read; the divergence logic is checked against a slow reference loop on random data, the resolver on synthetic bars incl. stop-first ties and the inverted bid/ask book; three signals hand-checked against the closes):
  1,749,216 one-minute bars, median spread $0.21, median ATR(14) $0.66 (so a 1 ATR stop is about $0.66 and the spread is about a third of R). Signals (all sessions, lookback 3): spike 0 -> 12,572; spike 1.0 (as written) -> 4,134 (1,968 long / 2,166 short; 2.7 a day; 4,058 one-at-a-time trades);
  spike 1.5 -> 596; spike 2.0 -> 61. Lookback 10 and the London+NY session cut these further (spike 1.0 / lookback 10 / LDN_NY: 114). Sets with fewer than 400 TRAIN trades cannot be selected (spike 2.0 and most of spike 1.5 with lookback >= 5).
POWER: ORIGINAL / INVERTED defaults have about 4,058 trades (standard error of mean net R about 0.02R; VALID+TEST about 1,500 trades, 0.04R). An edge smaller than about +0.08R net cannot be told from zero on VALID+TEST; stated before the run.
"""
import os, sys, json, time, subprocess
from types import SimpleNamespace
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idea_harness as H
import round271_one_to_one_generator as M

HERE = os.path.dirname(os.path.abspath(__file__))
HOLD = 120
GAP_MIN = 10
RISK = 300.0
TRAIN_END = pd.Timestamp("2024-01-01")
VALID_END = pd.Timestamp("2025-07-01")
SPIKES = [0.0, 1.0, 1.5, 2.0]
LOOKS = [3, 5, 10]
SESSIONS = ["ALL", "LDN_NY"]
STOPMS = [1.0, 1.5, 2.0, 3.0]
RRS = [0.5, 1.0, 2.0, 3.0]
MIN_TRAIN_TRADES = 400


def load():
    df = M.load("XAUUSD")
    df = df[(df.index >= "2021-10-04") & (df.index < "2026-10-01")]
    t = df.index.values
    f = lambda k: df[k].to_numpy(float)
    D = dict(t=t, bo=f("open"), bh=f("high"), bl=f("low"), bc=f("close"), ah=f("ask_high"), al=f("ask_low"), ac=f("ask_close"))
    n = len(t)
    dt_min = np.r_[np.inf, np.diff(t).astype("timedelta64[s]").astype(float) / 60.0]
    gap = dt_min > GAP_MIN
    # next gap index after i (first k > i with a gap before bar k)
    nxt = np.full(n, n, dtype=np.int64)
    gi = np.flatnonzero(gap)
    pos = np.searchsorted(gi, np.arange(n), side="right")
    ok = pos < len(gi)
    nxt[ok] = gi[pos[ok]]
    D["valid_len"] = np.minimum(np.minimum(nxt - np.arange(n) - 1, n - 1 - np.arange(n)), HOLD)
    s = pd.Series(D["bc"])
    c, h, l = s, pd.Series(D["bh"]), pd.Series(D["bl"])
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    D["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean().values
    d1 = c.diff()
    up = d1.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d1.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    D["rsi"] = (100 - 100 / (1 + up / dn.replace(0, np.nan))).values
    ml = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    D["hist"] = (ml - ml.ewm(span=9, adjust=False).mean()).values
    D["rng"] = (h - l).values
    nyh = pd.DatetimeIndex(t).hour
    D["sess"] = (nyh >= 3) & (nyh < 12)
    return D


def signals(D, spike, look, session):
    c, rsi, hist = pd.Series(D["bc"]), pd.Series(D["rsi"]), pd.Series(D["hist"])
    lc, lcp = c.rolling(look).min(), c.rolling(look).min().shift(1)
    hc, hcp = c.rolling(look).max(), c.rolling(look).max().shift(1)
    lr, lrp = rsi.rolling(look).min(), rsi.rolling(look).min().shift(1)
    hr, hrp = rsi.rolling(look).max(), rsi.rolling(look).max().shift(1)
    dh = hist.diff()
    bull = (lc < lcp) & (lr > lrp) & (dh > -0.01)
    bear = (hc > hcp) & (hr < hrp) & (dh < 0.01)
    sp = pd.Series(D["rng"] > D["atr"] * spike) if spike > 0 else pd.Series(D["rng"] > 0)
    long_ = (bull & (hist > hist.shift(1)) & sp).values
    short_ = (bear & (hist < hist.shift(1)) & sp).values
    s = np.where(long_, 1, np.where(short_, -1, 0))
    if session == "LDN_NY":
        s = np.where(D["sess"], s, 0)
    s[:300] = 0
    s[~(D["valid_len"] >= 1)] = 0
    s[np.isnan(D["atr"]) | (D["atr"] <= 0)] = 0
    return s


def windows(D, idx):
    H_ = HOLD
    W = {}
    for k in ("bl", "bh", "al", "ah", "bc", "ac"):
        sw = sliding_window_view(D[k].astype(np.float32), H_)
        W[k] = sw[idx + 1]
    return W


def resolve(D, idx, side, W, stopm, rr):
    """Vectorised first-touch resolution for signals idx (bar indices) traded as `side` (+1 long / -1 short)."""
    N = len(idx)
    atr = D["atr"][idx]
    dist = stopm * atr
    vl = D["valid_len"][idx]
    pos = np.arange(HOLD)[None, :]
    beyond = pos >= vl[:, None]
    entry = np.where(side > 0, D["ac"][idx], D["bc"][idx])
    stop = entry - side * dist
    tgt = entry + side * rr * dist
    lo_b = np.where(beyond, np.inf, W["bl"]); hi_b = np.where(beyond, -np.inf, W["bh"])
    lo_a = np.where(beyond, np.inf, W["al"]); hi_a = np.where(beyond, -np.inf, W["ah"])
    long_m = (side > 0)[:, None]
    hit_stop = np.where(long_m, lo_b <= stop[:, None], hi_a >= stop[:, None])
    hit_tgt = np.where(long_m, hi_b >= tgt[:, None], lo_a <= tgt[:, None])
    fs = np.where(hit_stop.any(1), hit_stop.argmax(1), HOLD)
    ft = np.where(hit_tgt.any(1), hit_tgt.argmax(1), HOLD)
    stopped = (fs < HOLD) & (fs <= ft)
    targeted = (ft < HOLD) & (ft < fs)
    off = np.where(stopped, fs, np.where(targeted, ft, vl - 1))
    off = np.clip(off, 0, HOLD - 1)
    ex_abs = idx + 1 + off
    exit_close = np.where(side > 0, W["bc"][np.arange(N), off], W["ac"][np.arange(N), off])
    r = np.where(stopped, -1.0, np.where(targeted, rr, side * (exit_close - entry) / dist))
    spr_in = D["ac"][idx] - D["bc"][idx]
    spr_out = D["ac"][ex_abs] - D["bc"][ex_abs]
    cost_R = (spr_in + spr_out) / 2.0 / dist
    return ex_abs, r, cost_R


def one_at_a_time(idx, ex_abs):
    keep = np.zeros(len(idx), bool)
    free = -1
    il, el = idx.tolist(), ex_abs.tolist()
    kp = []
    for k in range(len(il)):
        if il[k] > free:
            kp.append(k); free = el[k]
    keep[kp] = True
    return keep


def period_of(ts):
    return np.where(ts < np.datetime64(TRAIN_END), 0, np.where(ts < np.datetime64(VALID_END), 1, 2))


def agg(r_net, cost_R, per, win):
    out = {}
    for nm, m in (("TRAIN", per == 0), ("VALID", per == 1), ("TEST", per == 2), ("ALL", per >= 0)):
        k = int(m.sum())
        out[nm] = dict(n=k, net_R=float(r_net[m].mean()) if k else float("nan"), gross_R=float((r_net[m] + cost_R[m]).mean()) if k else float("nan"),
                       win=float(win[m].mean()) if k else float("nan"))
    return out


def run_config(D, idx, sgn, W, direction, stopm, rr, keep_trades=False):
    side = sgn if direction == "orig" else -sgn
    ex_abs, r, cost_R = resolve(D, idx, side, W, stopm, rr)
    keep = one_at_a_time(idx, ex_abs)
    ii, ee, rr_, cc, sd = idx[keep], ex_abs[keep], r[keep], cost_R[keep], side[keep]
    per = period_of(D["t"][ii])
    a = agg(rr_, cc, per, rr_ > 0)
    if not keep_trades:
        return a
    tr = pd.DataFrame(dict(entry_ts=pd.to_datetime(D["t"][ii]), exit_ts=pd.to_datetime(D["t"][ee]), direction=sd, r_gross=rr_ + cc, cost_R=cc, r_net=rr_, per=per))
    return a, tr


def as_trades(tr):
    if tr.empty:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r", "cost"])
    return pd.DataFrame(dict(entry_ts=tr["entry_ts"], exit_ts=tr["exit_ts"], direction=tr["direction"], contracts=1, pnl=tr["r_net"] * RISK, r=tr["r_gross"], cost=tr["cost_R"] * RISK))


def selftest():
    # divergence logic vs a slow reference on random data
    rng = np.random.default_rng(1)
    n = 2000
    c = 100 + np.cumsum(rng.normal(0, 0.3, n))
    D = dict(bc=c, rsi=np.clip(50 + np.cumsum(rng.normal(0, 3, n)), 1, 99), hist=np.cumsum(rng.normal(0, 0.1, n)) * 0.2, rng=np.abs(rng.normal(0, 0.5, n)) + 0.01,
             atr=np.full(n, 0.4), valid_len=np.full(n, HOLD), sess=np.ones(n, bool), t=np.arange(n).astype("datetime64[m]"))
    s = signals(D, 0.0, 3, "ALL")
    ref = np.zeros(n, int)
    for i in range(305, n):
        lc, lcp = c[i - 2:i + 1].min(), c[i - 3:i].min()
        lr, lrp = D["rsi"][i - 2:i + 1].min(), D["rsi"][i - 3:i].min()
        hc, hcp = c[i - 2:i + 1].max(), c[i - 3:i].max()
        hr, hrp = D["rsi"][i - 2:i + 1].max(), D["rsi"][i - 3:i].max()
        dh = D["hist"][i] - D["hist"][i - 1]
        if lc < lcp and lr > lrp and dh > -0.01 and D["hist"][i] > D["hist"][i - 1]:
            ref[i] = 1
        elif hc > hcp and hr < hrp and dh < 0.01 and D["hist"][i] < D["hist"][i - 1]:
            ref[i] = -1
    assert (s[305:] == ref[305:]).all(), (int((s[305:] != ref[305:]).sum()))
    # resolution: a long that hits its 2R target on the 3rd bar; stop-first tie; timeout
    m = 200
    base = 100.0
    Dm = dict(t=np.arange(m).astype("datetime64[m]"), atr=np.full(m, 1.0), valid_len=np.full(m, HOLD), bc=np.full(m, base), ac=np.full(m, base + 0.1),
              bl=np.full(m, base), bh=np.full(m, base), al=np.full(m, base + 0.1), ah=np.full(m, base + 0.1))
    Dm["bh"][12] = base + 2.5     # bar 12 reaches the long target (entry ask 100.1 + 2 = 102.1) on the bid
    idx = np.array([10]); sgn = np.array([1])
    W = windows(Dm, idx)
    ex, r, c_ = resolve(Dm, idx, sgn, W, 1.0, 2.0)
    assert ex[0] == 12 and abs(r[0] - 2.0) < 1e-9, (ex, r)
    # same bar touches stop and target: stop first
    Dm["bl"][12] = base - 5
    W = windows(Dm, idx)
    ex, r, c_ = resolve(Dm, idx, sgn, W, 1.0, 2.0)
    assert r[0] == -1.0, r
    # inverted short from the same bar: entry bid 100.0, stop on ask high >= 101.0 never, target ask low <= 98.0 never: timeout at ask close - 100.1 ... r = -(100.1-100.0)/1 = -0.1
    ex, r, c_ = resolve(Dm, idx, -sgn, windows(Dm, idx), 1.0, 2.0)
    assert abs(r[0] + 0.1) < 1e-4, r
    print("selftest ok")


def dry_run():
    selftest()
    t0 = time.time()
    D = load()
    print(f"bars {len(D['t'])}  {pd.Timestamp(D['t'][0])} -> {pd.Timestamp(D['t'][-1])}  loaded in {time.time() - t0:.0f}s; median spread ${np.median(D['ac'] - D['bc']):.2f}, median ATR14 ${np.nanmedian(D['atr']):.2f}")
    days = len(np.unique(pd.DatetimeIndex(D['t']).normalize()))
    for sp in SPIKES:
        row = []
        for lk in LOOKS:
            for se in SESSIONS:
                s = signals(D, sp, lk, se)
                row.append(f"L{lk}/{se}: {int((s != 0).sum())} ({(s == 1).sum()}L/{(s == -1).sum()}S)")
        print(f" spike {sp}: " + " | ".join(row))
    s = signals(D, 1.0, 3, "ALL")
    print(f"default signals per day: {(s != 0).sum() / days:.1f} over {days} days")
    # original as written: counts of trades, no P&L read
    idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + HOLD < len(D['t'])]
    W = windows(D, idx)
    ex, r, c = resolve(D, idx, s[idx], W, 1.0, 2.0)
    keep = one_at_a_time(idx, ex)
    print(f"default ORIGINAL one-at-a-time trades: {int(keep.sum())} (of {len(idx)} signals)")
    # hand-check three signals
    for k in (len(idx) // 5, len(idx) // 2, len(idx) - 50):
        i = idx[k]
        print(f"  hand-check {pd.Timestamp(D['t'][i])} side {s[i]:+d} bid close {D['bc'][i]:.2f} ask close {D['ac'][i]:.2f} ATR {D['atr'][i]:.2f} range {D['rng'][i]:.2f} rsi {D['rsi'][i]:.1f} hist {D['hist'][i]:+.3f} prev {D['hist'][i - 1]:+.3f}; closes i-3..i {np.round(D['bc'][i - 3:i + 1], 2).tolist()}")
    print("\n--dry-run: counts only, no P&L is read.")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    selftest()
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    D = load()
    all_days = sorted(set(pd.DatetimeIndex(D["t"]).normalize()))
    n = len(D["t"])
    grid = []
    sig_cache = {}
    for sp in SPIKES:
        for lk in LOOKS:
            for se in SESSIONS:
                s = signals(D, sp, lk, se)
                idx = np.flatnonzero(s != 0)
                idx = idx[idx + 1 + HOLD < n]
                W = windows(D, idx)
                sgn = s[idx]
                for direction in ("orig", "inv"):
                    for stopm in STOPMS:
                        for rr in RRS:
                            a = run_config(D, idx, sgn, W, direction, stopm, rr)
                            grid.append(dict(spike=sp, look=lk, sess=se, dir=direction, stopm=stopm, rr=rr, **{f"{p}_{k}": v for p, d in a.items() for k, v in d.items()}))
                del W
                print(f"  set spike {sp} look {lk} {se}: {len(idx)} signals, grid rows {len(grid)}  ({time.time() - t0:.0f}s)", flush=True)
    G = pd.DataFrame(grid)
    G.to_csv(os.path.join(HERE, "round311_grid.csv"), index=False)
    print(f"grid {len(G)} configurations in {time.time() - t0:.0f}s")

    def cfg_trades(row):
        s = signals(D, row.spike, int(row.look), row.sess)
        idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + HOLD < n]
        W = windows(D, idx)
        return run_config(D, idx, s[idx], W, row.dir, row.stopm, row.rr, keep_trades=True)

    # (1) and (2): original and inverted defaults
    kk = H.ledger_count()
    results, rows_out = {}, []
    dflt = dict(spike=1.0, look=3, sess="ALL", stopm=1.0, rr=2.0)
    for direction in ("orig", "inv"):
        a, tr = cfg_trades(SimpleNamespace(**dflt, dir=direction))
        kk += 1
        name = f"Reversal Signal Detector {'ORIGINAL' if direction == 'orig' else 'INVERTED'} (RSI/MACD divergence + ATR spike, stop 1 ATR target 2 ATR, hold <= 120 bars), MT5 XAUUSD 1-min bid/ask 2021-10..2026-09"
        row = H.test_idea(name, as_trades(tr), all_days, "MNQ", kk)
        rows_out.append(row)
        print(f"    default {direction}: win {a['ALL']['win']:.1%} net {a['ALL']['net_R']:+.3f}R gross {a['ALL']['gross_R']:+.3f}R n {a['ALL']['n']} | TRAIN {a['TRAIN']['net_R']:+.3f} VALID {a['VALID']['net_R']:+.3f} TEST {a['TEST']['net_R']:+.3f}", flush=True)
        results[f"default_{direction}"] = dict(agg=a, row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"},
                                                by_year={int(y): float(g["r_net"].mean()) for y, g in tr.groupby(tr["entry_ts"].dt.year)},
                                                by_hour={int(h_): float(g["r_net"].mean()) for h_, g in tr.groupby(tr["entry_ts"].dt.hour)},
                                                by_side={str(sd): dict(n=int(len(g)), net_R=float(g["r_net"].mean()), win=float((g["r_net"] > 0).mean())) for sd, g in tr.groupby("direction")})
    # (3) optimization: select on TRAIN only
    for direction in ("orig", "inv"):
        gd = G[(G["dir"] == direction) & (G["TRAIN_n"] >= MIN_TRAIN_TRADES)]
        best = gd.sort_values("TRAIN_net_R", ascending=False).iloc[0]
        pos = gd[gd["TRAIN_net_R"] > 0]
        decay = dict(n_configs=int(len(gd)), n_train_positive=int(len(pos)),
                     n_train_positive_valid_positive=int((pos["VALID_net_R"] > 0).sum()), n_train_positive_valid_and_test_positive=int(((pos["VALID_net_R"] > 0) & (pos["TEST_net_R"] > 0)).sum()),
                     median_train_net_R=float(gd["TRAIN_net_R"].median()), median_valid_net_R=float(gd["VALID_net_R"].median()), median_test_net_R=float(gd["TEST_net_R"].median()),
                     best_train_net_R=float(gd["TRAIN_net_R"].max()), best_valid_net_R=float(gd["VALID_net_R"].max()), best_test_net_R=float(gd["TEST_net_R"].max()))
        print(f"  {direction}: {decay}")
        a, tr = cfg_trades(best)
        vt = tr[tr["per"] >= 1]
        kk += 1
        name = (f"Reversal Signal Detector OPTIMIZED-{'ORIGINAL' if direction == 'orig' else 'INVERTED'} (selected on 2021-23 only: spike {best.spike}, look {int(best.look)}, {best.sess}, stop {best.stopm} ATR, RR {best.rr}), "
                f"MT5 XAUUSD 1-min, VALID 2024-01..2025-06 + TEST 2025-07..2026-09")
        # test_idea splits at 2025-07-01: its IS = VALID, its OOS = TEST (selection saw neither)
        row = H.test_idea(name, as_trades(vt), all_days, "MNQ", kk)
        rows_out.append(row)
        print(f"    selected {direction}: {dict(best[['spike','look','sess','stopm','rr']])}  TRAIN {a['TRAIN']['net_R']:+.3f}R (n {a['TRAIN']['n']}) VALID {a['VALID']['net_R']:+.3f}R (n {a['VALID']['n']}) TEST {a['TEST']['net_R']:+.3f}R (n {a['TEST']['n']}); win ALL {a['ALL']['win']:.1%}", flush=True)
        results[f"optimized_{direction}"] = dict(cfg={k: (v if isinstance(v, str) else float(v)) for k, v in best[["spike", "look", "sess", "stopm", "rr"]].items()}, agg=a, decay=decay,
                                                  row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"})
    lr = H.ledger_rows([{**r} for r in rows_out], "Round 311 (pre-registered, the trader's Reversal Signal Detector: original, inverted, optimized)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    with open(os.path.join(HERE, "round311_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote round311_results.json, round311_grid.csv and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
