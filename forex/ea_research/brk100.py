"""BRK100: 100 more untested breakout tests (79 new concepts + 21 out-of-sample market extensions of today's NSDQ / XAUUSD ideas)
on 46 MT5, one pre-registered round on BRK50's engine. Pre-registration: forex/ea_research/PREREG_BRK100.md.
   python -m forex.ea_research.brk100 --dry-run | --run"""
import argparse, collections, os, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.brk50 import Mkt, lt, last_of, LIS, NYZ, JST, H, DEV, VAL, HOLD, NONC
from forex.ea_research.orbx import ct, CRYPTO
from forex.ea_research.analog import mclass
from forex.ea_research.brk30 import (bars, sma, rmax, rmin, rsi, adx_di, pivots, cross_up, cross_dn, bc_trades, bs_trade,
                                  enter_at, sgn, tag, epoch, wilder)
from forex.ea_research.brk50b import holy_grail, day_returns, fut_volume, calendars

CACHE = "C:/work/scratch/brk100_trades.parquet"
UTC, BER, LDN, SHA, KOL, SYD = "UTC", "Europe/Berlin", "Europe/London", "Asia/Shanghai", "Asia/Kolkata", "Australia/Sydney"
CRY = tuple(sorted(CRYPTO)); ALLM = tuple(NONC); X36 = tuple(s for s in NONC if s not in ("NSDQ", "XAUUSD"))
FX = tuple(s for s in NONC if mclass(s) == "fx")
USDM = ("AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY")
JPYX = ("AUDJPY", "CADJPY", "CHFJPY", "EURJPY", "GBPJPY", "NZDJPY", "USDJPY")
EURX = ("EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD")
USI = ("SP", "NSDQ", "DOW")
IDEAS = [f"L{k:03d}" for k in range(1, 101)]
UNIV = {i: ALLM for i in IDEAS}
for i in range(1, 13):
    UNIV[f"L{i:03d}"] = CRY
UNIV.update({"L007": tuple(s for s in CRY if s != "BTCUSD"), "L012": ("BTCUSD", "ETHUSD"),
             "L013": USDM, "L014": JPYX, "L015": EURX, "L016": USDM, "L017": USDM, "L018": USDM,
             "L019": ("AUDUSD", "NZDUSD", "USDCAD"), "L020": ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"),
             "L021": ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"), "L022": ("AUDJPY", "NZDJPY", "CADJPY"),
             "L023": ("AUDUSD", "NZDUSD", "AUDJPY", "NZDJPY"), "L024": USDM,
             "L025": ("AUDJPY", "NZDJPY", "CADJPY", "GBPJPY", "EURJPY", "USDJPY"), "L026": USDM, "L027": FX, "L028": FX, "L029": FX,
             "L030": ("DAX",), "L031": ("DAX",), "L032": ("NIKKEI",), "L033": ("NIKKEI",), "L034": ("ASX",), "L035": USI, "L036": USI,
             "L037": USI, "L038": ("DAX",), "L039": ("NIKKEI",), "L040": ("ASX",), "L041": ("DAX",), "L042": ("DAX",),
             "L043": ("XAUUSD",), "L044": ("XAUUSD",), "L045": ("XAGUSD",), "L046": ("WTI", "BRENT"), "L047": ("WTI", "BRENT"),
             "L048": ("WTI", "BRENT"), "L049": ("XAGUSD",), "L050": ("WTI", "BRENT"), "L051": ("XAUUSD",), "L052": ("XAUUSD",),
             "L056": ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "SP", "NSDQ", "DOW", "XAUUSD", "XAGUSD", "WTI", "BRENT"),
             "L057": JPYX + ("AUDUSD", "NZDUSD", "NIKKEI", "ASX", "XAUUSD"),
             "L074": USDM + ("XAUUSD",) + USI, "L075": ("SP", "NSDQ", "XAUUSD", "XAGUSD"), "L076": ("SP", "NSDQ", "XAUUSD", "XAGUSD"),
             "L079": ("SP", "NSDQ", "DOW", "DAX", "ASX", "AUDUSD"), "L081": ("SP", "DOW", "DAX", "NIKKEI", "ASX"), "L082": ("SP", "DOW"),
             "L085": ALLM, "L091": ALLM, "L092": ALLM, "L099": ("DOW", "DAX", "NIKKEI", "ASX"), "L100": ("SP", "DOW")})
for i in ("L080", "L083", "L084", "L086", "L087", "L088", "L089", "L090", "L093", "L094", "L095", "L096", "L097", "L098"):
    UNIV[i] = X36
PARTNER56 = {"EURUSD": "GBPUSD", "GBPUSD": "EURUSD", "AUDUSD": "NZDUSD", "NZDUSD": "AUDUSD", "SP": "NSDQ", "NSDQ": "SP", "DOW": "SP",
             "XAUUSD": "XAGUSD", "XAGUSD": "XAUUSD", "WTI": "BRENT", "BRENT": "WTI"}
FUTROOT = {"NSDQ": "NQ", "SP": "ES", "XAUUSD": "GC", "XAGUSD": "SI"}
DAILY = "futures/data/daily/"
AUC = "futures/data/events/treasury_coupon_auctions.csv"
START = pd.Timestamp("2022-01-01")


# ---------------------------------------------------------------------- generic boxes
def BX(M, d, tz, b0, b1, w1, xe, long_ok=True, short_ok=True, mode="follow", need=0.8):
    a, b, w, x = (lt(d, h_, m_, tz) for h_, m_ in (b0, b1, w1, xe))
    bx = M.box(a, b, max(4, int(need * (b - a) / 60)))
    if not bx or not bx[0] > bx[1]:
        return None
    hi, lo = bx
    if mode == "fade":
        return M.level(hi, lo, b, w, "fade", dist=0.5 * (hi - lo), x_end=x)
    if not (long_ok or short_ok):
        return None
    return M.level(hi if long_ok else None, lo if short_ok else None, b, w, "follow", slU=lo, slL=hi, x_end=x)


def LB(M, d, lo=True, sh=True, mode="follow"):
    return BX(M, d, LIS, (8, 0), (8, 30), (11, 0), (17, 0), lo, sh, mode)


def NB(M, d, lo=True, sh=True, mode="follow"):
    return BX(M, d, NYZ, (9, 30), (10, 0), (12, 0), (15, 55), lo, sh, mode)


def SESSION(M, d, lo=True, sh=True, mode="follow"):
    s = M.sym
    if s in USI:
        return NB(M, d, lo, sh, mode)
    if s == "NIKKEI":
        return BX(M, d, JST, (9, 0), (9, 30), (11, 30), (14, 55), lo, sh, mode)
    if s == "ASX":
        return BX(M, d, SYD, (10, 0), (10, 30), (12, 30), (15, 55), lo, sh, mode)
    return LB(M, d, lo, sh, mode)


def SIDE(fn, M, d, s, **kw):
    return fn(M, d, s > 0, s < 0, **kw) if s else None


