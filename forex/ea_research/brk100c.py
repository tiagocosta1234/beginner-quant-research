"""BRK100C: another 100 ideas (CME microstructure, MT5 broker liquidity-weighted prices, minute lead-lag, untested calendars, adaptive rules,
untested moving averages / oscillators / candlesticks, factor residuals, CME attention), one pre-registered round on BRK100B's engine.
Pre-registration: forex/ea_research/PREREG_BRK100C.md.   python -m forex.ea_research.brk100c --dry-run | --run"""
import argparse, collections, os, numpy as np, pandas as pd
from multiprocessing import Pool
from scipy.special import ndtr
from forex.ea_research.brk50 import Mkt, lt, LIS, NYZ, JST, SYD, H, DEV, VAL, HOLD, NONC
from forex.ea_research.orbx import ct
from forex.ea_research.brk30 import ema, wilder, sma, rmax, rmin, true_range, rsi, cross_up, cross_dn, epoch, sgn, regression_band
from forex.ea_research.brk100 import BX, LB, NB, SESSION, DLV, PARTNER56, ydaily, open_mid
from forex.ea_research.brk50b import fut_volume, calendars
from forex.ea_research.brk100b import (shift1, sig2, flips, nxt, mclose, enter_k, enter_t, mk, bars2, bc2, run_bc, spread_rs, cbox, wma,
                                     ssmooth, FX, USI, IDX6, CME4, METALS, USDP, START, H4)

CACHE = "data/scratch/brk100c_trades.parquet"
IDEAS = [f"N{k:03d}" for k in range(1, 101)]
LDN, BER, SHA = "Europe/London", "Europe/Berlin", "Asia/Shanghai"
JPYX = ("AUDJPY", "CADJPY", "CHFJPY", "EURJPY", "GBPJPY", "NZDJPY", "USDJPY")
CAL = "forex/ea_research/EVENT_CALENDAR_2022_2026.csv"
GROUP = {}
for _k in range(1, 101):
    GROUP[f"N{_k:03d}"] = ("A CME micro" if _k <= 15 else "B MT5 broker liquidity" if _k <= 26 else "C lead-lag" if _k <= 38 else "D calendar"
                           if _k <= 52 else "E adaptive" if _k <= 57 else "F+G+H price-only" if _k <= 91 else "I factors" if _k <= 94
                           else "J CME attention" if _k <= 97 else "K extensions")
# lead-lag: follower -> [(idea, leader, tz, (h0, m0), (h1, m1), implied sign)]
LEADS = {"EURUSD": [("N027", "DAX", BER, (9, 0), (12, 0), 1)], "USDJPY": [("N028", "NIKKEI", JST, (9, 0), (11, 30), 1)],
         "AUDUSD": [("N029", "XAUUSD", LDN, (8, 0), (12, 0), 1)], "USDCAD": [("N030", "WTI", NYZ, (9, 0), (11, 30), -1)],
         "DAX": [("N031", "NSDQ", NYZ, (9, 30), (11, 30), 1)], "NIKKEI": [("N032", "USDJPY", JST, (9, 0), (11, 30), 1)],
         "XAGUSD": [("N033", "XAUUSD", NYZ, (8, 20), (11, 0), 1)], "GBPUSD": [("N034", "EURUSD", LDN, (8, 0), (12, 0), 1)],
         "DOW": [("N035", "SP", NYZ, (9, 30), (11, 30), 1)], "WTI": [("N036", "BRENT", LDN, (8, 0), (12, 0), 1)],
         "AUDJPY": [("N037", "USDJPY", JST, (9, 0), (12, 0), 1), ("N038", "NSDQ", NYZ, (9, 30), (11, 30), 1)]}
CHINA = [("2022-01-31", "2022-02-06"), ("2022-10-01", "2022-10-07"), ("2023-01-21", "2023-01-27"), ("2023-09-29", "2023-10-06"),
         ("2024-02-10", "2024-02-17"), ("2024-10-01", "2024-10-07"), ("2025-01-28", "2025-02-04"), ("2025-10-01", "2025-10-08"),
         ("2026-02-15", "2026-02-23"), ("2026-10-01", "2026-10-07")]
DIWALI = ["2022-10-24", "2023-11-12", "2024-11-01", "2025-10-20"]
UKBH = ["2022-01-03", "2022-04-15", "2022-04-18", "2022-05-02", "2022-06-02", "2022-06-03", "2022-08-29", "2022-09-19", "2022-12-26",
        "2022-12-27", "2023-01-02", "2023-04-07", "2023-04-10", "2023-05-01", "2023-05-08", "2023-05-29", "2023-08-28", "2023-12-25",
        "2023-12-26", "2024-01-01", "2024-03-29", "2024-04-01", "2024-05-06", "2024-05-27", "2024-08-26", "2024-12-25", "2024-12-26",
        "2025-01-01", "2025-04-18", "2025-04-21", "2025-05-05", "2025-05-26", "2025-08-25", "2025-12-25", "2025-12-26", "2026-01-01",
        "2026-04-03", "2026-04-06", "2026-05-04", "2026-05-25", "2026-08-31"]


# ---------------------------------------------------------------------- calendars
def nth_weekday(y, m, wd, n):
    d = pd.Timestamp(y, m, 1); d += pd.Timedelta(days=(wd - d.weekday()) % 7)
    return d + pd.Timedelta(weeks=n - 1)


def last_weekday(y, m, wd):
    d = pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)
    return d - pd.Timedelta(days=(d.weekday() - wd) % 7)


def calendar_sets():
    S = {}; years = range(2021, 2028)
    S["imm"] = {nth_weekday(y, m, 2, 3) for y in years for m in (3, 6, 9, 12)}
    S["china"] = set().union(*[set(pd.bdate_range(a, b)) for a, b in CHINA])
    S["diwali"] = set().union(*[set(pd.bdate_range(end=pd.Timestamp(x) - pd.Timedelta(days=1), periods=5)) for x in DIWALI])
    S["jgw"] = set().union(*[set(pd.bdate_range(f"{y}-04-29", f"{y}-05-06")) for y in years])
    dst = set()
    for y in years:
        us0, eu0 = nth_weekday(y, 3, 6, 2), last_weekday(y, 3, 6); eu1, us1 = last_weekday(y, 10, 6), nth_weekday(y, 11, 6, 1)
        dst |= set(pd.bdate_range(us0, eu0 - pd.Timedelta(days=1))) | set(pd.bdate_range(eu1, us1 - pd.Timedelta(days=1)))
    S["dst"] = dst
    S["earn"] = set().union(*[set(pd.bdate_range(pd.Timestamp(y, m, 1) + pd.Timedelta(days=7), pd.Timestamp(y, m, 1) + pd.Timedelta(days=34)))
                              for y in years for m in (1, 4, 7, 10)])
    S["ukbh"] = {pd.Timestamp(x) for x in UKBH}
    S["yearend"] = set().union(*[set(pd.bdate_range(f"{y}-12-22", f"{y + 1}-01-02")) for y in years])
    tier1, fomc = calendars(); S["blackout"] = set()
    for f in fomc:
        S["blackout"] |= set(pd.bdate_range(pd.Timestamp(f) - pd.Timedelta(days=11), pd.Timestamp(f)))
    c = pd.read_csv(CAL, parse_dates=["date"]); S["payroll"] = set()
    for n in c[c.kind == "NFP"].date:
        mon = n - pd.Timedelta(days=n.weekday())
        S["payroll"] |= {mon + pd.Timedelta(days=i) for i in range(3) if mon + pd.Timedelta(days=i) < n}
    ev = sorted(set(pd.Timestamp(x) for x in tier1)); wk = collections.Counter(x - pd.Timedelta(days=x.weekday()) for x in ev if x.weekday() < 5)
    S["heavy"] = {m + pd.Timedelta(days=i) for m, n in wk.items() if n >= 2 for i in (0, 1)}
    return S


