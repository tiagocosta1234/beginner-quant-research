"""BRK100B: 100 more ideas on information the breakout tests never used (MT5 broker spread, CME volume, cross-market states) plus untested
named systems, one pre-registered round on BRK50's engine. Pre-registration: forex/ea_research/PREREG_BRK100B.md.
   python -m forex.ea_research.brk100b --dry-run | --run"""
import argparse, collections, os, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.brk50 import Mkt, lt, LIS, NYZ, JST, SYD, H, DEV, VAL, HOLD, NONC
from forex.ea_research.orbx import ct
from forex.ea_research.analog import mclass
from forex.ea_research.brk30 import ema, wilder, sma, rmax, rmin, true_range, rsi, cci, cross_up, cross_dn, epoch, sgn
from forex.ea_research.brk100 import BX, LB, NB, SESSION, DLV, PARTNER56, ydaily, open_mid
from forex.ea_research.brk50b import fut_volume

CACHE = "data/scratch/brk100b_trades.parquet"
IDEAS = [f"M{k:03d}" for k in range(1, 101)]
FX = tuple(s for s in NONC if mclass(s) == "fx")
USI = ("SP", "NSDQ", "DOW"); IDX6 = USI + ("DAX", "NIKKEI", "ASX")
CME4 = {"NSDQ": "NQ", "SP": "ES", "XAUUSD": "GC", "XAGUSD": "SI"}
METALS = ("XAUUSD", "XAGUSD")
USDP = ("AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY")
CCY = ("EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY")
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
SPY = "futures/data/daily/SPY_yahoo_daily.csv"
START = pd.Timestamp("2022-01-01")
H4 = 4 * H
GROUP = {}
for _k in range(1, 101):
    _i = f"M{_k:03d}"
    GROUP[_i] = ("A spread" if _k <= 14 else "B+G CME volume" if _k <= 44 or 92 <= _k <= 94 or _k == 100 else "C cross-market"
                 if _k <= 52 else "D+E price-only" if _k <= 87 or _k in (95, 96) else "F VIX" if _k <= 91 else "H calendar")


# ---------------------------------------------------------------------- small helpers
def shift1(x):
    return np.r_[np.nan, np.asarray(x, float)[:-1]]


def sig2(up, dn):
    up = np.nan_to_num(np.asarray(up, float)) > 0; dn = np.nan_to_num(np.asarray(dn, float)) > 0
    return np.where(up, 1, np.where(dn, -1, 0))


def flips(s):
    """+1 where state s turns positive from non-positive, -1 where it turns negative from non-negative"""
    p = np.r_[0, s[:-1]]
    return sig2((s > 0) & (p <= 0), (s < 0) & (p >= 0))


def nxt(M, i, ahead=5):
    """the first index >= i whose minute is not the first of a server hour (lesson a) and not in the rollover window"""
    for k in range(i, min(i + ahead, M.n)):
        if M.t[k] % 3600 >= 60 and not M.D["roll"][k]:
            return k
    return None


def mclose(M, x):
    """mid close of the last minute starting at or before x (within 10 minutes)"""
    i = int(np.searchsorted(M.t, x, side="right")) - 1
    return M.mc[i] if i >= 0 and x - M.t[i] < 600 else np.nan


def enter_k(M, side, k, stop, x_end, mind=0.0):
    if k is None or k >= M.n or not np.isfinite(stop):
        return None
    e = M.D["ao"][k] if side > 0 else M.D["bo"][k]
    if mind > 0:
        stop = min(stop, e - mind) if side > 0 else max(stop, e + mind)
    ix = M.exit_idx(x_end)
    return None if ix is None else M.trade(side, k, e, stop, ix)


def enter_t(M, side, t0, stop=None, dist=None, x_end=None, mind=0.0):
    i = M.idx(t0)
    if i >= M.n or M.t[i] - t0 > 600:
        return None
    k = nxt(M, i)
    if k is None:
        return None
    e = M.D["ao"][k] if side > 0 else M.D["bo"][k]
    return enter_k(M, side, k, stop if stop is not None else e - side * dist, x_end, mind)