def DLV(M, d, U, L, atr, mode="follow"):
    if U is None and L is None:
        return None
    return M.level(U, L, lt(d, 8, 0), lt(d, 19, 0), mode, dist=0.5 * atr, x_end=lt(d, 20, 45))


def mv(P, a, b):
    return P.mid_at(b) - P.mid_at(a) if P is not None else np.nan


def open_mid(M, x):
    i = M.idx(x)
    return (M.D["bo"][i] + M.D["ao"][i]) / 2 if i < M.n and M.t[i] - x < 600 else np.nan


def last2(s, d):
    if s is None:
        return None
    i = int(s.index.searchsorted(d))
    if i < 2 or (d - s.index[i - 1]).days > 7:
        return None
    return s.iloc[i - 2], s.iloc[i - 1]


def lastn(s, d, n):
    i = int(s.index.searchsorted(d))
    if i < n or (d - s.index[i - 1]).days > 7:
        return None
    return s.iloc[i - n:i].to_numpy()


# ---------------------------------------------------------------------- day-based tests
def day_ideas(M, p, X, st):
    out = []; Dd = M.Dd
    if p < 25:
        return out
    r, y, yy = Dd.iloc[p], Dd.iloc[p - 1], Dd.iloc[p - 2]; atr = r.atr
    if not (atr > 0):
        return out
    d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); yd = pd.Timestamp(int(M.days[p - 1]) * 86400, unit="s")
    sym = M.sym; o1 = int(M.days[p]) * 86400 + H; wd = d.weekday()
    w08, w1430, w19, x20 = lt(d, 8, 0), lt(d, 14, 30), lt(d, 19, 0), lt(d, 20, 45); P = X["P"]; T1 = X["tier1"].get(d, set())

    def add(idea, res, **kw):
        if res is not None and sym in UNIV[idea]:
            res.update(idea=idea, sym=sym, day=d, **kw); out.append(res)

    def has(*ids):
        return any(sym in UNIV[i] for i in ids)

    # ---------------- CRYPTO
    if sym in CRY:
        add("L001", BX(M, d, UTC, (7, 30), (8, 0), (12, 0), (15, 55)))
        add("L002", BX(M, d, UTC, (15, 30), (16, 0), (19, 0), (19, 30)))
        if wd == 0:
            bx = M.box(lt(d, 0, 0, UTC), lt(d, 4, 0, UTC), 200)
            if bx and bx[0] > bx[1]:
                wed = d + pd.Timedelta(days=2)
                add("L003", M.level(bx[0], bx[1], lt(d, 4, 0, UTC), lt(wed, 19, 29, UTC), "follow", slU=bx[1], slL=bx[0], x_end=lt(wed, 19, 30, UTC)))
            sun = d - pd.Timedelta(days=1); s_ = sgn(mv(M, lt(sun, 0, 0, UTC), lt(sun, 20, 0, UTC)))
            add("L011", BX(M, d, UTC, (8, 0), (8, 30), (12, 0), (15, 55), s_ > 0, s_ < 0) if s_ else None)
        ar = M.box(lt(d, 0, 0, UTC), lt(d, 8, 0, UTC), 400)
        if ar and ar[0] > ar[1]:
            q = M.rng(lt(d, 8, 0, UTC), lt(d, 13, 30, UTC))
            if q and q[0] < ar[0] and q[1] > ar[1]:
                add("L004", M.level(ar[0], ar[1], lt(d, 13, 30, UTC), lt(d, 19, 0, UTC), "follow", slU=ar[1], slL=ar[0], x_end=lt(d, 19, 30, UTC)))
            if wd == 4 and (d + pd.Timedelta(days=7)).month != d.month:
                add("L008", BX(M, d, UTC, (0, 0), (8, 0), (16, 0), (19, 30), mode="fade"))
        add("L005", BX(M, d, JST, (9, 0), (9, 30), (11, 30), (15, 0)))
        if wd == 5:
            add("L006", BX(M, d, UTC, (0, 0), (4, 0), (16, 0), (19, 30)))
        if wd == 6:
            add("L010", BX(M, d, UTC, (0, 0), (4, 0), (16, 0), (19, 30), mode="fade"))
        if sym != "BTCUSD" and "BTCUSD" in P:
            B_ = P["BTCUSD"].Dd.C; days = M.days[p - 20:p]
            if all(int(x) in B_.index for x in days):
                ratio = M.Dd.C.iloc[p - 20:p].to_numpy() / B_.loc[days].to_numpy(); s_ = sgn(ratio[-1] - ratio.mean())
                add("L007", BX(M, d, UTC, (0, 0), (1, 0), (8, 0), (19, 30), s_ > 0, s_ < 0) if s_ else None)
        if "data" in T1:
            add("L009", BX(M, d, NYZ, (8, 30), (8, 45), (11, 0), (15, 55)))
        if "fomc" in T1:
            add("L009", BX(M, d, NYZ, (14, 0), (14, 45), (15, 30), (15, 55)))
        if sym in ("BTCUSD", "ETHUSD"):
            q = st.setdefault("l012", collections.deque(maxlen=14))
            a_, b_, c_ = M.mid_at(lt(d, 9, 30, NYZ)), M.mid_at(lt(d, 14, 59, NYZ)), M.mid_at(lt(d, 15, 55, NYZ))
            if len(q) == 14 and np.isfinite(a_) and np.isfinite(b_):
                s_ = sgn(b_ - a_)
                if s_:
                    add("L012", enter_at(M, s_, lt(d, 15, 0, NYZ), dist=2 * np.mean(q), x_end=lt(d, 15, 55, NYZ)))
            if np.isfinite(b_) and np.isfinite(c_):
                q.append(abs(c_ - b_))
        return out
    # ---------------- FX
    if has("L013"):
        add("L013", BX(M, d, NYZ, (9, 0), (9, 30), (10, 0), (10, 5), mode="fade"))
    if has("L014"):
        add("L014", BX(M, d, JST, (14, 30), (15, 0), (17, 0), (18, 55)))
    if has("L015"):
        add("L015", BX(M, d, BER, (13, 45), (14, 15), (15, 30), (16, 55)))
    if has("L016") and "data" in T1:
        add("L016", BX(M, d, NYZ, (8, 30), (8, 45), (11, 0), (15, 55)))
    if has("L017") and "fomc" in T1:
        add("L017", BX(M, d, NYZ, (14, 0), (14, 45), (15, 30), (15, 55)))
    if has("L018") and d in X["auction"]:
        add("L018", BX(M, d, NYZ, (13, 0), (13, 15), (14, 30), (15, 55)))
    vxc = last2(X["vix"], d); vch = (vxc[1] / vxc[0] - 1) if vxc else np.nan
    vdir = 1 if vch >= 0.08 else (-1 if vch <= -0.05 else 0)              # +1 = risk-off day
    if has("L019") and vdir:
        s_ = -vdir if sym in ("AUDUSD", "NZDUSD") else vdir; add("L019", SIDE(LB, M, d, s_))
    usd_base = sym.startswith("USD")
    zz = last2(X["zn"], d)
    if has("L020") and zz:
        s_usd = -sgn(zz[1] - zz[0]); add("L020", SIDE(LB, M, d, s_usd if usd_base else -s_usd))
    if has("L021") and "XAUUSD" in P:
        add("L021", SIDE(LB, M, d, sgn(mv(P["XAUUSD"], o1, lt(d, 7, 59)))))
    if has("L022") and "BTCUSD" in P:
        add("L022", SIDE(LB, M, d, sgn(mv(P["BTCUSD"], o1, lt(d, 7, 59)))))
    if has("L023"):
        add("L023", BX(M, d, SHA, (9, 30), (10, 0), (11, 30), (15, 0)))
    qend = bool(r.last_q) or (p + 1 < len(Dd) and bool(Dd.last_q.iloc[p + 1]) and Dd.q.iloc[p + 1] == r.q)
    if has("L024") and qend:
        add("L024", SIDE(LB, M, d, 1 if usd_base else -1))
    if has("L025"):
        add("L025", LB(M, d, True, False))
    if has("L026"):
        add("L026", BX(M, d, NYZ, (14, 30), (15, 0), (15, 45), (15, 55)))
    if has("L027") and wd == 0:
        add("L027", SIDE(LB, M, d, sgn(M.mid_at(o1) - y.C)))
    if sym in FX:                                                         # L028 / L029 candidates (selected across pairs later)
        bx = M.box(lt(d, 8, 0), lt(d, 8, 30), 24)
        if bx and bx[0] > bx[1]:
            res = LB(M, d) or dict(t_entry=np.nan, side=0, R=np.nan, Rm=np.nan, wsp=np.nan)
            out.append(dict(res, idea="_LBFX", sym=sym, day=d, box_atr=(bx[0] - bx[1]) / atr))
    # ---------------- INDICES
    if sym == "DAX":
        add("L030", BX(M, d, BER, (17, 30), (18, 0), (21, 0), (21, 55)))
        add("L031", BX(M, d, BER, (15, 30), (16, 0), (17, 25), (17, 25)))
        add("L038", SIDE(LB, M, d, -sgn(mv(P.get("EURUSD"), o1, lt(d, 7, 59)))))
        if "data" in T1:
            add("L041", BX(M, d, BER, (14, 30), (14, 45), (16, 30), (17, 25)))
        if wd == 4 and 15 <= d.day <= 21:
            add("L042", BX(M, d, BER, (12, 30), (13, 0), (15, 0), (17, 25)))
    if sym == "NIKKEI":
        add("L032", BX(M, d, JST, (12, 30), (13, 0), (14, 30), (14, 55)))
        if wd == 4 and 8 <= d.day <= 14:
            add("L033", BX(M, d, JST, (9, 0), (9, 30), (11, 30), (14, 55), mode="fade"))
        s_ = sgn(mv(P.get("USDJPY"), lt(yd, 15, 59, NYZ), lt(d, 8, 59, JST)))
        add("L039", BX(M, d, JST, (9, 0), (9, 30), (11, 30), (14, 55), s_ > 0, s_ < 0) if s_ else None)
    if sym == "ASX":
        add("L034", BX(M, d, SHA, (9, 30), (10, 0), (11, 30), (15, 0)))
        hg = last2(X["hg"], d)
        if hg:
            s_ = sgn(hg[1] - hg[0]); add("L040", BX(M, d, SYD, (10, 0), (10, 30), (12, 30), (15, 55), s_ > 0, s_ < 0) if s_ else None)
    if sym in USI:
        v3, v9, vv = last2(X["vix3m"], d), last2(X["vix9d"], d), vxc
        if vv and v3 and vv[1] >= v3[1]:
            add("L035", NB(M, d))
        if vv and v9 and v9[1] / vv[1] >= 1.1:
            add("L036", NB(M, d, mode="fade"))
        rt, es = last2(X["rty"], d), last2(X["es"], d)
        if rt and es:
            add("L037", SIDE(NB, M, d, sgn((rt[1] / rt[0]) - (es[1] / es[0]))))
    # ---------------- COMMODITIES
    if sym == "XAUUSD":
        add("L043", BX(M, d, LDN, (10, 0), (10, 30), (12, 0), (15, 0)))
        add("L044", BX(M, d, LDN, (14, 30), (15, 0), (16, 30), (18, 0)))
        add("L051", BX(M, d, SHA, (13, 45), (14, 15), (15, 30), (16, 0)))
        add("L052", BX(M, d, KOL, (9, 15), (9, 45), (12, 0), (14, 0)))
    if sym == "XAGUSD":
        add("L045", BX(M, d, LDN, (11, 30), (12, 0), (14, 0), (17, 0)))
        G_ = P.get("XAUUSD")
        if G_ is not None:
            days = M.days[p - 20:p]
            if all(int(x) in G_.Dd.index for x in days):
                ratio = G_.Dd.C.loc[days].to_numpy() / M.Dd.C.iloc[p - 20:p].to_numpy()
                add("L049", SIDE(LB, M, d, sgn(ratio[-1] - ratio.mean())))
    if sym in ("WTI", "BRENT"):
        add("L046", BX(M, d, NYZ, (14, 0), (14, 30), (15, 30), (15, 55)))
        if wd == 4:
            add("L047", BX(M, d, NYZ, (13, 0), (13, 15), (14, 30), (15, 55)))
        add("L048", BX(M, d, LDN, (1, 0), (1, 30), (5, 0), (7, 55)))
        if vdir:
            add("L050", BX(M, d, NYZ, (9, 0), (9, 30), (11, 30), (14, 25), vdir < 0, vdir > 0))
    # ---------------- STRUCTURE (ALL)
    i0, i1 = M.idx(int(M.days[p - 1]) * 86400 + H), M.idx(int(M.days[p - 1]) * 86400 + 23 * H)
    m08 = M.mid_at(w08)
    if i1 - i0 > 300 and np.isfinite(m08):
        V = float(M.mc[i0:i1].mean())
        add("L053", DLV(M, d, V if m08 < V else None, V if m08 > V else None, atr))
    am = mv(M, o1, lt(d, 7, 59))
    if np.isfinite(am) and abs(am) > 0.5 * atr:
        add("L054", SIDE(LB, M, d, -sgn(am)))
    lm = mv(M, w08, lt(d, 14, 29))
    if np.isfinite(lm) and abs(lm) > 0.5 * atr:
        add("L055", SIDE(NB, M, d, -sgn(lm)))
    if sym in PARTNER56 and PARTNER56[sym] in P:
        add("L056", partner_fade(M, P[PARTNER56[sym]], d))
    if has("L057"):
        ny = M.rng(lt(yd, 14, 30), lt(yd, 21, 0))
        if ny and ny[0] > ny[1]:
            hi, lo = ny; a_, b_, xe = lt(d, 1, 0), lt(d, 7, 30), lt(d, 7, 55)
            add("L057", M.level(hi, lo, a_, b_, "follow", slU=lo, slL=hi, x_end=xe) if hi - lo <= atr else M.level(hi, lo, a_, b_, "follow", dist=0.5 * atr, x_end=xe))
    asia = M.rng(o1, lt(d, 8, 0))
    if asia and asia[0] > asia[1]:
        q = M.rng(lt(d, 8, 0), w1430)
        if q and q[0] < asia[0] and q[1] > asia[1]:
            hi, lo = asia
            add("L058", M.level(hi, lo, w1430, w19, "follow", slU=lo, slL=hi, x_end=x20) if hi - lo <= atr else M.level(hi, lo, w1430, w19, "follow", dist=0.5 * atr, x_end=x20))
    # ---------------- NAMED SYSTEMS (daily ones)
    add("L062", DLV(M, d, y.H if y.C < yy.L else None, y.L if y.C > yy.H else None, atr))
    rg = y.H - y.L
    if rg > 0:
        top_open, bot_close = y.O >= y.L + 0.8 * rg, y.C <= y.L + 0.2 * rg
        bot_open, top_close = y.O <= y.L + 0.2 * rg, y.C >= y.L + 0.8 * rg
        if top_open and bot_close:
            add("L063", after_cross(M, d, y.L, -1, atr))
        elif bot_open and top_close:
            add("L063", after_cross(M, d, y.H, 1, atr))
    add("L064", acd(M, d, atr))
    add("L065", open_drive(M, d))
    if p >= 21:
        c20 = Dd.C.iloc[p - 20:p].to_numpy(); xx = np.arange(20.0); sl, ic = np.polyfit(xx, c20, 1)
        ss_res = ((c20 - (ic + sl * xx)) ** 2).sum(); ss_tot = ((c20 - c20.mean()) ** 2).sum()
        if ss_tot > 0 and 1 - ss_res / ss_tot > 0.7:
            add("L068", DLV(M, d, y.H if sl > 0 else None, y.L if sl < 0 else None, atr))
    pr = X["pinball"][p - 1]
    if np.isfinite(pr) and (pr < 30 or pr > 70):
        fh = M.box(lt(d, 8, 0), lt(d, 9, 0), 48)
        if fh and fh[0] > fh[1]:
            add("L069", M.level(fh[0] if pr < 30 else None, fh[1] if pr > 70 else None, lt(d, 9, 0), w19, "follow", slU=fh[1], slL=fh[0], x_end=x20))
    # ---------------- INFORMATION AND EVENTS
    if has("L074") and d in X["minutes"]:
        add("L074", BX(M, d, NYZ, (14, 0), (14, 30), (15, 30), (15, 55)))
    if sym in FUTROOT and X["fut"] is not None:
        res75, res76 = cme_volume(M, d, p, X["fut"])
        add("L075", res75); add("L076", res76)
    if p + 2 < len(M.days) and (int(M.days[p + 1]) in X["fomc_days"] or int(M.days[p + 2]) in X["fomc_days"]):
        add("L077", LB(M, d, mode="fade"))
    if "data" in T1:
        add("L078", LB(M, d, mode="fade"))
    if has("L079"):
        hgc, gcc = lastn(X["hg"], d, 20) if X["hg"] is not None else None, lastn(X["gc"], d, 20) if X["gc"] is not None else None
        if hgc is not None and gcc is not None:
            ratio = hgc / gcc; add("L079", SIDE(SESSION, M, d, sgn(ratio[-1] - ratio.mean())))
    # ---------------- OUT-OF-SAMPLE EXTENSIONS
    m = M.rng(w08, w1430)
    if m and (m[0] < y.H or m[1] > y.L):
        add("L080", M.level(y.H if m[0] < y.H else None, y.L if m[1] > y.L else None, w1430, w19, "follow", dist=0.5 * atr, x_end=x20))
    if has("L081"):
        add("L081", gap_session(M, d, yd, atr))
    if has("L082") and "NIKKEI" in P:
        add("L082", SIDE(NB, M, d, sgn(mv(P["NIKKEI"], lt(d, 9, 0, JST), lt(d, 15, 0, JST)))))
    add("L083", DLV(M, d, y.H if (y.L < yy.L and y.C > yy.L) else None, y.L if (y.H > yy.H and y.C < yy.H) else None, atr))
    Hs, Ls = Dd.H.iloc[p - 4:p].to_numpy(), Dd.L.iloc[p - 4:p].to_numpy()
    lh3, hl3 = Hs[3] < Hs[2] < Hs[1] < Hs[0], Ls[3] > Ls[2] > Ls[1] > Ls[0]
    add("L084", DLV(M, d, y.H if lh3 else None, y.L if hl3 else None, atr))
    bx = M.box(lt(d, 8, 0), lt(d, 8, 30), 24)
    if bx and bx[0] > bx[1]:
        lo_ok, sh_ok = abs(bx[0] - y.H) <= 0.15 * atr, abs(bx[1] - y.L) <= 0.15 * atr
        add("L085", LB(M, d, lo_ok, sh_ok) if (lo_ok or sh_ok) else None)
    add("L086", SIDE(NB, M, d, sgn(mv(M, w08, lt(d, 9, 29, NYZ)))))
    h1_ideas(M, d, X, add, w19, x20)
    vr = X["vr"][p]
    if np.isfinite(vr) and vr > 1.1:
        add("L091", LB(M, d))
    if np.isfinite(vr) and vr < 0.9:
        add("L092", LB(M, d, mode="fade"))
    if rg > 0:
        body = abs(y.C - y.O); lw, uw = min(y.O, y.C) - y.L, y.H - max(y.O, y.C); cl = (y.C - y.L) / rg
        add("L093", DLV(M, d, y.H if (lw > 2 * body and cl >= 2 / 3) else None, y.L if (uw > 2 * body and cl <= 1 / 3) else None, atr))
        if body < 0.1 * rg:
            add("L094", DLV(M, d, y.H, y.L, atr))
    Z = Dd.iloc[p - 5:p]; zr = (Z.H - Z.L).replace(0, np.nan); cpos = ((Z.C - Z.L) / zr).to_numpy()
    if np.isfinite(cpos).all():
        add("L095", DLV(M, d, y.H if (cpos > 0.5).all() else None, y.L if (cpos < 0.5).all() else None, atr))
    s11 = 1 if y.C > yy.H else (-1 if y.C < yy.L else 0)
    if s11 and sym in UNIV["L096"] and st.get("l096", 0) <= w08:
        xe = M.x_after(w08, 2); res = enter_at(M, s11, w08, dist=atr, x_end=xe)
        if res is not None:
            ix = M.exit_idx(xe); st["l096"] = int(M.t[min(ix, M.n - 1)]) if ix else 0
        add("L096", res)
    if wd in (3, 4):
        wk = Dd[(Dd.wk == r.wk) & (Dd.wd.isin([0, 1]))]
        if len(wk) == 2 and (wk.index < M.days[p]).all():
            add("L097", DLV(M, d, wk.H.max(), wk.L.min(), atr, "fade"))
    W = Dd.iloc[p - 21:p - 1]
    if len(W) == 20:
        lo20, ilo = W.L.min(), int(np.argmin(W.L.to_numpy())); hi20, ihi = W.H.max(), int(np.argmax(W.H.to_numpy()))
        add("L098", DLV(M, d, lo20 if (y.C < lo20 and 19 - ilo >= 3) else None, hi20 if (y.C > hi20 and 19 - ihi >= 3) else None, atr))
    if has("L099") and X["zn"] is not None:
        zn20 = lastn(X["zn"], d, 20)
        if zn20 is not None:
            add("L099", SIDE(SESSION, M, d, 1 if zn20[-1] > zn20.mean() else -1))
    if has("L100") and np.isfinite(vch):
        add("L100", SIDE(NB, M, d, 1 if vch <= -0.05 else (-1 if vch >= 0.08 else 0)))
    return out