def moon_age(d):
    t0 = pd.Timestamp("2000-01-06 18:14", tz="UTC"); x = (pd.Timestamp(d).tz_localize("UTC") + pd.Timedelta(hours=12) - t0).total_seconds() / 86400
    return x % 29.530589


# ---------------------------------------------------------------------- indicators (F, G)
def ema2(x, n):
    """EMA with alpha = 2 / n (DecisionPoint's smoothing)"""
    return pd.Series(x).ewm(alpha=2 / n, adjust=False).mean().to_numpy()


def t3(c, n=8, a=0.7):
    e1 = ema(c, n); e2 = ema(e1, n); e3 = ema(e2, n); e4 = ema(e3, n); e5 = ema(e4, n); e6 = ema(e5, n)
    c1, c2, c3, c4 = -a ** 3, 3 * a * a + 3 * a ** 3, -6 * a * a - 3 * a - 3 * a ** 3, 1 + 3 * a + a ** 3 + 3 * a * a
    return c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3


def alma(c, n=21, off=0.85, sig=6):
    m = off * (n - 1); s = n / sig; w = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s)); out = np.full(len(c), np.nan)
    if len(c) >= n:
        out[n - 1:] = np.convolve(c, w[::-1], mode="valid") / w.sum()
    return out


def mcginley(c, n=14):
    md = np.asarray(c, float).copy()
    for i in range(1, len(c)):
        md[i] = md[i - 1] + (c[i] - md[i - 1]) / (n * (c[i] / md[i - 1]) ** 4)
    return md


def frama(hh, ll, cc, n=16):
    h2 = n // 2; out = np.asarray(cc, float).copy()
    n1 = (rmax(hh, h2) - rmin(ll, h2)) / h2; n2 = np.r_[np.full(h2, np.nan), n1[:-h2]]          # newer half, older half
    n3 = (rmax(hh, n) - rmin(ll, n)) / n
    with np.errstate(invalid="ignore", divide="ignore"):
        dim = (np.log(n1 + n2) - np.log(n3)) / np.log(2)
    a = np.clip(np.exp(-4.6 * (dim - 1)), 0.01, 1.0)
    for i in range(1, len(cc)):
        ai = a[i] if np.isfinite(a[i]) else 1.0
        out[i] = ai * cc[i] + (1 - ai) * out[i - 1]
    return out


def gauss2(c, p=20):
    b = (1 - np.cos(2 * np.pi / p)) / (np.sqrt(2) - 1); a = -b + np.sqrt(b * b + 2 * b); g = np.asarray(c, float).copy()
    for i in range(2, len(c)):
        g[i] = a * a * c[i] + 2 * (1 - a) * g[i - 1] - (1 - a) ** 2 * g[i - 2]
    return g


def butter3(c, p=20):
    a = np.exp(-np.pi / p); b = 2 * a * np.cos(1.738 * np.pi / p); cc_ = a * a
    k2, k3, k4 = b + cc_, -(cc_ + b * cc_), cc_ * cc_; k1 = (1 - b + cc_) * (1 - cc_) / 8; f = np.asarray(c, float).copy()
    for i in range(3, len(c)):
        f[i] = k1 * (c[i] + 3 * c[i - 1] + 3 * c[i - 2] + c[i - 3]) + k2 * f[i - 1] + k3 * f[i - 2] + k4 * f[i - 3]
    return f


def holt_trend(c, a=0.2, b=0.1):
    L, T = c[0], 0.0; out = np.zeros(len(c))
    for i in range(1, len(c)):
        Lp = L; L = a * c[i] + (1 - a) * (L + T); T = b * (L - Lp) + (1 - b) * T; out[i] = T
    return out


def ultimate_smoother(c, p=20):
    a1 = np.exp(-1.414 * np.pi / p); c2 = 2 * a1 * np.cos(1.414 * np.pi / p); c3 = -a1 * a1; c1 = (1 + c2 - c3) / 4
    us = np.asarray(c, float).copy()
    for i in range(4, len(c)):
        us[i] = (1 - c1) * c[i] + (2 * c1 - c2) * c[i - 1] - (c1 + c3) * c[i - 2] + c2 * us[i - 1] + c3 * us[i - 2]
    return us


def roll_slope(y, n):
    x = np.arange(n) - (n - 1) / 2; w = x / (x * x).sum(); out = np.full(len(y), np.nan)
    if len(y) >= n:
        out[n - 1:] = np.convolve(y, w[::-1], mode="valid")
    return out


def rwi(hh, ll, cc, n=14):
    tr = true_range(hh, ll, cc); rh = np.full(len(cc), np.nan); rl = np.full(len(cc), np.nan)
    for k in range(2, n + 1):
        at = sma(tr, k) * np.sqrt(k)
        with np.errstate(invalid="ignore", divide="ignore"):
            h_ = (hh - np.r_[np.full(k, np.nan), ll[:-k]]) / at; l_ = (np.r_[np.full(k, np.nan), hh[:-k]] - ll) / at
        rh = np.fmax(rh, h_); rl = np.fmax(rl, l_)
    return rh, rl


