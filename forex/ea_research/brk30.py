"""BRK30: 30 untouched breakout ideas (patterns, indicators, systems, cross-asset, calendar, structure) on the 38 non-crypto MT5, one pre-registered round on BRK50's engine (`brk50.Mkt`). Pre-registration: forex/ea_research/PREREG_BRK30.md.
   python -m forex.ea_research.brk30 --dry-run | --run"""
import argparse, os, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.brk50 import Mkt, lt, last_of, LIS, NYZ, JST, H, DEV, VAL, HOLD, NONC
from forex.ea_research.orbx import ct
from forex.ea_research.analog import mclass

CACHE = "data/scratch/brk30_trades.parquet"
IDEAS = [f"K{k:02d}" for k in range(1, 31)]
UNIV = {i: tuple(NONC) for i in IDEAS}
UNIV.update({"K23": ("AUDUSD", "AUDJPY"), "K24": ("AUDUSD", "AUDJPY"), "K25": ("USDJPY", "USDCHF", "XAUUSD"), "K26": ("USDJPY",),
             "K27": ("SP", "NSDQ", "DOW"), "K28": ("SP", "NSDQ", "DOW", "DAX", "NIKKEI")})
DAILY = "futures/data/daily/"
START = pd.Timestamp("2022-01-01")
H4 = 4 * H