def after_cross(M, d, lvl, below, atr):
    """L063: after price trades through `lvl` (below = -1: below it), a stop order back through it"""
    D = M.D; i0, i1 = M.idx(lt(d, 8, 0)), M.idx(lt(d, 19, 0))
    if i1 - i0 < 30:
        return None
    hit = np.flatnonzero(D["bl"][i0:i1] < lvl) if below < 0 else np.flatnonzero(D["ah"][i0:i1] > lvl)
    if not len(hit):
        return None
    t_after = int(M.t[i0 + int(hit[0])]) + 60
    if below < 0:
        return M.level(lvl, None, t_after, lt(d, 19, 0), "follow", dist=0.5 * atr, x_end=lt(d, 20, 45))
    return M.level(None, lvl, t_after, lt(d, 19, 0), "follow", dist=0.5 * atr, x_end=lt(d, 20, 45))


def acd(M, d, atr):
    D = M.D; orb = M.box(lt(d, 8, 0), lt(d, 8, 15), 12)
    if not orb or not orb[0] > orb[1]:
        return None
    A = 0.1 * atr; up, dn = orb[0] + A, orb[1] - A; i0, i1 = M.idx(lt(d, 8, 15)), M.idx(lt(d, 12, 0))
    if i1 - i0 < 30:
        return None
    c = M.mc[i0:i1]; ab, be = (c > up).astype(int), (c < dn).astype(int)
    ru = np.convolve(ab, np.ones(7, int), "valid"); rd = np.convolve(be, np.ones(7, int), "valid")
    ku = np.flatnonzero(ru == 7); kd = np.flatnonzero(rd == 7)
    ku = int(ku[0]) + 6 if len(ku) else None; kd = int(kd[0]) + 6 if len(kd) else None
    if ku is None and kd is None:
        return None
    long_ = kd is None or (ku is not None and ku < kd); k = i0 + (ku if long_ else kd) + 1
    if k >= M.n or D["roll"][k]:
        return None
    side = 1 if long_ else -1; e = D["ao"][k] if long_ else D["bo"][k]
    ix = M.exit_idx(lt(d, 17, 0))
    return None if ix is None else M.trade(side, k, e, orb[1] if long_ else orb[0], ix)


