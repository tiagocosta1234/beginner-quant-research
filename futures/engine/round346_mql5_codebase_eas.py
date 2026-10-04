"""
Round 346 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): 15 public MT5 Expert Advisors from the MQL5 CodeBase, rebuilt from their published source and tested on
MT5 broker data, against the trader's bar: a plan that passes the MT5 1-Step $100K within 30 calendar days with probability >= 70%.

Why (disclosed): Round 345 showed 70% needs about +0.25 R a trade of real edge; no idea in 345 rounds came close. the trader asked whether public MT5 bots can be used.
SOURCE: www.mql5.com/en/code/mt5/experts, pages 1-4 read 2026-10-04 (160 entries, 99 trading EAs). Shortlist rule (fixed before reading any code): a trading EA whose
default symbol is in the MT5 broker data here (US100 / US500 / US30 / US2000 / GER40 / UK100 / FRA40 cash indices, XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF) or
that names no symbol (then tested on XAUUSD, US100.cash and EURUSD), with stated rules, and NOT a grid / martingale / recovery / averaging system (they hide losses; a
3% daily limit makes them unusable). 16 sources downloaded (futures/data/mql5_codebase/); 003-Weekly-Day-Reversal with its defaults (Monday, reverse) IS
001-Turnaround-Tuesday, so it is not counted twice: 15 EAs, 27 cells (EA x symbol; first written as 25, a counting slip found after the run: BH used all 27 p-values).
REBUILD: each EA's DEFAULT inputs (and the source's internal constants), its stated timeframe, rules read from the .mq5, signals on closed bars of MT5 broker bars built in SERVER
time (the MT5 broker server is the common GMT+2/+3 New-York-close clock, so server-time inputs are used as written). Fills on MT5 M1 bid / ask: market orders at the next bar
open (long at the ask, short at the bid); stop orders fill when the ask (buy) / bid (sell) reaches the level, at the level or the worse open on a gap; a long is stopped /
targeted on the bid, a short on the ask; stop wins a minute that touches both; on a stop-order entry minute only the stop is checked. Costs: the spread in the data,
commission 0.6 bp round trip on FX, 0.2 bp on gold, 0 on index CFDs; MT5 broker swap from the D1 manifests (points per lot per night, triple on swap_rollover3days).
Indicators follow MT5's definitions (EMA, SMA-of-TR ATR, Wilder RSI and ADX, Bollinger on the stated price, the EAs' own stochastic / Supertrend code); small
initialization differences from MT5 are possible and disclosed. Trades longer than 60 calendar days are closed at that point (none of the EAs is meant to hold that long).
CELLS (EA id: rule summary, symbol, timeframe):
  77691 Gold Breakout: close > 20-bar high (first such close) and > EMA200, long only, stop 2 ATR(20), target 2R; XAUUSD H4
  77900 Stochastic Daily Breakout: stochastic signal-line turn + Bollinger(9, weighted) filter -> stop order at yesterday's high / low, stop and target 1.9%, expiry 9 bars; XAUUSD H1
  77639 SMC Gold: swing (5 / 5) liquidity sweep >= 0.15 ATR, order-block close-through within 3 bars (range >= 0.3 ATR), H1 EMA50 trend, stop beyond the wick + 0.1 ATR (>= 0.5 ATR), 2R; XAUUSD M15
  77748 ZoneUS30: sell after a return to the zone around yesterday's high (0.12% zone, 0.40% pullback stage), stop +4%, target -0.75%; US30.cash M30
  77738 RSI Exhaustion: sell when RSI(14) crosses up through 65 between 14:00 and 18:00 server, spread <= 0.15 ATR, stop / target 4 ATR(14), max 96 bars; EURUSD M5
  73638 Long-only Breakout: close > previous bar's high -> buy, stop at the bar's low (>= 5,000 points), target 1R; US100.cash H4
  77718 Stormbreaker ADX: Supertrend(10, 3) + ADX(14) >= 23 + DI agreement, stop 2 ATR(10), exit on ADX < 18 or Supertrend flip; XAUUSD, US100.cash, EURUSD H4
  77967 ORB Risk Managed: 16:30-16:45 server range, stop orders 20 points outside, stop = range, 2R, last entry 18:30, flat 22:45, range 0.05-0.60 daily ATR; US100.cash
  76153 Session ORB: 08:00 server + 30 min range, close beyond range +- 20 points on M5 within 120 min, stop beyond the other side + 30 points, 2R; XAUUSD, US100.cash, EURUSD
  75586 Gold London Breakout: Asian range 00-07 server (0.15-0.70 daily ATR), stop orders 0.15 ATR outside from 07:00, stop 1.2 ATR, 1.8R, expiry 11:00, OCO; XAUUSD M15
  73674 Turnaround Tuesday: Tuesday opposite to Monday's candle, stop 0.5 daily ATR(14), 2.5R, flat 22:00 server; US500.cash, US100.cash, EURUSD, XAUUSD
  73884 Inside Bar: main bar body >= 80%, inside bar <= 50% of it, stop order at the main bar's high (bullish) / low (bearish), stop 0.62 x main range, 2.5R, expiry 3 bars; D1 on XAUUSD, US100.cash, EURUSD
  68082 4H Range Fakeout: first 4 hours of the New York day, M5 close back inside after a close outside -> reverse, stop at the excursion extreme, 2R; EURUSD, XAUUSD, US100.cash M5
  69545 VR Breakdown Level: buy when the ask reaches the previous bar's high, sell when the bid reaches its low, stop 200 / target 400 points; EURUSD H1
  73958 ADX Trend Pullback: ADX(14) > 25 and rising, distance to EMA20 crosses below 0.5 ATR, side by DI, stop 1.5 ATR(14), 2R; XAUUSD, EURUSD H1
STATISTICS per cell: trades, win rate, mean net R a trade (R = initial stop distance), profit factor, IS (exits before 2024-01-01) and OOS (from 2024-01-01) mean R,
day-clustered bootstrap P(mean R > 0) over all trades (5,000 draws, seed 346). CANDIDATE (fixed now): Benjamini-Hochberg q = 0.10 over the 27 one-sided p-values AND mean
R > 0 in both IS and OOS. For EVERY cell (candidate or not) the 1-Step replay: every start day, the EA's own trades taken in order inside 30 calendar days, risk 1% and
2% of the initial balance (clipped to 0.9 x the room to the nearer floor at entry, skipped under 0.25%), P&L booked at the exit, daily floor = the server day's start
balance - $3,000, end-of-day trailing floor, best-day rule; floating losses inside a trade are not tracked (disclosed: optimistic for multi-day holds).
MANUAL'S BAR (fixed now): an EA is worth running only if its 30-day pass probability is >= 70% in IS AND in OOS starts. Reported against the deployed 30-day table
(Round 345: 35% / 41%).
POWER: the H4 / D1 EAs trade 30-300 times in five years, so their mean R carries an s.e. of 0.1-0.25 R: only very large effects can be seen, which is what the bar asks.
DRY-RUN COUNTS (trades only; IS / OOS by exit date): 77691 142 (52 / 90); 77900 199 (78 / 121); 77639 1,286; 77748 36 (19 / 17); 77738 1,050; 73638 852; 77718 207 /
240 / 215 (XAU / US100 / EURUSD); 77967 1,251; 76153 1,272 / 1,275 / 1,262; 75586 976; 73674 254 / 254 / 257 / 254 (US500 / US100 / EURUSD / XAU); 73884 6 / 5 / 7 (too few
to test: reported, p-values still counted); 68082 2,659 / 2,785 / 2,968; 69545 32,161 (it opens on every touch of the previous hour's high / low, no position limit);
73958 106 / 92. All 25 cells 2021-09 / 10 .. 2026-10-02.
"""
import os, sys, json, time, datetime as dt
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); sys.path.insert(0, ROOT)

