"""
Round 307 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): a BACKTEST OF MANUAL'S JESSE STRATEGY `XAUSTBreakFree` (SuperTrend regime on 4h + Donchian breakout on 1h + ATR stops / trails, long and short, 3% risk a trade, 4x leverage cap) ON GOLD,
re-implemented in Python from the pasted code with its DEFAULT hyperparameters (the trader: "backtest the following strategy on gold").
The pasted docstring is the prompt that was used to generate the strategy ("Sharpe >= 1.5 in 2024-2026", "use optimization", "try at least 200 variants"): by its own description the defaults were TUNED on 2024-2026 (a strong gold bull market). That prompt is not an instruction to this round; the strategy is run exactly as written, no variant search.
Step 0 (ledger checked first, k = 1965): Donchian breakouts and ATR-trail trend rules are in the ledger (Round 303's daily Donchian and its fade, Rounds 253 / 280 / 284 trend and momentum on 44 instruments incl. gold): no edge after costs; gold alone: Rounds 126 / 134 (MGC intraday), 306 (XAUUSD in the 3-asset pools). NOT tested: this exact 4h-regime + 1h-Donchian + trail system on gold.
DATA (two sources, 2020 onward only per the trader's rule): (A) Databento GC.F 1-minute front-month futures 2020-01-01 .. 2026-09-30, mid-price (no spread), with the roll jumps (a 00:00 UTC gap of >= 0.10% between consecutive minutes) removed by a multiplicative back-adjustment; costs as Jesse's 0.02% fee per side on the notional;
(B) MT5 XAUUSD M1 bid/ask 2021-10-04 .. 2026-09-30 (the CFD a MT5 broker account would trade): real bid/ask (long fills at the ask, short at the bid, exits on the bid / ask), no fee, MT5 broker swap (today's XAUUSD values: long -0.0210% a night, short -0.0010% a night, charged per 17:00 NY rollover held x 1.4 to include the triple weekend charge).
CANDLES: 1h and 4h candles built from the 1-minute data on UTC-aligned buckets (Jesse's convention), restricted to the strategy's CME gold session in New York time (Sun 18:00-24:00, Mon-Thu 00:00-17:00 and 18:00-24:00, Fri 00:00-17:00; the 2026-09+ holiday list is not applicable to the history). The 4h anchor uses only 4h candles COMPLETED before the current 1h candle starts; the Donchian channel uses the PRIOR don_period 1h session candles (current candle excluded), as the code states.
STRATEGY AS CODED (hyperparameter defaults): SuperTrend(24, 4.0) and EMA(10) on the 4h anchor give the regime (long if the 1h close is above the SuperTrend line and above the 4h EMA, short if below both; else 0); entries at the 1h close inside the session: LONG if regime = +1, 4h ADX(14) >= 10 and close > the 85-bar Donchian high; SHORT if regime = -1, ADX >= 15 and close < the 85-bar Donchian low; ATR = 4h ATR(14);
long stop = entry - 3.0 ATR, no target; short stop = entry + 4.0 ATR and take-profit = entry - 5.0 ATR; trailing (updated at each 1h close, the best close since entry): long stop -> best close - 6.5 ATR when above the current stop and below the close, short stop -> best close + 3.5 ATR when below the current stop and above the close; exit_on_flip = 0; size = min(3% of equity / stop distance x entry, 4 x equity) in USD notional; one position at a time; stops and targets are checked on every 1-minute bar (stop-first on ties, a gap through a level fills at the bar open).
REPORTED per source and window: trades, win rate, profit factor, total return, annualised return (CAGR), maximum drawdown of the mark-to-market equity, annualised Sharpe of business-day returns (sqrt(252)), the long and short contributions; WINDOWS: full, PRE = before 2024-01-01 (NOT used by the generating prompt's optimisation: the out-of-sample view), TUNE = 2024-01-01 .. 2026-09-30 (the window the prompt optimised on).
BENCHMARKS: buy-and-hold gold over the same window; a COIN-FLIP-DIRECTION placebo on the same signal days (every signal day takes a random side with that side's own stop / target / trail rules, 20 seeds), which separates the entry rule from the gold drift and the exit geometry.
SENSITIVITY (descriptive, source A): each of the 12 hyperparameters moved one step down and one step up from its default (24 neighbours), full window: the spread of Sharpe and return shows how much of the default's result is a knife-edge of the tuning.
PRIOR (stated now): TUNE-window Sharpe near the prompt's claim (about 1.5-2, gold rose from ~2,060 to 4,100+ in the window); PRE-window clearly lower (about 0 to 0.8) and the long side carrying most of it; the coin-flip placebo capturing a large part of the TUNE-window return (the trend and the 4 x ATR trail geometry on a rising market); the neighbours' Sharpe in the TUNE window spread over about 0.5-2 (the default sits near the top). No claim of an edge will be made unless PRE and TUNE agree and the placebo is clearly beaten.
POWER_NOTES: ~100-200 trades per window; a Sharpe standard error of ~0.45 on 5 years; the default hyperparameters are not independent of the TUNE window; costs of source A are an assumption (Jesse's 0.02% a side), source B's spread and swap are MT5 broker's.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

DEFAULT = dict(st_period=24, st_factor=4.0, ema4=10, don_period=85, atr_stop=3.0, trail_atr=6.5, exit_on_flip=0, l_adx=10, s_adx=15, s_stop=4.0, s_trail=3.5, s_tp=5.0)
STEPS = dict(st_period=(7, 40, 1), st_factor=(1.5, 5.0, 0.5), ema4=(0, 100, 10), don_period=(10, 100, 5), atr_stop=(1.0, 5.0, 0.5), trail_atr=(1.5, 8.0, 0.5), exit_on_flip=(0, 1, 1), l_adx=(0, 40, 1), s_adx=(0, 40, 1), s_stop=(0.5, 4.0, 0.5), s_trail=(1.0, 6.0, 0.5), s_tp=(0.0, 6.0, 0.5))
RISK, MAXLEV = 0.03, 4.0
FEE_A = 0.0002
SWAP_L, SWAP_S, SWAP_K = -0.00021038586368553916, -1.009736747205193e-05, 1.4
TUNE_FROM = pd.Timestamp("2024-01-01")


# ------------------------------------------------------------------ data
def load(name):
    if name == "A":
        d = pd.read_parquet(os.path.join(ROOT, "futures", "data", "databento", "futures_GC.F_1m.parquet"))
        t = pd.DatetimeIndex(pd.to_datetime(d["ts"], utc=True)).tz_convert("UTC").tz_localize(None)
        o, h, l, c = (d[k].values.astype(float) for k in ("open", "high", "low", "close"))
        ok = t >= pd.Timestamp("2020-01-01")
        t, o, h, l, c = t[ok], o[ok], h[ok], l[ok], c[ok]
        # roll back-adjustment: a 00:00 UTC gap of >= 0.10% between consecutive minutes
        gap = np.zeros(len(t)); gap[1:] = o[1:] / c[:-1] - 1.0
        mins = t.hour * 60 + t.minute
        rolls = np.flatnonzero((np.abs(gap) >= 0.001) & (mins == 0) & (np.r_[False, np.diff(t.values).astype("timedelta64[m]").astype(int) <= 1]))
        adj = np.ones(len(t))
        for r in rolls:
            adj[:r] *= o[r] / c[r - 1]
        o, h, l, c = o * adj, h * adj, l * adj, c * adj
        return dict(t=t, o=o, h=h, l=l, c=c, bo=o, bh=h, bl=l, bc=c, ao=o, ah=h, al=l, ac=c, rolls=len(rolls))
    sys.path.insert(0, HERE)
    import round271_one_to_one_generator as M
    df = M.load("XAUUSD")
    df = df[(df.index >= "2021-10-04") & (df.index < "2026-10-01")]
    t = df.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
    keep = ~pd.isna(t)
    t = t[keep].tz_convert("UTC").tz_localize(None)
    g = lambda k: df[k].values.astype(float)[keep]
    bo, bh, bl, bc, ao, ah, al, ac = (g(k) for k in ("open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close"))
    return dict(t=t, o=(bo + ao) / 2, h=(bh + ah) / 2, l=(bl + al) / 2, c=(bc + ac) / 2, bo=bo, bh=bh, bl=bl, bc=bc, ao=ao, ah=ah, al=al, ac=ac, rolls=0)


def in_session(ts_utc):
    ny = pd.DatetimeIndex(ts_utc).tz_localize("UTC").tz_convert("America/New_York")
    dow, hr = ny.dayofweek.values, ny.hour.values
    return ((dow == 6) & (hr >= 18)) | ((dow <= 3) & ((hr < 17) | (hr >= 18))) | ((dow == 4) & (hr < 17))


def agg(D, freq):
    s = D["t"].floor(freq)
    df = pd.DataFrame({"s": s, "o": D["o"], "h": D["h"], "l": D["l"], "c": D["c"], "i": np.arange(len(s))})
    g = df.groupby("s", sort=True)
    out = pd.DataFrame({"o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last()})
    out["i0"], out["i1"] = g["i"].min().values, g["i"].max().values + 1
    return out


# ------------------------------------------------------------------ indicators on the 4h anchor (session candles only)
def wilder(x, p):
    out = np.full(len(x), np.nan)
    if len(x) < p:
        return out
    out[p - 1] = np.mean(x[:p])
    for i in range(p, len(x)):
        out[i] = (out[i - 1] * (p - 1) + x[i]) / p
    return out


def true_range(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))


def atr(h, l, c, p=14):
    return wilder(true_range(h, l, c), p)


def adx(h, l, c, p=14):
    up, dn = np.r_[0, np.diff(h)], np.r_[0, -np.diff(l)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(h, l, c)
    atr_ = wilder(tr, p)
    pdi = 100 * wilder(pdm, p) / atr_; mdi = 100 * wilder(mdm, p) / atr_
    dx = 100 * np.abs(pdi - mdi) / np.where(pdi + mdi == 0, np.nan, pdi + mdi)
    out = np.full(len(c), np.nan)
    ok = np.flatnonzero(np.isfinite(dx))
    if len(ok) >= p:
        s = ok[0]
        out[s + p - 1] = np.mean(dx[s:s + p])
        for i in range(s + p, len(c)):
            out[i] = (out[i - 1] * (p - 1) + dx[i]) / p
    return out


def ema(x, n):
    a = 2.0 / (n + 1); out = np.empty(len(x)); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def supertrend(h, l, c, p, f):
    a = atr(h, l, c, p)
    hl2 = (h + l) / 2
    ub, lb = hl2 + f * a, hl2 - f * a
    fu, fl = ub.copy(), lb.copy()
    line = np.full(len(c), np.nan); dirn = np.ones(len(c))
    for i in range(1, len(c)):
        if not np.isfinite(a[i]):
            fu[i], fl[i] = np.nan, np.nan
            continue
        pu, pl = fu[i - 1], fl[i - 1]
        fu[i] = ub[i] if (not np.isfinite(pu)) or ub[i] < pu or c[i - 1] > pu else pu
        fl[i] = lb[i] if (not np.isfinite(pl)) or lb[i] > pl or c[i - 1] < pl else pl
        if dirn[i - 1] == 1 and c[i] < fl[i]:
            dirn[i] = -1
        elif dirn[i - 1] == -1 and c[i] > fu[i]:
            dirn[i] = 1
        else:
            dirn[i] = dirn[i - 1]
        line[i] = fl[i] if dirn[i] == 1 else fu[i]
    return line


# ------------------------------------------------------------------ backtest
class Prep:
    pass


def prepare(D, hp):
    P = Prep()
    P.D = D
    h1 = agg(D, "1h"); h4 = agg(D, "4h")
    P.h1, P.h4 = h1, h4
    P.i0, P.i1 = h1["i0"].values.astype(int), h1["i1"].values.astype(int)
    s1 = in_session(h1.index.values); s4 = in_session(h4.index.values)
    P.s1 = s1
    a = h4[s4]
    P.a_end = (a.index + pd.Timedelta(hours=4)).values                           # end of each 4h anchor candle
    ah, al, ac = a["h"].values, a["l"].values, a["c"].values
    P.atr = atr(ah, al, ac, 14); P.adx = adx(ah, al, ac, 14)
    P.stline = supertrend(ah, al, ac, hp["st_period"], hp["st_factor"])
    P.ema = ema(ac, hp["ema4"]) if hp["ema4"] > 0 else None
    # Donchian over the PRIOR session 1h candles
    sess = h1[s1]
    P.sess_idx = np.flatnonzero(s1)
    hi = pd.Series(sess["h"].values).shift(1).rolling(hp["don_period"], min_periods=hp["don_period"]).max().values
    lo = pd.Series(sess["l"].values).shift(1).rolling(hp["don_period"], min_periods=hp["don_period"]).min().values
    P.don_hi = np.full(len(h1), np.nan); P.don_lo = np.full(len(h1), np.nan)
    P.don_hi[P.sess_idx] = hi; P.don_lo[P.sess_idx] = lo
    return P


def run(P, hp, mode, window=None, placebo_seed=None):
    """mode 'A' (mid, 0.02% fee a side) or 'B' (bid / ask, swap). Returns dict of trades and an equity curve (hourly)."""
    D, h1 = P.D, P.h1
    nh = len(h1)
    hs = h1.index.values
    c1 = h1["c"].values
    rng = np.random.default_rng(placebo_seed) if placebo_seed is not None else None
    eq = 1.0
    eqs = np.full(nh, np.nan)
    trades = []
    pos = None
    t0 = np.datetime64("2020-01-01") if window is None else np.datetime64(window[0])
    t1 = np.datetime64("2026-10-01") if window is None else np.datetime64(window[1])
    a_end = P.a_end
    ny = pd.DatetimeIndex(hs).tz_localize("UTC").tz_convert("America/New_York")
    rolls_hour = ((ny.hour.values == 17) & (ny.dayofweek.values <= 4))                    # the 17:00-18:00 NY hour starts after a rollover at 17:00 NY
    for i in range(nh):
        tt = hs[i]
        if tt < t0 or tt >= t1:
            eqs[i] = eq
            continue
        i0, i1_ = int(P.i0[i]), int(P.i1[i])
        # 1) manage the open position on this hour's 1-minute bars
        if pos is not None and i0 >= pos["start_i"]:
            side = pos["side"]
            sl = slice(i0, i1_)
            if side > 0:
                lows, highs, opens = D["bl"][sl], D["bh"][sl], D["bo"][sl]
                hit_s = lows <= pos["stop"]
                hit_t = np.zeros(len(lows), bool)
            else:
                lows, highs, opens = D["al"][sl], D["ah"][sl], D["ao"][sl]
                hit_s = highs >= pos["stop"]
                hit_t = (lows <= pos["tp"]) if pos["tp"] is not None else np.zeros(len(lows), bool)
            js = int(np.argmax(hit_s)) if hit_s.any() else None
            jt = int(np.argmax(hit_t)) if hit_t.any() else None
            ex = None
            if js is not None and (jt is None or js <= jt):
                px = min(pos["stop"], opens[js]) if side > 0 else max(pos["stop"], opens[js])
                ex = (px, i0 + js)
            elif jt is not None:
                px = min(pos["tp"], opens[jt])
                ex = (px, i0 + jt)
            if ex is not None:
                eq = close_trade(P, pos, ex[0], ex[1], mode, trades, eq, tt)
                pos = None
        # swap rollovers counted at hour starts of 17:00 NY
        if pos is not None and rolls_hour[i]:
            pos["rolls"] += 1
        # 2) at the hour close: update the position or look for an entry
        mark = eq
        if pos is not None:
            side = pos["side"]
            pos["best"] = max(pos["best"], c1[i]) if side > 0 else min(pos["best"], c1[i])
            k = np.searchsorted(a_end, tt, side="right") - 1                      # anchor candles completed by the start of this hour
            if k >= 14 and np.isfinite(P.atr[k]):
                atr4 = P.atr[k]
                if side > 0:
                    trail = pos["best"] - atr4 * hp["trail_atr"]
                    if pos["stop"] < trail < c1[i]:
                        pos["stop"] = trail
                else:
                    trail = pos["best"] + atr4 * hp["s_trail"]
                    if c1[i] < trail < pos["stop"]:
                        pos["stop"] = trail
            mark = eq * (1 + pos["side"] * pos["units_frac"] * (c1[i] / pos["entry_mid"] - 1))
        elif P.s1[i] and np.isfinite(P.don_hi[i]):
            k = np.searchsorted(a_end, tt, side="right") - 1
            if k >= 30 and np.isfinite(P.atr[k]) and np.isfinite(P.stline[k]) and np.isfinite(P.adx[k]):
                c = c1[i]
                regime = 1 if c > P.stline[k] else -1
                if hp["ema4"] > 0 and P.ema is not None:
                    if (regime == 1 and c < P.ema[k]) or (regime == -1 and c > P.ema[k]):
                        regime = 0
                side = 0
                if regime == 1 and (hp["l_adx"] <= 0 or P.adx[k] >= hp["l_adx"]) and c > P.don_hi[i]:
                    side = 1
                elif regime == -1 and (hp["s_adx"] <= 0 or P.adx[k] >= hp["s_adx"]) and c < P.don_lo[i]:
                    side = -1
                if side != 0:
                    if rng is not None:
                        side = 1 if rng.random() < 0.5 else -1
                    atr4 = P.atr[k]
                    if side > 0:
                        stop = c - atr4 * hp["atr_stop"]; tp = None
                    else:
                        stop = c + atr4 * hp["s_stop"]; tp = c - atr4 * hp["s_tp"] if hp["s_tp"] > 0 else None
                    dist = abs(c - stop)
                    if dist > 0:
                        notional_frac = min(RISK * c / dist, MAXLEV)             # notional as a multiple of equity
                        fill = (D["ac"][i1_ - 1] if side > 0 else D["bc"][i1_ - 1]) if mode == "B" else c
                        pos = dict(side=side, stop=stop, tp=tp, best=c, entry_mid=c, entry_fill=fill, units_frac=notional_frac, start_i=i1_, entry_t=tt, rolls=0, eq0=eq)
        eqs[i] = mark
    return trades, eqs


def close_trade(P, pos, px, idx, mode, trades, eq, tt):
    side = pos["side"]
    gross = pos["units_frac"] * side * (px / pos["entry_fill"] - 1.0)
    if mode == "A":
        cost = FEE_A * pos["units_frac"] * (1 + px / pos["entry_fill"])
    else:
        cost = -pos["units_frac"] * (SWAP_L if side > 0 else SWAP_S) * SWAP_K * pos["rolls"]
    r = gross - cost
    new = eq * (1 + r)
    trades.append(dict(entry=pos["entry_t"], exit=tt, side=side, ret=r, gross=gross, cost=cost))
    return new


def stats(trades, eqs, hs, window, bench):
    t0, t1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    ts = pd.DatetimeIndex(hs)
    s = pd.Series(eqs, index=ts).ffill()
    s = s[(s.index >= t0) & (s.index < t1)].dropna()
    if len(s) < 100:
        return None
    daily = s.resample("1D").last().dropna()
    daily = daily[daily.index.dayofweek <= 4]
    r = daily.pct_change().dropna()
    yrs = (daily.index[-1] - daily.index[0]).days / 365.25
    dd = float(((daily / daily.cummax()) - 1).min())
    tr = [x for x in trades if t0 <= pd.Timestamp(x["exit"]) < t1]
    rets = np.array([x["ret"] for x in tr]) if tr else np.array([0.0])
    win = rets[rets > 0].sum(); lossv = -rets[rets <= 0].sum()
    tot = float(daily.iloc[-1] / daily.iloc[0] - 1)
    longs = [x for x in tr if x["side"] > 0]; shorts = [x for x in tr if x["side"] < 0]
    return dict(trades=len(tr), win=float(np.mean(rets > 0)) if tr else 0.0, pf=float(win / lossv) if lossv > 0 else float("inf"), total=tot, cagr=float((1 + tot) ** (1 / yrs) - 1) if yrs > 0 else 0.0, maxdd=dd,
                sharpe=float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0, long_n=len(longs), long_sum=float(sum(x["ret"] for x in longs)), short_n=len(shorts), short_sum=float(sum(x["ret"] for x in shorts)),
                bench=bench)


def bench_ret(D, window):
    t0, t1 = np.datetime64(window[0]), np.datetime64(window[1])
    m = (D["t"].values >= t0) & (D["t"].values < t1)
    c = D["c"][m]
    return float(c[-1] / c[0] - 1) if m.any() else float("nan")


WIN_A = {"FULL": ("2020-01-01", "2026-10-01"), "PRE": ("2020-01-01", "2024-01-01"), "TUNE": ("2024-01-01", "2026-10-01")}
WIN_B = {"FULL": ("2021-10-04", "2026-10-01"), "PRE": ("2021-10-04", "2024-01-01"), "TUNE": ("2024-01-01", "2026-10-01")}
WINDOWS = WIN_A


def dry_run():
    # indicator sanity: SuperTrend on a clean uptrend stays below price; ATR/ADX finite; EMA seed
    n = 200
    c = np.linspace(100, 200, n) + np.sin(np.arange(n)) * 0.5
    h, l = c + 1, c - 1
    st = supertrend(h, l, c, 10, 3.0)
    assert np.all(st[30:] < c[30:]) and np.isfinite(adx(h, l, c)[-1]) and adx(h, l, c)[-1] > 25
    print("indicator sanity: SuperTrend below price in a clean uptrend, ADX high")
    for name in ("A", "B"):
        t = time.time()
        D = load(name)
        print(f"source {name}: {len(D['t']):,} one-minute bars {D['t'][0]} .. {D['t'][-1]}, back-adjusted rolls {D['rolls']}, price now {D['c'][-1]:.1f}, loaded in {time.time() - t:.0f}s")
        P = prepare(D, DEFAULT)
        print(f"   1h candles {len(P.h1):,} ({int(P.s1.sum()):,} in session), 4h anchor candles in session {len(P.a_end):,}, Donchian ready on {int(np.isfinite(P.don_hi).sum()):,} hours")
        # the Donchian value of an hour excludes that hour's own high: it equals the max of the PREVIOUS don_period session highs
        sess_h = P.h1["h"].values[P.sess_idx]
        j = 500
        assert abs(P.don_hi[P.sess_idx[j]] - sess_h[j - DEFAULT["don_period"]:j].max()) < 1e-9
        i = int(P.sess_idx[j])
        hs0 = P.h1.index.values[i]
        k = np.searchsorted(P.a_end, hs0, side="right") - 1
        assert P.a_end[k] <= hs0
        print("   Donchian excludes the current candle and the anchor is complete before the hour starts: checks passed")
        t = time.time()
        tr, eqs = run(P, DEFAULT, name, window=("2024-01-01", "2024-03-01"))
        print(f"   a two-month run in {time.time() - t:.1f}s: {len(tr)} trades (results not printed)")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    out = {}
    for name in ("A", "B"):
        D = load(name)
        P = prepare(D, DEFAULT)
        hs = P.h1.index.values
        trades, eqs = run(P, DEFAULT, name)
        out[name] = {}
        wins = WIN_A if name == "A" else WIN_B
        for w, win in wins.items():
            b = bench_ret(D, win)
            st = stats(trades, eqs, hs, win, b)
            out[name][w] = st
            if st:
                print(f"[{name}] {w:>4} {win[0]}..: trades {st['trades']:>3}, win {st['win']:.0%}, PF {st['pf']:.2f}, return {st['total']:+.1%} (CAGR {st['cagr']:+.1%}), max DD {st['maxdd']:.1%}, Sharpe {st['sharpe']:+.2f} | long {st['long_n']} trades {st['long_sum']:+.1%}, short {st['short_n']} trades {st['short_sum']:+.1%} | gold buy-and-hold {b:+.1%}", flush=True)
        # by year
        yr = {}
        s = pd.Series(eqs, index=pd.DatetimeIndex(hs)).ffill()
        for y in range(2020, 2027):
            a, b_ = s[(s.index >= f"{y}-01-01") & (s.index < f"{y + 1}-01-01")].dropna(), None
            if len(a) > 50:
                yr[y] = float(a.iloc[-1] / a.iloc[0] - 1)
        out[name]["by_year"] = yr
        print(f"[{name}] by calendar year: " + ", ".join(f"{y} {v:+.1%}" for y, v in yr.items()), flush=True)
        # placebo: coin-flip direction on the same signal days
        plc = {w: [] for w in wins}
        for seed in range(20):
            tr_p, eq_p = run(P, DEFAULT, name, placebo_seed=seed)
            for w, win in wins.items():
                st = stats(tr_p, eq_p, hs, win, 0.0)
                if st:
                    plc[w].append((st["sharpe"], st["total"], st["trades"]))
        out[name]["placebo"] = {w: dict(sharpe=float(np.mean([a[0] for a in v])), sharpe_sd=float(np.std([a[0] for a in v])), total=float(np.mean([a[1] for a in v])), trades=float(np.mean([a[2] for a in v]))) for w, v in plc.items() if v}
        for w, v in out[name]["placebo"].items():
            print(f"[{name}] coin-flip placebo {w:>4}: mean Sharpe {v['sharpe']:+.2f} (sd {v['sharpe_sd']:.2f}), mean return {v['total']:+.1%}, {v['trades']:.0f} trades", flush=True)
        print(f"[{name}] done ({time.time() - t0:.0f}s)", flush=True)
        if name == "A":
            sens = []
            for k, (lo, hi, st_) in STEPS.items():
                for sgn in (-1, 1):
                    v = DEFAULT[k] + sgn * st_
                    if v < lo or v > hi:
                        continue
                    hp = dict(DEFAULT); hp[k] = type(DEFAULT[k])(v)
                    Pq = prepare(D, hp)
                    trq, eqq = run(Pq, hp, "A")
                    row = dict(param=k, value=hp[k])
                    for w in ("PRE", "TUNE"):
                        s_ = stats(trq, eqq, hs, WIN_A[w], 0.0)
                        row[w] = dict(sharpe=s_["sharpe"], total=s_["total"], trades=s_["trades"]) if s_ else None
                    sens.append(row)
            out["sensitivity"] = sens
            for w in ("PRE", "TUNE"):
                sh = [r[w]["sharpe"] for r in sens if r[w]]
                print(f"[A] sensitivity {w}: {len(sh)} neighbours, Sharpe min {min(sh):+.2f}, median {np.median(sh):+.2f}, max {max(sh):+.2f} (default {out['A'][w]['sharpe']:+.2f})", flush=True)
    json.dump(out, open(os.path.join(HERE, "round307_results.json"), "w"), indent=1, default=float)
    print(f"Saved round307_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