def session_box_times(M, d):
    s = M.sym
    if s in USI:
        return [lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ), lt(d, 15, 55, NYZ)]
    if s == "NIKKEI":
        return [lt(d, 9, 0, JST), lt(d, 9, 30, JST), lt(d, 14, 55, JST)]
    if s == "ASX":
        return [lt(d, 10, 0, SYD), lt(d, 10, 30, SYD), lt(d, 15, 55, SYD)]
    return [lt(d, 8, 0), lt(d, 8, 30), lt(d, 17, 0)]


def open_drive(M, d):
    a, b, xe = session_box_times(M, d); i0, i1 = M.idx(a), M.idx(b)
    if i1 - i0 < 24:
        return None
    hi, lo = M.D["bh"][i0:i1].max(), M.D["bl"][i0:i1].min(); rgb = hi - lo
    if not rgb > 0:
        return None
    o_, c_ = (M.D["bo"][i0] - lo) / rgb, (M.D["bc"][i1 - 1] - lo) / rgb
    s_ = 1 if (c_ >= 0.9 and o_ <= 0.2) else (-1 if (c_ <= 0.1 and o_ >= 0.8) else 0)
    if not s_:
        return None
    return enter_at(M, s_, b, stop=lo if s_ > 0 else hi, x_end=xe)