def dyn_rsi(cc):
    sd5 = pd.Series(cc).rolling(5).std().to_numpy(); vi = sd5 / sma(sd5, 10)
    with np.errstate(invalid="ignore", divide="ignore"):
        per = np.clip(np.round(14 / vi), 5, 30)
    d = np.r_[0, np.diff(cc)]; cu, cd = np.r_[0, np.cumsum(np.maximum(d, 0))], np.r_[0, np.cumsum(np.maximum(-d, 0))]
    out = np.full(len(cc), np.nan); idx = np.arange(len(cc))
    ok = np.isfinite(per); p_ = np.where(ok, per, 5).astype(int); j0 = idx + 1 - p_; ok &= j0 >= 1
    up = np.where(ok, cu[idx + 1] - cu[np.maximum(j0, 0)], np.nan); dn = np.where(ok, cd[idx + 1] - cd[np.maximum(j0, 0)], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = 100 * up / (up + dn)
    return out


def pfe(cc, atr, n=10, sm=5):
    z = cc / np.where(atr > 0, atr, np.nan)                                     # price in ATR units (scale-free)
    num = np.sqrt((z - np.r_[np.full(n, np.nan), z[:-n]]) ** 2 + n * n)
    den = pd.Series(np.sqrt(np.r_[np.nan, np.diff(z)] ** 2 + 1)).rolling(n).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = np.sign(z - np.r_[np.full(n, np.nan), z[:-n]]) * 100 * num / den
    return ema(np.nan_to_num(raw), sm)


def projection_osc(hh, ll, cc, n=14):
    sh, sl = roll_slope(hh, n), roll_slope(ll, n); ub = np.full(len(cc), -np.inf); lb = np.full(len(cc), np.inf)
    for i in range(n):
        hs = np.r_[np.full(i, np.nan), hh[:len(hh) - i]] + i * sh; ls = np.r_[np.full(i, np.nan), ll[:len(ll) - i]] + i * sl
        ub = np.fmax(ub, hs); lb = np.fmin(lb, ls)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100 * (cc - lb) / np.where(ub - lb > 0, ub - lb, np.nan)


def safezone(hh, ll, n=10, k=2.0):
    dpen = np.where(np.r_[False, ll[1:] < ll[:-1]], np.r_[0, ll[:-1] - ll[1:]], 0.0); upen = np.where(np.r_[False, hh[1:] > hh[:-1]], np.r_[0, hh[1:] - hh[:-1]], 0.0)
    cntd = pd.Series((dpen > 0).astype(float)).rolling(n).sum().to_numpy(); cntu = pd.Series((upen > 0).astype(float)).rolling(n).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        avd = pd.Series(dpen).rolling(n).sum().to_numpy() / np.where(cntd > 0, cntd, np.nan)
        avu = pd.Series(upen).rolling(n).sum().to_numpy() / np.where(cntu > 0, cntu, np.nan)
    return shift1(ll) - k * avd, shift1(hh) + k * avu                         # long stop, short stop


def inertia(cc, n=20):
    sd = pd.Series(cc).rolling(10).std().to_numpy(); d = np.r_[0, np.diff(cc)]
    u, dn = ema(np.nan_to_num(np.where(d > 0, sd, 0)), 14), ema(np.nan_to_num(np.where(d < 0, sd, 0)), 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = 100 * u / np.where(u + dn > 0, u + dn, np.nan)
    return regression_band(np.nan_to_num(rv, nan=50.0), n)[0]


def reflex_trendflex(cc, n=20):
    f = ssmooth(cc, n // 2); N = len(f); rf, tf = np.full(N, np.nan), np.full(N, np.nan); ms_r = ms_t = 0.0
    for t in range(n, N):
        slope = (f[t - n] - f[t]) / n
        sr = sum(f[t] + i * slope - f[t - i] for i in range(1, n + 1)) / n; st = sum(f[t] - f[t - i] for i in range(1, n + 1)) / n
        ms_r = 0.04 * sr * sr + 0.96 * ms_r; ms_t = 0.04 * st * st + 0.96 * ms_t
        rf[t] = sr / np.sqrt(ms_r) if ms_r > 0 else 0.0; tf[t] = st / np.sqrt(ms_t) if ms_t > 0 else 0.0
    return rf, tf


def corr_trend(cc, n=20):
    x = np.arange(n, dtype=float); W = np.lib.stride_tricks.sliding_window_view(cc, n); out = np.full(len(cc), np.nan)
    ym = W.mean(axis=1, keepdims=True); xm = x.mean()
    num = ((W - ym) * (x - xm)).sum(axis=1); den = np.sqrt(((W - ym) ** 2).sum(axis=1) * ((x - xm) ** 2).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        out[n - 1:] = num / den
    return out


def price_bar_ideas(M, rs):
    out = []; B1, B4 = bars2(M, H), bars2(M, H4)
    hh, ll, cc, oo = B1["hh"], B1["ll"], B1["cc"], B1["oo"]; z = np.zeros(len(cc))
    h10, l10 = rmax(hh, 10), rmin(ll, 10); dd = cc - (h10 + l10) / 2; rr = h10 - l10
    with np.errstate(invalid="ignore", divide="ignore"):
        smi = 100 * ema(ema(dd, 3), 3) / (0.5 * np.where(ema(ema(rr, 3), 3) > 0, ema(ema(rr, 3), 3), np.nan))
    sms = ema(np.nan_to_num(smi), 3); run_bc(out, M, B1, cross_up(smi, sms) & (smi < -40), cross_dn(smi, sms) & (smi > 40), "N071")
    mo = cc - np.r_[np.full(5, np.nan), cc[:-5]]; wu, wd_ = wilder(np.nan_to_num(np.maximum(mo, 0)), 14), wilder(np.nan_to_num(np.maximum(-mo, 0)), 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        rmi = 100 * wu / np.where(wu + wd_ > 0, wu + wd_, np.nan)
    run_bc(out, M, B1, cross_up(rmi, z + 30), cross_dn(rmi, z + 70), "N072")
    g_ = pd.Series(np.maximum(cc - oo, 0)).rolling(14).sum().to_numpy(); l_ = pd.Series(np.maximum(oo - cc, 0)).rolling(14).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        imi = 100 * g_ / np.where(g_ + l_ > 0, g_ + l_, np.nan)
    run_bc(out, M, B1, cross_up(imi, z + 30), cross_dn(imi, z + 70), "N075")
    dr = dyn_rsi(cc); run_bc(out, M, B1, cross_up(dr, z + 30), cross_dn(dr, z + 70), "N076")
    hh, ll, cc, oo, atr = B4["hh"], B4["ll"], B4["cc"], B4["oo"], B4["atr"]; z = np.zeros(len(cc))
    for idea, ma in (("N058", 2 * ema(cc, 21) - ema(ema(cc, 21), 21)), ("N059", ema(cc + (cc - np.r_[np.full(10, np.nan), cc[:-10]]), 21)),
                     ("N060", t3(cc)), ("N061", alma(cc)), ("N062", mcginley(cc)), ("N063", frama(hh, ll, cc)),
                     ("N064", regression_band(cc, 25)[0]), ("N065", sma(sma(cc, 11), 11)), ("N066", wilder(cc, 21)),
                     ("N067", gauss2(cc)), ("N068", butter3(cc)), ("N070", ultimate_smoother(cc))):
        run_bc(out, M, B4, cross_up(cc, ma), cross_dn(cc, ma), idea)
    out.extend(bc2(M, B4, flips(np.sign(holt_trend(cc))), 2.0, 30, "N069"))
    roc = 100 * (cc / np.r_[cc[0], cc[:-1]] - 1); pmo = ema2(10 * ema2(roc, 35), 20); pms = ema(pmo, 10)
    run_bc(out, M, B4, cross_up(pmo, pms), cross_dn(pmo, pms), "N073")
    rh, rl = rwi(hh, ll, cc); run_bc(out, M, B4, cross_up(rh, rl) & (rh > 1), cross_up(rl, rh) & (rl > 1), "N074")
    pf = pfe(cc, atr); run_bc(out, M, B4, cross_up(pf, z), cross_dn(pf, z), "N077")
    po = projection_osc(hh, ll, cc); run_bc(out, M, B4, cross_up(po, z + 20), cross_dn(po, z + 80), "N078")
    etr = ema(true_range(hh, ll, cc), 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        pgo = (cc - sma(cc, 14)) / np.where(etr > 0, etr, np.nan)
    run_bc(out, M, B4, cross_up(pgo, z + 3), cross_dn(pgo, z - 3), "N079")
    szl, szs = safezone(hh, ll); run_bc(out, M, B4, cross_up(cc, szs), cross_dn(cc, szl), "N082")
    ine = inertia(cc); run_bc(out, M, B4, cross_up(ine, z + 50), cross_dn(ine, z + 50), "N083")
    rf, tf = reflex_trendflex(cc); run_bc(out, M, B4, cross_up(rf, z), cross_dn(rf, z), "N084"); run_bc(out, M, B4, cross_up(tf, z), cross_dn(tf, z), "N085")
    cti = corr_trend(cc); run_bc(out, M, B4, cross_up(cti, z + 0.5), cross_dn(cti, z - 0.5), "N086")
    fin = np.isfinite(rs); s_ = np.add.reduceat(np.where(fin, rs, 0.0), B4["st"]); c_ = np.add.reduceat(fin.astype(float), B4["st"])
    rsb = np.where(c_ > 0, s_ / np.where(c_ > 0, c_, 1), np.nan); q = rsb < 0.9
    run_bc(out, M, B4, q & (cc > shift1(rmax(cc, 20))), q & (cc < shift1(rmin(cc, 20))), "N023")
    return out


def mfi_bw(M, v):
    out = []; B = bars2(M, H); V = np.add.reduceat(v, B["st"]); hh, ll, cc = B["hh"], B["ll"], B["cc"]
    with np.errstate(invalid="ignore", divide="ignore"):
        mf = (hh - ll) / np.where(V > 0, V, np.nan)
    green = (mf > shift1(mf)) & (V > shift1(V)); rg = hh - ll; cl = np.where(rg > 0, (cc - ll) / np.where(rg > 0, rg, 1), 0.5)
    run_bc(out, M, B, green & (cl >= 0.5), green & (cl < 0.5), "N080")
    return out


# ---------------------------------------------------------------------- per-day helpers
def lsession(M, d):
    s = M.sym
    if s in USI:
        return lt(d, 9, 30, NYZ), lt(d, 15, 55, NYZ)
    if s == "NIKKEI":
        return lt(d, 9, 0, JST), lt(d, 14, 55, JST)
    if s == "ASX":
        return lt(d, 10, 0, SYD), lt(d, 15, 55, SYD)
    return lt(d, 8, 0), lt(d, 17, 0)


def enter_dist(M, side, k, dist, x_end):
    if k is None or k >= M.n or not (dist > 0):
        return None
    e = M.D["ao"][k] if side > 0 else M.D["bo"][k]
    ix = M.exit_idx(x_end)
    return None if ix is None else M.trade(side, k, e, e - side * dist, ix)


def wap_rules(M, add, i0, i1, a, xe, w, atr, tag):
    """BRK100B M015 / M017 / M020 / M016 rules on a weighted average price (weights w) over session minutes [i0, i1)"""
    mcs, mhs, mls, tss = M.mc[i0:i1], M.mh[i0:i1], M.ml[i0:i1], M.t[i0:i1]
    cw, cp, c2 = np.cumsum(w), np.cumsum(w * mcs), np.cumsum(w * mcs * mcs)
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = np.where(cw > 0, cp / np.where(cw > 0, cw, 1), np.nan); sg = np.sqrt(np.maximum(np.where(cw > 0, c2 / np.where(cw > 0, cw, 1), np.nan) - vw ** 2, 0))
    iw0, iw1 = int(np.searchsorted(tss, a + 1800)), int(np.searchsorted(tss, xe - 3600))
    if iw1 <= iw0:
        return vw
    below = np.r_[False, np.maximum.accumulate(mcs <= vw - 0.25 * atr)[:-1]]; above = np.r_[False, np.maximum.accumulate(mcs >= vw + 0.25 * atr)[:-1]]
    cu = np.r_[False, (mcs[1:] > vw[1:]) & (mcs[:-1] <= vw[:-1])]; cd = np.r_[False, (mcs[1:] < vw[1:]) & (mcs[:-1] >= vw[:-1])]
    sL, sS = cu & below, cd & above; j_ = np.flatnonzero((sL | sS)[iw0:iw1])
    if len(j_):
        j = iw0 + int(j_[0]); side = 1 if sL[j] else -1
        add(tag[0], enter_k(M, side, nxt(M, i0 + j + 1), mls[:j + 1].min() if side > 0 else mhs[:j + 1].max(), xe, 0.1 * atr))
    u2, d2 = (mcs > vw + 2 * sg) & (sg > 0), (mcs < vw - 2 * sg) & (sg > 0); j_ = np.flatnonzero((u2 | d2)[iw0:iw1])
    if len(j_):
        j = iw0 + int(j_[0]); side = 1 if u2[j] else -1
        add(tag[1], enter_k(M, side, nxt(M, i0 + j + 1), vw[j], xe, 0.1 * atr))
    upf = np.r_[False, np.maximum.accumulate(mhs - vw >= 0.5 * atr)[:-1]]; dnf = np.r_[False, np.maximum.accumulate(vw - mls >= 0.5 * atr)[:-1]]
    tL, tS = upf & (mls <= vw), dnf & (mhs >= vw); j_ = np.flatnonzero((tL | tS)[iw0:iw1])
    if len(j_):
        j = iw0 + int(j_[0]); side = 1 if tL[j] else -1
        add(tag[2], enter_k(M, side, nxt(M, i0 + j + 1), vw[j] - side * 0.25 * atr, xe, 0.1 * atr))
    jA, jB = int(np.searchsorted(tss, a + 1800)), int(np.searchsorted(tss, a + 5400))
    if jB - jA >= 50 and jB < len(tss):
        up_, dn_ = (mcs[jA:jB] > vw[jA:jB]).all(), (mcs[jA:jB] < vw[jA:jB]).all()
        if up_ or dn_:
            side = 1 if up_ else -1
            add(tag[3], enter_t(M, side, a + 5400, stop=vw[jB - 1] - side * 0.1 * atr, x_end=xe, mind=0.1 * atr))
    return vw


def leadlag(M, L, d, tz, w0, w1, sgp, hist, idea, add):
    a, b = lt(d, *w0, tz), lt(d, *w1, tz); g = np.arange(a + 300, b + 1, 300)
    if len(g) < 3:
        return
    def rets(X):
        i1 = np.searchsorted(X.t, g - 60, side="right") - 1; i0 = np.searchsorted(X.t, g - 360, side="right") - 1
        ok = (i0 >= 0) & (i1 >= 0) & (g - 60 - X.t[np.maximum(i1, 0)] < 120) & (g - 360 - X.t[np.maximum(i0, 0)] < 120)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(ok, np.log(X.mc[np.maximum(i1, 0)] / X.mc[np.maximum(i0, 0)]), np.nan)
    rL, rF = rets(L), rets(M)
    if len(hist["L"]) == 20:
        sL, sF = np.nanstd(np.concatenate(hist["L"])), np.nanstd(np.concatenate(hist["F"]))
        if sL > 0 and sF > 0:
            busy = -1
            for j in range(len(g)):
                if g[j] <= busy or not (np.isfinite(rL[j]) and np.isfinite(rF[j])):
                    continue
                zL, zF = rL[j] / sL, rF[j] / sF
                if abs(zL) > 1.5:
                    side = int(np.sign(zL)) * sgp
                    if zF * side < 0.5 * abs(zL):
                        k = nxt(M, M.idx(int(g[j])))
                        if k is not None and M.t[k] - g[j] < 300:
                            res = enter_dist(M, side, k, 3 * sF * M.mc[k], int(M.t[k]) + 900)
                            if res is not None:
                                add(idea, res); busy = int(M.t[k]) + 900
    hist["L"].append(rL[np.isfinite(rL)]); hist["F"].append(rF[np.isfinite(rF)])


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

    rs = spread_rs(M); fin = np.isfinite(rs); shock = fin & (rs >= 4); CS = calendar_sets()
    C, O_, Hd, Ld = Dd.C.to_numpy(), Dd.O.to_numpy(), Dd.H.to_numpy(), Dd.L.to_numpy()
    nsh = np.zeros(nd); ac1 = np.full(nd, np.nan)
    for p in range(nd):
        d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); i0, i1 = M.idx(lt(d, 8, 0)), M.idx(lt(d, 19, 0))
        if i1 - i0 > 60:
            nsh[p] = shock[i0:i1].sum(); x = rs[i0:i1]; x = x[np.isfinite(x)]
            if len(x) > 60 and x.std() > 0:
                ac1[p] = np.corrcoef(x[1:], x[:-1])[0, 1]
    # daily indicators for E / G / H (value at q uses closes up to day q)
    s20, s50 = sma(C, 20), sma(C, 50); roc20 = C / np.r_[np.full(20, np.nan), C[:-20]] - 1
    macd = ema(C, 12) - ema(C, 26); msig = ema(macd, 9); r14 = rsi(C, 14)
    vup = (C > s50).astype(int) + (s20 > s50) + (roc20 > 0) + (macd > msig) + (r14 > 50)
    vdn = (C < s50).astype(int) + (s20 < s50) + (roc20 < 0) + (macd < msig) + (r14 < 50)
    upd = np.r_[False, C[1:] > C[:-1]]; psy = pd.Series(upd.astype(float)).rolling(12).mean().to_numpy()
    # partners
    P = {}
    for (idea, ld, *_r) in LEADS.get(sym, []):
        P.setdefault(ld, Mkt(ld, cut))
    hist = {x[0]: {"L": collections.deque(maxlen=20), "F": collections.deque(maxlen=20)} for x in LEADS.get(sym, [])}
    prt = None
    if sym in PARTNER56:
        prt = Mkt(PARTNER56[sym], cut); prs = spread_rs(prt)
    if sym in ("AUDJPY", "NZDJPY", "CADJPY"):
        vix = ydaily("^VIX_yahoo_daily.csv", cd); v3m = ydaily("^VIX3M_yahoo_daily.csv", cd)
    if sym == "USDCAD":
        oil = ydaily("CL=F_yahoo_daily.csv", cd)
    att = {"XAUUSD": ("GC", SHA, (9, 0), (10, 0)), "DAX": ("ES", BER, (8, 0), (8, 30)), "NIKKEI": ("NQ", JST, (9, 0), (9, 30))}
    if sym in att:
        AF = fut_volume(att[sym][0], cut); AV = np.full(nd, np.nan)
    cme = sym in CME4
    if cme:
        ft, cv = fut_volume(CME4[sym], cut); v = cv[np.searchsorted(ft, M.t + 60)] - cv[np.searchsorted(ft, M.t)]
        oth = {"NSDQ": "ES", "SP": "NQ", "XAGUSD": "GC"}.get(sym); OF = fut_volume(oth, cut) if oth else None
        ses = ((8, 20), (13, 30), (13, 25)) if sym in METALS else ((9, 30), (16, 0), (15, 55))
        dm = np.r_[0.0, np.diff(M.mc)]; sig_day = np.full(nd, np.nan); sess_rng = {}; dq = collections.deque(maxlen=20)
        for p in range(nd):
            d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); a, b = lt(d, *ses[0], NYZ), lt(d, *ses[1], NYZ); i0, i1 = M.idx(a), M.idx(b)
            if len(dq) == 20:
                sig_day[p] = np.std(np.concatenate(dq))
            if i1 - i0 >= 0.8 * (b - a) / 60:
                sess_rng[p] = (i0, i1, a, b, lt(d, *ses[2], NYZ)); dq.append(dm[i0 + 1:i1])
        pos = np.searchsorted(M.days, M.t // 86400); pos = np.minimum(pos, nd - 1); same = M.days[pos] == M.t // 86400
        sgm = np.where(same, sig_day[pos], np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            sv = np.where(np.isfinite(sgm) & (sgm > 0), v * (2 * ndtr(dm / np.where(sgm > 0, sgm, 1)) - 1), 0.0)
        okm = ~D["roll"]; bid = M.t // 1800; bt = bid[okm]; st_ = np.flatnonzero(np.r_[True, bt[1:] != bt[:-1]])
        bsv = np.add.reduceat(sv[okm], st_); bv = np.add.reduceat(v[okm], st_); bend = (bt[st_] + 1) * 1800
        with np.errstate(invalid="ignore", divide="ignore"):
            imb = np.where(bv > 0, np.abs(bsv) / np.where(bv > 0, bv, 1), np.nan)
        keep = np.isfinite(imb); bend, imb = bend[keep], imb[keep]; cimb = np.r_[0, np.cumsum(imb)]

        def vpin(x):
            k = int(np.searchsorted(bend, x, side="right"))
            return (cimb[k] - cimb[k - 16]) / 16 if k >= 16 else np.nan
        SV, VWp, TWp, LAM, AMI, CSV, ONR, VP, SH_, FV = (np.full(nd, np.nan) for _ in range(10))
        pmin = collections.deque(maxlen=20)
    last_fol = None; folq, fadq = collections.deque(maxlen=20), collections.deque(maxlen=20); LW, TW = np.full(nd, np.nan), np.full(nd, np.nan)
    for p in range(nd):
        d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); atr = Dd.atr.iloc[p]
        live = d >= START and p >= 61 and np.isfinite(atr)
        y = Dd.iloc[p - 1] if p >= 1 else None
        # ------------------------------------------------ CME-based stats (every day) and tests
        if cme:
            if p >= 2 and np.isfinite(SV[p - 1]) and SV[p - 1] > 0:
                AMI[p - 1] = abs(C[p - 1] / C[p - 2] - 1) / SV[p - 1]
            if p in sess_rng:
                i0, i1, a, b, xe = sess_rng[p]; vs = v[i0:i1]; mcs = M.mc[i0:i1]
                SV[p] = vs.sum(); VWp[p] = (vs * mcs).sum() / vs.sum() if vs.sum() > 0 else np.nan; TWp[p] = mcs.mean()
                svs, dms = sv[i0:i1], dm[i0:i1]
                if np.var(svs) > 0:
                    LAM[p] = np.cov(dms, svs)[0, 1] / np.var(svs, ddof=1)
                tl = M.t[i0:i1] >= xe - 30 * 60
                CSV[p] = svs[tl].sum() / vs[tl].sum() if vs[tl].sum() > 0 else np.nan
                FV[p] = vs[M.t[i0:i1] < a + 1800].sum()
                if OF is not None:
                    if sym in ("NSDQ", "SP"):
                        o30 = OF[1][np.searchsorted(OF[0], a + 1800)] - OF[1][np.searchsorted(OF[0], a)]
                        SH_[p] = (FV[p] / (FV[p] + o30) if sym == "NSDQ" else o30 / (FV[p] + o30)) if FV[p] + o30 > 0 else np.nan
                    else:
                        o30 = OF[1][np.searchsorted(OF[0], a + 1800)] - OF[1][np.searchsorted(OF[0], a)]
                        SH_[p] = FV[p] / (FV[p] + o30) if FV[p] + o30 > 0 else np.nan
                ON = cv[np.searchsorted(ft, a)] - cv[np.searchsorted(ft, lt(d - pd.Timedelta(days=1), 18, 0, NYZ))]
                ONR[p] = ON / SV[p - 1] if p >= 1 and SV[p - 1] > 0 else np.nan
                VP[p] = vpin(a + 1800)
                if live:
                    hv = VP[max(0, p - 60):p]; hv = hv[np.isfinite(hv)]
                    if len(hv) >= 40 and np.isfinite(VP[p]):
                        if VP[p] >= np.percentile(hv, 80):
                            add("N001", cbox(M, d)); add("N002", cbox(M, d, mode="fade"))
                        elif VP[p] <= np.percentile(hv, 20):
                            add("N003", cbox(M, d))
                    hl = LAM[max(0, p - 61):p - 1]; hl = hl[np.isfinite(hl)]
                    if len(hl) >= 40 and np.isfinite(LAM[p - 1]):
                        if LAM[p - 1] >= np.percentile(hl, 80):
                            add("N004", cbox(M, d))
                        elif LAM[p - 1] <= np.percentile(hl, 20):
                            add("N005", cbox(M, d, mode="fade"))
                    ho = ONR[max(0, p - 20):p]; ho = ho[np.isfinite(ho)]
                    if len(ho) >= 15 and np.isfinite(ONR[p]) and ONR[p] >= 1.5 * np.median(ho):
                        add("N009", cbox(M, d, mode="fade"))
                    hs = SH_[max(0, p - 20):p]; hs = hs[np.isfinite(hs)]
                    if len(hs) >= 15 and np.isfinite(SH_[p]):
                        if sym == "NSDQ" and SH_[p] >= 1.2 * np.median(hs):
                            add("N010", cbox(M, d))
                        if sym == "SP" and SH_[p] >= 1.2 * np.median(hs):              # SH_ is the NQ share in both index processes
                            add("N011", cbox(M, d, mode="fade"))
                        if sym == "XAGUSD" and SH_[p] >= 1.3 * np.median(hs):
                            add("N012", cbox(M, d))
                    if len(pmin) == 20:
                        thr = np.percentile(np.concatenate(pmin), 99); tss = M.t[i0:i1]
                        j0, j1 = int(np.searchsorted(tss, a + 900)), int(np.searchsorted(tss, b - 65 * 60))
                        cand = np.flatnonzero((vs[j0:j1] >= thr) & (rs[i0 + j0:i0 + j1] <= 1.2)) if thr > 0 else []
                        if len(cand):
                            c_ = i0 + j0 + int(cand[0]); dr = sgn(M.mc[c_] - (D["bo"][c_] + D["ao"][c_]) / 2)
                            if dr:
                                k = nxt(M, c_ + 1)
                                if k is not None:
                                    add("N014", enter_dist(M, dr, k, 0.2 * atr, int(M.t[k]) + 3600))
                pmin.append(vs)
            if live and y is not None:
                ha = AMI[max(0, p - 61):p - 1]; ha = ha[np.isfinite(ha)]
                if len(ha) >= 40 and np.isfinite(AMI[p - 1]):
                    if AMI[p - 1] >= np.percentile(ha, 80):
                        add("N006", DLV(M, d, y.H, y.L, atr))
                    elif AMI[p - 1] <= np.percentile(ha, 20):
                        add("N007", DLV(M, d, y.H, y.L, atr, "fade"))
                if np.isfinite(CSV[p - 1]) and p + 4 < nd:
                    s8 = 1 if CSV[p - 1] >= 0.2 else (-1 if CSV[p - 1] <= -0.2 else 0)
                    if s8:
                        add("N008", enter_t(M, s8, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
                if np.isfinite(VWp[p - 1]) and np.isfinite(TWp[p - 1]):
                    g13 = VWp[p - 1] - TWp[p - 1]
                    if g13 >= 0.1 * atr:
                        add("N013", cbox(M, d, True, False))
                    elif g13 <= -0.1 * atr:
                        add("N013", cbox(M, d, False, True))
                if sym in ("NSDQ", "SP"):
                    for mo_ in (3, 6, 9, 12):
                        if d.month == mo_:
                            f3 = nth_weekday(d.year, mo_, 4, 3)
                            if f3 - pd.Timedelta(days=11) <= d <= f3 - pd.Timedelta(days=7):
                                add("N015", NB(M, d, mode="fade"))
        if sym in att:
            r_, tz_, h0, h1 = att[sym]; aa, bb = lt(d, *h0, tz_), lt(d, *h1, tz_)
            AV[p] = AF[1][np.searchsorted(AF[0], bb)] - AF[1][np.searchsorted(AF[0], aa)]
        if not live:
            continue
        # ------------------------------------------------ session trades (shared)
        fol, fad = SESSION(M, d), SESSION(M, d, mode="fade")
        # E adaptive (use only trades of earlier days)
        if fol is not None and last_fol is not None:
            add("N053" if last_fol < 0 else "N054", fol)
        if len(folq) == 20 and len(fadq) == 20:
            add("N055", fol if np.mean(folq) > np.mean(fadq) else fad)
        if fol is not None:
            last_fol = fol["R"]; folq.append(fol["R"])
        if fad is not None:
            fadq.append(fad["R"])
        q = p - 1
        if vup[q] == 5:
            add("N056", DLV(M, d, y.H, None, atr))
        elif vdn[q] == 5:
            add("N056", DLV(M, d, None, y.L, atr))
        if C[q] > C[q - 1] > C[q - 2] > C[q - 3] > C[q - 4]:
            add("N057", DLV(M, d, None, y.L, atr))
        elif C[q] < C[q - 1] < C[q - 2] < C[q - 3] < C[q - 4]:
            add("N057", DLV(M, d, y.H, None, atr))
        # ------------------------------------------------ B. MT5 broker liquidity
        a, xe = lsession(M, d); i0, i1 = M.idx(a), M.idx(xe)
        if i1 - i0 >= 0.8 * (xe - a) / 60:
            w = 1 / np.maximum(D["sp"][i0:i1], 1e-12)
            vw = wap_rules(M, add, i0, i1, a, xe, w, atr, ("N016", "N017", "N018", "N019"))
            LW[p], TW[p] = vw[-1], M.mc[i0:i1].mean()
        if np.isfinite(LW[p - 1]) and np.isfinite(TW[p - 1]):
            g20 = LW[p - 1] - TW[p - 1]
            if g20 >= 0.05 * atr:
                add("N020", SESSION(M, d, True, False))
            elif g20 <= -0.05 * atr:
                add("N020", SESSION(M, d, False, True))
        if np.isfinite(ac1[q]) and ac1[q] >= 0.6:
            add("N021", fad)
        if sym not in USI + ("NIKKEI", "ASX"):
            seg = rs[M.idx(lt(d, 1, 5)):M.idx(lt(d, 8, 0))]; seg = seg[np.isfinite(seg)]          # 01:05-07:59 local
            bx = rs[M.idx(lt(d, 8, 0)):M.idx(lt(d, 8, 30))]; bx = bx[np.isfinite(bx)]
            if len(seg) >= 60 and len(bx) >= 10 and np.median(bx) > 0 and seg.mean() / np.median(bx) >= 1.5:
                add("N022", LB(M, d))
        if nsh[q] >= 3 and y.H > y.L:
            loc = (y.C - y.L) / (y.H - y.L)
            if loc >= 0.75:
                add("N024", DLV(M, d, y.H, None, atr))
            elif loc <= 0.25:
                add("N024", DLV(M, d, None, y.L, atr))
        if prt is not None:
            j0, j1 = prt.idx(lt(d, 8, 0)), prt.idx(lt(d, 19, 0)); ksh = np.flatnonzero((prs[j0:j1] >= 4) & ~prt.D["roll"][j0:j1])
            if len(ksh) and j0 + ksh[0] >= 1:
                kp = j0 + int(ksh[0]); T0 = int(prt.t[kp]); io = M.idx(T0)
                if io < M.n and M.t[io] == T0 and np.isfinite(rs[io]) and rs[io] <= 1.2:
                    dr = sgn(prt.mc[kp] - prt.mc[kp - 1]); k = nxt(M, io + 1)
                    if dr and k is not None:
                        add("N025", enter_dist(M, dr, k, 0.1 * atr, int(M.t[k]) + 3600))
        state("_SH", d, sh=float(nsh[p] >= 1)); add("_SD", fad)
        # ------------------------------------------------ C. lead-lag
        for (idea, ld, tz, w0, w1, sgp) in LEADS.get(sym, []):
            leadlag(M, P[ld], d, tz, w0, w1, sgp, hist[idea], idea, add)
        # ------------------------------------------------ D. calendar
        if sym in FX and d in CS["imm"]:
            add("N039", LB(M, d, mode="fade"))
        if sym in METALS and d in CS["china"]:
            add("N040", LB(M, d, mode="fade"))
        if sym == "XAUUSD" and d in CS["diwali"]:
            add("N041", LB(M, d, True, False))
        if sym in JPYX and d in CS["jgw"]:
            add("N042", LB(M, d, mode="fade"))
        if d in CS["dst"]:
            add("N043", fad)
        age = moon_age(d)
        if age <= 3 or age >= 29.530589 - 3:
            add("N044", fol)
        if abs(age - 14.765) <= 3:
            add("N045", fad)
        if sym in IDX6:
            add("N046", fad if 5 <= d.month <= 10 else fol)
        if (sym in USDP or sym == "XAUUSD" or sym in USI) and d in CS["blackout"]:
            add("N047", fol)
        if sym in USI and d in CS["earn"]:
            add("N048", NB(M, d))
        if sym in USDP and d in CS["payroll"]:
            add("N049", LB(M, d, mode="fade"))
        if sym in USI and d.weekday() == 1 and Dd.wd.iloc[p - 1] == 0 and C[p - 1] < C[p - 2]:
            add("N050", NB(M, d, True, False))
        if sym in FX and d in CS["ukbh"]:
            add("N051", LB(M, d, mode="fade"))
        if d in CS["yearend"]:
            add("N052", fad)
        if (sym in USDP or sym in USI or sym == "XAUUSD") and d in CS["heavy"]:
            add("N100", fad)
        # ------------------------------------------------ G / H daily
        if np.isfinite(psy[q]):
            if psy[q] >= 0.75:
                add("N081", DLV(M, d, None, y.L, atr))
            elif psy[q] <= 0.25:
                add("N081", DLV(M, d, y.H, None, atr))
        bod = C - O_; A_ = atr
        if p + 4 < nd and all(bod[q - i] >= 0.3 * A_ for i in range(3)) and C[q] > C[q - 1] > C[q - 2]:
            add("N087", enter_t(M, 1, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
        elif p + 4 < nd and all(bod[q - i] <= -0.3 * A_ for i in range(3)) and C[q] < C[q - 1] < C[q - 2]:
            add("N087", enter_t(M, -1, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
        hi1, lo1 = max(O_[q - 1], C[q - 1]), min(O_[q - 1], C[q - 1]); hi0, lo0 = max(O_[q], C[q]), min(O_[q], C[q])
        if abs(bod[q - 1]) >= 0.6 * A_ and hi0 <= hi1 and lo0 >= lo1:
            add("N088", DLV(M, d, y.H, None, atr) if bod[q - 1] < 0 else DLV(M, d, None, y.L, atr))
        mid1 = (O_[q - 1] + C[q - 1]) / 2
        if bod[q - 1] <= -0.6 * A_ and O_[q] < C[q - 1] and mid1 < C[q] < O_[q - 1]:
            add("N089", DLV(M, d, y.H, None, atr))
        elif bod[q - 1] >= 0.6 * A_ and O_[q] > C[q - 1] and O_[q - 1] < C[q] < mid1:
            add("N089", DLV(M, d, None, y.L, atr))
        if abs(Ld[q] - Ld[q - 1]) <= 0.05 * A_ and C[q] > O_[q]:
            add("N090", DLV(M, d, y.H, None, atr))
        elif abs(Hd[q] - Hd[q - 1]) <= 0.05 * A_ and C[q] < O_[q]:
            add("N090", DLV(M, d, None, y.L, atr))
        hi2, lo2 = max(O_[q - 2], C[q - 2]), min(O_[q - 2], C[q - 2])
        if p + 4 < nd and abs(bod[q - 2]) >= 0.6 * A_ and hi1 <= hi2 and lo1 >= lo2:
            if bod[q - 2] < 0 and C[q] > O_[q - 2]:
                add("N091", enter_t(M, 1, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
            elif bod[q - 2] > 0 and C[q] < O_[q - 2]:
                add("N091", enter_t(M, -1, lt(d, 8, 5), dist=1.5 * atr, x_end=M.at2045(p + 4)))
        # ------------------------------------------------ I. factor helpers
        t105 = int(M.days[p]) * 86400 + 3900
        if sym in USDP:
            with np.errstate(invalid="ignore", divide="ignore"):
                mb = np.log(mclose(M, lt(d, 8, 29))) - np.log(mclose(M, lt(d, 8, 5))); ma_ = np.log(mclose(M, lt(d, 8, 29))) - np.log(mclose(M, t105))
            sgu = 1 if sym.startswith("USD") else -1
            state("_UF", d, ub=sgu * mb, ua=sgu * ma_); add("_LBL", LB(M, d, True, False)); add("_LBS", LB(M, d, False, True))
        if sym in IDX6:
            with np.errstate(invalid="ignore", divide="ignore"):
                state("_IX", d, mv=np.log(mclose(M, lt(d, 9, 29, NYZ))) - np.log(mclose(M, t105)))
        if sym in USI:
            add("_NBL", NB(M, d, True, False)); add("_NBS", NB(M, d, False, True))
        # ------------------------------------------------ J. CME attention
        if sym in att:
            ha = AV[max(0, p - 20):p]; ha = ha[np.isfinite(ha)]
            if len(ha) >= 15 and np.median(ha) > 0 and AV[p] >= 1.5 * np.median(ha):
                if sym == "NIKKEI":
                    add("N097", SESSION(M, d))
                else:
                    add("N095" if sym == "XAUUSD" else "N096", LB(M, d))
        # ------------------------------------------------ K. extensions
        if sym in ("AUDJPY", "NZDJPY", "CADJPY"):
            vb, tb = vix[vix.index < d], v3m[v3m.index < d]
            if len(vb) and len(tb) and (d - vb.index[-1]).days <= 7 and vb.iloc[-1] >= tb.iloc[-1]:
                add("N098", LB(M, d, False, True))
        if sym == "USDCAD":
            ob = oil[oil.index < d]
            if len(ob) >= 2 and (d - ob.index[-1]).days <= 7:
                ch = ob.iloc[-1] / ob.iloc[-2] - 1
                if ch >= 0.03:
                    add("N099", LB(M, d, False, True))
                elif ch <= -0.03:
                    add("N099", LB(M, d, True, False))
    out += price_bar_ideas(M, rs)
    if cme:
        out += mfi_bw(M, v)
    T = pd.DataFrame(out)
    return T[T.day >= START] if len(T) else T


# ---------------------------------------------------------------------- post-stage
def combine(T):
    rows = [T[~T.idea.str.startswith("_")]]
    SH = T[T.idea == "_SH"].pivot_table(index="day", columns="sym", values="sh").sort_index(); cnt = SH.sum(axis=1)
    prev_cnt = cnt.shift(1); days26 = set(prev_cnt[prev_cnt >= 20].index); SD = T[T.idea == "_SD"]
    rows.append(SD[SD.day.isin(days26)].assign(idea="N026"))
    UF = T[T.idea == "_UF"].pivot_table(index="day", columns="sym", values="ub"); UA = T[T.idea == "_UF"].pivot_table(index="day", columns="sym", values="ua")
    LBL, LBS = T[T.idea == "_LBL"].set_index(["day", "sym"]), T[T.idea == "_LBS"].set_index(["day", "sym"]); sel = []
    UF = UF[UF.notna().sum(axis=1) == 7]
    for day, r in UF.iterrows():
        for s in USDP:
            res = r[s] - r.drop(s).mean()                                          # > 0: USD stronger against s's currency than the factor
            usd_base = s.startswith("USD"); long_ok = (res > 0) if usd_base else (res < 0)
            src = LBL if long_ok else LBS
            if res != 0 and (day, s) in src.index:
                sel.append(src.loc[[(day, s)]].reset_index().assign(idea="N092"))
    bloc = ["AUDUSD", "NZDUSD", "USDCAD"]; UAb = UA.reindex(columns=bloc).dropna()
    for day, r in UAb.iterrows():
        if (r > 0).all() or (r < 0).all():
            usd_up = (r > 0).all()
            for s in bloc:
                long_ok = usd_up if s.startswith("USD") else not usd_up
                src = LBL if long_ok else LBS
                if (day, s) in src.index:
                    sel.append(src.loc[[(day, s)]].reset_index().assign(idea="N094"))
    IX = T[T.idea == "_IX"].pivot_table(index="day", columns="sym", values="mv"); IX = IX[IX.notna().sum(axis=1) == 6]
    NBL, NBS = T[T.idea == "_NBL"].set_index(["day", "sym"]), T[T.idea == "_NBS"].set_index(["day", "sym"])
    for day, r in IX.iterrows():
        m6 = r.mean()
        for s in USI:
            res = r[s] - m6; src = NBL if res > 0 else NBS
            if res != 0 and (day, s) in src.index:
                sel.append(src.loc[[(day, s)]].reset_index().assign(idea="N093"))
    out = pd.concat(rows + sel, ignore_index=True)
    return out[out.day >= START][["idea", "sym", "day", "t_entry", "side", "R", "Rm", "wsp"]]


WORKERS = 4                                                                     # --workers 2 halves peak memory (18 Oct: the 4-worker dry run was stopped for low RAM)


def build(raw=False):
    rawc = CACHE.replace(".parquet", "_raw.parquet")
    if os.path.exists(CACHE) and not raw:
        return pd.read_parquet(CACHE)
    if os.path.exists(rawc):
        Tr = pd.read_parquet(rawc)
    else:
        with Pool(WORKERS) as pl:
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
    rng = np.random.default_rng(1002); Tr = build(raw=True)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = Tr[Tr.sym == sym]; ft_ = full.t_entry.dropna()
        cut = int(rng.uniform(ft_.quantile(.4), ft_.quantile(.8)))
        tr = market((sym, cut)); cdy = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[(full.day < cdy) & full.t_entry.notna()][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[(tr.day < cdy) & tr.t_entry.notna()][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        sc = [x for x in ("sh", "ub", "ua", "mv") if x in full.columns]
        sa = full[(full.day < cdy) & full.t_entry.isna()].sort_values(["idea", "day"]).reset_index(drop=True)
        sb = tr[(tr.day < cdy) & tr.t_entry.isna()].reindex(columns=sa.columns).sort_values(["idea", "day"]).reset_index(drop=True)
        same_s = len(sa) == len(sb) and (sa[["idea", "day"]].values == sb[["idea", "day"]].values).all() and np.allclose(
            sa[sc].astype(float).to_numpy(), sb[sc].astype(float).to_numpy(), equal_nan=True)
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')} server; trades >= 35 days before the cut {len(a)} vs {len(b)}, identical {same};"
              f" helper states {len(sa)} vs {len(sb)}, identical {same_s}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("N001", "N014", "N016", "N025", "N027", "N039", "N044", "N053", "N060", "N074", "N087", "N092"):
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
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1900)
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
    S.to_csv("forex/ea_research/BRK100C_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(); WORKERS = a.workers
    if a.dry_run:
        dry_run()
    if a.run:
        run()