def epoch(ts_naive):
    return int((pd.Timestamp(ts_naive) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


# ---------------------------------------------------------------------- indicators on bar arrays
def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def wilder(x, n):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def rmax(x, n):
    return pd.Series(x).rolling(n, min_periods=n).max().to_numpy()


def rmin(x, n):
    return pd.Series(x).rolling(n, min_periods=n).min().to_numpy()


def true_range(hh, ll, cc):
    pc = np.r_[cc[0], cc[:-1]]
    return np.maximum(hh, pc) - np.minimum(ll, pc)


def rsi(cc, n=14):
    d = np.diff(cc, prepend=cc[0]); up = wilder(np.maximum(d, 0), n); dn = wilder(np.maximum(-d, 0), n)
    return 100 - 100 / (1 + up / np.maximum(dn, 1e-12))


def adx_di(hh, ll, cc, n=14):
    ph, pl = np.r_[hh[0], hh[:-1]], np.r_[ll[0], ll[:-1]]
    up, dn = hh - ph, pl - ll
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    at = wilder(true_range(hh, ll, cc), n)
    pdi = 100 * wilder(pdm, n) / np.maximum(at, 1e-12); ndi = 100 * wilder(ndm, n) / np.maximum(at, 1e-12)
    return wilder(100 * np.abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-12), n), pdi, ndi


def aroon(hh, ll, n=25):
    up = pd.Series(hh).rolling(n + 1, min_periods=n + 1).apply(lambda a: float(np.argmax(a)), raw=True).to_numpy()
    dn = pd.Series(ll).rolling(n + 1, min_periods=n + 1).apply(lambda a: float(np.argmin(a)), raw=True).to_numpy()
    return 100 * up / n, 100 * dn / n                                  # argmax position n = the newest bar -> 100


def cci(hh, ll, cc, n=20):
    tp = (hh + ll + cc) / 3; m = sma(tp, n)
    md = pd.Series(tp).rolling(n, min_periods=n).apply(lambda a: np.mean(np.abs(a - a.mean())), raw=True).to_numpy()
    return (tp - m) / (0.015 * np.maximum(md, 1e-12))


def regression_band(cc, n=100):
    """fitted value at the newest point of a least-squares line over the last n closes, and the residual SD"""
    y = cc.astype(float); idx = np.arange(len(y), dtype=float)
    c1 = np.r_[0, np.cumsum(y)]; cm = np.r_[0, np.cumsum(idx * y)]; c2 = np.r_[0, np.cumsum(y * y)]
    b = np.arange(len(y)); a0 = b - n + 1; ok = a0 >= 0; a0c = np.where(ok, a0, 0)
    Sy = c1[b + 1] - c1[a0c]; Smy = cm[b + 1] - cm[a0c]; Syy = c2[b + 1] - c2[a0c]
    Sxy = Smy - a0c * Sy; Sx = n * (n - 1) / 2; Sxx = (n - 1) * n * (2 * n - 1) / 6
    slope = (n * Sxy - Sx * Sy) / (n * Sxx - Sx ** 2); icpt = (Sy - slope * Sx) / n
    fit = icpt + slope * (n - 1)
    sse = Syy - Sy ** 2 / n - slope ** 2 * (Sxx - Sx ** 2 / n)
    sd = np.sqrt(np.maximum(sse, 0) / (n - 2))
    return np.where(ok, fit, np.nan), np.where(ok, sd, np.nan)


def chop(hh, ll, cc, n=14):
    s = pd.Series(true_range(hh, ll, cc)).rolling(n, min_periods=n).sum().to_numpy()
    rg = rmax(hh, n) - rmin(ll, n)
    return 100 * np.log10(s / np.maximum(rg, 1e-12)) / np.log10(n)


def kama(cc, n=10, fast=2, slow=30):
    ch = np.abs(cc - np.r_[np.full(n, np.nan), cc[:-n]])
    vol = pd.Series(np.abs(np.diff(cc, prepend=cc[0]))).rolling(n, min_periods=n).sum().to_numpy()
    er = np.where(vol > 0, ch / np.maximum(vol, 1e-12), 0.0)
    sc = (np.nan_to_num(er) * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    k = np.empty_like(cc, dtype=float); k[0] = cc[0]
    for i in range(1, len(cc)):
        k[i] = k[i - 1] + sc[i] * (cc[i] - k[i - 1])
    return k


def ichimoku(hh, ll):
    ten = (rmax(hh, 9) + rmin(ll, 9)) / 2; kij = (rmax(hh, 26) + rmin(ll, 26)) / 2
    sa = (ten + kij) / 2; sb = (rmax(hh, 52) + rmin(ll, 52)) / 2
    sa26, sb26 = np.r_[np.full(26, np.nan), sa[:-26]], np.r_[np.full(26, np.nan), sb[:-26]]
    return ten, kij, np.fmax(sa26, sb26), np.fmin(sa26, sb26)


def pivots(hh, ll, k=3):
    """pivot highs / lows (extreme of the 2k+1 bars centred on the bar), as index arrays"""
    ph = rmax(hh, 2 * k + 1); pl = rmin(ll, 2 * k + 1)
    ph = np.r_[ph[k:], np.full(k, np.nan)]; pl = np.r_[pl[k:], np.full(k, np.nan)]   # centred window
    return np.flatnonzero(hh == ph), np.flatnonzero(ll == pl)


def cross_up(a, b):
    return np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]


def cross_dn(a, b):
    return np.r_[False, (a[1:] < b[1:]) & (a[:-1] >= b[:-1])]


# ---------------------------------------------------------------------- bars and trade mechanics
def bars(M, tf):
    key = M.t // tf; st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], M.n]
    B = dict(st=st, en=en, hh=np.maximum.reduceat(M.mh, st), ll=np.minimum.reduceat(M.ml, st), cc=M.mc[en - 1], t0=key[st] * tf)
    B["atr"] = sma(true_range(B["hh"], B["ll"], B["cc"]), 14)
    return B


def tag(res, idea, M, k):
    res.update(idea=idea, sym=M.sym, day=pd.Timestamp(int(M.t[k]) // 86400 * 86400, unit="s"))
    return res


def bc_trades(M, B, sig, k_atr, N, idea):
    """bar-close signals: enter at the next minute's open, stop k ATR14, exit at the start of bar b + 1 + N; one at a time"""
    out = []; D, t0, en, atr = M.D, B["t0"], B["en"], B["atr"]; busy = -1; b0 = int(np.searchsorted(t0, epoch(START)))
    for b in np.flatnonzero(sig):
        if b < max(b0, 60) or b <= busy or b + 1 + N >= len(t0) or not (atr[b] > 0):
            continue
        side = int(sig[b]); kk = int(en[b])
        if kk >= M.n or D["roll"][kk]:
            continue
        e = D["ao"][kk] if side > 0 else D["bo"][kk]
        ix = M.exit_idx(int(t0[b + 1 + N]))
        if ix is None:
            continue
        res = M.trade(side, kk, e, e - side * k_atr * atr[b], ix)
        if res is not None:
            out.append(tag(res, idea, M, kk)); busy = int(np.searchsorted(t0, M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


def bs_trade(M, B, b, U, L, slU, slL, nb, hold, idea, dist=None):
    """stop orders at U (buy) / L (sell) live for the nb bars after bar b; first touch; stop absolute (slU / slL) or `dist`;
    exit at the start of the bar `hold` bars after the fill bar. Returns (trade dict or None, exit index)."""
    D, t0, st, en = M.D, B["t0"], B["st"], B["en"]
    if b + nb >= len(t0):
        return None, -1
    i0, i1 = int(en[b]), int(en[b + nb])
    if i1 - i0 < 3 or i0 >= M.n:
        return None, -1
    m0 = M.mc[i0]
    if U is not None and not m0 < U:
        U = None
    if L is not None and not m0 > L:
        L = None
    if U is None and L is None:
        return None, -1
    nr = ~D["roll"][i0:i1]
    up = np.flatnonzero((D["ah"][i0:i1] >= U) & nr) if U is not None else np.array([], int)
    dn = np.flatnonzero((D["bl"][i0:i1] <= L) & nr) if L is not None else np.array([], int)
    ku = int(up[0]) if len(up) else None; kd = int(dn[0]) if len(dn) else None
    if (ku is None and kd is None) or (ku is not None and ku == kd):
        return None, -1
    long_ = kd is None or (ku is not None and ku < kd); k = i0 + (ku if long_ else kd)
    side = 1 if long_ else -1; e = max(U, D["ao"][k]) if long_ else min(L, D["bo"][k])
    stop = (slU if long_ else slL) if dist is None else e - side * dist
    fb = int(np.searchsorted(st, k, side="right")) - 1
    if stop is None or fb + hold >= len(t0):
        return None, -1
    ix = M.exit_idx(int(t0[fb + hold]))
    if ix is None:
        return None, -1
    res = M.trade(side, k, e, stop, ix)
    return (tag(res, idea, M, k) if res is not None else None), ix


def enter_at(M, side, t0, stop=None, dist=None, x_end=None):
    k = M.idx(t0)
    if k >= M.n or M.t[k] - t0 > 600 or M.D["roll"][k]:
        return None
    e = M.D["ao"][k] if side > 0 else M.D["bo"][k]
    ix = M.exit_idx(x_end)
    return None if ix is None else M.trade(side, k, e, stop if stop is not None else e - side * dist, ix)


def box_trade(M, a, b, w1, xe, long_ok=True, short_ok=True, mode="follow"):
    bx = M.box(a, b, 20)
    if not bx or not bx[0] > bx[1]:
        return None
    hi, lo = bx
    if mode == "fade":
        return M.level(hi, lo, b, w1, "fade", dist=0.5 * (hi - lo), x_end=xe)
    if not (long_ok or short_ok):
        return None
    return M.level(hi if long_ok else None, lo if short_ok else None, b, w1, "follow", slU=lo, slL=hi, x_end=xe)


def lb(M, d, long_ok=True, short_ok=True):
    return box_trade(M, lt(d, 8, 0), lt(d, 8, 30), lt(d, 11, 0), lt(d, 17, 0), long_ok, short_ok)


def nb(M, d, long_ok=True, short_ok=True, mode="follow"):
    return box_trade(M, lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ), lt(d, 12, 0, NYZ), lt(d, 15, 55, NYZ), long_ok, short_ok, mode)


def sgn(x):
    return 0 if not np.isfinite(x) or x == 0 else (1 if x > 0 else -1)


# ---------------------------------------------------------------------- bar ideas
def pattern_ideas(M, B, idea, kind, nb_, hold, tol):
    """K01-K04 on one bar set"""
    out = []; hh, ll, atr = B["hh"], B["ll"], B["atr"]; PH, PL = pivots(hh, ll)
    ev = sorted([(i + 3, "L", i) for i in PL] + [(i + 3, "H", i) for i in PH]); busy = -1
    t_start = epoch(START); lows, highs = [], []
    for kb, typ, i in ev:
        (lows if typ == "L" else highs).append(i)
        if kb >= len(hh) - nb_ - 1 or B["t0"][kb] < t_start or kb <= busy or not (atr[kb] > 0):
            continue
        res, ix = None, -1
        if kind == "double":
            src = lows if typ == "L" else highs
            if len(src) >= 2:
                i1, i2 = src[-2], src[-1]
                if 5 <= i2 - i1 <= 40:
                    if typ == "L" and abs(ll[i2] - ll[i1]) <= tol * atr[kb]:
                        res, ix = bs_trade(M, B, kb, hh[i1:i2 + 1].max(), None, min(ll[i1], ll[i2]), None, nb_, hold, idea)
                    elif typ == "H" and abs(hh[i2] - hh[i1]) <= tol * atr[kb]:
                        res, ix = bs_trade(M, B, kb, None, ll[i1:i2 + 1].min(), None, max(hh[i1], hh[i2]), nb_, hold, idea)
        elif kind == "triple":
            src = lows if typ == "L" else highs
            if len(src) >= 3:
                i1, i2, i3 = src[-3:]
                if i3 - i1 <= 60:
                    v = ll[[i1, i2, i3]] if typ == "L" else hh[[i1, i2, i3]]
                    if v.max() - v.min() <= tol * atr[kb]:
                        if typ == "L":
                            res, ix = bs_trade(M, B, kb, hh[i1:i3 + 1].max(), None, v.min(), None, nb_, hold, idea)
                        else:
                            res, ix = bs_trade(M, B, kb, None, ll[i1:i3 + 1].min(), None, v.max(), nb_, hold, idea)
        elif kind == "broad":
            if len(highs) >= 2 and len(lows) >= 2:
                h1, h2 = highs[-2:]; l1, l2 = lows[-2:]
                if hh[h2] > hh[h1] and ll[l2] < ll[l1]:
                    if typ == "L" and l2 == i and l2 > h2:
                        res, ix = bs_trade(M, B, kb, hh[h2], None, ll[l2], None, nb_, hold, idea)
                    elif typ == "H" and h2 == i and h2 > l2:
                        res, ix = bs_trade(M, B, kb, None, ll[l2], None, hh[h2], nb_, hold, idea)
        if res is not None:
            out.append(res); busy = int(np.searchsorted(B["t0"], M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


def bar_ideas(M):
    out = []; B1, B4 = bars(M, H), bars(M, H4)
    out += pattern_ideas(M, B1, "K01", "double", 12, 24, 0.25)
    out += pattern_ideas(M, B4, "K02", "double", 6, 30, 0.25)
    out += pattern_ideas(M, B4, "K03", "triple", 6, 30, 0.30)
    out += pattern_ideas(M, B4, "K04", "broad", 6, 30, 0.0)
    hh, ll, cc = B4["hh"], B4["ll"], B4["cc"]
    ten, kij, top, bot = ichimoku(hh, ll)
    s06 = np.where(cross_up(cc, top) & (ten > kij), 1, np.where(cross_dn(cc, bot) & (ten < kij), -1, 0))
    out += bc_trades(M, B4, s06, 2, 30, "K06")
    s08 = np.where(cross_up(ten, kij) & (cc > top), 1, np.where(cross_dn(ten, kij) & (cc < bot), -1, 0))
    out += bc_trades(M, B4, s08, 2, 30, "K08")
    macd = ema(cc, 12) - ema(cc, 26); hist = macd - ema(macd, 9)
    s09 = np.where(cross_up(macd, np.zeros_like(macd)) & (hist > 0), 1, np.where(cross_dn(macd, np.zeros_like(macd)) & (hist < 0), -1, 0))
    out += bc_trades(M, B4, s09, 2, 30, "K09")
    adx, pdi, ndi = adx_di(hh, ll, cc)
    birth = cross_up(adx, np.full_like(adx, 25.0))
    out += bc_trades(M, B4, np.where(birth & (pdi > ndi), 1, np.where(birth & (ndi > pdi), -1, 0)), 2, 30, "K12")
    au, ad = aroon(hh, ll)
    s13 = np.where(cross_up(au, np.full_like(au, 70.0)) & (ad < 30), 1, np.where(cross_up(ad, np.full_like(ad, 70.0)) & (au < 30), -1, 0))
    out += bc_trades(M, B4, s13, 2, 30, "K13")
    c4 = cci(hh, ll, cc)
    out += bc_trades(M, B4, np.where(cross_up(c4, np.full_like(c4, 100.0)), 1, np.where(cross_dn(c4, np.full_like(c4, -100.0)), -1, 0)), 2, 30, "K15")
    hh, ll, cc = B1["hh"], B1["ll"], B1["cc"]
    macd = ema(cc, 12) - ema(cc, 26); sig = ema(macd, 9)
    s10 = np.where(cross_up(macd, sig) & (macd > 0) & (sig > 0), 1, np.where(cross_dn(macd, sig) & (macd < 0) & (sig < 0), -1, 0))
    out += bc_trades(M, B1, s10, 1.5, 24, "K10")
    r = rsi(cc); lo10 = pd.Series(r).shift(1).rolling(10, min_periods=10).min().to_numpy(); hi10 = pd.Series(r).shift(1).rolling(10, min_periods=10).max().to_numpy()
    s11 = np.where(cross_up(r, np.full_like(r, 60.0)) & (lo10 < 40), 1, np.where(cross_dn(r, np.full_like(r, 40.0)) & (hi10 > 60), -1, 0))
    out += bc_trades(M, B1, s11, 1.5, 24, "K11")
    fit, sd = regression_band(cc)
    out += bc_trades(M, B1, np.where(cross_up(cc, fit + 2 * sd), 1, np.where(cross_dn(cc, fit - 2 * sd), -1, 0)), 1.5, 24, "K16")
    e9, e21 = ema(cc, 9), ema(cc, 21)
    out += bc_trades(M, B1, np.where(cross_up(e9, e21), 1, np.where(cross_dn(e9, e21), -1, 0)), 1.5, 24, "K17")
    ka = kama(cc)
    out += bc_trades(M, B1, np.where(cross_up(cc, ka), 1, np.where(cross_dn(cc, ka), -1, 0)), 1.5, 24, "K20")
    out += chop_donchian(M, B1) + fractal_alligator(M, B1)
    return out


def chop_donchian(M, B):
    out = []; hh, ll, cc, atr = B["hh"], B["ll"], B["cc"], B["atr"]; ch = chop(hh, ll, cc); u20, d20 = rmax(hh, 20), rmin(ll, 20)
    busy = -1; b0 = int(np.searchsorted(B["t0"], epoch(START)))
    for b in np.flatnonzero(ch < 38.2):
        if b < max(b0, 60) or b <= busy or not (atr[b] > 0):
            continue
        res, ix = bs_trade(M, B, b, u20[b], d20[b], None, None, 1, 24, "K19", dist=1.5 * atr[b])
        if res is not None:
            out.append(res); busy = int(np.searchsorted(B["t0"], M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


def fractal_alligator(M, B):
    out = []; hh, ll, cc, atr = B["hh"], B["ll"], B["cc"], B["atr"]; mp = (hh + ll) / 2
    jaw = np.r_[np.full(8, np.nan), wilder(mp, 13)[:-8]]; teeth = np.r_[np.full(5, np.nan), wilder(mp, 8)[:-5]]
    lips = np.r_[np.full(3, np.nan), wilder(mp, 5)[:-3]]
    f_hi = hh == np.r_[rmax(hh, 5)[2:], np.full(2, np.nan)]; f_lo = ll == np.r_[rmin(ll, 5)[2:], np.full(2, np.nan)]
    busy = -1; last_up = last_dn = -1; b0 = int(np.searchsorted(B["t0"], epoch(START)))
    for b in range(2, len(hh) - 8):
        if f_hi[b - 2]:
            last_up = b - 2                                                # a fractal is known 2 bars after its bar
        if f_lo[b - 2]:
            last_dn = b - 2
        if b < max(b0, 60) or b <= busy or not (atr[b] > 0):
            continue
        res = ix = None
        if last_up >= 0 and lips[b] > teeth[b] > jaw[b] and cc[b] > teeth[b]:
            res, ix = bs_trade(M, B, b, hh[last_up], None, None, None, 6, 24, "K22", dist=1.5 * atr[b])
        elif last_dn >= 0 and lips[b] < teeth[b] < jaw[b] and cc[b] < teeth[b]:
            res, ix = bs_trade(M, B, b, None, ll[last_dn], None, None, 6, 24, "K22", dist=1.5 * atr[b])
        if res is not None:
            out.append(res); busy = int(np.searchsorted(B["t0"], M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


# ---------------------------------------------------------------------- day ideas
def daily_indicators(M):
    Dd = M.Dd; Hd, Ld, Cd, Od = (Dd[c].to_numpy() for c in ("H", "L", "C", "O"))
    ten, kij, top, bot = ichimoku(Hd, Ld)
    X = dict(k07=np.where(cross_up(Cd, top) & (ten > kij), 1, np.where(cross_dn(Cd, bot) & (ten < kij), -1, 0)))
    c = cci(Hd, Ld, Cd); X["k14"] = np.where(cross_up(c, np.full_like(c, 100.0)), 1, np.where(cross_dn(c, np.full_like(c, -100.0)), -1, 0))
    s50, s200 = sma(Cd, 50), sma(Cd, 200); X["k18"] = np.where(cross_up(s50, s200), 1, np.where(cross_dn(s50, s200), -1, 0))
    fk = 100 * (Cd - rmin(Ld, 5)) / np.maximum(rmax(Hd, 5) - rmin(Ld, 5), 1e-12); X["slowk"] = sma(fk, 3)
    wk = Dd.wk.to_numpy(); wc = pd.Series(Cd).groupby(wk).last(); we = pd.Series(ema(wc.to_numpy(), 13), index=wc.index)
    prev = we.shift(1); prev2 = we.shift(2)
    X["w_rise"] = pd.Series(wk).map((prev > prev2).astype(float).where(prev2.notna())).to_numpy()   # last completed week vs the one before
    return X


def safe(f):
    try:
        return f()
    except Exception:
        return None


def day_ideas(M, p, X, busy):
    out = []; Dd = M.Dd
    if p < 5:                                       # indicator warm-ups (SMA200, Ichimoku) are NaN -> no signal by themselves
        return out
    r, y = Dd.iloc[p], Dd.iloc[p - 1]; atr = r.atr
    if not (atr > 0):
        return out
    d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); sym = M.sym; o1 = int(M.days[p]) * 86400 + H
    w08, w19, x20 = lt(d, 8, 0), lt(d, 19, 0), lt(d, 20, 45); I = X["ind"]

    def add(idea, res):
        if res is not None and sym in UNIV[idea]:
            res.update(idea=idea, sym=sym, day=d); out.append(res)
            ix = M.exit_idx(res.get("_x")) if res.get("_x") else None
            busy[idea] = int(M.t[min(ix, M.n - 1)]) if ix else 0

    def free(idea):
        return busy.get(idea, 0) <= w08

    # K05 morning / evening star
    a3, a2 = Dd.iloc[p - 3], Dd.iloc[p - 2]
    b3, r3 = a3.O - a3.C, a3.H - a3.L
    if r3 > 0 and abs(b3) > 0.6 * r3 and r3 > 0.8 * atr and abs(a2.C - a2.O) < 0.25 * abs(b3):
        m2 = (a2.O + a2.C) / 2
        if b3 > 0 and m2 < a3.C and y.C > y.O and y.C > (a3.O + a3.C) / 2:
            add("K05", M.level(y.H, None, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
        elif b3 < 0 and m2 > a3.C and y.C < y.O and y.C < (a3.O + a3.C) / 2:
            add("K05", M.level(None, y.L, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
    # K07 / K14 / K18 daily bar-close signals (yesterday's close -> 08:00 LIS today)
    for idea, key, stp, k in (("K07", "k07", 1.0, 9), ("K14", "k14", 1.0, 4), ("K18", "k18", 2.0, 19)):
        s = int(I[key][p - 1])
        if s and free(idea):
            xe = M.x_after(w08, k); res = enter_at(M, s, w08, dist=stp * atr, x_end=xe)
            if res is not None:
                res["_x"] = xe
            add(idea, res)
    # K21 Elder triple screen
    wr, kk = I["w_rise"][p], I["slowk"][p - 1]
    if np.isfinite(wr) and np.isfinite(kk) and free("K21"):
        if wr == 1 and kk < 30:
            res = M.level(y.H, None, w08, w19, "follow", slU=y.L, xk=4)
            if res is not None:
                res["_x"] = M.x_after(res["t_entry"], 4)
            add("K21", res)
        elif wr == 0 and kk > 70:
            res = M.level(None, y.L, w08, w19, "follow", slL=y.H, xk=4)
            if res is not None:
                res["_x"] = M.x_after(res["t_entry"], 4)
            add("K21", res)
    # K23 - K26 cross-asset (London box)
    if sym in ("AUDUSD", "AUDJPY"):
        hg = X["hg"]; i = int(hg.index.searchsorted(d))
        if i >= 2 and (d - hg.index[i - 1]).days <= 7:
            s = sgn(hg.iloc[i - 1] - hg.iloc[i - 2]); add("K23", lb(M, d, s > 0, s < 0) if s else None)
        g = X["P"].get("XAUUSD")
        if g is not None:
            s = sgn(g.mid_at(lt(d, 7, 59)) - g.mid_at(o1)); add("K24", lb(M, d, s > 0, s < 0) if s else None)
    if sym in ("USDJPY", "USDCHF", "XAUUSD"):
        vx = X["vix"]; i = int(vx.index.searchsorted(d))
        if i >= 2 and (d - vx.index[i - 1]).days <= 7:
            ch = vx.iloc[i - 1] / vx.iloc[i - 2] - 1; haven = 1 if sym == "XAUUSD" else -1      # the safe-haven side of each market
            s = haven if ch >= 0.08 else (-haven if ch <= -0.05 else 0)
            add("K25", lb(M, d, s > 0, s < 0) if s else None)
    if sym == "USDJPY":
        zn = X["zn"]; i = int(zn.index.searchsorted(d))
        if i >= 2 and (d - zn.index[i - 1]).days <= 7:
            s = -sgn(zn.iloc[i - 1] - zn.iloc[i - 2]); add("K26", lb(M, d, s > 0, s < 0) if s else None)
    # K27 OPEX Friday pinning fade, K28 quarter-end against the quarter
    if sym in ("SP", "NSDQ", "DOW") and d.weekday() == 4 and 15 <= d.day <= 21:
        add("K27", nb(M, d, mode="fade"))
    if sym in UNIV["K28"]:
        last2 = bool(r.last_q) or (p + 1 < len(Dd) and bool(Dd.last_q.iloc[p + 1]) and Dd.q.iloc[p + 1] == r.q)
        if last2:
            q0 = Dd[Dd.q == r.q].O.iloc[0]
            if sym == "DAX":
                ref, box = lt(d, 8, 0), (lt(d, 8, 0), lt(d, 8, 30), lt(d, 11, 0), lt(d, 16, 0))
            elif sym == "NIKKEI":
                ref, box = lt(d, 9, 0, JST), (lt(d, 9, 0, JST), lt(d, 9, 30, JST), lt(d, 11, 30, JST), lt(d, 14, 55, JST))
            else:
                ref, box = lt(d, 9, 30, NYZ), (lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ), lt(d, 12, 0, NYZ), lt(d, 15, 55, NYZ))
            s = -sgn(M.mid_at(ref - 60) - q0)
            add("K28", box_trade(M, *box, s > 0, s < 0) if s else None)
    # K29 outside week, K30 morning-range afternoon fade
    if r.first_wk and pd.notna(r.ppwkH) and r.pwkH > r.ppwkH and r.pwkL < r.ppwkL and r.pwkH > r.pwkL:
        cl = (r.pwkC - r.pwkL) / (r.pwkH - r.pwkL); wend = last_of(M, p, "wk")
        if wend is not None and (cl >= 0.7 or cl <= 0.3):
            thu = d + pd.Timedelta(days=max(0, 3 - d.weekday()))
            add("K29", M.level(r.pwkH if cl >= 0.7 else None, r.pwkL if cl <= 0.3 else None, w08, lt(thu, 19, 0), "follow",
                               dist=atr, x_end=lt(wend, 20, 45)))
    m = M.rng(o1, lt(d, 12, 0))
    if m and m[0] > m[1]:
        add("K30", M.level(m[0], m[1], lt(d, 14, 0), w19, "fade", dist=0.5 * atr, x_end=x20))
    for o in out:
        o.pop("_x", None)
    return out


def market(args):
    sym, cut = args
    M = Mkt(sym, cut)
    X = dict(ind=daily_indicators(M), P={}, hg=None, vix=None, zn=None)
    cd = pd.Timestamp(cut, unit="s").normalize() if cut is not None else None
    def ydaily(f):
        s = pd.read_csv(DAILY + f, parse_dates=["date"]).set_index("date").close.sort_index()
        return s[s.index < cd] if cd is not None else s
    if sym in ("AUDUSD", "AUDJPY"):
        X["hg"] = ydaily("HG=F_yahoo_daily.csv"); X["P"]["XAUUSD"] = Mkt("XAUUSD", cut)
    if sym in ("USDJPY", "USDCHF", "XAUUSD"):
        X["vix"] = ydaily("^VIX_yahoo_daily.csv")
    if sym == "USDJPY":
        X["zn"] = ydaily("ZN=F_yahoo_daily.csv")
    out, busy = [], {}
    for p in range(len(M.days)):
        if M.days[p] * 86400 < START.timestamp():
            continue
        out += day_ideas(M, p, X, busy)
    out += bar_ideas(M)
    T = pd.DataFrame(out)
    return T[T.day >= START] if len(T) else T


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    with Pool(4) as pl:
        T = pd.concat(pl.map(market, [(s, None) for s in NONC]), ignore_index=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    T = build()
    print(f"trades {len(T)}, markets {T.sym.nunique()}, {T.day.min().date()}..{T.day.max().date()}")
    c = T.assign(per=np.select([per(T, DEV), per(T, VAL)], ["DEV", "VAL"], "HOLD")).groupby(["idea", "per"]).size().unstack().reindex(IDEAS)
    c["markets"] = T.groupby("idea").sym.nunique(); c["long%"] = (T.groupby("idea").side.apply(lambda s: (s > 0).mean()) * 100).round(0)
    c["stop_sp_med"] = T.groupby("idea").wsp.median().round(0)
    pd.set_option("display.width", 200); print(c.to_string())
    rng = np.random.default_rng(30)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = T[T.sym == sym]
        cut = int(rng.uniform(full.t_entry.quantile(.4), full.t_entry.quantile(.8)))
        tr = market((sym, cut)); cdy = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[full.day < cdy][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[tr.day < cdy][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')} server, trades entered >= 35 days before the cut {len(a)} vs {len(b)}, identical {same}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("K01", "K04", "K06", "K13", "K16", "K22", "K25", "K28"):
        x = T[T.idea == idea]
        if len(x):
            r = x.sample(1, random_state=5).iloc[0]
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens")
            print(f"  hand check {idea} {r.sym} entry {loc.tz_convert(LIS):%Y-%m-%d %H:%M} LIS side {r.side:+d} stop width {r.wsp:.0f} spreads")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T = build(); rows = []
    for idea in IDEAS:
        x = T[T.idea == idea]
        if not len(x):
            rows.append(dict(idea=idea, n_dev=0)); continue
        d, v = x[per(x, DEV)], x[per(x, VAL)]
        mu, t = ct(d) if len(d) > 2 else (np.nan, np.nan)
        mi, ti = ct(d.assign(R=d.R - d.Rm)) if len(d) > 2 else (np.nan, np.nan)
        yrs = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 150 and mu > 0 and t >= 2.94 and (yrs > 0).sum() >= 2 and mi > 0 and ti >= 2.0
        mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        row = dict(idea=idea, n_dev=len(d), R_dev=mu, t_dev=t, info=mi, t_info=ti, yrs="/".join(f"{q:+.2f}" for q in yrs), win=(d.R > 0).mean(),
                   n_val=len(v), R_val=mv, t_val=tv, dev_pass=ok, val_pass=ok and mv > 0 and tv >= 1.65,
                   gold=d[d.sym == "XAUUSD"].R.mean(), nsdq=d[d.sym == "NSDQ"].R.mean(),
                   fx=d[d.sym.map(mclass) == "fx"].R.mean(), idx=d[d.sym.map(mclass) == "index"].R.mean())
        if row["val_pass"]:
            h = x[per(x, HOLD)]; mh, th = ct(h); row.update(R_hold=mh, t_hold=th, hold_pass=mh > 0 and th >= 1.65)
        rows.append(row)
    S = pd.DataFrame(rows); pd.set_option("display.width", 280)
    print(S.round(3).to_string(index=False))
    tv_ = S.t_dev.dropna()
    print(f"\nDEV t-values of {len(tv_)} ideas: mean {tv_.mean():+.2f}, sd {tv_.std():.2f}, positive {int((tv_ > 0).sum())}, t>1.65 {int((tv_ > 1.65).sum())}"
          f" (null expectation ~{0.05 * len(tv_):.1f}), t>2.94 {int((tv_ > 2.94).sum())}")
    passers = S[S.get("hold_pass", pd.Series(False, index=S.index)).fillna(False).astype(bool)].idea.tolist() if "hold_pass" in S else []
    print("DEV + VAL passers:", S[S.val_pass.fillna(False).astype(bool)].idea.tolist() or "none", "| full passers:", passers or "none")
    top = S.dropna(subset=["t_dev"]).nlargest(5, "t_dev").idea.tolist(); print("account view for the 5 best by DEV t:", top)
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1630)
    for idea in sorted(set(top + passers)):
        x = T[(T.idea == idea) & (T.day < "2026-01-01")]
        for label, sel, risk, cap in (("universe $50, max 5/day", x, 50, 5), ("NSDQ+XAUUSD $250", x[x.sym.isin(["NSDQ", "XAUUSD"])], 250, 10)):
            if not len(sel):
                continue
            sel = sel.sort_values("t_entry").groupby("day").head(cap)
            Rd = sel.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); rr = Rd.fillna(0).to_numpy()
            s = rng.integers(0, len(rr) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
            st, ev, _ = account(rr[bi], trd[bi], risk)
            print(f"  {idea} {label} ({len(sel)} trades 2022-25, {sel.R.mean():+.3f} R): " + "  ".join(
                f"{k} pass {100*np.mean((st==1)&(ev<h_)):.1f}% / breach {100*np.mean((st==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    S.to_csv("forex/ea_research/BRK30_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