SEED, SPLIT = 346, pd.Timestamp("2024-01-01")
DATA = os.path.join(ROOT, "mt5broker", "data"); SPECS = os.path.join(ROOT, "mt5broker", "specs")
COMM_BP = {"XAUUSD": 0.2, "EURUSD": 0.6}
MAX_HOLD_MIN = 60 * 24 * 60
INITIAL, TARGET, DAILY, TRAIL = 100_000.0, 110_000.0, 3_000.0, 10_000.0


# --------------------------------------------------------------------------------------------------------------------- data
class Sym:
    def __init__(self, name):
        raw = pd.read_parquet(os.path.join(DATA, f"{name}_M1_ticks_full.parquet")).sort_values("time").drop_duplicates("time")
        self.name = name
        self.t = raw["time"].to_numpy().astype(np.int64)                      # server seconds
        for c, k in (("open", "o"), ("high", "h"), ("low", "l"), ("close", "c"), ("ask_open", "ao"), ("ask_high", "ah"), ("ask_low", "al"), ("ask_close", "ac")):
            setattr(self, k, raw[c].to_numpy().astype(float))
        spec = json.load(open(os.path.join(SPECS, f"{name}_D1_manifest.json")))
        flat = json.dumps(spec)
        import re
        g = lambda key: float(re.search(rf'"{key}": ([-0-9.e]+)', flat).group(1))
        self.point = g("point")
        self.swap_long, self.swap_short = g("swap_long") * self.point, g("swap_short") * self.point
        self.triple = {3: 2, 5: 4}.get(int(g("swap_rollover3days")), 2)          # MQL day of week -> python weekday
        self.comm_bp = COMM_BP.get(name, 0.0)
        self.idx = pd.to_datetime(self.t, unit="s")
        self.day = (self.t // 86400).astype(np.int64)

    def bars(self, minutes):
        """Bars of `minutes` (1440 = D1) in server time: dict of arrays + the M1 index of each bar's first and last minute."""
        key = self.t // (minutes * 60)
        u, first = np.unique(key, return_index=True)
        last = np.r_[first[1:], len(key)] - 1
        f = lambda a, fn: fn.reduceat(a, first)
        b = dict(t=u * minutes * 60, o=self.o[first], c=self.c[last], h=np.maximum.reduceat(self.h, first), l=np.minimum.reduceat(self.l, first),
                 ao=self.ao[first], ac=self.ac[last], first=first, last=last)
        return b


# ----------------------------------------------------------------------------------------------------------------- indicators
def ema(x, n):
    a = 2.0 / (n + 1); out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def tr(b):
    pc = np.r_[b["c"][0], b["c"][:-1]]
    return np.maximum(b["h"] - b["l"], np.maximum(np.abs(b["h"] - pc), np.abs(b["l"] - pc)))


def atr(b, n):
    return sma(tr(b), n)


def wilder(x, n):
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    out[n] = np.nanmean(x[1:n + 1])
    for i in range(n + 1, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up, dn = np.maximum(d, 0), np.maximum(-d, 0)
    au, ad = wilder(up, n), wilder(dn, n)
    return 100 - 100 / (1 + au / np.where(ad == 0, np.nan, ad))


def adx(b, n):
    h, l = b["h"], b["l"]
    upm = np.r_[0, h[1:] - h[:-1]]; dnm = np.r_[0, l[:-1] - l[1:]]
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); mdm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    trs = wilder(tr(b), n); pdi = 100 * wilder(pdm, n) / trs; mdi = 100 * wilder(mdm, n) / trs
    dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    return wilder(np.nan_to_num(dx), n), pdi, mdi


def supertrend(b, n, f):
    a = wilder(tr(b), n); hl2 = (b["h"] + b["l"]) / 2; up, dn = hl2 - f * a, hl2 + f * a
    c = b["c"]; d = np.ones(len(c)); fu, fd = up.copy(), dn.copy()
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
        d[i] = 1 if c[i] > fd[i - 1] else (-1 if c[i] < fu[i - 1] else d[i - 1])
    return d


# ------------------------------------------------------------------------------------------------------------------ simulator
def first_true(mask):
    return int(np.argmax(mask)) if mask.any() else -1


def fill_stop_order(S, i0, i1, side, level):
    """First M1 index in [i0, i1) where a buy stop (ask high >= level) / sell stop (bid low <= level) fills, and the fill price."""
    if side == 1:
        j = first_true(S.ah[i0:i1] >= level)
        return (-1, 0.0) if j < 0 else (i0 + j, max(level, S.ao[i0 + j]))
    j = first_true(S.l[i0:i1] <= level)
    return (-1, 0.0) if j < 0 else (i0 + j, min(level, S.o[i0 + j]))


def run_trade(S, i, side, entry, sl, tp, i_force=None, stop_entry=False, exit_fn=None):
    """Simulate from M1 index i (the entry minute). Returns (exit index, exit price, reason). exit_fn(k) -> True closes at the open of minute k (signal exits)."""
    end = min(len(S.t), i + MAX_HOLD_MIN) if i_force is None else min(i_force, len(S.t))
    lo, hi = (S.l, S.h) if side == 1 else (S.al, S.ah)
    j0 = i
    if stop_entry:                                         # entry minute: only the stop
        if (side == 1 and lo[i] <= sl) or (side == -1 and hi[i] >= sl):
            return i, sl, "sl"
        j0 = i + 1
    seg_lo, seg_hi = lo[j0:end], hi[j0:end]
    s_hit = first_true(seg_lo <= sl) if side == 1 else first_true(seg_hi >= sl)
    t_hit = -1 if tp is None else (first_true(seg_hi >= tp) if side == 1 else first_true(seg_lo <= tp))
    cand = [x for x in (s_hit, t_hit) if x >= 0]
    k = min(cand) if cand else -1
    if exit_fn is not None:
        e = exit_fn(j0, end if k < 0 else j0 + k + 1)
        if e is not None and (k < 0 or e < j0 + k):
            px = S.o[e] if side == 1 else S.ao[e]
            return e, px, "signal"
    if k >= 0:
        kk = j0 + k
        if s_hit == k:
            op = S.o[kk] if side == 1 else S.ao[kk]
            return kk, (min(sl, op) if side == 1 else max(sl, op)), "sl"
        op = S.o[kk] if side == 1 else S.ao[kk]
        return kk, (max(tp, op) if side == 1 else min(tp, op)), "tp"
    e = end - 1
    return e, (S.c[e] if side == 1 else S.ac[e]), "time"


def book(S, trades, i_in, i_out, side, entry, exit_px, sl0, reason, tag=""):
    risk = abs(entry - sl0)
    if not (risk > 0):
        return
    nights = 0
    d0, d1 = S.day[i_in], S.day[i_out]
    for d in range(d0, d1):
        wd = (pd.Timestamp(d * 86400, unit="s")).weekday()
        if wd < 5:
            nights += 3 if wd == S.triple else 1
    swap = (S.swap_long if side == 1 else S.swap_short) * nights
    pnl = side * (exit_px - entry) + swap - S.comm_bp * 1e-4 * entry
    trades.append(dict(t_in=int(S.t[i_in]), t_out=int(S.t[i_out]), side=side, entry=entry, exit=exit_px, R=pnl / risk, reason=reason, nights=nights, tag=tag))


def m1_index(S, server_ts):
    return int(np.searchsorted(S.t, server_ts))


# --------------------------------------------------------------------------------------------------------------------- the EAs
def ea_77691(S):
    b = S.bars(240); c, h = b["c"], b["h"]; a = atr(b, 20); e = ema(c, 200)
    hh = pd.Series(h).rolling(20).max().shift(1).to_numpy()
    T, busy = [], -1
    for i in range(221, len(c) - 1):
        brk = c[i] > hh[i] and not (c[i - 1] > hh[i - 1]) and c[i] > e[i]
        j = b["first"][i + 1]
        if not brk or j <= busy or not np.isfinite(a[i]):
            continue
        entry = S.ao[j]; stop = 2 * a[i]
        if (S.ao[j] - S.o[j]) > 0.10 * stop:
            continue
        sl, tp = entry - stop, entry + 2 * stop
        k, px, why = run_trade(S, j, 1, entry, sl, tp)
        book(S, T, j, k, 1, entry, px, sl, why); busy = k
    return T


def ea_77900(S):
    b = S.bars(60); d = S.bars(1440)
    c = b["c"]; n = len(c)
    wp = (b["h"] + b["l"] + 2 * c) / 4
    mid = sma(wp, 9); sd = pd.Series(wp).rolling(9).std(ddof=0).to_numpy(); up, lo = mid + 2 * sd, mid - 2 * sd
    K, D, SL_ = 23, 3, 7
    hi = pd.Series(c).rolling(K).max().to_numpy(); lw = pd.Series(c).rolling(K).min().to_numpy()
    k = np.where(hi - lw > 1e-8, 100 * (c - lw) / (hi - lw), np.nan); k = pd.Series(k).ffill().fillna(50).to_numpy()
    main = np.empty(n); sig = np.empty(n); main[0] = sig[0] = 50
    for i in range(1, n):
        main[i] = (main[i - 1] * (SL_ - 1) + k[i]) / SL_
        sig[i] = (sig[i - 1] * (D - 1) + main[i]) / D
    dday = d["t"] // 86400
    T, busy = [], -1
    pend = {}                                              # side -> (level, placed bar)
    for i in range(30, n - 1):
        j = b["first"][i + 1]                               # bar i+1 just opened: closed bars are i, i-1, i-2 (s1, s2, s3)
        if j <= busy:
            pend = {}; continue
        s1, s2, s3 = sig[i], sig[i - 1], sig[i - 2]
        open3 = b["o"][i - 2]
        di = np.searchsorted(dday, b["t"][i + 1] // 86400) - 1
        if di < 0:
            continue
        buy = open3 < up[i - 3] and (s3 < s2 and s2 > s1)
        sell = open3 > lo[i - 3] and (s3 > s2 and s2 < s1)
        if buy and d["h"][di] > S.ao[j]:
            pend[1] = (d["h"][di], i + 1)
        elif sell and d["l"][di] < S.o[j]:
            pend[-1] = (d["l"][di], i + 1)
        for side in list(pend):
            lvl, placed = pend[side]
            if i + 1 - placed >= 9:
                pend.pop(side); continue
        # check fills during bar i+1
        j1 = b["last"][i + 1] + 1 if i + 1 < n else len(S.t)
        best = None
        for side, (lvl, placed) in pend.items():
            f, px = fill_stop_order(S, j, j1, side, lvl)
            if f >= 0 and (best is None or f < best[0]):
                best = (f, side, px)
        if best:
            f, side, entry = best
            sl, tp = entry - side * entry * 0.019, entry + side * entry * 0.019
            kx, px, why = run_trade(S, f, side, entry, sl, tp, stop_entry=True)
            book(S, T, f, kx, side, entry, px, sl, why); busy = kx; pend = {}
    return T


def ea_77639(S):
    b = S.bars(15); h1 = S.bars(60); a = atr(b, 14); e50 = ema(h1["c"], 50)
    o, h, l, c = b["o"], b["h"], b["l"], b["c"]; n = len(c); L = 5
    T, busy = [], -1
    last_sh = last_sl = None
    pend = None                                            # (side, ob_lo, ob_hi, wick, bars_left)
    for i in range(2 * L + 1, n - 1):
        p = i - L                                          # swing confirmed L bars later
        if h[p] == h[p - L:p + L + 1].max():
            last_sh = h[p]
        if l[p] == l[p - L:p + L + 1].min():
            last_sl = l[p]
        j = b["first"][i + 1]
        if j <= busy or not np.isfinite(a[i]):
            continue
        hi_ = np.searchsorted(h1["t"], b["t"][i], side="right") - 2  # last CLOSED H1 bar
        if hi_ < 50:
            continue
        trend = 1 if h1["c"][hi_] > e50[hi_] else -1
        if pend is not None:
            side, ob_lo, ob_hi, wick, left = pend
            ok = (c[i] > ob_hi if side == 1 else c[i] < ob_lo) and (h[i] - l[i]) >= 0.3 * a[i]
            if ok:
                entry = S.ao[j] if side == 1 else S.o[j]
                sl = wick - side * 0.10 * a[i]
                dist = abs(entry - sl); spr = S.ao[j] - S.o[j]
                if dist >= 0.5 * a[i] and dist >= 3 * spr and side * (entry - sl) > 0:
                    tp = entry + side * 2 * dist
                    k, px, why = run_trade(S, j, side, entry, sl, tp)
                    book(S, T, j, k, side, entry, px, sl, why); busy = k
                pend = None
            else:
                pend = None if left <= 1 else (side, ob_lo, ob_hi, wick, left - 1)
            continue
        if trend == 1 and last_sl is not None and l[i] <= last_sl - 0.15 * a[i] and c[i] > last_sl:
            pend = (1, min(o[i], c[i]), max(o[i], c[i]), l[i], 3)
        elif trend == -1 and last_sh is not None and h[i] >= last_sh + 0.15 * a[i] and c[i] < last_sh:
            pend = (-1, min(o[i], c[i]), max(o[i], c[i]), h[i], 3)
    return T


def ea_77748(S):
    b = S.bars(30); d = S.bars(1440); dday = d["t"] // 86400
    T, busy, stage, cur = [], -1, 0, None
    for i in range(1, len(b["c"]) - 1):
        day = b["t"][i + 1] // 86400
        di = np.searchsorted(dday, day) - 1
        if di < 0:
            continue
        if day != cur:
            cur, stage = day, 0
        ph = d["h"][di]; half = ph * 0.12 / 100 / 2; top, bot = ph + half, ph - half
        cl = b["c"][i]
        if stage == 0 and cl >= bot:
            stage = 1
        if stage == 1 and cl <= bot * (1 - 0.40 / 100):
            stage = 2
        if stage == 2 and bot <= cl <= top:
            stage = 3
        if stage != 3:
            continue
        stage = 0
        j = b["first"][i + 1]
        if j <= busy:
            continue
        entry = S.o[j]; sl, tp = entry * 1.04, entry * (1 - 0.0075)
        k, px, why = run_trade(S, j, -1, entry, sl, tp)
        book(S, T, j, k, -1, entry, px, sl, why); busy = k
    return T


def ea_77738(S):
    b = S.bars(5); r = rsi(b["c"], 14); a = atr(b, 14)
    T, busy = [], -1
    for i in range(20, len(b["c"]) - 1):
        hr = (b["t"][i] % 86400) // 3600
        if not (14 <= hr < 18) or not (r[i - 1] < 65 <= r[i]) or not np.isfinite(a[i]):
            continue
        j = b["first"][i + 1]
        if j <= busy or (S.ao[j] - S.o[j]) > 0.15 * a[i]:
            continue
        entry = S.o[j]; sl, tp = entry + 4 * a[i], entry - 4 * a[i]
        i_force = b["first"][min(i + 1 + 96, len(b["c"]) - 1)]
        k, px, why = run_trade(S, j, -1, entry, sl, tp, i_force=i_force)
        book(S, T, j, k, -1, entry, px, sl, why); busy = k
    return T


def ea_73638(S):
    b = S.bars(240); T, busy = [], -1
    for i in range(2, len(b["c"]) - 1):
        if not b["c"][i] > b["h"][i - 1]:
            continue
        j = b["first"][i + 1]
        if j <= busy:
            continue
        entry = S.ao[j]; sl = b["l"][i]
        if (entry - sl) / S.point < 5000:
            continue
        tp = entry + 1.0 * (entry - sl)
        k, px, why = run_trade(S, j, 1, entry, sl, tp)
        book(S, T, j, k, 1, entry, px, sl, why); busy = k
    return T


def ea_77718(S):
    b = S.bars(240); st = supertrend(b, 10, 3.0); ax, pdi, mdi = adx(b, 14); a = wilder(tr(b), 10)
    T, busy = [], -1
    n = len(b["c"])
    for i in range(30, n - 1):
        j = b["first"][i + 1]
        if j <= busy or not np.isfinite(ax[i]):
            continue
        side = 1 if (st[i] == 1 and ax[i] >= 23 and pdi[i] > mdi[i]) else (-1 if (st[i] == -1 and ax[i] >= 23 and mdi[i] > pdi[i]) else 0)
        if side == 0:
            continue
        entry = S.ao[j] if side == 1 else S.o[j]; sl = b["c"][i] - side * 2 * a[i]
        if side * (entry - sl) <= 0:
            continue

        def exit_fn(j0, j1, side=side, start_bar=i + 1):
            # signal exit at the open of the bar after a closed bar with ADX < 18 or a Supertrend flip
            for bb in range(start_bar, n - 1):
                if b["first"][bb + 1] >= j1:
                    return None
                if ax[bb] < 18 or st[bb] != side:
                    return int(b["first"][bb + 1])
            return None
        k, px, why = run_trade(S, j, side, entry, sl, None, exit_fn=exit_fn)
        book(S, T, j, k, side, entry, px, sl, why); busy = k
    return T


def ea_77967(S):
    d = S.bars(1440); da = atr(d, 14); T = []
    for di in range(15, len(d["t"])):
        day0 = d["t"][di]
        if pd.Timestamp(day0, unit="s").weekday() >= 5:
            continue
        r0, r1 = m1_index(S, day0 + 16 * 3600 + 30 * 60), m1_index(S, day0 + 16 * 3600 + 45 * 60)
        e_end, c_end = m1_index(S, day0 + 18 * 3600 + 30 * 60), m1_index(S, day0 + 22 * 3600 + 45 * 60)
        if r1 - r0 < 10 or e_end <= r1:
            continue
        hi, lo = S.h[r0:r1].max(), S.l[r0:r1].min(); rng = hi - lo
        if not (0.05 * da[di - 1] <= rng <= 0.60 * da[di - 1]):
            continue
        buf = 20 * S.point
        fb, pb = fill_stop_order(S, r1, e_end, 1, hi + buf); fs, ps = fill_stop_order(S, r1, e_end, -1, lo - buf)
        cands = [(f, s, p) for f, s, p in ((fb, 1, pb), (fs, -1, ps)) if f >= 0]
        if not cands:
            continue
        f, side, entry = min(cands)
        sl = entry - side * rng; tp = entry + side * 2 * rng
        k, px, why = run_trade(S, f, side, entry, sl, tp, i_force=c_end, stop_entry=True)
        book(S, T, f, k, side, entry, px, sl, why)
    return T


def ea_76153(S):
    m5 = S.bars(5); T = []
    days = np.unique(S.t // 86400)
    for day in days:
        t0 = day * 86400 + 8 * 3600
        if pd.Timestamp(t0, unit="s").weekday() >= 5:
            continue
        r0, r1 = m1_index(S, t0), m1_index(S, t0 + 30 * 60)
        if r1 - r0 < 20:
            continue
        hi, lo = S.h[r0:r1].max(), S.l[r0:r1].min()
        buf, slb = 20 * S.point, 30 * S.point
        b0, b1 = np.searchsorted(m5["t"], t0 + 30 * 60), np.searchsorted(m5["t"], t0 + 150 * 60)
        for bi in range(b0, min(b1, len(m5["t"]) - 1)):
            cl = m5["c"][bi]; side = 1 if cl > hi + buf else (-1 if cl < lo - buf else 0)
            if side == 0:
                continue
            j = m5["first"][bi + 1]
            entry = S.ao[j] if side == 1 else S.o[j]
            sl = (lo - slb) if side == 1 else (hi + slb)
            if side * (entry - sl) <= 0:
                break
            tp = entry + side * 2 * abs(entry - sl)
            k, px, why = run_trade(S, j, side, entry, sl, tp)
            book(S, T, j, k, side, entry, px, sl, why)
            break
    return T


def ea_75586(S):
    m15 = S.bars(15); a15 = atr(m15, 14); d = S.bars(1440); da = atr(d, 14); T = []
    for di in range(15, len(d["t"])):
        day0 = d["t"][di]
        if pd.Timestamp(day0, unit="s").weekday() >= 5:
            continue
        r0, r1 = m1_index(S, day0), m1_index(S, day0 + 7 * 3600)
        x1 = m1_index(S, day0 + 11 * 3600)
        if r1 - r0 < 100 or x1 <= r1:
            continue
        hi, lo = S.h[r0:r1].max(), S.l[r0:r1].min()
        if not (0.15 * da[di - 1] <= hi - lo <= 0.70 * da[di - 1]):
            continue
        bi = np.searchsorted(m15["t"], day0 + 7 * 3600) - 1
        A = a15[bi]
        if not np.isfinite(A) or (S.ao[r1] - S.o[r1]) > 350 * S.point:
            continue
        fb, pb = fill_stop_order(S, r1, x1, 1, hi + 0.15 * A); fs, ps = fill_stop_order(S, r1, x1, -1, lo - 0.15 * A)
        cands = [(f, s, p) for f, s, p in ((fb, 1, pb), (fs, -1, ps)) if f >= 0]
        if not cands:
            continue
        f, side, entry = min(cands)
        sl = entry - side * 1.2 * A; tp = entry + side * 1.8 * 1.2 * A
        k, px, why = run_trade(S, f, side, entry, sl, tp, stop_entry=True)
        book(S, T, f, k, side, entry, px, sl, why)
    return T


def ea_73674(S):
    d = S.bars(1440); da = atr(d, 14); T = []
    for di in range(15, len(d["t"]) - 1):
        if pd.Timestamp(d["t"][di], unit="s").weekday() != 0:        # Monday's candle
            continue
        nxt = di + 1
        if pd.Timestamp(d["t"][nxt], unit="s").weekday() != 1:
            continue
        side = 1 if d["c"][di] < d["o"][di] else -1
        j = d["first"][nxt]; entry = S.ao[j] if side == 1 else S.o[j]
        stop = 0.5 * da[di]; sl, tp = entry - side * stop, entry + side * 2.5 * stop
        k, px, why = run_trade(S, j, side, entry, sl, tp, i_force=m1_index(S, d["t"][nxt] + 22 * 3600))
        book(S, T, j, k, side, entry, px, sl, why)
    return T


def ea_73884(S):
    d = S.bars(1440); T, busy = [], -1
    for i in range(2, len(d["t"]) - 1):
        mo, mh, ml, mc = d["o"][i - 1], d["h"][i - 1], d["l"][i - 1], d["c"][i - 1]
        rng = mh - ml
        if rng <= 0 or abs(mc - mo) < 0.80 * rng:
            continue
        if not (d["h"][i] < mh and d["l"][i] > ml and (d["h"][i] - d["l"][i]) <= 0.50 * rng):
            continue
        side = 1 if mc > mo else -1
        lvl = mh if side == 1 else ml
        j0 = d["first"][i + 1]; j1 = d["first"][min(i + 4, len(d["t"]) - 1)]
        if j0 <= busy:
            continue
        f, entry = fill_stop_order(S, j0, j1, side, lvl)
        if f < 0:
            continue
        sl = entry - side * 0.62 * rng; tp = entry + side * 2.5 * 0.62 * rng
        k, px, why = run_trade(S, f, side, entry, sl, tp, stop_entry=True)
        book(S, T, f, k, side, entry, px, sl, why); busy = k
    return T


def ea_68082(S):
    m5 = S.bars(5); T, busy = [], -1
    ny = pd.to_datetime(m5["t"], unit="s") - pd.Timedelta(hours=7)          # server = NY + 7
    nymin = (ny.hour * 60 + ny.minute).to_numpy(); nyday = ny.normalize().values
    rng_top = rng_bot = None; cur = None; formed = False
    for i in range(2, len(m5["t"]) - 1):
        if nyday[i] != cur and nymin[i] < 240:
            cur, rng_top, rng_bot, formed = nyday[i], -np.inf, np.inf, False
        if cur is None:
            continue
        if nymin[i] < 240 and nyday[i] == cur:
            rng_top = max(rng_top, m5["h"][i]); rng_bot = min(rng_bot, m5["l"][i]); continue
        formed = True
        j = m5["first"][i + 1]
        if j <= busy:
            continue
        c1, c2 = m5["c"][i], m5["c"][i - 1]
        side = 1 if (c1 > rng_bot and c2 < rng_bot) else (-1 if (c1 < rng_top and c2 > rng_top) else 0)
        if side == 0:
            continue
        q = i - 1; ext = m5["l"][q] if side == 1 else m5["h"][q]
        while q > 0 and ((m5["c"][q] < rng_bot) if side == 1 else (m5["c"][q] > rng_top)):
            ext = min(ext, m5["l"][q]) if side == 1 else max(ext, m5["h"][q]); q -= 1
        if (i - 1 - q) * 5 > 75:                                       # stayed outside more than 75 minutes: invalid
            continue
        entry = S.ao[j] if side == 1 else S.o[j]; sl = ext
        if side * (entry - sl) <= 0:
            continue
        tp = entry + side * 2 * abs(entry - sl)
        k, px, why = run_trade(S, j, side, entry, sl, tp)
        book(S, T, j, k, side, entry, px, sl, why); busy = k
    return T


def ea_69545(S):
    b = S.bars(60); T = []
    for i in range(1, len(b["t"]) - 1):
        up, dn = b["h"][i - 1], b["l"][i - 1]
        j0, j1 = b["first"][i], b["last"][i] + 1
        for side, lvl in ((1, up), (-1, dn)):
            f, entry = fill_stop_order(S, j0, j1, side, lvl)
            if f < 0:
                continue
            entry = S.ao[f] if side == 1 else S.o[f]                     # market order on the touch
            entry = max(entry, lvl) if side == 1 else min(entry, lvl)
            sl, tp = entry - side * 200 * S.point, entry + side * 400 * S.point
            k, px, why = run_trade(S, f, side, entry, sl, tp, stop_entry=True)
            book(S, T, f, k, side, entry, px, sl, why)
    return T


def ea_73958(S):
    b = S.bars(60); ax, pdi, mdi = adx(b, 14); e = ema(b["c"], 20); a = atr(b, 14)
    dist = np.abs(b["c"] - e) / a
    T, busy = [], -1
    for i in range(30, len(b["t"]) - 1):
        if not (ax[i] > 25 and ax[i] > ax[i - 1] and dist[i - 1] >= 0.5 and dist[i] < 0.5):
            continue
        side = 1 if pdi[i] > mdi[i] else -1
        j = b["first"][i + 1]
        if j <= busy:
            continue
        entry = S.ao[j] if side == 1 else S.o[j]; stop = 1.5 * a[i]
        sl, tp = entry - side * stop, entry + side * 2 * stop
        k, px, why = run_trade(S, j, side, entry, sl, tp)
        book(S, T, j, k, side, entry, px, sl, why); busy = k
    return T


CELLS = [("77691 Gold Breakout", ea_77691, "XAUUSD"), ("77900 Stoch Daily Breakout", ea_77900, "XAUUSD"), ("77639 SMC Gold", ea_77639, "XAUUSD"),
         ("77748 ZoneUS30", ea_77748, "US30.cash"), ("77738 RSI Exhaustion", ea_77738, "EURUSD"), ("73638 Long-only Breakout", ea_73638, "US100.cash")] + \
        [("77718 Stormbreaker ADX", ea_77718, s) for s in ("XAUUSD", "US100.cash", "EURUSD")] + \
        [("77967 ORB Risk Managed", ea_77967, "US100.cash")] + [("76153 Session ORB", ea_76153, s) for s in ("XAUUSD", "US100.cash", "EURUSD")] + \
        [("75586 Gold London Breakout", ea_75586, "XAUUSD")] + [("73674 Turnaround Tuesday", ea_73674, s) for s in ("US500.cash", "US100.cash", "EURUSD", "XAUUSD")] + \
        [("73884 Inside Bar", ea_73884, s) for s in ("XAUUSD", "US100.cash", "EURUSD")] + [("68082 4H Range Fakeout", ea_68082, s) for s in ("EURUSD", "XAUUSD", "US100.cash")] + \
        [("69545 VR Breakdown Level", ea_69545, "EURUSD")] + [("73958 ADX Trend Pullback", ea_73958, s) for s in ("XAUUSD", "EURUSD")]


# ---------------------------------------------------------------------------------------------------------------- evaluation
def boot_p(df, rng, draws=5000):
    g = df.groupby(df.t_out // 86400)["R"].agg(["sum", "count"])
    idx = rng.integers(0, len(g), (draws, len(g)))
    m = g["sum"].values[idx].sum(1) / g["count"].values[idx].sum(1)
    return float((m <= 0).mean())


def bh(p, q=0.10):
    p = np.asarray(p); n = len(p); o = np.argsort(p); ok = p[o] <= q * np.arange(1, n + 1) / n
    k = np.max(np.flatnonzero(ok)) + 1 if ok.any() else 0
    keep = np.zeros(n, bool); keep[o[:k]] = True
    return keep


def pass30(df, risk_pct, start_days):
    """Every start day: the EA's trades entered in [start, start + 30 calendar days), sized at risk_pct of the initial balance."""
    t_in, t_out, R = df.t_in.values, df.t_out.values, df.R.values
    res = []
    for s in start_days:
        s0, s1 = s * 86400, (s + 30) * 86400
        sel = np.flatnonzero((t_in >= s0) & (t_in < s1))
        bal, hwm, pos, best = INITIAL, INITIAL, 0.0, 0.0
        day, day_start = None, INITIAL
        daypnl = {}
        ok = 0
        for q in sel[np.argsort(t_out[sel])]:
            dq = t_out[q] // 86400
            if dq != day:
                day, day_start = dq, bal; hwm = max(hwm, bal)
            floor = max(hwm - TRAIL, day_start - DAILY)
            r = min(risk_pct * INITIAL, 0.9 * (bal - floor))
            if r < 0.0025 * INITIAL:
                continue
            pnl = r * R[q]; bal += pnl
            daypnl[dq] = daypnl.get(dq, 0.0) + pnl
            if bal <= floor:
                break
            if bal > TARGET:
                pd_ = [v for v in daypnl.values() if v > 0]
                if pd_ and max(pd_) <= 0.5 * sum(pd_):
                    ok = 1; break
        res.append(ok)
    return np.array(res)


def main(dry):
    t0 = time.time(); rng = np.random.default_rng(SEED)
    syms = {}
    rows, all_trades = [], {}
    for name, fn, sym in CELLS:
        if sym not in syms:
            syms[sym] = Sym(sym)
        S = syms[sym]
        T = pd.DataFrame(fn(S))
        all_trades[f"{name}|{sym}"] = T
        n = len(T)
        if dry:
            print(f"{name:28s} {sym:11s} trades {n:5d}" + (f"  from {pd.Timestamp(T.t_in.min(), unit='s').date()} to {pd.Timestamp(T.t_in.max(), unit='s').date()}, "
                  f"IS {int((pd.to_datetime(T.t_out, unit='s') < SPLIT).sum())} / OOS {int((pd.to_datetime(T.t_out, unit='s') >= SPLIT).sum())}" if n else "") +
                  f"  ({time.time() - t0:.0f}s)", flush=True)
            continue
        is_ = pd.to_datetime(T.t_out, unit="s") < SPLIT
        win = T.R > 0
        gp, gl = T.R[T.R > 0].sum(), -T.R[T.R < 0].sum()
        rows.append(dict(ea=name, symbol=sym, trades=n, win=float(win.mean()), meanR=float(T.R.mean()), PF=float(gp / gl) if gl > 0 else float("inf"),
                         R_IS=float(T.R[is_].mean()), R_OOS=float(T.R[~is_].mean()), n_IS=int(is_.sum()), n_OOS=int((~is_).sum()), p=boot_p(T, rng),
                         sumR=float(T.R.sum()), avg_nights=float(T.nights.mean())))
        r = rows[-1]
        print(f"{name:28s} {sym:11s} n {n:5d} win {r['win']:.2f} R {r['meanR']:+.3f} (IS {r['R_IS']:+.3f} / OOS {r['R_OOS']:+.3f}) PF {r['PF']:.2f} "
              f"sumR {r['sumR']:+.0f} p {r['p']:.3f} ({time.time() - t0:.0f}s)", flush=True)
    if dry:
        return
    sc = pd.DataFrame(rows)
    sc["candidate"] = bh(sc.p.values) & (sc.R_IS > 0) & (sc.R_OOS > 0)
    # 30-day 1-Step replay for every cell
    first_day = max(int(S.t[0] // 86400) for S in syms.values()) + 30
    last_day = min(int(S.t[-1] // 86400) for S in syms.values()) - 30
    days = np.array([d for d in range(first_day, last_day) if pd.Timestamp(d * 86400, unit="s").weekday() < 5])
    is_days = days[pd.to_datetime((days + 30) * 86400, unit="s") < SPLIT]
    oos_days = days[pd.to_datetime(days * 86400, unit="s") >= SPLIT]
    for i, row in sc.iterrows():
        T = all_trades[f"{row.ea}|{row.symbol}"]
        for rp in (0.01, 0.02):
            a, b_ = pass30(T, rp, is_days), pass30(T, rp, oos_days)
            sc.loc[i, f"pass30_IS_{int(rp*100)}%"] = a.mean(); sc.loc[i, f"pass30_OOS_{int(rp*100)}%"] = b_.mean()
    sc["meets_70"] = (sc[["pass30_IS_1%", "pass30_IS_2%"]].max(1) >= 0.70) & (sc[["pass30_OOS_1%", "pass30_OOS_2%"]].max(1) >= 0.70)
    pd.set_option("display.width", 250)
    print(sc[["ea", "symbol", "trades", "win", "meanR", "R_IS", "R_OOS", "PF", "p", "candidate", "pass30_IS_1%", "pass30_OOS_1%", "pass30_IS_2%", "pass30_OOS_2%", "meets_70"]]
          .to_string(float_format=lambda v: f"{v:.3f}"))
    print("candidates:", sc.loc[sc.candidate, ["ea", "symbol"]].values.tolist(), "| meets the trader's 70% bar:", sc.loc[sc.meets_70, ["ea", "symbol"]].values.tolist())
    json.dump(dict(cells=sc.to_dict("records"), n_start_days=dict(IS=len(is_days), OOS=len(oos_days))), open(os.path.join(HERE, "round346_results_mt5broker_ask.json"), "w"), indent=1, default=str)
    pd.concat([t.assign(cell=k) for k, t in all_trades.items() if len(t)]).to_csv(os.path.join(HERE, "round346_trades_mt5broker_ask.csv.gz"), index=False)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