def mk(M, idea, res):
    if res is None:
        return None
    r = dict(res); r.update(idea=idea, sym=M.sym, day=pd.Timestamp(int(r["t_entry"]) // 86400 * 86400, unit="s"))
    return r


def bars2(M, tf):
    key = M.t // tf; st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], M.n]
    hh = np.maximum.reduceat(M.mh, st); ll = np.minimum.reduceat(M.ml, st); cc = M.mc[en - 1]
    B = dict(st=st, en=en, hh=hh, ll=ll, cc=cc, oo=(M.D["bo"][st] + M.D["ao"][st]) / 2, t0=key[st] * tf, tf=tf)
    B["atr"] = sma(true_range(hh, ll, cc), 14)
    return B


def bc2(M, B, sig, k_atr, N, idea):
    """bar-close signals; entry at the open of the second minute after the bar close (lesson a); stop k ATR14; exit at bar b+1+N"""
    out = []; D, t0, en, atr = M.D, B["t0"], B["en"], B["atr"]; busy = -1; b0 = int(np.searchsorted(t0, epoch(START)))
    for b in np.flatnonzero(sig):
        if b < max(b0, 60) or b <= busy or b + 1 + N >= len(t0) or not (atr[b] > 0):
            continue
        kk = nxt(M, int(en[b]))
        if kk is None or M.t[kk] - (t0[b] + B["tf"]) > 600:
            continue
        side = int(sig[b]); e = D["ao"][kk] if side > 0 else D["bo"][kk]
        ix = M.exit_idx(int(t0[b + 1 + N]))
        if ix is None:
            continue
        res = M.trade(side, kk, e, e - side * k_atr * atr[b], ix)
        if res is not None:
            out.append(mk(M, idea, res)); busy = int(np.searchsorted(t0, M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


def run_bc(out, M, B, up, dn, idea):
    k, N = (1.5, 24) if B["tf"] == H else (2.0, 30)
    out.extend(bc2(M, B, sig2(up, dn), k, N, idea))


def spread_rs(M):
    """minute spread / median spread of the same server minute-of-day over the previous 20 trading days"""
    t = M.t; day = t // 86400; mod = (t % 86400) // 60
    ud, di = np.unique(day, return_inverse=True)
    P = np.full((len(ud), 1440), np.nan); P[di, mod] = M.D["sp"]
    med = pd.DataFrame(P).rolling(20, min_periods=10).median().shift(1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        return M.D["sp"] / med[di, mod]


def sess_box(M, d):
    s = M.sym
    if s in USI:
        return lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ)
    if s == "NIKKEI":
        return lt(d, 9, 0, JST), lt(d, 9, 30, JST)
    if s == "ASX":
        return lt(d, 10, 0, SYD), lt(d, 10, 30, SYD)
    return lt(d, 8, 0), lt(d, 8, 30)


def cbox(M, d, lo=True, sh=True, mode="follow"):
    """CME session box: NB for NSDQ / SP, COMEX box for the metals"""
    if M.sym in METALS:
        return BX(M, d, NYZ, (8, 20), (8, 50), (11, 0), (13, 25), lo, sh, mode)
    return BX(M, d, NYZ, (9, 30), (10, 0), (12, 0), (15, 55), lo, sh, mode)


def us_holidays():
    s = pd.read_csv(SPY, parse_dates=["date"]).date
    s = s[s >= "2021-06-01"]
    return set(pd.bdate_range(s.min(), s.max()).difference(pd.DatetimeIndex(s)))


# ---------------------------------------------------------------------- indicators (bar arrays)
def wma(x, n):
    x = np.asarray(x, float); w = np.arange(1, n + 1, dtype=float); out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.convolve(x, w[::-1], mode="valid") / w.sum()
    return out


def ssmooth(x, n):
    a = np.exp(-1.414 * np.pi / n); c2 = 2 * a * np.cos(1.414 * np.pi / n); c3 = -a * a; c1 = 1 - c2 - c3
    x = np.asarray(x, float); y = np.copy(x)
    for i in range(2, len(x)):
        y[i] = c1 * (x[i] + x[i - 1]) / 2 + c2 * y[i - 1] + c3 * y[i - 2]
    return y


def hp2(x, n):
    w = 0.707 * 2 * np.pi / n; a = (np.cos(w) + np.sin(w) - 1) / np.cos(w); y = np.zeros(len(x))
    for i in range(2, len(x)):
        y[i] = (1 - a / 2) ** 2 * (x[i] - 2 * x[i - 1] + x[i - 2]) + 2 * (1 - a) * y[i - 1] - (1 - a) ** 2 * y[i - 2]
    return y


def hp1(x, n):
    a = (1 - np.sin(2 * np.pi / n)) / np.cos(2 * np.pi / n); y = np.zeros(len(x))
    for i in range(1, len(x)):
        y[i] = 0.5 * (1 + a) * (x[i] - x[i - 1]) + a * y[i - 1]
    return y


def ebsw(c, hpn=40, ssn=10):
    f = ssmooth(hp1(c, hpn), ssn); f1, f2 = shift1(f), np.r_[np.nan, np.nan, f[:-2]]
    wave = (f + f1 + f2) / 3; pwr = (f * f + f1 * f1 + f2 * f2) / 3
    with np.errstate(invalid="ignore", divide="ignore"):
        return wave / np.sqrt(np.where(pwr > 0, pwr, np.nan))


def laguerre_rsi(c, g=0.5):
    L0 = L1 = L2 = L3 = c[0]; out = np.full(len(c), np.nan)
    for i in range(len(c)):
        l0p, l1p, l2p = L0, L1, L2
        L0 = (1 - g) * c[i] + g * L0
        L1 = -g * L0 + l0p + g * L1
        L2 = -g * L1 + l1p + g * L2
        L3 = -g * L2 + l2p + g * L3
        cu = max(L0 - L1, 0) + max(L1 - L2, 0) + max(L2 - L3, 0); cd = max(L1 - L0, 0) + max(L2 - L1, 0) + max(L3 - L2, 0)
        out[i] = cu / (cu + cd) if cu + cd > 0 else np.nan
    return out


def itrend(c, a=0.07):
    it = np.asarray(c, float).copy()
    for i in range(2, len(c)):
        if i < 7:
            it[i] = (c[i] + 2 * c[i - 1] + c[i - 2]) / 4
        else:
            it[i] = ((a - a * a / 4) * c[i] + 0.5 * a * a * c[i - 1] - (a - 0.75 * a * a) * c[i - 2]
                     + 2 * (1 - a) * it[i - 1] - (1 - a) ** 2 * it[i - 2])
    return it, 2 * it - np.r_[np.nan, np.nan, it[:-2]]


def cyber_cycle(c, a=0.07):
    n = len(c); sm = np.asarray(c, float).copy(); cy = np.zeros(n)
    for i in range(3, n):
        sm[i] = (c[i] + 2 * c[i - 1] + 2 * c[i - 2] + c[i - 3]) / 6
    for i in range(2, n):
        cy[i] = ((c[i] - 2 * c[i - 1] + c[i - 2]) / 4 if i < 7 else
                 (1 - a / 2) ** 2 * (sm[i] - 2 * sm[i - 1] + sm[i - 2]) + 2 * (1 - a) * cy[i - 1] - (1 - a) ** 2 * cy[i - 2])
    return cy


def cog(hh, ll, n=10):
    p = (hh + ll) / 2; num = np.zeros(len(p)); den = np.zeros(len(p))
    for i in range(n):
        pi = np.r_[np.full(i, np.nan), p[:len(p) - i]]; num = num + (i + 1) * pi; den = den + pi
    return -num / den


def mama_fama(c, fast=0.5, slow=0.05):
    n = len(c); p = np.asarray(c, float)
    sm, dt, per, i1, q1, ji, jq, i2, q2, re, im, ph = (np.zeros(n) for _ in range(12))
    mama, fama = p.copy(), p.copy()
    for t in range(6, n):
        sm[t] = (4 * p[t] + 3 * p[t - 1] + 2 * p[t - 2] + p[t - 3]) / 10
        k = 0.075 * per[t - 1] + 0.54
        dt[t] = (0.0962 * sm[t] + 0.5769 * sm[t - 2] - 0.5769 * sm[t - 4] - 0.0962 * sm[t - 6]) * k
        q1[t] = (0.0962 * dt[t] + 0.5769 * dt[t - 2] - 0.5769 * dt[t - 4] - 0.0962 * dt[t - 6]) * k
        i1[t] = dt[t - 3]
        ji[t] = (0.0962 * i1[t] + 0.5769 * i1[t - 2] - 0.5769 * i1[t - 4] - 0.0962 * i1[t - 6]) * k
        jq[t] = (0.0962 * q1[t] + 0.5769 * q1[t - 2] - 0.5769 * q1[t - 4] - 0.0962 * q1[t - 6]) * k
        i2[t] = 0.2 * (i1[t] - jq[t]) + 0.8 * i2[t - 1]; q2[t] = 0.2 * (q1[t] + ji[t]) + 0.8 * q2[t - 1]
        re[t] = 0.2 * (i2[t] * i2[t - 1] + q2[t] * q2[t - 1]) + 0.8 * re[t - 1]
        im[t] = 0.2 * (i2[t] * q2[t - 1] - q2[t] * i2[t - 1]) + 0.8 * im[t - 1]
        pr = 360 / np.degrees(np.arctan(im[t] / re[t])) if (im[t] != 0 and re[t] != 0) else per[t - 1]
        if per[t - 1] > 0:
            pr = min(max(pr, 0.67 * per[t - 1]), 1.5 * per[t - 1])
        pr = min(max(pr, 6), 50); per[t] = 0.2 * pr + 0.8 * per[t - 1]
        ph[t] = np.degrees(np.arctan(q1[t] / i1[t])) if i1[t] != 0 else ph[t - 1]
        alpha = max(fast / max(ph[t - 1] - ph[t], 1), slow)
        mama[t] = alpha * p[t] + (1 - alpha) * mama[t - 1]; fama[t] = 0.5 * alpha * mama[t] + (1 - 0.5 * alpha) * fama[t - 1]
    return mama, fama


def qqe_trend(c, n=14, sf=5, q=4.236):
    rm = ema(rsi(c, n), sf); ar = np.abs(np.r_[0, np.diff(rm)]); wp = 2 * n - 1
    dar = ema(ema(ar, wp), wp) * q
    N = len(c); lb = np.zeros(N); sb = np.zeros(N); tr = np.zeros(N, int)
    for i in range(1, N):
        nsb, nlb = rm[i] + dar[i], rm[i] - dar[i]
        lb[i] = max(lb[i - 1], nlb) if (rm[i - 1] > lb[i - 1] and rm[i] > lb[i - 1]) else nlb
        sb[i] = min(sb[i - 1], nsb) if (rm[i - 1] < sb[i - 1] and rm[i] < sb[i - 1]) else nsb
        if rm[i] > sb[i - 1] and rm[i - 1] <= sb[i - 1]:
            tr[i] = 1
        elif rm[i] < lb[i - 1] and rm[i - 1] >= lb[i - 1]:
            tr[i] = -1
        else:
            tr[i] = tr[i - 1]
    return tr


def wavetrend(hh, ll, cc, n1=10, n2=21):
    ap = (hh + ll + cc) / 3; esa = ema(ap, n1); d = ema(np.abs(ap - esa), n1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ci = (ap - esa) / (0.015 * np.where(d > 0, d, np.nan))
    wt1 = ema(np.nan_to_num(ci), n2)
    return wt1, sma(wt1, 4)


def ssl_state(hh, ll, cc, n=10):
    sh, sl = sma(hh, n), sma(ll, n); s = np.zeros(len(cc), int)
    for i in range(1, len(cc)):
        s[i] = 1 if cc[i] > sh[i] else (-1 if cc[i] < sl[i] else s[i - 1])
    return s


def range_filter_dir(c, per=100, mult=3.0):
    smr = ema(ema(np.abs(np.r_[0, np.diff(c)]), per), 2 * per - 1) * mult
    f = np.asarray(c, float).copy(); d = np.zeros(len(c), int)
    for i in range(1, len(c)):
        f[i] = max(f[i - 1], c[i] - smr[i]) if c[i] > f[i - 1] else min(f[i - 1], c[i] + smr[i])
        d[i] = 1 if f[i] > f[i - 1] else (-1 if f[i] < f[i - 1] else d[i - 1])
    return d


def halftrend_up(hh, ll, cc, amp=2):
    """+1 while HalfTrend is up, -1 while down"""
    n = len(cc); trend = np.zeros(n, int); nt = 0; maxl, minh = ll[0], hh[0]
    hp = pd.Series(hh).rolling(amp, min_periods=1).max().to_numpy(); lp = pd.Series(ll).rolling(amp, min_periods=1).min().to_numpy()
    hma, lma = sma(hh, amp), sma(ll, amp)
    for i in range(1, n):
        tr = trend[i - 1]
        if nt == 1:
            maxl = max(lp[i], maxl)
            if hma[i] < maxl and cc[i] < ll[i - 1]:
                tr, nt, minh = 1, 0, hp[i]
        else:
            minh = min(hp[i], minh)
            if lma[i] > minh and cc[i] > hh[i - 1]:
                tr, nt, maxl = 0, 1, lp[i]
        trend[i] = tr
    return np.where(trend == 0, 1, -1)


def alphatrend(hh, ll, cc, ap=14, coeff=1.0):
    atr = sma(true_range(hh, ll, cc), ap); up, dn = ll - atr * coeff, hh + atr * coeff; r = rsi(cc, ap)
    a = np.asarray(cc, float).copy()
    for i in range(1, len(cc)):
        if not np.isfinite(atr[i]):
            continue
        a[i] = (a[i - 1] if up[i] < a[i - 1] else up[i]) if r[i] >= 50 else (a[i - 1] if dn[i] > a[i - 1] else dn[i])
    return a


def trend_magic(hh, ll, cc, cn=20, an=5, mult=1.0):
    c_ = cci(hh, ll, cc, cn); atr = sma(true_range(hh, ll, cc), an); up, dn = ll - atr * mult, hh + atr * mult
    m = np.asarray(cc, float).copy()
    for i in range(1, len(cc)):
        if np.isfinite(c_[i]) and np.isfinite(atr[i]):
            m[i] = max(up[i], m[i - 1]) if c_[i] >= 0 else min(dn[i], m[i - 1])
    return m


def coral(c, sm=21, cd=0.4):
    di = (sm - 1) / 2 + 1; c1 = 2 / (di + 1); c2 = 1 - c1
    c3 = 3 * (cd * cd + cd ** 3); c4 = -3 * (2 * cd * cd + cd + cd ** 3); c5 = 3 * cd + 1 + cd ** 3 + 3 * cd * cd
    i1 = i2 = i3 = i4 = i5 = i6 = c[0]; out = np.zeros(len(c))
    for k in range(len(c)):
        i1 = c1 * c[k] + c2 * i1; i2 = c1 * i1 + c2 * i2; i3 = c1 * i2 + c2 * i3
        i4 = c1 * i3 + c2 * i4; i5 = c1 * i4 + c2 * i5; i6 = c1 * i5 + c2 * i6
        out[k] = -cd ** 3 * i6 + c3 * i5 + c4 * i4 + c5 * i3
    return out


def tsi(c, r=25, s=13, sg=7):
    m = np.r_[0, np.diff(c)]; den = ema(ema(np.abs(m), r), s)
    with np.errstate(invalid="ignore", divide="ignore"):
        t = 100 * ema(ema(m, r), s) / np.where(den > 0, den, np.nan)
    return t, ema(np.nan_to_num(t), sg)


def vidya(c, n=14, cm=9):
    d = np.r_[0, np.diff(c)]; up = pd.Series(np.maximum(d, 0)).rolling(cm).sum().to_numpy()
    dn = pd.Series(np.maximum(-d, 0)).rolling(cm).sum().to_numpy(); a = 2 / (n + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        k = np.abs((up - dn) / np.where(up + dn > 0, up + dn, np.nan))
    v = np.asarray(c, float).copy()
    for i in range(1, len(c)):
        kk = k[i] if np.isfinite(k[i]) else 0.0
        v[i] = a * kk * c[i] + (1 - a * kk) * v[i - 1]
    return v


def hurst(c, win=128):
    r = np.diff(np.log(c)); out = np.full(len(c), np.nan)
    if len(r) < win:
        return out
    W = np.lib.stride_tricks.sliding_window_view(r, win); scales = (8, 16, 32, 64, 128); lrs = []
    for s in scales:
        X = W.reshape(W.shape[0], win // s, s); Z = np.cumsum(X - X.mean(axis=2, keepdims=True), axis=2)
        R = Z.max(axis=2) - Z.min(axis=2); S = X.std(axis=2)
        with np.errstate(invalid="ignore", divide="ignore"):
            lrs.append(np.log(np.nanmean(np.where(S > 0, R / np.where(S > 0, S, 1), np.nan), axis=1)))
    L = np.vstack(lrs).T; ls = np.log(scales); lsm = ls - ls.mean()
    out[win:] = ((L - L.mean(axis=1, keepdims=True)) * lsm).sum(axis=1) / (lsm ** 2).sum()
    return out


def perm_entropy(c, win=60):
    X = np.stack([c[:-2], c[1:-1], c[2:]], axis=1); P = np.argsort(X, axis=1, kind="stable")
    code = P[:, 0] * 9 + P[:, 1] * 3 + P[:, 2]; m = win - 2; ent = np.zeros(len(code))
    for u in np.unique(code):
        pu = pd.Series((code == u).astype(float)).rolling(m).sum().to_numpy() / m
        with np.errstate(invalid="ignore", divide="ignore"):
            ent = ent - np.where(pu > 0, pu * np.log(np.where(pu > 0, pu, 1)), 0)
    out = np.full(len(c), np.nan); out[2:] = ent / np.log(6); out[:win] = np.nan
    return out


def kalman_slope(c):
    n = len(c); out = np.full(n, np.nan); var = pd.Series(np.r_[np.nan, np.diff(c)]).rolling(250, min_periods=100).var().shift(1).to_numpy()
    x0, x1 = c[0], 0.0; P00 = P01 = P11 = 0.0; started = False
    for i in range(1, n):
        R = var[i]
        if not (np.isfinite(R) and R > 0):
            continue
        if not started:
            x0, x1, P00, P01, P11, started = c[i], 0.0, R, 0.0, R, True
            continue
        x0 = x0 + x1
        P00, P01, P11 = P00 + 2 * P01 + P11 + 0.01 * R, P01 + P11, P11 + 0.0001 * R
        S = P00 + R; K0, K1 = P00 / S, P01 / S; y = c[i] - x0
        x0, x1 = x0 + K0 * y, x1 + K1 * y
        P00, P01, P11 = (1 - K0) * P00, (1 - K0) * P01, P11 - K1 * P01
        out[i] = x1
    return out


def ift_rsi(c):
    v = wma(0.1 * (rsi(c, 5) - 50), 9)
    return np.tanh(v)                                                    # = (e^2v - 1) / (e^2v + 1)


# ---------------------------------------------------------------------- bar-based tests
def price_bar_ideas(M, rs):
    out = []; B1, B4 = bars2(M, H), bars2(M, H4)
    # M010 stress bar
    fin = np.isfinite(rs); s_ = np.add.reduceat(np.where(fin, rs, 0.0), B1["st"]); c_ = np.add.reduceat(fin.astype(float), B1["st"])
    rsb = np.where(c_ > 0, s_ / np.where(c_ > 0, c_, 1), np.nan); mx = rmax(rsb, 24)
    hh, ll, cc = B1["hh"], B1["ll"], B1["cc"]; rg = hh - ll; cl = np.where(rg > 0, (cc - ll) / np.where(rg > 0, rg, 1), 0.5)
    st_ = (rsb >= mx) & (rsb > 1)
    run_bc(out, M, B1, st_ & (cl >= 0.75), st_ & (cl <= 0.25), "M010")
    # H1 indicators
    z = np.zeros(len(cc)); qt = qqe_trend(cc); run_bc(out, M, B1, (qt == 1) & (np.r_[0, qt[:-1]] != 1), (qt == -1) & (np.r_[0, qt[:-1]] != -1), "M057")
    rf = range_filter_dir(cc); out.extend(bc2(M, B1, flips(rf), 1.5, 24, "M060"))
    t_, ts_ = tsi(cc); run_bc(out, M, B1, cross_up(t_, ts_), cross_dn(t_, ts_), "M066")
    lr_ = laguerre_rsi(cc); run_bc(out, M, B1, cross_up(lr_, z + 0.2), cross_dn(lr_, z + 0.8), "M074")
    cg = cog(hh, ll); cgt = shift1(cg); run_bc(out, M, B1, cross_up(cg, cgt), cross_dn(cg, cgt), "M079")
    ift = ift_rsi(cc); run_bc(out, M, B1, cross_up(ift, z - 0.5), cross_dn(ift, z + 0.5), "M095")
    hu = hurst(cc); pmx, pmn = shift1(rmax(cc, 20)), shift1(rmin(cc, 20)); bu, bd = cc > pmx, cc < pmn
    run_bc(out, M, B1, (hu > 0.6) & bu, (hu > 0.6) & bd, "M082")
    run_bc(out, M, B1, (hu < 0.4) & bd, (hu < 0.4) & bu, "M083")
    pe = perm_entropy(cc); run_bc(out, M, B1, (pe < 0.9) & bu, (pe < 0.9) & bd, "M084")
    ks = kalman_slope(cc); kp = shift1(ks); run_bc(out, M, B1, (ks > 0) & (kp <= 0), (ks < 0) & (kp >= 0), "M085")
    # H4 indicators
    hh, ll, cc, oo = B4["hh"], B4["ll"], B4["cc"], B4["oo"]; z = np.zeros(len(cc)); mp = (hh + ll) / 2
    ao = sma(mp, 5) - sma(mp, 34); ac = ao - sma(ao, 5); run_bc(out, M, B4, cross_up(ac, z), cross_dn(ac, z), "M056")
    w1, w2 = wavetrend(hh, ll, cc); run_bc(out, M, B4, cross_up(w1, w2) & (w1 < -53), cross_dn(w1, w2) & (w1 > 53), "M058")
    out.extend(bc2(M, B4, flips(ssl_state(hh, ll, cc)), 2.0, 30, "M059"))
    out.extend(bc2(M, B4, flips(halftrend_up(hh, ll, cc)), 2.0, 30, "M061"))
    at = alphatrend(hh, ll, cc); at2 = np.r_[np.nan, np.nan, at[:-2]]; run_bc(out, M, B4, cross_up(at, at2), cross_dn(at, at2), "M062")
    tm = trend_magic(hh, ll, cc); run_bc(out, M, B4, cross_up(cc, tm), cross_dn(cc, tm), "M063")
    co = coral(cc); dco = np.r_[0, np.diff(co)]; out.extend(bc2(M, B4, flips(np.sign(dco)), 2.0, 30, "M064"))
    vi = vidya(cc); run_bc(out, M, B4, cross_up(cc, vi), cross_dn(cc, vi), "M067")
    atr10 = sma(true_range(hh, ll, cc), 10); sshort = rmax(rmax(hh, 10) - atr10, 9); slong = rmin(rmin(ll, 10) + atr10, 9)
    run_bc(out, M, B4, cross_up(cc, sshort), cross_dn(cc, slong), "M069")
    den = pd.Series(np.abs(np.r_[np.nan, np.diff(cc)])).rolling(28).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vh = (rmax(cc, 28) - rmin(cc, 28)) / np.where(den > 0, den, np.nan)
    p28x, p28n = shift1(rmax(cc, 28)), shift1(rmin(cc, 28)); run_bc(out, M, B4, (vh > 0.4) & (cc > p28x), (vh > 0.4) & (cc < p28n), "M070")
    qs = sma(cc - oo, 14); run_bc(out, M, B4, cross_up(qs, z), cross_dn(qs, z), "M071")
    s10, s40 = ssmooth(cc, 10), ssmooth(cc, 40); run_bc(out, M, B4, cross_up(s10, s40), cross_dn(s10, s40), "M073")
    rf_ = ssmooth(hp2(cc, 48), 10); run_bc(out, M, B4, cross_up(rf_, z), cross_dn(rf_, z), "M075")
    it, tr = itrend(cc); run_bc(out, M, B4, cross_up(tr, it), cross_dn(tr, it), "M076")
    ma, fa = mama_fama(cc); run_bc(out, M, B4, cross_up(ma, fa), cross_dn(ma, fa), "M077")
    cy = cyber_cycle(cc); cyt = shift1(cy); run_bc(out, M, B4, cross_up(cy, cyt) & (cy < 0), cross_dn(cy, cyt) & (cy > 0), "M078")
    dco_ = hp2(cc, 60) - hp2(cc, 30); run_bc(out, M, B4, cross_up(dco_, z), cross_dn(dco_, z), "M080")
    eb = ebsw(cc); run_bc(out, M, B4, cross_up(eb, z - 0.9), cross_dn(eb, z + 0.9), "M081")
    return out


def cme_bar_ideas(M, v):
    out = []; B1, B4 = bars2(M, H), bars2(M, H4)
    for B in (B1, B4):
        B["V"] = np.add.reduceat(v, B["st"])
    hh, ll, cc, oo, V = B1["hh"], B1["ll"], B1["cc"], B1["oo"], B1["V"]; dc = np.r_[0, np.diff(cc)]; z = np.zeros(len(cc))
    obv = np.cumsum(np.sign(dc) * V)
    run_bc(out, M, B1, (obv > shift1(rmax(obv, 20))) & (cc < shift1(rmax(cc, 20))), (obv < shift1(rmin(obv, 20))) & (cc > shift1(rmin(cc, 20))), "M033")
    tp = (hh + ll + cc) / 3; mf = tp * V; dtp = np.r_[0, np.diff(tp)]
    pos = pd.Series(np.where(dtp > 0, mf, 0)).rolling(14).sum().to_numpy(); neg = pd.Series(np.where(dtp < 0, mf, 0)).rolling(14).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        mfi = np.where(neg > 0, 100 - 100 / (1 + pos / np.where(neg > 0, neg, 1)), np.where(pos > 0, 100.0, np.nan))
    run_bc(out, M, B1, cross_up(mfi, z + 20), cross_dn(mfi, z + 80), "M034")
    hlc = hh + ll + cc; trend = np.where(np.r_[False, hlc[1:] > hlc[:-1]], 1, -1); dm = hh - ll; cm = np.zeros(len(cc))
    for i in range(1, len(cc)):
        cm[i] = cm[i - 1] + dm[i] if trend[i] == trend[i - 1] else dm[i - 1] + dm[i]
    with np.errstate(invalid="ignore", divide="ignore"):
        vf = np.nan_to_num(V * np.abs(2 * (dm / np.where(cm > 0, cm, np.nan)) - 1) * trend * 100)
    kvo = ema(vf, 34) - ema(vf, 55); ksg = ema(kvo, 13)
    run_bc(out, M, B1, cross_up(kvo, ksg) & (kvo < 0), cross_dn(kvo, ksg) & (kvo > 0), "M035")
    fi = ema(dc * V, 13); run_bc(out, M, B1, cross_up(fi, z), cross_dn(fi, z), "M036")
    rg = hh - ll; mfm = np.where(rg > 0, ((cc - ll) - (hh - cc)) / np.where(rg > 0, rg, 1), 0); adl = np.cumsum(mfm * V)
    cho = ema(adl, 3) - ema(adl, 10); run_bc(out, M, B1, cross_up(cho, z), cross_dn(cho, z), "M038")
    e26 = ema(V, 26)
    with np.errstate(invalid="ignore", divide="ignore"):
        pvo = 100 * (ema(V, 12) - e26) / np.where(e26 > 0, e26, np.nan)
    cu = cross_up(pvo, z); run_bc(out, M, B1, cu & (cc > oo), cu & (cc < oo), "M040")

    def vwma(c_, V_, n):
        sv = pd.Series(V_).rolling(n).sum().to_numpy()
        with np.errstate(invalid="ignore", divide="ignore"):
            return pd.Series(c_ * V_).rolling(n).sum().to_numpy() / np.where(sv > 0, sv, np.nan)
    vm = vwma(cc, V, 12) - vwma(cc, V, 26); vms = ema(np.nan_to_num(vm), 9); run_bc(out, M, B1, cross_up(vm, vms), cross_dn(vm, vms), "M042")
    hh, ll, cc, oo, V = B4["hh"], B4["ll"], B4["cc"], B4["oo"], B4["V"]; dc = np.r_[0, np.diff(cc)]; z = np.zeros(len(cc))
    mp = (hh + ll) / 2
    with np.errstate(invalid="ignore", divide="ignore"):
        emv = sma(np.nan_to_num(np.r_[0, np.diff(mp)] * (hh - ll) / np.where(V > 0, V, np.nan)), 14)
    run_bc(out, M, B4, cross_up(emv, z), cross_dn(emv, z), "M037")
    vpt = np.cumsum(V * dc / np.r_[cc[0], cc[:-1]]); vps = ema(vpt, 13); run_bc(out, M, B4, cross_up(vpt, vps), cross_dn(vpt, vps), "M039")
    ev = ema(V, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        vzo = 100 * ema(np.sign(dc) * V, 14) / np.where(ev > 0, ev, np.nan)
    run_bc(out, M, B4, cross_up(vzo, z), cross_dn(vzo, z), "M041")
    pc = np.r_[cc[0], cc[:-1]]; trh, trl = np.maximum(hh, pc), np.minimum(ll, pc); rr = trh - trl
    ad = np.where(rr > 0, V * ((cc - trl) - (trh - cc)) / np.where(rr > 0, rr, 1), 0); wv = wilder(V, 21)
    with np.errstate(invalid="ignore", divide="ignore"):
        tmf = wilder(ad, 21) / np.where(wv > 0, wv, np.nan)
    run_bc(out, M, B4, cross_up(tmf, z), cross_dn(tmf, z), "M043")
    s20, s5 = sma(cc, 20), sma(cc, 5); v20 = sma(V, 20)
    with np.errstate(invalid="ignore", divide="ignore"):
        vpci = (vwma(cc, V, 20) - s20) * (vwma(cc, V, 5) / s5) * (sma(V, 5) / np.where(v20 > 0, v20, np.nan))
    run_bc(out, M, B4, cross_up(vpci, z) & (cc > s20), cross_dn(vpci, z) & (cc < s20), "M044")
    return out


# ---------------------------------------------------------------------- CME daily (NVI)
def cme_daily(root, cut=None):
    f = pd.read_parquet(FUTP.format(root), columns=["ts", "close", "volume"]).sort_values("ts")
    if cut is not None:
        srv = f.ts.dt.tz_convert("Europe/Athens").dt.tz_localize(None)
        f = f[((srv - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy() < cut]
    td = (f.ts.dt.tz_convert(NYZ) + pd.Timedelta(hours=6)).dt.tz_localize(None).dt.normalize()
    g = pd.DataFrame({"td": td.to_numpy(), "c": f.close.to_numpy(), "v": f.volume.to_numpy()}).groupby("td").agg(c=("c", "last"), v=("v", "sum"))
    return g[g.index.weekday < 5]


def nvi_sign(g):
    r = g.c.pct_change().fillna(0).to_numpy(); v = g.v.to_numpy(); nvi = np.ones(len(g))
    for i in range(1, len(g)):
        nvi[i] = nvi[i - 1] * (1 + r[i]) if v[i] < v[i - 1] else nvi[i - 1]
    e = ema(nvi, 255)
    return pd.Series(np.where(np.arange(len(g)) >= 255, np.sign(nvi - e), 0.0), index=g.index)


def rbreaker_rev(M, d, P_, H_, L_):
    ss, se, bs_, be = P_ + (H_ - L_), 2 * P_ - L_, P_ - (H_ - L_), 2 * P_ - H_
    i0, i1 = M.idx(lt(d, 8, 0)), M.idx(lt(d, 19, 0))
    if i1 - i0 < 60:
        return None
    rh, rl = np.maximum.accumulate(M.mh[i0:i1]), np.minimum.accumulate(M.ml[i0:i1]); mc = M.mc[i0:i1]
    sS, sL = (rh > ss) & (mc <= se), (rl < bs_) & (mc >= be)
    j = np.flatnonzero(sS | sL)
    if not len(j):
        return None
    j = int(j[0]); side = -1 if sS[j] else 1
    return enter_k(M, side, nxt(M, i0 + j + 1), rh[j] if side < 0 else rl[j], lt(d, 20, 45))


# ---------------------------------------------------------------------- per-market build
def market(args):
    sym, cut = args
    M = Mkt(sym, cut); D, Dd = M.D, M.Dd; out = []; nd = len(M.days)
    cd = pd.Timestamp(cut, unit="s").normalize() if cut is not None else None

    def add(idea, res):
        r = mk(M, idea, res)
        if r is not None:
            out.append(r)

    def state(idea, d, **kw):
        out.append(dict(idea=idea, sym=sym, day=d, **kw))

    rs = spread_rs(M); fin = np.isfinite(rs); shock = fin & (rs >= 4)
    hol = us_holidays()
    C, Hd, Ld = Dd.C.to_numpy(), Dd.H.to_numpy(), Dd.L.to_numpy(); lr = np.r_[np.nan, np.diff(np.log(C))]
    drs = np.full(nd, np.nan); nsh = np.zeros(nd)
    for p in range(nd):
        d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); i0, i1 = M.idx(lt(d, 8, 0)), M.idx(lt(d, 19, 0))
        if i1 - i0 > 60 and fin[i0:i1].any():
            drs[p] = np.nanmean(rs[i0:i1]); nsh[p] = shock[i0:i1].sum()
    # daily indicators (value at q uses data up to the close of day q)
    e13 = ema(C, 13); macd = ema(C, 12) - ema(C, 26); hist = macd - ema(macd, 9)
    green = np.r_[False, (e13[1:] > e13[:-1]) & (hist[1:] > hist[:-1])]; red = np.r_[False, (e13[1:] < e13[:-1]) & (hist[1:] < hist[:-1])]
    with np.errstate(invalid="ignore", divide="ignore"):
        roc = lambda n: 100 * (C / np.r_[np.full(n, np.nan), C[:-n]] - 1)
        cop = wma(roc(14) + roc(11), 10)
        mx14 = rmax(C, 14); ui = np.sqrt(sma((100 * (C - mx14) / mx14) ** 2, 14)); ui60 = rmin(ui, 60)
        hc22, lc22 = rmax(C, 22), rmin(C, 22); wvf = (hc22 - Ld) / hc22; iwv = (Hd - lc22) / lc22
    wub = sma(wvf, 20) + 2 * pd.Series(wvf).rolling(20).std().to_numpy(); iub = sma(iwv, 20) + 2 * pd.Series(iwv).rolling(20).std().to_numpy()
    ac60 = pd.Series(lr).rolling(60).corr(pd.Series(lr).shift(1)).to_numpy()
    X = {}
    if sym == "XAUUSD":
        X["EURUSD"] = Mkt("EURUSD", cut)
    if sym in USI:
        vix = ydaily("^VIX_yahoo_daily.csv", cd); v3m = ydaily("^VIX3M_yahoo_daily.csv", cd); tsx = (v3m - vix).dropna()
    cme = sym in CME4
    if cme:
        ft, cv = fut_volume(CME4[sym], cut); v = cv[np.searchsorted(ft, M.t + 60)] - cv[np.searchsorted(ft, M.t)]
        nsg = nvi_sign(cme_daily(CME4[sym], cut))
        SV, VW, SC, SH, SL, FV, LV = (np.full(nd, np.nan) for _ in range(7))
        prevmin = collections.deque(maxlen=20); blocks = collections.deque(maxlen=20)
        ses = ((8, 20), (13, 30), (13, 25)) if sym in METALS else ((9, 30), (16, 0), (15, 55))
    for p in range(nd):
        d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); live = d >= START and p >= 30
        atr = Dd.atr.iloc[p]
        if not np.isfinite(atr):
            live = False
        # ------------------------------------------------ CME sessions (stats for every day, trades when live)
        if cme:
            a, b, xe = lt(d, *ses[0], NYZ), lt(d, *ses[1], NYZ), lt(d, *ses[2], NYZ)
            i0, i1 = M.idx(a), M.idx(b)
            if i1 - i0 >= 0.8 * (b - a) / 60:
                sl = slice(i0, i1); mcs, mhs, mls, vs, tss = M.mc[sl], M.mh[sl], M.ml[sl], v[sl], M.t[sl]
                mos = (D["bo"][sl] + D["ao"][sl]) / 2
                cvv, cpv, cp2 = np.cumsum(vs), np.cumsum(vs * mcs), np.cumsum(vs * mcs * mcs)
                with np.errstate(invalid="ignore", divide="ignore"):
                    vw = np.where(cvv > 0, cpv / np.where(cvv > 0, cvv, 1), np.nan)
                    sg = np.sqrt(np.maximum(np.where(cvv > 0, cp2 / np.where(cvv > 0, cvv, 1), np.nan) - vw ** 2, 0))
                SV[p], VW[p], SC[p], SH[p], SL[p] = vs.sum(), vw[-1], mclose(M, xe - 60), mhs.max(), mls.min()
                FV[p] = vs[tss < a + 1800].sum()
                if sym in ("NSDQ", "SP"):
                    LV[p] = vs[(tss >= lt(d, 11, 30, NYZ)) & (tss < lt(d, 13, 0, NYZ))].sum()
                mid0 = lt(d, 0, 0, NYZ); fb = mid0 + 60 * int(np.ceil((a + 1800 - mid0) / 60 / 15) * 15); tblk = {}
                for bs in range(fb, b - 75 * 60 + 1, 900):
                    m_ = (tss >= bs) & (tss < bs + 900)
                    if m_.sum() >= 12:
                        tblk[bs - mid0] = (vs[m_].sum(), mhs[m_].max() - mls[m_].min(), bs, D["bh"][sl][m_].max(), D["bl"][sl][m_].min())
                if live:
                    iw0, iw1 = int(np.searchsorted(tss, a + 1800)), int(np.searchsorted(tss, b - 3600))
                    below = np.r_[False, np.maximum.accumulate(mcs <= vw - 0.25 * atr)[:-1]]
                    above = np.r_[False, np.maximum.accumulate(mcs >= vw + 0.25 * atr)[:-1]]
                    cu = np.r_[False, (mcs[1:] > vw[1:]) & (mcs[:-1] <= vw[:-1])]; cdn = np.r_[False, (mcs[1:] < vw[1:]) & (mcs[:-1] >= vw[:-1])]
                    sL, sS = cu & below, cdn & above; j_ = np.flatnonzero((sL | sS)[iw0:iw1])
                    if len(j_):                                                    # M015 VWAP reclaim
                        j = iw0 + int(j_[0]); side = 1 if sL[j] else -1
                        add("M015", enter_k(M, side, nxt(M, i0 + j + 1), mls[:j + 1].min() if side > 0 else mhs[:j + 1].max(), xe, 0.1 * atr))
                    jA, jB = int(np.searchsorted(tss, a + 1800)), int(np.searchsorted(tss, a + 5400))
                    if jB - jA >= 50 and jB < len(tss):                            # M016 VWAP trend hold
                        up_, dn_ = (mcs[jA:jB] > vw[jA:jB]).all(), (mcs[jA:jB] < vw[jA:jB]).all()
                        if up_ or dn_:
                            side = 1 if up_ else -1
                            add("M016", enter_t(M, side, a + 5400, stop=vw[jB - 1] - side * 0.1 * atr, x_end=xe, mind=0.1 * atr))
                    u2, d2 = (mcs > vw + 2 * sg) & (sg > 0), (mcs < vw - 2 * sg) & (sg > 0); j_ = np.flatnonzero((u2 | d2)[iw0:iw1])
                    if len(j_):                                                    # M017 / M018 VWAP 2 sigma
                        j = iw0 + int(j_[0]); side = 1 if u2[j] else -1; k = nxt(M, i0 + j + 1)
                        add("M017", enter_k(M, side, k, vw[j], xe, 0.1 * atr))
                        if k is not None:
                            ef = D["ao"][k] if -side > 0 else D["bo"][k]
                            add("M018", enter_k(M, -side, k, ef + side * sg[j], xe, 0.1 * atr))
                    if p >= 1 and np.isfinite(VW[p - 1]):                          # M019 yesterday's VWAP level
                        m0 = M.mid_at(a); Vs = VW[p - 1]
                        if np.isfinite(m0) and m0 != Vs:
                            add("M019", M.level(Vs if m0 < Vs else None, Vs if m0 > Vs else None, a, a + 3 * 3600, "follow", dist=0.25 * atr, x_end=xe))
                    upf = np.r_[False, np.maximum.accumulate(mhs - vw >= 0.5 * atr)[:-1]]; dnf = np.r_[False, np.maximum.accumulate(vw - mls >= 0.5 * atr)[:-1]]
                    tL, tS = upf & (mls <= vw), dnf & (mhs >= vw); j_ = np.flatnonzero((tL | tS)[iw0:iw1])
                    if len(j_):                                                    # M020 VWAP pullback
                        j = iw0 + int(j_[0]); side = 1 if tL[j] else -1
                        add("M020", enter_k(M, side, nxt(M, i0 + j + 1), vw[j] - side * 0.25 * atr, xe, 0.1 * atr))
                    if len(prevmin) == 20:                                         # M021 / M022 volume climax
                        pv = np.concatenate([x[0] for x in prevmin]); pr = np.concatenate([x[1] for x in prevmin])
                        thr, mr = np.percentile(pv, 99.5), np.median(pr)
                        jc0, jc1 = int(np.searchsorted(tss, a + 900)), int(np.searchsorted(tss, b - 65 * 60))
                        if thr > 0 and mr > 0:
                            cand = np.flatnonzero((vs[jc0:jc1] >= thr) & ((mhs - mls)[jc0:jc1] >= 3 * mr))
                            if len(cand):
                                c = jc0 + int(cand[0]); dirc = sgn(mcs[c] - mos[c]); midc = (mhs[c] + mls[c]) / 2
                                if dirc and c + 6 < len(tss) and tss[c + 5] - tss[c] <= 300:
                                    n5 = mcs[c + 1:c + 6]; ret = np.flatnonzero(n5 < midc) if dirc > 0 else np.flatnonzero(n5 > midc)
                                    if len(ret):
                                        k = nxt(M, i0 + c + 2 + int(ret[0]))
                                        if k is not None:
                                            add("M021", enter_k(M, -dirc, k, mhs[c] if dirc > 0 else mls[c], int(M.t[k]) + 3600, 0.1 * atr))
                                    else:
                                        k = nxt(M, i0 + c + 6)
                                        if k is not None:
                                            add("M022", enter_k(M, dirc, k, midc, int(M.t[k]) + 3600, 0.1 * atr))
                    if sym in ("NSDQ", "SP"):                                      # M023 lunch dry-up
                        pl = LV[max(0, p - 20):p]; pl = pl[np.isfinite(pl)]
                        if len(pl) >= 15 and np.isfinite(LV[p]) and LV[p] < 0.5 * np.median(pl):
                            add("M023", BX(M, d, NYZ, (11, 30), (13, 0), (15, 30), (15, 55)))
                    if len(blocks) == 20:                                          # M024 absorption
                        for key in sorted(tblk):
                            bv, br, bs, bhi, blo = tblk[key]
                            hv = [x[key][0] for x in blocks if key in x]; hr = [x[key][1] for x in blocks if key in x]
                            if len(hv) >= 15 and br > 0 and bv >= 2.5 * np.median(hv) and br <= 0.5 * np.median(hr):
                                add("M024", M.level(bhi, blo, bs + 900, bs + 900 + 3600, "follow", slU=blo, slL=bhi, x_end=xe))
                                break
                    j60 = int(np.searchsorted(tss, a + 3600))
                    if 45 <= j60 < len(tss):                                       # M025 opening-hour signed volume
                        prevc = np.r_[M.mc[i0 - 1] if i0 > 0 else mcs[0], mcs[:-1]]
                        upv = vs[:j60][mcs[:j60] > prevc[:j60]].sum(); dnv = vs[:j60][mcs[:j60] < prevc[:j60]].sum()
                        if upv > 0 and dnv > 0:
                            if upv / dnv >= 1.5:
                                add("M025", enter_t(M, 1, a + 3600, stop=mls[:j60].min(), x_end=xe, mind=0.1 * atr))
                            elif upv / dnv <= 1 / 1.5:
                                add("M025", enter_t(M, -1, a + 3600, stop=mhs[:j60].max(), x_end=xe, mind=0.1 * atr))
                    j120 = int(np.searchsorted(tss, a + 7200))
                    if 90 <= j120 < len(tss):                                      # M026 cumulative-delta divergence
                        rgm = mhs[:j120] - mls[:j120]
                        dl = np.where(rgm > 0, vs[:j120] * (mcs[:j120] - mos[:j120]) / np.where(rgm > 0, rgm, 1), 0).sum(); pc = mcs[j120 - 1] - mos[0]
                        if pc > 0 and dl < 0:
                            add("M026", enter_t(M, -1, a + 7200, stop=mhs[:j120].max() + 0.05 * atr, x_end=xe, mind=0.1 * atr))
                        elif pc < 0 and dl > 0:
                            add("M026", enter_t(M, 1, a + 7200, stop=mls[:j120].min() - 0.05 * atr, x_end=xe, mind=0.1 * atr))
                    if sym in ("NSDQ", "SP"):                                      # M100 helper
                        pf = FV[max(0, p - 20):p]; pf = pf[np.isfinite(pf)]
                        if len(pf) >= 15 and np.median(pf) > 0:
                            state("_RVS", d, relv=FV[p] / np.median(pf)); add("_RVT", cbox(M, d))
                prevmin.append((vs, mhs - mls)); blocks.append(tblk)
            if live and p >= 61:                                                   # daily CME ideas (yesterday's session)
                y, yy = Dd.iloc[p - 1], Dd.iloc[p - 2]; chg = y.C - yy.C
                prevS = SV[p - 21:p - 1]; prevS = prevS[np.isfinite(prevS)]
                if np.isfinite(SV[p - 1]) and len(prevS) >= 15:
                    medS = np.median(prevS); loc = (y.C - y.L) / (y.H - y.L) if y.H > y.L else np.nan
                    if SV[p - 1] >= 1.5 * medS:
                        if loc >= 0.8:
                            add("M027", DLV(M, d, y.H, None, atr))
                        elif loc <= 0.2:
                            add("M027", DLV(M, d, None, y.L, atr))
                    if SV[p - 1] <= 0.8 * medS:
                        if chg >= 0.5 * atr:
                            add("M028", DLV(M, d, y.H, None, atr, "fade"))
                        elif chg <= -0.5 * atr:
                            add("M028", DLV(M, d, None, y.L, atr, "fade"))
                    if SV[p - 1] >= 2 * medS:
                        if chg <= -atr:
                            add("M092", cbox(M, d, True, False))
                        elif chg >= atr:
                            add("M092", cbox(M, d, False, True))
                if np.isfinite(VW[p - 1]) and np.isfinite(SC[p - 1]):
                    dv = SC[p - 1] - VW[p - 1]
                    if dv >= 0.25 * atr:
                        add("M029", cbox(M, d, True, False))
                    elif dv <= -0.25 * atr:
                        add("M029", cbox(M, d, False, True))
                if np.isfinite(VW[p - 1]) and SH[p - 1] > SL[p - 1]:
                    lv = (VW[p - 1] - SL[p - 1]) / (SH[p - 1] - SL[p - 1])
                    if lv >= 0.7:
                        add("M030", DLV(M, d, y.H, None, atr, "fade"))
                    elif lv <= 0.3:
                        add("M030", DLV(M, d, None, y.L, atr, "fade"))
                s10 = SV[p - 10:p]
                if np.isfinite(s10).all():
                    c10, c10p = C[p - 10:p], C[p - 11:p - 1]; upv, dnv = s10[c10 > c10p].sum(), s10[c10 < c10p].sum()
                    ratio = upv / dnv if dnv > 0 else np.inf
                    if ratio >= 1.5:
                        add("M031", DLV(M, d, y.H, None, atr))
                    elif ratio <= 0.67:
                        add("M031", DLV(M, d, None, y.L, atr))
                nv = nsg[nsg.index < d]
                if len(nv) and (d - nv.index[-1]).days <= 5 and nv.iloc[-1] != 0:
                    add("M032", DLV(M, d, y.H, None, atr) if nv.iloc[-1] > 0 else DLV(M, d, None, y.L, atr))
                m10, m60 = SV[p - 10:p], SV[p - 60:p]
                if np.isfinite(m10).sum() >= 8 and np.isfinite(m60).sum() >= 45:
                    ratio = np.nanmean(m10) / np.nanmean(m60)
                    if ratio >= 1.2:
                        add("M093", cbox(M, d))
                    elif ratio <= 0.8:
                        add("M094", cbox(M, d, mode="fade"))
        # ------------------------------------------------ helper states that need every day (correlation warm-up)
        if sym in PARTNER56:
            state("_DC", d, C=C[p])
        if not live:
            continue
        y = Dd.iloc[p - 1]
        # ------------------------------------------------ A. spread
        i0, i1 = M.idx(lt(d, 8, 0)), M.idx(lt(d, 19, 0))
        ks = np.flatnonzero(shock[i0:i1] & ~D["roll"][i0:i1])
        if len(ks) and i0 + ks[0] >= 1:                                            # M001 / M002
            k = i0 + int(ks[0]); w = slice(k + 1, min(k + 31, M.n))
            jj = np.flatnonzero((M.t[w] <= M.t[k] + 1800) & (rs[w] <= 1.5))
            if len(jj):
                n_ = k + 1 + int(jj[0]); dirn = sgn(M.mc[n_] - M.mc[k - 1]); kk = nxt(M, n_ + 1)
                if dirn and kk is not None and M.t[kk] - M.t[n_] <= 300:
                    wl, wh = M.ml[k:n_ + 1].min(), M.mh[k:n_ + 1].max()
                    add("M001", enter_k(M, dirn, kk, wl if dirn > 0 else wh, int(M.t[kk]) + 3600, 0.1 * atr))
                    add("M002", enter_k(M, -dirn, kk, wh if dirn > 0 else wl, int(M.t[kk]) + 3600, 0.1 * atr))
        fol, fad = SESSION(M, d), SESSION(M, d, mode="fade")
        a_, b_ = sess_box(M, d); br = rs[M.idx(a_):M.idx(b_)]; brf = br[np.isfinite(br)]
        if len(brf) >= 10:                                                         # M003 - M007
            med, mxb = np.median(brf), brf.max()
            if fol is not None:
                if med <= 0.9 and mxb < 2:
                    add("M003", fol)
                if med >= 1.4:
                    add("M004", fol)
                kf = M.idx(fol["t_entry"])
                if kf < M.n and np.isfinite(rs[kf]) and rs[kf] <= 0.8:
                    add("M007", fol)
            if fad is not None:
                if med >= 1.4:
                    add("M005", fad)
                kt = M.idx(fad["t_entry"]) - 1
                if np.isfinite(rs[kt]) and rs[kt] >= 2:
                    add("M006", fad)
        if np.isfinite(drs[p - 1]):                                                # M008 / M009
            if drs[p - 1] >= 1.3:
                add("M008", DLV(M, d, y.H, y.L, atr))
            elif drs[p - 1] <= 0.8:
                add("M009", DLV(M, d, y.H, y.L, atr, "fade"))
        if nsh[p - 5:p].sum() >= 5 and fol is not None:                            # M013
            add("M013", fol)
        if d.weekday() == 0 and sym not in ("NIKKEI", "ASX") and fad is not None:  # M014
            seg = rs[M.idx(int(M.days[p]) * 86400 + 3600):M.idx(int(M.days[p]) * 86400 + 3 * 3600)]; seg = seg[np.isfinite(seg)]
            if len(seg) >= 30 and seg.mean() >= 2:
                add("M014", fad)
        # ------------------------------------------------ C. cross-market helpers and direct tests
        if sym in FX:
            bx = rs[M.idx(lt(d, 8, 0)):M.idx(lt(d, 8, 30))]; bxf = bx[np.isfinite(bx)]; t105 = int(M.days[p]) * 86400 + 3900
            with np.errstate(invalid="ignore", divide="ignore"):
                asia = np.log(mclose(M, lt(d, 8, 29))) - np.log(mclose(M, t105))
                bmove = np.log(mclose(M, lt(d, 8, 29))) - np.log(mclose(M, lt(d, 8, 5)))
                usdm = np.nan
                if sym in USDP:
                    mv_ = np.log(mclose(M, lt(d, 8, 19, NYZ))) - np.log(mclose(M, t105)); usdm = mv_ if sym.startswith("USD") else -mv_
            state("_FXS", d, boxrs=np.median(bxf) if len(bxf) >= 10 else np.nan, asia=asia, bmove=bmove, usdm=usdm)
            add("_LB2", LB(M, d)); add("_LBL", LB(M, d, True, False)); add("_LBS", LB(M, d, False, True)); add("_LBF", LB(M, d, mode="fade"))
            if d in hol:
                add("M097", LB(M, d, mode="fade"))
        if sym in IDX6:
            m959 = mclose(M, lt(d, 9, 59, NYZ))
            if np.isfinite(m959):
                state("_BR", d, above=float(m959 > y.C))
        if sym in USI:
            add("_NBL", NB(M, d, True, False)); add("_NBS", NB(M, d, False, True))
            if d + pd.offsets.BDay(1) in hol:
                add("M098", NB(M, d, mode="fade"))
            if d - pd.offsets.BDay(1) in hol:
                add("M099", NB(M, d))
            tb = tsx[tsx.index < d]                                                # F. VIX
            if len(tb) >= 6 and (d - tb.index[-1]).days <= 7 and tb.iloc[-1] - tb.iloc[-6] >= 1.5:
                add("M088", NB(M, d, True, False))
            vb = vix[vix.index < d]
            if len(vb) >= 252 and (d - vb.index[-1]).days <= 7:
                if vb.iloc[-1] <= np.percentile(vb.iloc[-252:].to_numpy(), 10):
                    add("M089", NB(M, d, mode="fade"))
                rv = np.std(lr[p - 20:p], ddof=1) * np.sqrt(252) * 100
                if np.isfinite(rv):
                    if vb.iloc[-1] - rv >= 8:
                        add("M090", NB(M, d, mode="fade"))
                    if rv - vb.iloc[-1] >= 0:
                        add("M091", NB(M, d))
        if sym in METALS:
            add("_CXL", cbox(M, d, True, False)); add("_CXS", cbox(M, d, False, True))
        if sym == "XAUUSD":
            E = X["EURUSD"]; t105 = int(M.days[p]) * 86400 + 3900; t849 = lt(d, 8, 49, NYZ)
            with np.errstate(invalid="ignore", divide="ignore"):
                gm = (np.log(mclose(M, t849)) - np.log(mclose(E, t849))) - (np.log(mclose(M, t105)) - np.log(mclose(E, t105)))
            s_ = sgn(gm)
            if s_:
                add("M049", cbox(M, d, s_ > 0, s_ < 0))
        if sym in PARTNER56:
            add("_SF", fol)
        # ------------------------------------------------ D / D2 / E daily ideas
        w4 = slice(p - 4, p); Rg = max(Hd[w4].max() - C[w4].min(), C[w4].max() - Ld[w4].min()); O = open_mid(M, lt(d, 8, 1))
        if np.isfinite(O) and Rg > 0:                                              # M053 Dual Thrust
            add("M053", M.level(O + 0.5 * Rg, O - 0.5 * Rg, lt(d, 8, 1), lt(d, 19, 0), "follow", slU=O, slL=O, x_end=lt(d, 20, 45)))
        P_ = (y.H + y.L + y.C) / 3
        add("M054", DLV(M, d, y.H + 2 * (P_ - y.L), y.L - 2 * (y.H - P_), atr))
        add("M055", rbreaker_rev(M, d, P_, y.H, y.L))
        if p + 4 < nd:                                                             # D-NEXT ideas
            s65 = 1 if (green[p - 1] and not green[p - 2]) else (-1 if (red[p - 1] and not red[p - 2]) else 0)
            if s65:
                add("M065", enter_t(M, s65, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
            q = p - 1; s68 = 0
            if np.isfinite(cop[q]) and np.isfinite(cop[q - 2]):
                if cop[q] > cop[q - 1] and cop[q - 1] <= cop[q - 2] and cop[q] < 0:
                    s68 = 1
                elif cop[q] < cop[q - 1] and cop[q - 1] >= cop[q - 2] and cop[q] > 0:
                    s68 = -1
            if s68:
                add("M068", enter_t(M, s68, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
        if np.isfinite(ui[p - 1]) and np.isfinite(ui60[p - 1]) and ui[p - 1] <= ui60[p - 1]:
            add("M072", DLV(M, d, y.H, y.L, atr))
        if np.isfinite(ac60[p - 1]):
            if ac60[p - 1] > 0.1:
                add("M086", DLV(M, d, y.H, y.L, atr))
            elif ac60[p - 1] < -0.1:
                add("M087", DLV(M, d, y.H, y.L, atr, "fade"))
        U96 = y.H if (np.isfinite(wub[p - 1]) and wvf[p - 1] > wub[p - 1]) else None
        L96 = y.L if (np.isfinite(iub[p - 1]) and iwv[p - 1] > iub[p - 1]) else None
        if U96 is not None or L96 is not None:
            add("M096", DLV(M, d, U96, L96, atr))
    out += price_bar_ideas(M, rs)
    if cme:
        out += cme_bar_ideas(M, v)
    T = pd.DataFrame(out)
    if not len(T):
        return T
    return T[(T.day >= START) | (T.idea == "_DC")]


# ---------------------------------------------------------------------- post-stage: tests built from same-day states
def combine(T):
    rows = [T[~T.idea.str.startswith("_")]]
    S = T[T.idea == "_FXS"].set_index(["day", "sym"])
    LB2, LBF = T[T.idea == "_LB2"], T[T.idea == "_LBF"]
    med = S.boxrs.groupby(level="day").agg(lambda s: s.median() if s.notna().sum() >= 20 else np.nan)
    rows.append(LBF[LBF.day.isin(set(med[med >= 1.3].index))].assign(idea="M011"))
    rows.append(LB2[LB2.day.isin(set(med[med <= 0.85].index))].assign(idea="M012"))
    LBL = T[T.idea == "_LBL"].set_index(["day", "sym"]); LBS = T[T.idea == "_LBS"].set_index(["day", "sym"]); LBFi = LBF.set_index(["day", "sym"])
    A = S.asia.unstack("sym"); A = A[A.notna().sum(axis=1) == 28]; pairs = set(FX)
    St = pd.DataFrame({c: sum((A[q] if q[:3] == c else -A[q]) for q in A.columns if c in (q[:3], q[3:])) / 7 for c in CCY})
    sel = []

    def pick(day, a, b, idea):                                                 # strong a against weak b
        if a + b in pairs:
            if (day, a + b) in LBL.index:
                sel.append(LBL.loc[[(day, a + b)]].reset_index().assign(idea=idea))
        elif b + a in pairs and (day, b + a) in LBS.index:
            sel.append(LBS.loc[[(day, b + a)]].reset_index().assign(idea=idea))
    for day, r in St.iterrows():
        o = r.sort_values(ascending=False).index.tolist(); s1, w1 = o[0], o[-1]
        pick(day, s1, w1, "M045")
        for a in o[:2]:
            for b in o[-2:]:
                pick(day, a, b, "M046")
        pf = s1 + w1 if s1 + w1 in pairs else w1 + s1
        if (day, pf) in LBFi.index:
            sel.append(LBFi.loc[[(day, pf)]].reset_index().assign(idea="M047"))
    BRs = T[T.idea == "_BR"].pivot_table(index="day", columns="sym", values="above"); BRs = BRs[BRs.notna().sum(axis=1) == 6]; cnt = BRs.sum(axis=1)
    NBL, NBS = T[T.idea == "_NBL"], T[T.idea == "_NBS"]
    rows += [NBL[NBL.day.isin(set(cnt[cnt >= 5].index))].assign(idea="M048"), NBS[NBS.day.isin(set(cnt[cnt <= 1].index))].assign(idea="M048")]
    U = S.usdm.unstack("sym")[list(USDP)]; U = U[U.notna().sum(axis=1) == 7]; dol = U.mean(axis=1)
    CXL, CXS = T[T.idea == "_CXL"], T[T.idea == "_CXS"]
    rows += [CXS[CXS.day.isin(set(dol[dol > 0].index))].assign(idea="M050"), CXL[CXL.day.isin(set(dol[dol < 0].index))].assign(idea="M050")]
    Bm = S.bmove.unstack("sym")

    def vs_usd(c, day):
        if c + "USD" in Bm.columns:
            return Bm.at[day, c + "USD"]
        return -Bm.at[day, "USD" + c] if "USD" + c in Bm.columns else np.nan
    for day in Bm.index:
        for q in (x for x in FX if "USD" not in x):
            sx, sy = vs_usd(q[:3], day), vs_usd(q[3:], day)
            if sx > 0 and sy < 0 and (day, q) in LBL.index:
                sel.append(LBL.loc[[(day, q)]].reset_index().assign(idea="M051"))
            elif sx < 0 and sy > 0 and (day, q) in LBS.index:
                sel.append(LBS.loc[[(day, q)]].reset_index().assign(idea="M051"))
    DC = T[T.idea == "_DC"].pivot_table(index="day", columns="sym", values="C").sort_index(); R = np.log(DC).diff(); SF = T[T.idea == "_SF"]
    for s, ptn in PARTNER56.items():
        if s in R and ptn in R:
            cr = R[s].rolling(20, min_periods=15).corr(R[ptn]).shift(1)
            rows.append(SF[(SF.sym == s) & SF.day.isin(set(cr[cr < 0.5].index))].assign(idea="M052"))
    RV = T[T.idea == "_RVS"].pivot_table(index="day", columns="sym", values="relv")
    if {"NSDQ", "SP"} <= set(RV.columns):
        lead = RV.dropna(subset=["NSDQ", "SP"]).idxmax(axis=1); RVT = T[T.idea == "_RVT"]
        x = RVT.merge(lead.rename("lead"), left_on="day", right_index=True)
        rows.append(x[x.sym == x.lead].drop(columns="lead").assign(idea="M100"))
    out = pd.concat(rows + sel, ignore_index=True)
    out = out[out.day >= START]
    return out[["idea", "sym", "day", "t_entry", "side", "R", "Rm", "wsp"]]


def build(raw=False):
    rawc = CACHE.replace(".parquet", "_raw.parquet")
    if os.path.exists(CACHE) and not raw:
        return pd.read_parquet(CACHE)
    if os.path.exists(rawc):
        Tr = pd.read_parquet(rawc)
    else:
        with Pool(4) as pl:
            Tr = pd.concat(pl.map(market, [(s, None) for s in NONC]), ignore_index=True)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True); Tr.to_parquet(rawc)
    if raw:
        return Tr
    T = combine(Tr); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    T = build()
    print(f"trades {len(T)}, markets {T.sym.nunique()}, {T.day.min().date()}..{T.day.max().date()}")
    c = T.assign(per=np.select([per(T, DEV), per(T, VAL)], ["DEV", "VAL"], "HOLD")).groupby(["idea", "per"]).size().unstack().reindex(IDEAS)
    c["mkts"] = T.groupby("idea").sym.nunique(); c["long%"] = (T.groupby("idea").side.apply(lambda s: (s > 0).mean()) * 100).round(0)
    c["stop_sp"] = T.groupby("idea").wsp.median().round(0); c["group"] = pd.Series(GROUP)
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200); print(c.to_string())
    rng = np.random.default_rng(1001); Tr = build(raw=True)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = Tr[Tr.sym == sym]; ft_ = full.t_entry.dropna()
        cut = int(rng.uniform(ft_.quantile(.4), ft_.quantile(.8)))
        tr = market((sym, cut)); cdy = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[(full.day < cdy) & full.t_entry.notna()][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[(tr.day < cdy) & tr.t_entry.notna()][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        sc = [x for x in ("boxrs", "asia", "bmove", "usdm", "above", "relv", "C") if x in full.columns]
        sa = full[(full.day < cdy) & full.t_entry.isna()].sort_values(["idea", "day"]).reset_index(drop=True)
        sb = tr[(tr.day < cdy) & tr.t_entry.isna()].sort_values(["idea", "day"]).reset_index(drop=True)
        sb = sb.reindex(columns=sa.columns)
        same_s = len(sa) == len(sb) and (sa[["idea", "day"]].values == sb[["idea", "day"]].values).all() and np.allclose(
            sa[sc].astype(float).to_numpy(), sb[sc].astype(float).to_numpy(), equal_nan=True)
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')} server; trades >= 35 days before the cut {len(a)} vs {len(b)}, identical {same};"
              f" helper states {len(sa)} vs {len(sb)}, identical {same_s}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("M001", "M006", "M015", "M021", "M033", "M045", "M048", "M053", "M055", "M065", "M082", "M097"):
        x = T[T.idea == idea]
        if len(x):
            r = x.sample(1, random_state=7).iloc[0]; loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens")
            print(f"  hand check {idea} {r.sym} entry {loc.tz_convert(LIS):%Y-%m-%d %H:%M} LIS ({loc.tz_convert(NYZ):%H:%M} NY, server {loc:%H:%M}) side {int(r.side):+d} stop {r.wsp:.0f} spreads")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T = build(); rows = []
    for idea in IDEAS:
        x = T[T.idea == idea]
        if not len(x):
            rows.append(dict(idea=idea, n_dev=0, group=GROUP[idea])); continue
        d, v = x[per(x, DEV)], x[per(x, VAL)]
        mu, t = ct(d) if len(d) > 2 else (np.nan, np.nan)
        mi, ti = ct(d.assign(R=d.R - d.Rm)) if len(d) > 2 else (np.nan, np.nan)
        yrs = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 100 and mu > 0 and t >= 3.29 and (yrs > 0).sum() >= 2 and mi > 0 and ti >= 2.0
        mv_, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        row = dict(idea=idea, group=GROUP[idea], n_dev=len(d), R_dev=mu, t_dev=t, info=mi, t_info=ti, yrs="/".join(f"{q:+.2f}" for q in yrs),
                   win=(d.R > 0).mean(), n_val=len(v), R_val=mv_, t_val=tv, mkts=x.sym.nunique(), dev_pass=ok, val_pass=ok and mv_ > 0 and tv >= 1.65)
        if row["val_pass"]:
            h = x[per(x, HOLD)]; mh, th = ct(h); row.update(R_hold=mh, t_hold=th, hold_pass=mh > 0 and th >= 1.65)
        rows.append(row)
    S = pd.DataFrame(rows); pd.set_option("display.width", 260); pd.set_option("display.max_rows", 200)
    print(S.round(3).to_string(index=False))
    tv_ = S.t_dev.dropna()
    print(f"\nDEV t-values of {len(tv_)} tests: mean {tv_.mean():+.2f}, sd {tv_.std():.2f}, positive {int((tv_ > 0).sum())}, t>1.65 {int((tv_ > 1.65).sum())}"
          f" (null ~{0.05 * len(tv_):.1f}), t>3.29 {int((tv_ > 3.29).sum())}")
    print(S.groupby("group").agg(n=("idea", "size"), t_mean=("t_dev", "mean"), positive=("t_dev", lambda s: int((s > 0).sum())),
                                 t165=("t_dev", lambda s: int((s > 1.65).sum())), R_mean=("R_dev", "mean")).round(2).to_string())
    passers = S[S.get("hold_pass", pd.Series(False, index=S.index)).fillna(False).astype(bool)].idea.tolist() if "hold_pass" in S else []
    print("DEV + VAL passers:", S[S.val_pass.fillna(False).astype(bool)].idea.tolist() or "none", "| full passers:", passers or "none")
    top = S.dropna(subset=["t_dev"]).nlargest(5, "t_dev").idea.tolist(); print("account view for the 5 best by DEV t:", top)
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1800)
    for idea in sorted(set(top + passers)):
        x = T[(T.idea == idea) & (T.day < "2026-01-01")]
        for label, sel, risk, cap in (("universe $50, max 5/day", x, 50, 5), ("NSDQ+XAUUSD $250", x[x.sym.isin(["NSDQ", "XAUUSD"])], 250, 10)):
            if not len(sel):
                continue
            sel = sel.sort_values("t_entry").groupby("day").head(cap)
            Rd = sel.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); rr = Rd.fillna(0).to_numpy()
            s = rng.integers(0, len(rr) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
            st_, ev, _ = account(rr[bi], trd[bi], risk)
            print(f"  {idea} {label} ({len(sel)} trades 2022-25, {sel.R.mean():+.3f} R): " + "  ".join(
                f"{k} pass {100*np.mean((st_==1)&(ev<h_)):.1f}% / breach {100*np.mean((st_==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    S.to_csv("forex/ea_research/BRK100B_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
