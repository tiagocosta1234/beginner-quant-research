"""
Round 312 (2026-10-02, PRE-REGISTERED): the trader: "actually put it as it was but add more pips, look at the eurusd performance, can you spot any tweaks we could do to make this really profitable?"
"As it was" = the trader's ORIGINAL Reversal Signal Detector direction (not inverted; Round 311 found the inversion worse: -0.32R vs -0.25R on gold 1-minute). "More pips" = wider stop / target distances.
The chart is OANDA:EURUSD on the 5-minute timeframe (the 5-15 minute idea left open at the end of Round 311).

FIDELITY NOTE: the original's MACD-change thresholds are ABSOLUTE (+-0.01 in price units): meaningful on gold (price ~4,200) but ALWAYS TRUE on EURUSD (histogram changes are ~0.0001), so as written on EURUSD the
divergence + "histogram rising / falling" + ATR-spike conditions apply and the +-0.01 change test is a no-op; this is replicated as written, not rescaled.

Signal (unchanged from the original): bullish divergence (lowest close of `look` bars below the previous window's while the lowest RSI(14) is above the previous window's and the MACD histogram
change > -0.01) AND the MACD(12,26,9) histogram rising AND an ATR(14) spike (bar range > spike x ATR) -> LONG; mirror -> SHORT. Stop = stopM x ATR from the entry, target = RR x stop.

Step 0 (ledger checked first, k = 1999): Round 311 tested this signal on MT5 XAUUSD 1-minute: original -0.251R, inverted -0.322R, a 768-config TRAIN-only search found nothing profitable (the selected setting lost
0.06R on unseen data); gross (before spread) skill +0.09R, spread 0.34R of a 1 ATR stop. Not tested: EURUSD, the 5 and 15 minute timeframes, FX commission, wider stops (up to 4 ATR), a spread cap, a with-trend filter.
Honest expectation (stated before the run): EURUSD's median spread is 0.3 pip and MT5 broker's measured commission is $6 a lot round trip (0.6 pip), about 0.9 pip against a 1-minute ATR of about 1.4 pips: a 1 ATR stop on 1 minute
pays ~0.6R in costs, so only wider stops or a slower timeframe can even reach a break-even; the gross skill (+0.09R on gold) may not exist on EURUSD at all.

DATA: MT5 EURUSD M1 bid/ask (forex/early_mt5/data/EURUSD_M1_ticks_full.parquet via round271.load, New York time) 2021-10-04 .. 2026-09-30, aggregated to 1, 5 and 15 minute bars (bid open/high/low/close; ask high/low/close);
the indicator is computed on the bid candles of the chosen timeframe. Long entries at the ASK close of the signal bar, long stops / targets / timeouts on the BID book, shorts the reverse (stop wins a tie; fills at the level);
MT5 broker commission $6 per lot round trip = 0.6 pip charged in R; max hold 120 / 60 / 40 bars for 1 / 5 / 15 minutes; no position through a data gap (> 2 bars missing); one position at a time. R = the stop distance.
Splits (fixed): TRAIN 2021-10-04..2023-12-31, VALID 2024-01-01..2025-06-30, TEST 2025-07-01..2026-09-30.

THE TESTS
  (1) AS WRITTEN on EURUSD for each timeframe (1, 5, 15 minutes): spike 1.0, lookback 3, all sessions, stop 1 ATR, RR 2 (3 ledger rows).
  (2) DIAGNOSTICS on the TRAIN years only (not selection, not ledger): for the as-written signal and for a 3 ATR stop, net R by New York hour, by spike size (bar range / ATR), by spread in R, with / against the 200-bar EMA trend.
  (3) SEARCH (TRAIN-only selection): per timeframe, spike {0, 1.0, 1.5} x lookback {3, 5} x session {all, 03-12 New York} x stop {1, 2, 3, 4} ATR x RR {1, 2, 3} x spread cap {none, <= 1.5 x the 500-bar median spread}
      x trend {none, with the 200-bar EMA: longs above it, shorts below it} = 576 configurations per timeframe, 1,728 in all (the original direction only). Selection rule fixed now: among configurations with >= 400 TRAIN
      trades take the highest TRAIN mean net R over ALL timeframes (one winner); it is then read once on VALID and on TEST. It counts as "really profitable" only if VALID and TEST net R are both > 0 AND it passes
      idea_harness.test_idea's candidate bar at the new k on VALID + TEST. The TRAIN table and its decay on VALID / TEST are reported for the whole grid. Nothing is tuned after seeing VALID / TEST.
  Ledger rows (4): the three as-written rows (full period) and the one selected row (VALID + TEST only; VALID is its in-sample part, TEST its OOS). k -> 2003.
  CANDIDATE (idea_harness.test_idea): positive before AND after costs, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/k.

DRY-RUN COUNTS (no P&L read; the divergence logic is checked against a slow reference loop, the resolver against synthetic bars incl. the 0.6 pip commission):
  1,842,671 EURUSD M1 bars 2021-10-04..2026-09-30, median spread 0.30 pip. Median ATR14 / cost (spread + commission = 0.90 pip) as a share of a 1 ATR stop: 1-minute 1.34 pips / 0.67; 5-minute 3.33 pips / 0.27; 15-minute 6.12 pips / 0.15.
  Signals as written (spike 1.0, lookback 3, all sessions): 1-minute 3,379 (3,321 one-at-a-time trades), 5-minute 826 (808), 15-minute 272 (261). Spike 1.5 leaves 489 / 110 / 44; lookback 5 about half of lookback 3.
POWER: standard error of the mean net R at RR 2 is about 0.017R (1-minute, 3,321 trades), 0.035R (5-minute, 808), 0.065R (15-minute, 261); on VALID + TEST only (about 40% of the trades) 0.03 / 0.055 / 0.10R. The 15-minute and 5-minute rows
  cannot show an edge below about +0.1R / +0.15R net; most 15-minute and spike >= 1.5 configurations have < 400 TRAIN trades and cannot be selected. A winner among 1,728 configurations read on VALID + TEST needs both to be positive;
  with this many configurations a lucky TRAIN winner is expected unless the effect is real, which is what the VALID / TEST read tests.
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
TFS = [1, 5, 15]
HOLD = {1: 120, 5: 60, 15: 40}
RISK = 300.0
COMM = 0.00006                # $6 a lot round trip = 0.6 pip
TRAIN_END = pd.Timestamp("2024-01-01")
VALID_END = pd.Timestamp("2025-07-01")
SPIKES = [0.0, 1.0, 1.5]
LOOKS = [3, 5]
SESSIONS = ["ALL", "LDN_NY"]
STOPMS = [1.0, 2.0, 3.0, 4.0]
RRS = [1.0, 2.0, 3.0]
CAPS = [None, 1.5]
TRENDS = [False, True]
MIN_TRAIN = 400


def load_raw():
    df = M.load("EURUSD")
    return df[(df.index >= "2021-10-04") & (df.index < "2026-10-01")]


def build(df, tf):
    if tf == 1:
        b = pd.DataFrame(dict(bo=df["open"], bh=df["high"], bl=df["low"], bc=df["close"], ah=df["ask_high"], al=df["ask_low"], ac=df["ask_close"]))
    else:
        g = df.resample(f"{tf}min", label="left", closed="left")
        b = pd.DataFrame(dict(bo=g["open"].first(), bh=g["high"].max(), bl=g["low"].min(), bc=g["close"].last(), ah=g["ask_high"].max(), al=g["ask_low"].min(), ac=g["ask_close"].last(), n=g["close"].count()))
        b = b[b["n"] >= 1].drop(columns="n").dropna()
    t = b.index.values
    D = {k: b[k].to_numpy(float) for k in b.columns}
    D["t"] = t
    n = len(t)
    dt_min = np.r_[np.inf, np.diff(t).astype("timedelta64[s]").astype(float) / 60.0]
    gap = dt_min > max(10, 2 * tf)
    gi = np.flatnonzero(gap)
    nxt = np.full(n, n, dtype=np.int64)
    pos = np.searchsorted(gi, np.arange(n), side="right")
    ok = pos < len(gi)
    nxt[ok] = gi[pos[ok]]
    D["valid_len"] = np.minimum(np.minimum(nxt - np.arange(n) - 1, n - 1 - np.arange(n)), HOLD[tf])
    c, h, l = pd.Series(D["bc"]), pd.Series(D["bh"]), pd.Series(D["bl"])
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
    D["ema200"] = c.ewm(span=200, adjust=False).mean().values
    spr = pd.Series(D["ac"] - D["bc"])
    D["spr"] = spr.values
    D["spr_med"] = spr.rolling(500, min_periods=100).median().values
    nyh = pd.DatetimeIndex(t).hour
    D["sess"] = (nyh >= 3) & (nyh < 12)
    D["hour"] = np.asarray(nyh)
    D["tf"] = tf
    return D


def base_signals(D, spike, look, session):
    c, rsi, hist = pd.Series(D["bc"]), pd.Series(D["rsi"]), pd.Series(D["hist"])
    lc, lcp = c.rolling(look).min(), c.rolling(look).min().shift(1)
    hc, hcp = c.rolling(look).max(), c.rolling(look).max().shift(1)
    lr, lrp = rsi.rolling(look).min(), rsi.rolling(look).min().shift(1)
    hr, hrp = rsi.rolling(look).max(), rsi.rolling(look).max().shift(1)
    dh = hist.diff()
    bull = (lc < lcp) & (lr > lrp) & (dh > -0.01 * D["scale"])
    bear = (hc > hcp) & (hr < hrp) & (dh < 0.01 * D["scale"])
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
    H_ = HOLD[D["tf"]]
    return {k: sliding_window_view(D[k].astype(np.float64), H_)[idx + 1] for k in ("bl", "bh", "al", "ah", "bc", "ac")}


def resolve(D, idx, side, W, stopm, rr):
    HD = HOLD[D["tf"]]
    N = len(idx)
    dist = stopm * D["atr"][idx]
    vl = D["valid_len"][idx]
    beyond = np.arange(HD)[None, :] >= vl[:, None]
    entry = np.where(side > 0, D["ac"][idx], D["bc"][idx])
    stop = entry - side * dist
    tgt = entry + side * rr * dist
    lo_b = np.where(beyond, np.inf, W["bl"]); hi_b = np.where(beyond, -np.inf, W["bh"])
    lo_a = np.where(beyond, np.inf, W["al"]); hi_a = np.where(beyond, -np.inf, W["ah"])
    lm = (side > 0)[:, None]
    hit_stop = np.where(lm, lo_b <= stop[:, None], hi_a >= stop[:, None])
    hit_tgt = np.where(lm, hi_b >= tgt[:, None], lo_a <= tgt[:, None])
    fs = np.where(hit_stop.any(1), hit_stop.argmax(1), HD)
    ft = np.where(hit_tgt.any(1), hit_tgt.argmax(1), HD)
    stopped = (fs < HD) & (fs <= ft)
    targeted = (ft < HD) & (ft < fs)
    off = np.clip(np.where(stopped, fs, np.where(targeted, ft, vl - 1)), 0, HD - 1)
    ex_abs = idx + 1 + off
    exit_close = np.where(side > 0, W["bc"][np.arange(N), off], W["ac"][np.arange(N), off])
    r_fill = np.where(stopped, -1.0, np.where(targeted, rr, side * (exit_close - entry) / dist))
    cost_R = ((D["ac"][idx] - D["bc"][idx]) + (D["ac"][ex_abs] - D["bc"][ex_abs])) / 2.0 / dist + COMM / dist
    r_net = r_fill - COMM / dist
    return ex_abs, r_net, cost_R


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


def agg(r_net, cost_R, per):
    out = {}
    for nm, m in (("TRAIN", per == 0), ("VALID", per == 1), ("TEST", per == 2), ("ALL", per >= 0)):
        k = int(m.sum())
        out[nm] = dict(n=k, net_R=float(r_net[m].mean()) if k else float("nan"), gross_R=float((r_net[m] + cost_R[m]).mean()) if k else float("nan"), win=float((r_net[m] > 0).mean()) if k else float("nan"),
                       cost_R=float(cost_R[m].mean()) if k else float("nan"))
    return out


def masks(D, idx, sgn, cap, trend):
    m = np.ones(len(idx), bool)
    if cap is not None:
        m &= D["spr"][idx] <= cap * D["spr_med"][idx]
    if trend:
        m &= ((sgn == 1) & (D["bc"][idx] > D["ema200"][idx])) | ((sgn == -1) & (D["bc"][idx] < D["ema200"][idx]))
    return m


def make_trades(D, idx, ex_abs, r_net, cost_R, sgn, keep):
    ii, ee = idx[keep], ex_abs[keep]
    return pd.DataFrame(dict(entry_ts=pd.to_datetime(D["t"][ii]), exit_ts=pd.to_datetime(D["t"][ee]), direction=sgn[keep], r_gross=r_net[keep] + cost_R[keep], cost_R=cost_R[keep], r_net=r_net[keep],
                             per=period_of(D["t"][ii]), hour=D["hour"][ii], spread_R=(D["spr"][ii] / (1.0 * D["atr"][ii])), rng_atr=D["rng"][ii] / D["atr"][ii],
                             with_trend=(((sgn[keep] == 1) & (D["bc"][ii] > D["ema200"][ii])) | ((sgn[keep] == -1) & (D["bc"][ii] < D["ema200"][ii])))))


def as_trades(tr):
    if tr.empty:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r", "cost"])
    return pd.DataFrame(dict(entry_ts=tr["entry_ts"], exit_ts=tr["exit_ts"], direction=tr["direction"], contracts=1, pnl=tr["r_net"] * RISK, r=tr["r_gross"], cost=tr["cost_R"] * RISK))


def selftest():
    # divergence logic vs a slow reference (scale 1) and a resolver check with FX-sized prices
    rng = np.random.default_rng(2)
    n = 2000
    c = 1.1 + np.cumsum(rng.normal(0, 0.0003, n))
    D = dict(bc=c, rsi=np.clip(50 + np.cumsum(rng.normal(0, 3, n)), 1, 99), hist=np.cumsum(rng.normal(0, 0.0001, n)) * 0.2, rng=np.abs(rng.normal(0, 0.0005, n)) + 1e-5,
             atr=np.full(n, 0.0004), valid_len=np.full(n, 120), sess=np.ones(n, bool), t=np.arange(n).astype("datetime64[m]"), scale=1.0)
    s = base_signals(D, 0.0, 3, "ALL")
    ref = np.zeros(n, int)
    th = 0.01 * 1.0
    for i in range(305, n):
        lc, lcp = c[i - 2:i + 1].min(), c[i - 3:i].min()
        lr, lrp = D["rsi"][i - 2:i + 1].min(), D["rsi"][i - 3:i].min()
        hc, hcp = c[i - 2:i + 1].max(), c[i - 3:i].max()
        hr, hrp = D["rsi"][i - 2:i + 1].max(), D["rsi"][i - 3:i].max()
        dh = D["hist"][i] - D["hist"][i - 1]
        if lc < lcp and lr > lrp and dh > -th and D["hist"][i] > D["hist"][i - 1]:
            ref[i] = 1
        elif hc > hcp and hr < hrp and dh < th and D["hist"][i] < D["hist"][i - 1]:
            ref[i] = -1
    assert (s[305:] == ref[305:]).all()
    # resolve: long, 2R target reached on the bid on bar 12; commission 0.6 pip charged
    m = 200
    base = 1.1
    Dm = dict(t=np.arange(m).astype("datetime64[m]"), atr=np.full(m, 0.0004), valid_len=np.full(m, HOLD[1]), bc=np.full(m, base), ac=np.full(m, base + 0.00003), bl=np.full(m, base), bh=np.full(m, base),
              al=np.full(m, base + 0.00003), ah=np.full(m, base + 0.00003), tf=1)
    Dm["bh"][12] = base + 0.002
    idx = np.array([10]); sgn = np.array([1])
    W = windows(Dm, idx)
    ex, r, cst = resolve(Dm, idx, sgn, W, 1.0, 2.0)
    assert ex[0] == 12 and abs(r[0] - (2.0 - COMM / 0.0004)) < 1e-9, (ex, r)
    Dm["bl"][12] = base - 0.002
    W = windows(Dm, idx)
    ex, r, cst = resolve(Dm, idx, sgn, W, 1.0, 2.0)
    assert abs(r[0] - (-1.0 - COMM / 0.0004)) < 1e-9, r
    print("selftest ok")


def dry_run():
    selftest()
    t0 = time.time()
    df = load_raw()
    print(f"EURUSD M1 rows {len(df)} {df.index[0]} -> {df.index[-1]}; median spread {np.median(df['ask_close'] - df['close']) / 1e-4:.2f} pip")
    for tf in TFS:
        D = build(df, tf)
        D["scale"] = 1.0
        n = len(D["t"])
        print(f"\n{tf}-minute: {n} bars; median ATR14 {np.nanmedian(D['atr']) / 1e-4:.2f} pips; median spread+commission {(np.median(D['spr']) + COMM) / 1e-4:.2f} pips = {(np.median(D['spr']) + COMM) / np.nanmedian(D['atr']):.2f} of a 1 ATR stop")
        for sp in SPIKES:
            row = []
            for lk in LOOKS:
                for se in SESSIONS:
                    s = base_signals(D, sp, lk, se)
                    row.append(f"L{lk}/{se}: {int((s != 0).sum())}")
            print(f"  spike {sp}: " + " | ".join(row))
        s = base_signals(D, 1.0, 3, "ALL")
        idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + HOLD[tf] < n]
        W = windows(D, idx)
        ex, r, c = resolve(D, idx, s[idx], W, 1.0, 2.0)
        keep = one_at_a_time(idx, ex)
        print(f"  as-written one-at-a-time trades: {int(keep.sum())} of {len(idx)} signals (no P&L read)")
    print("\n--dry-run: counts only, no P&L is read.")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    selftest()
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    df = load_raw()
    all_days = sorted(set(pd.DatetimeIndex(df.index).normalize()))
    grid, results = [], {}
    DS = {}
    for tf in TFS:
        D = build(df, tf)
        D["scale"] = 1.0
        DS[tf] = D
        n = len(D["t"])
        for sp in SPIKES:
            for lk in LOOKS:
                for se in SESSIONS:
                    s = base_signals(D, sp, lk, se)
                    idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + HOLD[tf] < n]
                    sgn = s[idx]
                    W = windows(D, idx)
                    for stopm in STOPMS:
                        for rr in RRS:
                            ex, r, cst = resolve(D, idx, sgn, W, stopm, rr)
                            for cap in CAPS:
                                for tr_ in TRENDS:
                                    mk = masks(D, idx, sgn, cap, tr_)
                                    ii, ee, rr_, cc, sd = idx[mk], ex[mk], r[mk], cst[mk], sgn[mk]
                                    keep = one_at_a_time(ii, ee)
                                    per = period_of(D["t"][ii[keep]])
                                    a = agg(rr_[keep], cc[keep], per)
                                    grid.append(dict(tf=tf, spike=sp, look=lk, sess=se, stopm=stopm, rr=rr, cap=("none" if cap is None else cap), trend=tr_, **{f"{p}_{k}": v for p, d in a.items() for k, v in d.items()}))
                    del W
        print(f"  tf {tf}: grid rows {len(grid)} ({time.time() - t0:.0f}s)", flush=True)
    G = pd.DataFrame(grid)
    G.to_csv(os.path.join(HERE, "round312_grid.csv"), index=False)

    def cfg_trades(row):
        D = DS[int(row.tf)]
        n = len(D["t"])
        s = base_signals(D, float(row.spike), int(row.look), row.sess)
        idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + HOLD[int(row.tf)] < n]
        sgn = s[idx]
        W = windows(D, idx)
        ex, r, cst = resolve(D, idx, sgn, W, float(row.stopm), float(row.rr))
        cap = None if row.cap in ("none", None) else float(row.cap)
        mk = masks(D, idx, sgn, cap, bool(row.trend))
        ii, ee, rr_, cc, sd = idx[mk], ex[mk], r[mk], cst[mk], sgn[mk]
        keep = one_at_a_time(ii, ee)
        tr = make_trades(D, ii, ee, rr_, cc, sd, keep)
        return agg(rr_[keep], cc[keep], period_of(D["t"][ii[keep]])), tr

    kk = H.ledger_count()
    rows_out = []
    dflt = dict(spike=1.0, look=3, sess="ALL", stopm=1.0, rr=2.0, cap="none", trend=False)
    for tf in TFS:
        a, tr = cfg_trades(SimpleNamespace(tf=tf, **dflt))
        kk += 1
        name = f"Reversal Signal Detector AS WRITTEN (RSI/MACD divergence + ATR spike, stop 1 ATR target 2 ATR), MT5 EURUSD {tf}-min bid/ask + $6/lot commission, 2021-10..2026-09"
        row = H.test_idea(name, as_trades(tr), all_days, "MNQ", kk)
        rows_out.append(row)
        print(f"    as written {tf}m: win {a['ALL']['win']:.1%} net {a['ALL']['net_R']:+.3f}R gross {a['ALL']['gross_R']:+.3f}R cost {a['ALL']['cost_R']:.3f}R n {a['ALL']['n']} | TRAIN {a['TRAIN']['net_R']:+.3f} VALID {a['VALID']['net_R']:+.3f} TEST {a['TEST']['net_R']:+.3f}", flush=True)
        # diagnostics on TRAIN only
        d = {}
        t0_ = tr[tr["per"] == 0]
        if len(t0_):
            d["by_hour"] = {int(h_): dict(n=int(len(g)), net_R=float(g["r_net"].mean())) for h_, g in t0_.groupby("hour") if len(g) >= 30}
            d["by_spike_bucket"] = {str(k): dict(n=int(len(g)), net_R=float(g["r_net"].mean())) for k, g in t0_.groupby(pd.cut(t0_["rng_atr"], [0, 1.0, 1.5, 2.0, 3.0, 99])) if len(g) >= 30}
            d["by_spread_R_bucket"] = {str(k): dict(n=int(len(g)), net_R=float(g["r_net"].mean())) for k, g in t0_.groupby(pd.cut(t0_["spread_R"] + 0.0, [0, 0.1, 0.2, 0.3, 0.5, 99])) if len(g) >= 30}
            d["by_with_trend"] = {str(k): dict(n=int(len(g)), net_R=float(g["r_net"].mean()), gross_R=float(g["r_gross"].mean())) for k, g in t0_.groupby("with_trend")}
            d["by_side"] = {str(k): dict(n=int(len(g)), net_R=float(g["r_net"].mean())) for k, g in t0_.groupby("direction")}
        results[f"as_written_{tf}m"] = dict(agg=a, diag_train=d, row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"})
    gd = G[G["TRAIN_n"] >= MIN_TRAIN]
    best = gd.sort_values("TRAIN_net_R", ascending=False).iloc[0]
    pos = gd[gd["TRAIN_net_R"] > 0]
    decay = dict(n_configs=int(len(gd)), n_train_positive=int(len(pos)), n_train_positive_valid_positive=int((pos["VALID_net_R"] > 0).sum()),
                 n_train_positive_valid_and_test_positive=int(((pos["VALID_net_R"] > 0) & (pos["TEST_net_R"] > 0)).sum()),
                 median_train_net_R=float(gd["TRAIN_net_R"].median()), median_valid_net_R=float(gd["VALID_net_R"].median()), median_test_net_R=float(gd["TEST_net_R"].median()),
                 best_train_net_R=float(gd["TRAIN_net_R"].max()), best_valid_net_R=float(gd["VALID_net_R"].max()), best_test_net_R=float(gd["TEST_net_R"].max()),
                 by_tf_best_train={int(tf): float(gd[gd.tf == tf]["TRAIN_net_R"].max()) for tf in TFS if len(gd[gd.tf == tf])})
    print("  grid:", decay)
    a, tr = cfg_trades(best)
    vt = tr[tr["per"] >= 1]
    kk += 1
    name = (f"Reversal Signal Detector OPTIMIZED (selected on 2021-23 only: {int(best.tf)}-min, spike {best.spike}, look {int(best.look)}, {best.sess}, stop {best.stopm} ATR, RR {best.rr}, spread cap {best.cap}, with-trend {best.trend}), "
            f"MT5 EURUSD, VALID 2024-01..2025-06 + TEST 2025-07..2026-09")
    row = H.test_idea(name, as_trades(vt), all_days, "MNQ", kk)
    rows_out.append(row)
    print(f"    selected: {dict(best[['tf','spike','look','sess','stopm','rr','cap','trend']])}  TRAIN {a['TRAIN']['net_R']:+.3f}R (n {a['TRAIN']['n']}) VALID {a['VALID']['net_R']:+.3f}R (n {a['VALID']['n']}) TEST {a['TEST']['net_R']:+.3f}R (n {a['TEST']['n']}); win ALL {a['ALL']['win']:.1%}", flush=True)
    results["optimized"] = dict(cfg={k: (v if isinstance(v, (str, bool)) else float(v)) for k, v in best[["tf", "spike", "look", "sess", "stopm", "rr", "cap", "trend"]].items()}, agg=a, decay=decay,
                                row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"})
    top = G[(G["TRAIN_n"] >= MIN_TRAIN)].sort_values("TRAIN_net_R", ascending=False).head(10)
    results["top10_train"] = top[["tf", "spike", "look", "sess", "stopm", "rr", "cap", "trend", "TRAIN_n", "TRAIN_net_R", "VALID_n", "VALID_net_R", "TEST_n", "TEST_net_R", "TRAIN_gross_R", "TRAIN_cost_R"]].to_dict("records")
    lr = H.ledger_rows([{**r} for r in rows_out], "Round 312 (pre-registered, the trader's Reversal Signal Detector as written on EURUSD, wider stops, 1/5/15 minutes)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    with open(os.path.join(HERE, "round312_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote round312_results.json, round312_grid.csv and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