def gap_session(M, d, yd, atr):
    s = M.sym
    if s in USI:
        s0, b1, ref = lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ), lt(yd, 15, 59, NYZ)
    elif s == "DAX":
        s0, b1, ref = lt(d, 9, 0, BER), lt(d, 9, 30, BER), lt(yd, 17, 29, BER)
    elif s == "NIKKEI":
        s0, b1, ref = lt(d, 9, 0, JST), lt(d, 9, 30, JST), lt(yd, 14, 59, JST)
    else:
        s0, b1, ref = lt(d, 10, 0, SYD), lt(d, 10, 30, SYD), lt(yd, 15, 59, SYD)
    o_, pc = open_mid(M, s0), M.mid_at(ref)
    if not (np.isfinite(o_) and np.isfinite(pc)) or abs(o_ - pc) <= 0.2 * atr:
        return None
    q = M.rng(s0, b1)
    if not q:
        return None
    if o_ > pc and q[1] > pc:
        return SESSION(M, d, True, False)
    if o_ < pc and q[0] < pc:
        return SESSION(M, d, False, True)
    return None


def partner_fade(M, Pm, d):
    """L056: fade a London-box touch that the partner market has not confirmed by that minute"""
    a, b, w, xe = lt(d, 8, 0), lt(d, 8, 30), lt(d, 11, 0), lt(d, 17, 0)
    bx, pb = M.box(a, b, 24), Pm.box(a, b, 24)
    if not bx or not pb or not bx[0] > bx[1] or not pb[0] > pb[1]:
        return None
    D = M.D; i0, i1 = M.idx(b), M.idx(w)
    if i1 - i0 < 30 or not (bx[1] < M.mc[i0] < bx[0]):
        return None
    nr = ~D["roll"][i0:i1]
    up = np.flatnonzero((D["ah"][i0:i1] >= bx[0]) & nr); dn = np.flatnonzero((D["bl"][i0:i1] <= bx[1]) & nr)
    ku = int(up[0]) if len(up) else None; kd = int(dn[0]) if len(dn) else None
    if (ku is None and kd is None) or (ku is not None and ku == kd):
        return None
    hit_up = kd is None or (ku is not None and ku < kd); k = i0 + (ku if hit_up else kd); tk = int(M.t[k])
    j0, j1 = Pm.idx(b), Pm.idx(tk + 60)
    if j1 <= j0:
        return None
    confirmed = (Pm.D["ah"][j0:j1] >= pb[0]).any() if hit_up else (Pm.D["bl"][j0:j1] <= pb[1]).any()
    if confirmed:
        return None
    side = -1 if hit_up else 1; kk = k + 1
    if kk >= M.n or D["roll"][kk]:
        return None
    e = D["bo"][kk] if side < 0 else D["ao"][kk]; ix = M.exit_idx(xe)
    return None if ix is None else M.trade(side, kk, e, e - side * 0.5 * (bx[0] - bx[1]), ix)


def cme_volume(M, d, p, F):
    """L075 / L076 on the NB (indices) or the COMEX box (metals)"""
    t_, cv = F
    if M.sym in ("SP", "NSDQ"):
        box = ((9, 30), (10, 0), (12, 0), (15, 55))
    else:
        box = ((8, 20), (8, 50), (11, 0), (13, 25))
    res = BX(M, d, NYZ, *box)
    a, b = lt(d, *box[0], NYZ), lt(d, *box[1], NYZ)
    def vol(x0, x1):
        return cv[int(np.searchsorted(t_, x1))] - cv[int(np.searchsorted(t_, x0))]
    prev = [pd.Timestamp(int(M.days[q]) * 86400, unit="s") for q in range(max(0, p - 20), p)]
    out75 = out76 = None
    if len(prev) == 20:
        bv = vol(a, b); pv = [vol(lt(x, *box[0], NYZ), lt(x, *box[1], NYZ)) for x in prev]
        if np.mean(pv) > 0 and bv < 0.6 * np.mean(pv):
            out76 = dict(res) if res is not None else None
        if res is not None:
            loc = pd.Timestamp(res["t_entry"], unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
            fv = vol(res["t_entry"], res["t_entry"] + 60)
            hv = [vol(lt(x, loc.hour, loc.minute, NYZ), lt(x, loc.hour, loc.minute, NYZ) + 60) for x in prev]
            if np.median(hv) > 0 and fv >= 3 * np.median(hv):
                out75 = dict(res)
    return out75, out76


def h1_ideas(M, d, X, add, w19, x20):
    """L087 - L089: BRK50B J20 / J22 / J23 on the other markets"""
    B = X["B1"]; t0 = B["t0"]; hh, ll, cc = B["hh"], B["ll"], B["cc"]
    rng_ = range(int(np.searchsorted(t0, lt(d, 9, 0))), int(np.searchsorted(t0, lt(d, 18, 0))))
    for b in rng_:
        if b > 0 and t0[b] - t0[b - 1] == H and hh[b] < hh[b - 1] and ll[b] > ll[b - 1]:
            e0 = t0[b] + H
            add("L087", M.level(hh[b], ll[b], e0, min(e0 + 2 * H, w19), "follow", slU=ll[b], slL=hh[b], x_end=x20)); break
    rngs = hh - ll
    for b in rng_:
        if b >= 20 and rngs[b] > 2 * rngs[b - 20:b].mean() > 0:
            cl = (cc[b] - ll[b]) / rngs[b]
            if cl >= 0.75 or cl <= 0.25:
                add("L088", enter_at(M, 1 if cl >= 0.75 else -1, t0[b] + H, stop=(hh[b] + ll[b]) / 2, x_end=x20)); break
    for b in rng_:
        if b >= 3 and t0[b] - t0[b - 3] == 3 * H:
            upm = cc[b - 2] > hh[b - 3] and cc[b - 1] > hh[b - 2] and cc[b] > hh[b - 1]
            dnm = cc[b - 2] < ll[b - 3] and cc[b - 1] < ll[b - 2] and cc[b] < ll[b - 1]
            if upm or dnm:
                add("L089", enter_at(M, 1 if upm else -1, t0[b] + H, stop=ll[b - 2:b + 1].min() if upm else hh[b - 2:b + 1].max(), x_end=x20)); break


# ---------------------------------------------------------------------- bar-based named systems (H1 / H4), ALL
def busy_loop(M, B, cand, fn, idea):
    out = []; busy = -1; b0 = int(np.searchsorted(B["t0"], epoch(START)))
    for b in cand:
        if b < max(b0, 60) or b <= busy:
            continue
        res, ix = fn(b)
        if res is not None:
            res["idea"] = idea; out.append(res); busy = int(np.searchsorted(B["t0"], M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


def bar_systems(M):
    out = []; B = bars(M, H); hh, ll, cc, atr = B["hh"], B["ll"], B["cc"], B["atr"]; n = len(hh)
    # L059 pivot reversal (4 left, 2 right)
    phm = pd.Series(hh).rolling(7, min_periods=7).max().shift(-2).to_numpy(); plm = pd.Series(ll).rolling(7, min_periods=7).min().shift(-2).to_numpy()
    ph_lvl = pd.Series(np.where(hh == phm, hh, np.nan)).shift(2).ffill().to_numpy(); pl_lvl = pd.Series(np.where(ll == plm, ll, np.nan)).shift(2).ffill().to_numpy()
    ok = np.isfinite(ph_lvl) & np.isfinite(pl_lvl) & (atr > 0)
    out += busy_loop(M, B, np.flatnonzero(ok), lambda b: bs_trade(M, B, b, ph_lvl[b], pl_lvl[b], None, None, 1, 24, "L059", dist=1.5 * atr[b]), "L059")
    # L060 consecutive up / down
    up3 = np.r_[np.zeros(3, bool), (cc[3:] > cc[2:-1]) & (cc[2:-1] > cc[1:-2]) & (cc[1:-2] > cc[:-3])]
    dn3 = np.r_[np.zeros(3, bool), (cc[3:] < cc[2:-1]) & (cc[2:-1] < cc[1:-2]) & (cc[1:-2] < cc[:-3])]
    out += [dict(r_, idea="L060") for r_ in bc_trades(M, B, np.where(up3, 1, np.where(dn3, -1, 0)), 1.5, 24, "L060")]
    # L061 momentum stop orders
    mom = cc - np.r_[np.full(12, np.nan), cc[:-12]]; dm = np.r_[np.nan, np.diff(mom)]
    c61 = np.flatnonzero(((mom > 0) & (dm > 0)) | ((mom < 0) & (dm < 0)))
    out += busy_loop(M, B, c61, lambda b: bs_trade(M, B, b, hh[b] if mom[b] > 0 else None, ll[b] if mom[b] < 0 else None, None, None, 1, 24, "L061", dist=1.5 * atr[b]) if atr[b] > 0 else (None, -1), "L061")
    # L066 Renko, L067 point and figure
    out += renko(M, B) + point_figure(M, B)
    # L070 stochastic pop on H4
    B4 = bars(M, 4 * H); h4, l4, c4 = B4["hh"], B4["ll"], B4["cc"]
    fk = 100 * (c4 - rmin(l4, 14)) / np.maximum(rmax(h4, 14) - rmin(l4, 14), 1e-12); sk = sma(fk, 3); ad, _, _ = adx_di(h4, l4, c4)
    s70 = np.where((ad < 20) & cross_up(sk, np.full_like(sk, 80.0)), 1, np.where((ad < 20) & cross_dn(sk, np.full_like(sk, 20.0)), -1, 0))
    out += [dict(r_, idea="L070") for r_ in bc_trades(M, B4, s70, 2, 30, "L070")]
    # L071 Ross 1-2-3, L072 Ross hook, L073 Hikkake
    PH, PL = pivots(hh, ll); ev = sorted([(i + 3, "L", i) for i in PL] + [(i + 3, "H", i) for i in PH])
    seq = []; c71 = {}
    for kb, typ, i in ev:
        seq.append((typ, i))
        if len(seq) >= 3:
            (t1, i1), (t2, i2), (t3, i3) = seq[-3:]
            if t1 == "L" and t2 == "H" and t3 == "L" and ll[i3] > ll[i1]:
                c71[kb] = (1, hh[i2], ll[i3])
            elif t1 == "H" and t2 == "L" and t3 == "H" and hh[i3] < hh[i1]:
                c71[kb] = (-1, ll[i2], hh[i3])
    out += busy_loop(M, B, sorted(k for k in c71 if k < n - 13),
                     lambda b: bs_trade(M, B, b, c71[b][1] if c71[b][0] > 0 else None, c71[b][1] if c71[b][0] < 0 else None,
                                        c71[b][2], c71[b][2], 12, 24, "L071"), "L071")
    hi20, lo20 = rmax(hh, 20), rmin(ll, 20)
    newhi = np.r_[False, hh[:-1] >= hi20[:-1]]; newlo = np.r_[False, ll[:-1] <= lo20[:-1]]
    hook_u = newhi & (hh < np.r_[np.inf, hh[:-1]]); hook_d = newlo & (ll > np.r_[-np.inf, ll[:-1]])
    out += busy_loop(M, B, np.flatnonzero(hook_u | hook_d),
                     lambda b: bs_trade(M, B, b, hh[b - 1] if hook_u[b] else None, ll[b - 1] if (hook_d[b] and not hook_u[b]) else None,
                                        ll[b], hh[b], 6, 24, "L072"), "L072")
    c73 = {}
    for i in range(2, n - 6):
        if hh[i] < hh[i - 1] and ll[i] > ll[i - 1]:
            upb, dnb = hh[i + 1] > hh[i], ll[i + 1] < ll[i]
            if upb and not dnb:
                c73[i + 1] = (-1, ll[i], hh[i + 1])
            elif dnb and not upb:
                c73[i + 1] = (1, hh[i], ll[i + 1])
    out += busy_loop(M, B, sorted(c73), lambda b: bs_trade(M, B, b, c73[b][1] if c73[b][0] > 0 else None, c73[b][1] if c73[b][0] < 0 else None,
                                                           c73[b][2], c73[b][2], 3, 24, "L073"), "L073")
    return out


def renko(M, B):
    """L066: bricks of 0.5 ATR14(H1) (the last completed H1 bar's ATR) on minute mids; two up bricks after a down brick -> long"""
    out = []; D = M.D; t0 = B["t0"]; atr = B["atr"]; mc = M.mc; t = M.t
    hb = np.searchsorted(t0, t, side="right") - 2                        # the last COMPLETED H1 bar of each minute
    i_start = int(np.searchsorted(t, epoch(START)))
    base = None; dirs = []; busy_t = -1
    for i in range(max(1, i_start - 50000), M.n - 1):
        b = hb[i]
        if b < 15 or not (atr[b] > 0):
            continue
        s_ = 0.5 * atr[b]; px = mc[i]
        if base is None:
            base = px; continue
        new = 0
        if px >= base + s_ and (not dirs or dirs[-1] > 0 or px >= base + 2 * s_):
            new = 1; base = base + s_ if (not dirs or dirs[-1] > 0) else base + 2 * s_
        elif px <= base - s_ and (not dirs or dirs[-1] < 0 or px <= base - 2 * s_):
            new = -1; base = base - s_ if (not dirs or dirs[-1] < 0) else base - 2 * s_
        if not new:
            continue
        dirs.append(new); dirs = dirs[-3:]
        if i < i_start or t[i] <= busy_t or len(dirs) < 3:
            continue
        if dirs[-1] == dirs[-2] and dirs[-3] == -dirs[-1]:
            side = dirs[-1]; kk = i + 1
            if D["roll"][kk]:
                continue
            e = D["ao"][kk] if side > 0 else D["bo"][kk]; xb = b + 1 + 24
            if xb >= len(t0):
                continue
            ix = M.exit_idx(int(t0[xb]))
            if ix is None:
                continue
            res = M.trade(side, kk, e, e - side * 1.5 * atr[b], ix)
            if res is not None:
                out.append(tag(res, "L066", M, kk)); busy_t = int(M.t[min(ix, M.n - 1)])
    return out


def point_figure(M, B):
    """L067: box 0.25 ATR(daily, the day before), 3-box reversal, on H1 closes; a new X (O) column beyond the previous X (O)"""
    out = []; D = M.D; t0, cc, en = B["t0"], B["cc"], B["en"]; Dd = M.Dd
    datr = pd.Series(Dd.atr.to_numpy(), index=Dd.index); bday = t0 // 86400
    col = 0; hi = lo = None; prev_x = prev_o = None; busy = -1; b0 = int(np.searchsorted(t0, epoch(START)))
    for b in range(len(cc) - 26):
        a_ = datr.get(int(bday[b]))
        if a_ is None or not (a_ > 0):
            continue
        bx = 0.25 * a_; c = cc[b]; sig = 0
        if col == 0:
            hi = lo = c; col = 1; continue
        if col > 0:
            if c >= hi + bx:
                hi = c
                if prev_x is not None and c > prev_x and hi - bx <= prev_x:
                    sig = 1
            elif c <= hi - 3 * bx:
                prev_x = hi; col = -1; lo = c
        else:
            if c <= lo - bx:
                lo = c
                if prev_o is not None and c < prev_o and lo + bx >= prev_o:
                    sig = -1
            elif c >= lo + 3 * bx:
                prev_o = lo; col = 1; hi = c
        if sig and b >= max(b0, 60) and b > busy:
            kk = int(en[b])
            if kk >= M.n or D["roll"][kk]:
                continue
            e = D["ao"][kk] if sig > 0 else D["bo"][kk]; ix = M.exit_idx(int(t0[b + 1 + 24]))
            if ix is None:
                continue
            res = M.trade(sig, kk, e, e - sig * 3 * bx, ix)
            if res is not None:
                out.append(tag(res, "L067", M, kk)); busy = int(np.searchsorted(t0, M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


# ---------------------------------------------------------------------- per-market build
def ydaily(name, cd):
    s = pd.read_csv(DAILY + name, parse_dates=["date"]).set_index("date").close.sort_index()
    return s[s.index < cd] if cd is not None else s


def market(args):
    sym, cut = args
    M = Mkt(sym, cut); cd = pd.Timestamp(cut, unit="s").normalize() if cut is not None else None
    need = set()
    if sym in CRY and sym != "BTCUSD":
        need.add("BTCUSD")
    if sym in UNIV["L021"]:
        need.add("XAUUSD")
    if sym in UNIV["L022"]:
        need.add("BTCUSD")
    if sym == "DAX":
        need.add("EURUSD")
    if sym == "NIKKEI":
        need.add("USDJPY")
    if sym in UNIV["L082"]:
        need.add("NIKKEI")
    if sym == "XAGUSD":
        need.add("XAUUSD")
    if sym in PARTNER56:
        need.add(PARTNER56[sym])
    X = dict(P={s: Mkt(s, cut) for s in need if s != sym})
    X["tier1"], fomc = calendars()
    X["fomc_days"] = set(int(pd.Timestamp(f).value // 86400 // 10 ** 9) for f in fomc)
    X["minutes"] = set(pd.Timestamp(f) + pd.Timedelta(days=21) for f in fomc)
    a = pd.read_csv(AUC, parse_dates=["date"]); X["auction"] = set(a.date)
    for k, f in (("vix", "^VIX_yahoo_daily.csv"), ("vix9d", "^VIX9D_yahoo_daily.csv"), ("vix3m", "^VIX3M_yahoo_daily.csv"),
                 ("rty", "RTY=F_yahoo_daily.csv"), ("es", "ES=F_yahoo_daily.csv"), ("hg", "HG=F_yahoo_daily.csv"),
                 ("gc", "GC=F_yahoo_daily.csv"), ("zn", "ZN=F_yahoo_daily.csv")):
        X[k] = ydaily(f, cd)
    X["fut"] = fut_volume(FUTROOT[sym], cut) if sym in FUTROOT else None
    X["B1"] = bars(M, H)
    rr = [day_returns(M, p) for p in range(len(M.days))]; vr = np.full(len(M.days), np.nan)
    for p in range(20, len(M.days)):
        r5 = np.concatenate([rr[q][0] for q in range(p - 20, p)]); r30 = np.concatenate([rr[q][1] for q in range(p - 20, p)])
        if len(r5) > 500 and len(r30) > 80 and r5.var() > 0:
            vr[p] = r30.var() / (6 * r5.var())
    X["vr"] = vr
    dc = np.r_[np.nan, np.diff(M.Dd.C.to_numpy())]; X["pinball"] = rsi(np.nan_to_num(dc), 3)
    out, st = [], {}
    for p in range(len(M.days)):
        if M.days[p] * 86400 < START.timestamp():
            continue
        out += day_ideas(M, p, X, st)
    if sym not in CRY:
        out += bar_systems(M)
        hg = holy_grail(M)
        out += [dict(r_, idea="L090") for r_ in hg] if sym in UNIV["L090"] else []
    T = pd.DataFrame(out)
    return T[T.day >= START] if len(T) else T


def select_class(T):
    """L028 / L029: per day, the FX pair with the smallest / largest London box per ATR (its LB trade, if it filled)"""
    C = T[T.idea == "_LBFX"].dropna(subset=["box_atr"]); rows = []
    for _, g in C.groupby("day"):
        if len(g) < 10:
            continue
        for idea, r_ in (("L028", g.loc[g.box_atr.idxmin()]), ("L029", g.loc[g.box_atr.idxmax()])):
            if pd.notna(r_.R):
                rows.append(dict(r_, idea=idea))
    return pd.concat([T[T.idea != "_LBFX"], pd.DataFrame(rows)], ignore_index=True)


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    with Pool(4) as pl:
        T = pd.concat(pl.map(market, [(s, None) for s in NONC + list(CRY)]), ignore_index=True)
    T = select_class(T)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    T = build()
    print(f"trades {len(T)}, markets {T.sym.nunique()}, {T.day.min().date()}..{T.day.max().date()}")
    c = T.assign(per=np.select([per(T, DEV), per(T, VAL)], ["DEV", "VAL"], "HOLD")).groupby(["idea", "per"]).size().unstack().reindex(IDEAS)
    c["mkts"] = T.groupby("idea").sym.nunique(); c["long%"] = (T.groupby("idea").side.apply(lambda s: (s > 0).mean()) * 100).round(0)
    c["stop_sp"] = T.groupby("idea").wsp.median().round(0)
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200); print(c.to_string())
    rng = np.random.default_rng(100)
    for sym in ("EURUSD", "XAUUSD", "NSDQ", "BTCUSD"):
        full = T[(T.sym == sym) & (~T.idea.isin(["L028", "L029"]))]
        cut = int(rng.uniform(full.t_entry.quantile(.4), full.t_entry.quantile(.8)))
        tr = market((sym, cut)); tr = tr[tr.idea != "_LBFX"]; cdy = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[full.day < cdy][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[tr.day < cdy][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')} server, trades >= 35 days before the cut {len(a)} vs {len(b)}, identical {same}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("L001", "L013", "L015", "L023", "L031", "L044", "L056", "L064", "L066", "L067", "L073", "L075"):
        x = T[T.idea == idea]
        if len(x):
            r = x.sample(1, random_state=7).iloc[0]; loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens")
            print(f"  hand check {idea} {r.sym} entry {loc.tz_convert(LIS):%Y-%m-%d %H:%M} LIS ({loc.tz_convert(NYZ):%H:%M} NY) side {r.side:+d} stop {r.wsp:.0f} spreads")


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
        ok = len(d) >= 100 and mu > 0 and t >= 3.29 and (yrs > 0).sum() >= 2 and mi > 0 and ti >= 2.0
        mv_, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        row = dict(idea=idea, n_dev=len(d), R_dev=mu, t_dev=t, info=mi, t_info=ti, yrs="/".join(f"{q:+.2f}" for q in yrs), win=(d.R > 0).mean(),
                   n_val=len(v), R_val=mv_, t_val=tv, mkts=x.sym.nunique(), dev_pass=ok, val_pass=ok and mv_ > 0 and tv >= 1.65)
        if row["val_pass"]:
            h = x[per(x, HOLD)]; mh, th = ct(h); row.update(R_hold=mh, t_hold=th, hold_pass=mh > 0 and th >= 1.65)
        rows.append(row)
    S = pd.DataFrame(rows); pd.set_option("display.width", 260); pd.set_option("display.max_rows", 200)
    print(S.round(3).to_string(index=False))
    tv_ = S.t_dev.dropna()
    print(f"\nDEV t-values of {len(tv_)} tests: mean {tv_.mean():+.2f}, sd {tv_.std():.2f}, positive {int((tv_ > 0).sum())}, t>1.65 {int((tv_ > 1.65).sum())}"
          f" (null ~{0.05 * len(tv_):.1f}), t>3.29 {int((tv_ > 3.29).sum())} | new concepts L001-L079: t>1.65 {int((S[S.idea <= 'L079'].t_dev > 1.65).sum())};"
          f" market extensions L080-L100: t>1.65 {int((S[S.idea >= 'L080'].t_dev > 1.65).sum())}")
    passers = S[S.get("hold_pass", pd.Series(False, index=S.index)).fillna(False).astype(bool)].idea.tolist() if "hold_pass" in S else []
    print("DEV + VAL passers:", S[S.val_pass.fillna(False).astype(bool)].idea.tolist() or "none", "| full passers:", passers or "none")
    top = S.dropna(subset=["t_dev"]).nlargest(5, "t_dev").idea.tolist(); print("account view for the 5 best by DEV t:", top)
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1700)
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
    S.to_csv("forex/ea_research/BRK100_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
