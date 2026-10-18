"""BRK50B: 50 more breakout ideas on gold and Nasdaq (MT5 M1 bid/ask), one pre-registered round on BRK50's engine (`brk50.Mkt`).
Pre-registration: forex/ea_research/PREREG_BRK50B.md.   python -m forex.ea_research.brk50b --dry-run | --run"""
import argparse, collections, os, numpy as np, pandas as pd
from forex.ea_research.brk50 import Mkt, lt, last_of, LIS, NYZ, JST, H, DEV, VAL, HOLD
from forex.ea_research.orbx import ct

CACHE = "C:/work/scratch/brk50b_trades.parquet"
IDEAS = [f"J{k:02d}" for k in range(1, 51)]
GNU, NU, GU = ("NSDQ", "XAUUSD"), ("NSDQ",), ("XAUUSD",)
UNIV = {i: GNU for i in IDEAS}
for _i in ("J27", "J28", "J33", "J34", "J35", "J36", "J37", "J39", "J43"):
    UNIV[_i] = NU
for _i in ("J38", "J40", "J41", "J42", "J50"):
    UNIV[_i] = GU
# session start, session end, box end (= order window start), order window end, exit, closing hour start / last minute
SESS = {"NSDQ": dict(s0=(9, 30), s1=(16, 0), b1=(10, 0), w1=(12, 0), xe=(15, 55), c0=(15, 0), c1=(15, 59), root="NQ"),
        "XAUUSD": dict(s0=(8, 20), s1=(13, 30), b1=(8, 50), w1=(11, 0), xe=(13, 25), c0=(12, 30), c1=(13, 29), root="GC")}
MORNING = {"NSDQ": ((9, 30), (11, 0), (14, 0), (15, 55)), "XAUUSD": ((8, 20), (10, 0), (12, 30), (13, 25))}
SMALLDAY = {"NSDQ": ((9, 30), (14, 0), (15, 30), (15, 55)), "XAUUSD": ((8, 20), (11, 30), (13, 0), (13, 25))}
PARTNERS = {"NSDQ": ("BTCUSD", "DAX", "NIKKEI", "USDJPY"), "XAUUSD": ("WTI", "XAGUSD", "NSDQ", "USDJPY")}
DAILY = "futures/data/daily/"
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
CAL = "forex/ea_research/EVENT_CALENDAR_2022_2026.csv"
FOMC = "futures/data/events/fomc_statement_dates.csv"
START = pd.Timestamp("2022-01-01")


def nyt(d, hm):
    return lt(d, hm[0], hm[1], NYZ)


def epoch(ts_naive):
    return int((pd.Timestamp(ts_naive) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


# ---------------------------------------------------------------------- context: partners, daily files, CME volume, calendars
def yahoo(name, cut=None):
    d = pd.read_csv(DAILY + name, parse_dates=["date"]).set_index("date").sort_index()
    if cut is not None:
        d = d[d.index < pd.Timestamp(cut, unit="s").normalize()]
    return d


def before(s, d, n=1):
    """the last n values of series s dated strictly before d (None if the newest is older than 7 days)"""
    i = int(s.index.searchsorted(d))
    if i < n or (d - s.index[i - 1]).days > 7:
        return None
    return s.iloc[i - n:i].to_numpy()


def fut_volume(root, cut=None):
    f = pd.read_parquet(FUTP.format(root), columns=["ts", "volume"]).sort_values("ts")
    srv = f.ts.dt.tz_convert("Europe/Athens").dt.tz_localize(None)
    t = ((srv - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy().astype(np.int64)
    v = f.volume.to_numpy().astype(float)
    if cut is not None:
        k = int(np.searchsorted(t, cut)); t, v = t[:k], v[:k]
    return t, np.r_[0.0, np.cumsum(v)]


def vsum(F, a, b):
    t, cv = F
    return cv[int(np.searchsorted(t, b))] - cv[int(np.searchsorted(t, a))]


def calendars():
    c = pd.read_csv(CAL, parse_dates=["date"]); tier1 = {}
    for k, d in zip(c.kind, c.date):
        tier1.setdefault(d, set()).add("fomc" if k == "FOMC" else "data")
    fomc = sorted(pd.read_csv(FOMC, parse_dates=["date"]).date)
    return tier1, fomc


def bars(M, tf):
    key = M.t // tf; st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], M.n]
    return dict(st=st, en=en, hh=np.maximum.reduceat(M.mh, st), ll=np.minimum.reduceat(M.ml, st), cc=M.mc[en - 1], t0=key[st] * tf)


def day_returns(M, p):
    """5- and 30-minute log returns of mids at exact marks, 08:00-20:59 LIS of day p"""
    d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); a, b = lt(d, 8, 0), lt(d, 21, 0); out = []
    for step in (300, 1800):
        marks = np.arange(a, b + 1, step); i = np.searchsorted(M.t, marks); i = np.minimum(i, M.n - 1)
        ok = M.t[i] == marks; x = np.where(ok, M.mc[i], np.nan); r = np.diff(np.log(x))
        out.append(r[np.isfinite(r)])
    return out


def context(sym, cut=None):
    M = Mkt(sym, cut)
    X = dict(P={s: Mkt(s, cut) for s in PARTNERS[sym]}, fut=fut_volume(SESS[sym]["root"], cut),
             vix=yahoo("^VIX_yahoo_daily.csv", cut), zn=yahoo("ZN=F_yahoo_daily.csv", cut).close, hg=yahoo("HG=F_yahoo_daily.csv", cut).close)
    X["tier1"], X["fomc"] = calendars()
    X["B1"], X["B15"] = bars(M, H), bars(M, 900)
    rr = [day_returns(M, p) for p in range(len(M.days))]
    vr = np.full(len(M.days), np.nan)
    for p in range(20, len(M.days)):
        r5 = np.concatenate([rr[q][0] for q in range(p - 20, p)]); r30 = np.concatenate([rr[q][1] for q in range(p - 20, p)])
        if len(r5) > 500 and len(r30) > 80 and r5.var() > 0:
            vr[p] = r30.var() / (6 * r5.var())
    X["vr"] = vr
    S = SESS[sym]; on, sv = np.full(len(M.days), np.nan), np.full(len(M.days), np.nan)
    for p in range(len(M.days)):
        d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); pv = d - pd.Timedelta(days=1)
        on[p] = vsum(X["fut"], lt(pv, 18, 0, NYZ), nyt(d, S["s0"])); sv[p] = vsum(X["fut"], nyt(d, S["s0"]), nyt(d, S["s1"]))
    X["on"], X["sv"] = on, sv
    return M, X


# ---------------------------------------------------------------------- building blocks
def sbox(M, d):
    S = SESS[M.sym]
    return M.box(nyt(d, S["s0"]), nyt(d, S["b1"]), 20)


def sb(M, d, long_ok=True, short_ok=True, mode="follow", box=None):
    S = SESS[M.sym]; b = box if box is not None else sbox(M, d)
    if not b or not b[0] > b[1]:
        return None
    hi, lo = b; w0, w1, xe = nyt(d, S["b1"]), nyt(d, S["w1"]), nyt(d, S["xe"])
    if mode == "fade":
        return M.level(hi, lo, w0, w1, "fade", dist=0.5 * (hi - lo), x_end=xe)
    if not (long_ok or short_ok):
        return None
    return M.level(hi if long_ok else None, lo if short_ok else None, w0, w1, "follow", slU=lo, slL=hi, x_end=xe)


def lbx(M, d, long_ok=True, short_ok=True):
    b = M.box(lt(d, 8, 0), lt(d, 8, 30), 20)
    if not b or not b[0] > b[1] or not (long_ok or short_ok):
        return None
    hi, lo = b
    return M.level(hi if long_ok else None, lo if short_ok else None, lt(d, 8, 30), lt(d, 11, 0), "follow", slU=lo, slL=hi, x_end=lt(d, 17, 0))


def dl(M, d, U, L, atr, mode="follow"):
    if U is None and L is None:
        return None
    return M.level(U, L, lt(d, 8, 0), lt(d, 19, 0), mode, dist=0.5 * atr, x_end=lt(d, 20, 45))


def enter_at(M, side, t0, stop=None, dist=None, x_end=None):
    """market order at the open of the first minute at / after t0 (ask for a buy, bid for a sell)"""
    k = M.idx(t0)
    if k >= M.n or M.t[k] - t0 > 600 or M.D["roll"][k]:
        return None
    e = M.D["ao"][k] if side > 0 else M.D["bo"][k]
    ix = M.exit_idx(x_end)
    if ix is None:
        return None
    return M.trade(side, k, e, stop if stop is not None else e - side * dist, ix)


def open_mid(M, x):
    i = M.idx(x)
    return (M.D["bo"][i] + M.D["ao"][i]) / 2 if i < M.n and M.t[i] - x < 600 else np.nan


def sgn(x):
    return 0 if not np.isfinite(x) or x == 0 else (1 if x > 0 else -1)


def dir_sb(M, d, s):
    """session box only on side s (+1 long-only, -1 short-only); None when s == 0"""
    return sb(M, d, s > 0, s < 0) if s else None


def win_bars(B, a, b):
    """indices of bars whose start lies in [a, b)"""
    return range(int(np.searchsorted(B["t0"], a)), int(np.searchsorted(B["t0"], b)))


# ---------------------------------------------------------------------- the 49 day-based ideas (J24 is bar-based)
def day_ideas(M, p, X):
    out = []; Dd = M.Dd
    if p < 25:
        return out
    r, y, yy = Dd.iloc[p], Dd.iloc[p - 1], Dd.iloc[p - 2]; atr = r.atr
    if not (atr > 0):
        return out
    d = pd.Timestamp(int(M.days[p]) * 86400, unit="s"); yd = pd.Timestamp(int(M.days[p - 1]) * 86400, unit="s")
    sym = M.sym; S = SESS[sym]; o1 = int(M.days[p]) * 86400 + H
    w08, w1430, w19, x20 = lt(d, 8, 0), lt(d, 14, 30), lt(d, 19, 0), lt(d, 20, 45)
    s0, b1 = nyt(d, S["s0"]), nyt(d, S["b1"])

    def add(idea, res):
        if res is not None and sym in UNIV[idea]:
            res.update(idea=idea, sym=sym, day=d); out.append(res)

    # LEVELS AND DAILY STRUCTURE
    m = M.rng(w08, w1430)
    if m:
        add("J01", M.level(y.H if m[0] < y.H else None, y.L if m[1] > y.L else None, w1430, w19, "follow", dist=0.5 * atr, x_end=x20)
            if (m[0] < y.H or m[1] > y.L) else None)
    ny = M.rng(lt(yd, 14, 30), lt(yd, 21, 0))
    if ny:
        hi, lo = ny
        add("J02", M.level(hi, lo, w1430, w19, "follow", slU=lo, slL=hi, x_end=x20) if hi - lo <= atr
            else M.level(hi, lo, w1430, w19, "follow", dist=0.5 * atr, x_end=x20))
    ch = M.rng(nyt(yd, S["c0"]), nyt(yd, S["c1"]) + 60)
    if ch:
        hi, lo = ch
        add("J03", M.level(hi, lo, w08, w19, "follow", slU=lo, slL=hi, x_end=x20) if hi - lo <= 0.5 * atr
            else M.level(hi, lo, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
    Hs, Ls = Dd.H.iloc[p - 4:p].to_numpy(), Dd.L.iloc[p - 4:p].to_numpy()
    lh3 = Hs[3] < Hs[2] < Hs[1] < Hs[0]; hl3 = Ls[3] > Ls[2] > Ls[1] > Ls[0]
    hh3 = Hs[3] > Hs[2] > Hs[1] > Hs[0]; ll3 = Ls[3] < Ls[2] < Ls[1] < Ls[0]
    add("J04", dl(M, d, y.H if lh3 else None, y.L if hl3 else None, atr))
    add("J05", dl(M, d, y.H if (hh3 and hl3) else None, y.L if (lh3 and ll3) else None, atr))
    sr = M.rng(nyt(yd, S["s0"]), nyt(yd, S["s1"])); o_ = open_mid(M, s0)
    if sr and np.isfinite(o_):
        if o_ < sr[1]:
            add("J06", M.level(sr[1], None, s0 + 60, nyt(d, S["w1"]), "follow", dist=0.5 * atr, x_end=nyt(d, S["xe"])))
        elif o_ > sr[0]:
            add("J06", M.level(None, sr[0], s0 + 60, nyt(d, S["w1"]), "follow", dist=0.5 * atr, x_end=nyt(d, S["xe"])))
    rg = y.H - y.L
    if rg > 0:
        body = abs(y.C - y.O); lw, uw = min(y.O, y.C) - y.L, y.H - max(y.O, y.C); cl = (y.C - y.L) / rg
        add("J07", dl(M, d, y.H if (lw > 2 * body and cl >= 2 / 3) else None, y.L if (uw > 2 * body and cl <= 1 / 3) else None, atr))
        if body < 0.1 * rg:
            add("J08", dl(M, d, y.H, y.L, atr))
    Z = Dd.iloc[p - 5:p]; zr = (Z.H - Z.L).replace(0, np.nan); cpos = ((Z.C - Z.L) / zr).to_numpy()
    if np.isfinite(cpos).all():
        add("J09", dl(M, d, y.H if (cpos > 0.5).all() else None, y.L if (cpos < 0.5).all() else None, atr))
    add("J10", dir_sb(M, d, sgn(M.mid_at(nyt(yd, S["c1"])) - M.mid_at(nyt(yd, S["c0"])))))
    s11 = 1 if y.C > yy.H else (-1 if y.C < yy.L else 0)
    if s11:
        add("J11", enter_at(M, s11, w08, dist=atr, x_end=M.x_after(w08, 2)))
    if r.first_wk and pd.notna(r.pwkC) and pd.notna(r.ppwkH):
        s12 = 1 if r.pwkC > r.ppwkH else (-1 if r.pwkC < r.ppwkL else 0)
        wend = last_of(M, p, "wk")
        if s12 and wend is not None:
            add("J12", enter_at(M, s12, w08, dist=atr, x_end=lt(wend, 20, 45)))
    # INTRADAY STRUCTURE
    add("J13", dir_sb(M, d, sgn(M.mid_at(s0 - 60) - M.mid_at(w08))))
    s14 = sgn(M.mid_at(lt(d, 7, 59)) - M.mid_at(o1))
    if s14:
        add("J14", lbx(M, d, s14 > 0, s14 < 0))
    if sr and np.isfinite(o_):
        b5 = M.box(s0, s0 + 300, 4)
        if b5 and b5[0] > b5[1]:
            w5, w1_, xe = s0 + 300, nyt(d, S["w1"]), nyt(d, S["xe"])
            if o_ > sr[0]:
                add("J15", M.level(b5[0], None, w5, w1_, "follow", slU=b5[1], x_end=xe))
            elif o_ < sr[1]:
                add("J15", M.level(None, b5[1], w5, w1_, "follow", slL=b5[0], x_end=xe))
    pc = M.mid_at(nyt(yd, S["c1"]))
    if np.isfinite(o_) and np.isfinite(pc) and abs(o_ - pc) > 0.2 * atr:
        bx = M.rng(s0, b1)
        if bx:
            if o_ > pc and bx[1] > pc:
                add("J16", sb(M, d, True, False))
            elif o_ < pc and bx[0] < pc:
                add("J16", sb(M, d, False, True))
    mo = MORNING[sym]; i0, i1 = M.idx(nyt(d, mo[0])), M.idx(nyt(d, mo[1]))
    if i1 - i0 >= 60:
        x = M.mc[i0:i1]; path = np.abs(np.diff(x)).sum(); er = abs(x[-1] - x[0]) / path if path > 0 else 0.0
        hi, lo = M.mh[i0:i1].max(), M.ml[i0:i1].min(); wa, wb, xe = nyt(d, mo[1]), nyt(d, mo[2]), nyt(d, mo[3])
        if er > 0.4 and hi > lo:
            up = x[-1] > x[0]; mid = (hi + lo) / 2
            add("J17", M.level(hi if up else None, None if up else lo, wa, wb, "follow", slU=mid, slL=mid, x_end=xe))
        if er < 0.15 and hi > lo:
            add("J18", M.level(hi, lo, wa, wb, "fade", dist=0.5 * (hi - lo), x_end=xe))
    sd = SMALLDAY[sym]; q = M.rng(nyt(d, sd[0]), nyt(d, sd[1]))
    if q and q[0] - q[1] < 0.6 * atr:
        add("J19", M.level(q[0], q[1], nyt(d, sd[1]), nyt(d, sd[2]), "follow", dist=0.25 * atr, x_end=nyt(d, sd[3])))
    B = X["B1"]; t0 = B["t0"]
    for b in win_bars(B, lt(d, 9, 0), lt(d, 18, 0)):                     # J20 first H1 inside bar
        if b > 0 and t0[b] - t0[b - 1] == H and B["hh"][b] < B["hh"][b - 1] and B["ll"][b] > B["ll"][b - 1]:
            e0 = t0[b] + H
            add("J20", M.level(B["hh"][b], B["ll"][b], e0, min(e0 + 2 * H, w19), "follow", slU=B["ll"][b], slL=B["hh"][b], x_end=x20))
            break
    Q = X["B15"]; q0 = Q["t0"]
    for b in win_bars(Q, lt(d, 13, 0) - 900, lt(d, 18, 0) - 900):        # J21 double inside M15 (bar b ends 13:00-17:59)
        if b > 1 and q0[b] - q0[b - 2] == 1800 and Q["hh"][b - 1] < Q["hh"][b - 2] and Q["ll"][b - 1] > Q["ll"][b - 2] \
                and Q["hh"][b] < Q["hh"][b - 1] and Q["ll"][b] > Q["ll"][b - 1]:
            e0 = q0[b] + 900; mh_, ml_ = Q["hh"][b - 2], Q["ll"][b - 2]
            add("J21", M.level(mh_, ml_, e0, min(e0 + H, w19), "follow", slU=ml_, slL=mh_, x_end=x20))
            break
    rngs = B["hh"] - B["ll"]
    for b in win_bars(B, lt(d, 9, 0), lt(d, 18, 0)):                     # J22 H1 wide-range bar
        if b >= 20 and rngs[b] > 2 * rngs[b - 20:b].mean() > 0:
            cl = (B["cc"][b] - B["ll"][b]) / rngs[b]
            if cl >= 0.75 or cl <= 0.25:
                s_ = 1 if cl >= 0.75 else -1
                add("J22", enter_at(M, s_, t0[b] + H, stop=(B["hh"][b] + B["ll"][b]) / 2, x_end=x20))
                break
    for b in win_bars(B, lt(d, 9, 0), lt(d, 18, 0)):                     # J23 three-bar momentum (bars ending 10:00-18:59)
        if b >= 3 and t0[b] - t0[b - 3] == 3 * H:
            cc_, hh_, ll_ = B["cc"], B["hh"], B["ll"]
            upm = cc_[b - 2] > hh_[b - 3] and cc_[b - 1] > hh_[b - 2] and cc_[b] > hh_[b - 1]
            dnm = cc_[b - 2] < ll_[b - 3] and cc_[b - 1] < ll_[b - 2] and cc_[b] < ll_[b - 1]
            if upm or dnm:
                s_ = 1 if upm else -1; st_ = ll_[b - 2:b + 1].min() if upm else hh_[b - 2:b + 1].max()
                add("J23", enter_at(M, s_, t0[b] + H, stop=st_, x_end=x20))
                break
    # VOLATILITY / REGIME STATES
    vr = X["vr"][p]
    if np.isfinite(vr) and vr > 1.1:
        add("J25", sb(M, d))
    if np.isfinite(vr) and vr < 0.9:
        add("J26", sb(M, d, mode="fade"))
    if sym == "NSDQ":
        vc = before(X["vix"].close, d, 2)
        if vc is not None:
            ch_ = vc[1] / vc[0] - 1
            add("J27", dir_sb(M, d, 1 if ch_ <= -0.05 else (-1 if ch_ >= 0.08 else 0)))
        vx = X["vix"]
        if d in vx.index:
            k = int(vx.index.get_loc(d))
            if k > 61:
                gaps = (vx.open.iloc[1:k + 1].to_numpy() / vx.close.iloc[:k].to_numpy()) - 1
                g, past = gaps[-1], gaps[max(0, len(gaps) - 251):-1]
                if np.isfinite(g) and len(past) >= 60:
                    lo20, hi20 = np.nanpercentile(past, 20), np.nanpercentile(past, 80)
                    add("J28", dir_sb(M, d, 1 if g <= lo20 else (-1 if g >= hi20 else 0)))
    zz = before(X["zn"], d, 62)
    if zz is not None:
        zr_ = np.diff(zz) / zz[:-1]
        if abs(zr_[-1]) > 2 * zr_[:-1].std(ddof=1):
            add("J29", sb(M, d))
    bx = sbox(M, d)
    if bx and y.atr > 0 and (y.H - y.L) > 1.5 * y.atr and bx[0] - bx[1] < 0.25 * atr:
        add("J30", sb(M, d, box=bx))
    if (Dd.H.iloc[p - 5:p] - Dd.L.iloc[p - 5:p]).mean() < 0.7 * atr:
        add("J31", dl(M, d, y.H, y.L, atr))
    onh = X["on"][max(0, p - 20):p]
    if p >= 20 and np.isfinite(X["on"][p]) and np.isfinite(onh).all() and onh.mean() > 0 and X["on"][p] > 1.5 * onh.mean():
        add("J32", sb(M, d))
    # CROSS-ASSET LEADS
    P = X["P"]
    if sym == "NSDQ":
        bt = P["BTCUSD"]
        if r.wd == 0 and y.wd == 4:
            a_, b_ = bt.mid_at(lt(yd, 16, 0, NYZ)), bt.mid_at(s0 - 60)
            if np.isfinite(a_) and np.isfinite(b_) and a_ > 0:
                mv = b_ / a_ - 1; add("J33", dir_sb(M, d, 1 if mv > 0.02 else (-1 if mv < -0.02 else 0)))
        a_, b_ = bt.mid_at(lt(yd, 16, 0, NYZ)), bt.mid_at(s0 - 60)
        if np.isfinite(a_) and np.isfinite(b_) and a_ > 0:
            mv = b_ / a_ - 1; add("J34", dir_sb(M, d, 1 if mv > 0.01 else (-1 if mv < -0.01 else 0)))
        add("J35", dir_sb(M, d, sgn(P["DAX"].mid_at(lt(d, 14, 29)) - P["DAX"].mid_at(w08))))
        add("J36", dir_sb(M, d, sgn(P["NIKKEI"].mid_at(lt(d, 15, 0, JST)) - P["NIKKEI"].mid_at(lt(d, 9, 0, JST)))))
        add("J37", dir_sb(M, d, sgn(P["USDJPY"].mid_at(lt(d, 14, 29)) - P["USDJPY"].mid_at(w08))))
        hg = before(X["hg"], d, 2)
        if hg is not None:
            add("J39", dir_sb(M, d, sgn(hg[1] - hg[0])))
    else:
        add("J38", dir_sb(M, d, sgn(P["WTI"].mid_at(lt(d, 8, 19, NYZ)) - P["WTI"].mid_at(w08))))
        Ag = P["XAGUSD"].Dd.C
        days = M.days[p - 20:p]
        if all(int(x) in Ag.index for x in days):
            ratio = M.Dd.C.iloc[p - 20:p].to_numpy() / Ag.loc[days].to_numpy()
            add("J40", dir_sb(M, d, 1 if ratio[-1] < ratio.mean() else (-1 if ratio[-1] > ratio.mean() else 0)))
        nq = P["NSDQ"]; nm = sgn(nq.mid_at(lt(d, 9, 59, NYZ)) - nq.mid_at(lt(d, 9, 29, NYZ)))
        gb = M.box(lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ), 20)
        if nm and gb and gb[0] > gb[1]:
            add("J41", M.level(gb[0] if nm < 0 else None, gb[1] if nm > 0 else None, lt(d, 10, 0, NYZ), lt(d, 12, 0, NYZ), "follow",
                               slU=gb[1], slL=gb[0], x_end=lt(d, 15, 55, NYZ)))
        uj = sgn(P["USDJPY"].mid_at(lt(d, 7, 59)) - P["USDJPY"].mid_at(o1))
        if uj:
            add("J42", lbx(M, d, uj < 0, uj > 0))
        cr = M.rng(nyt(d, (8, 20)), nyt(d, (13, 30)))
        if cr and cr[0] > cr[1]:
            hi, lo = cr; mid = (hi + lo) / 2
            add("J50", M.level(hi, lo, nyt(d, (13, 30)), nyt(d, (15, 30)), "follow", slU=mid, slL=mid, x_end=nyt(d, (15, 55)))
                if hi - lo <= atr else M.level(hi, lo, nyt(d, (13, 30)), nyt(d, (15, 30)), "follow", dist=0.5 * atr, x_end=nyt(d, (15, 55))))
    # CALENDAR AND EVENTS
    if sym == "NSDQ":
        fo = X["fomc"]; i = int(np.searchsorted(np.array(fo, dtype="datetime64[ns]"), np.datetime64(d), side="right")) - 1
        even = False
        if i >= 0:
            k = int(np.searchsorted(M.days, int(pd.Timestamp(fo[i]).value // 86400 // 10 ** 9))); kd = p - k
            even = kd in range(0, 4) or kd in range(9, 14) or kd in range(19, 24) or kd in range(29, 34)
        if i + 1 < len(fo) and p + 1 < len(M.days) and int(M.days[p + 1]) == int(pd.Timestamp(fo[i + 1]).value // 86400 // 10 ** 9):
            even = True                                                   # day -1 before the next statement
        if even:
            add("J43", sb(M, d, True, False))
    ev = X["tier1"].get(yd)
    if ev:
        kind = "fomc" if "fomc" in ev else "data"
        rel = (13, 59) if kind == "fomc" else (8, 29); close = (15, 59) if (kind == "fomc" or sym == "NSDQ") else (13, 29)
        add("J44", dir_sb(M, d, sgn(M.mid_at(nyt(yd, close)) - M.mid_at(nyt(yd, rel)))))
    # MORE STRUCTURE
    if bx and bx[0] > bx[1]:
        add("J45", sb(M, d, abs(bx[0] - y.H) <= 0.15 * atr, abs(bx[1] - y.L) <= 0.15 * atr, box=bx)
            if (abs(bx[0] - y.H) <= 0.15 * atr or abs(bx[1] - y.L) <= 0.15 * atr) else None)
    if r.wd in (3, 4):
        wk = Dd[(Dd.wk == r.wk) & (Dd.wd.isin([0, 1]))]
        if len(wk) == 2 and (wk.index < M.days[p]).all():
            add("J46", dl(M, d, wk.H.max(), wk.L.min(), atr, "fade"))
    W = Dd.iloc[p - 21:p - 1]
    if len(W) == 20:
        lo20, ilo = W.L.min(), int(np.argmin(W.L.to_numpy())); hi20, ihi = W.H.max(), int(np.argmax(W.H.to_numpy()))
        old_lo, old_hi = (19 - ilo) >= 3, (19 - ihi) >= 3                    # set >= 4 days before yesterday
        add("J47", dl(M, d, lo20 if (y.C < lo20 and old_lo) else None, hi20 if (y.C > hi20 and old_hi) else None, atr))
    svh = X["sv"][max(0, p - 20):p]
    if p >= 20 and np.isfinite(svh).all() and svh.mean() > 0:
        tgt = 0.12 * svh.mean(); t_, cv_ = X["fut"]; a = int(np.searchsorted(t_, s0))
        j = int(np.searchsorted(cv_, cv_[a] + tgt, side="left")) - 1
        if 0 <= j < len(t_):
            be = int(np.clip(t_[j] + 60, s0 + 300, s0 + 3600))
            b48 = M.box(s0, be, 4)
            if b48 and b48[0] > b48[1]:
                add("J48", M.level(b48[0], b48[1], be, nyt(d, S["w1"]), "follow", slU=b48[1], slL=b48[0], x_end=nyt(d, S["xe"])))
    bull_trap = y.H > yy.H and y.C < yy.H; bear_trap = y.L < yy.L and y.C > yy.L
    add("J49", dl(M, d, y.H if bear_trap else None, y.L if bull_trap else None, atr))
    return out


def holy_grail(M):
    """J24: ADX(14) > 30 trend, a bar touching EMA(20), stop order at its far end for the next 3 bars; exit after 12 H1 bars"""
    out = []; B = bars(M, H); hh, ll, cc, t0 = B["hh"], B["ll"], B["cc"], B["t0"]; D = M.D
    pc = np.r_[cc[0], cc[:-1]]; ph = np.r_[hh[0], hh[:-1]]; pl = np.r_[ll[0], ll[:-1]]
    tr = np.maximum(hh, pc) - np.minimum(ll, pc); up, dn = hh - ph, pl - ll
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    w = lambda x: pd.Series(x).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    at = w(tr); pdi = 100 * w(pdm) / np.maximum(at, 1e-12); ndi = 100 * w(ndm) / np.maximum(at, 1e-12)
    adx = w(100 * np.abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-12)); ema = pd.Series(cc).ewm(span=20, adjust=False).mean().to_numpy()
    busy = -1; b0 = int(np.searchsorted(t0, epoch(START)))
    for b in range(max(b0, 60), len(t0) - 16):
        if t0[b] < busy or adx[b] <= 30:
            continue
        if pdi[b] > ndi[b] and ll[b] <= ema[b] <= hh[b]:
            side, lvl, stp = 1, hh[b], ll[b]
        elif ndi[b] > pdi[b] and ll[b] <= ema[b] <= hh[b]:
            side, lvl, stp = -1, ll[b], hh[b]
        else:
            continue
        i0, i1 = M.idx(t0[b] + H), M.idx(t0[b] + 4 * H)
        if i1 - i0 < 5 or i0 >= M.n or not ((M.mc[i0] < lvl) if side > 0 else (M.mc[i0] > lvl)):
            continue
        nr = ~D["roll"][i0:i1]
        hit = np.flatnonzero(((D["ah"][i0:i1] >= lvl) if side > 0 else (D["bl"][i0:i1] <= lvl)) & nr)
        if not len(hit):
            continue
        k = i0 + int(hit[0]); e = max(lvl, D["ao"][k]) if side > 0 else min(lvl, D["bo"][k])
        ix = M.exit_idx(int((M.t[k] // H) * H + 12 * H))
        if ix is None:
            continue
        res = M.trade(side, k, e, stp, ix)
        if res is not None:
            res.update(idea="J24", sym=M.sym, day=pd.Timestamp(int(M.t[k]) // 86400 * 86400, unit="s")); out.append(res)
            busy = int(M.t[min(ix, M.n - 1)])
    return out


def market(sym, cut=None):
    M, X = context(sym, cut); out = []
    for p in range(len(M.days)):
        if M.days[p] * 86400 < START.timestamp():
            continue
        out += day_ideas(M, p, X)
    out += holy_grail(M)
    T = pd.DataFrame(out)
    return T[T.day >= START] if len(T) else T


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    T = pd.concat([market(s) for s in GNU], ignore_index=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    T = build()
    print(f"trades {len(T)}, {T.day.min().date()}..{T.day.max().date()}")
    c = T.assign(per=np.select([per(T, DEV), per(T, VAL)], ["DEV", "VAL"], "HOLD")).groupby(["idea", "per"]).size().unstack().reindex(IDEAS)
    c["long%"] = (T.groupby("idea").side.apply(lambda s: (s > 0).mean()) * 100).round(0)
    c["stop_sp_med"] = T.groupby("idea").wsp.median().round(0)
    c["markets"] = T.groupby("idea").sym.apply(lambda s: "+".join(sorted(s.unique())))
    pd.set_option("display.width", 200); print(c.to_string())
    rng = np.random.default_rng(18)
    for sym in GNU:
        full = T[T.sym == sym]
        cut = int(rng.uniform(full.t_entry.quantile(.4), full.t_entry.quantile(.8)))
        tr = market(sym, cut); cd = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[full.day < cd][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[tr.day < cd][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')} server, trades entered >= 35 days before the cut {len(a)} vs {len(b)}, identical {same}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("J01", "J06", "J11", "J15", "J17", "J20", "J24", "J28", "J33", "J48"):
        x = T[T.idea == idea]
        if len(x):
            r = x.sample(1, random_state=4).iloc[0]
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens")
            print(f"  hand check {idea} {r.sym} {r.day.date()} entry {loc.tz_convert(LIS):%Y-%m-%d %H:%M} LIS / {loc.tz_convert(NYZ):%H:%M} NY side {r.side:+d} stop width {r.wsp:.0f} spreads")


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
        ok = len(d) >= 100 and mu > 0 and t >= 3.09 and (yrs > 0).sum() >= 2 and mi > 0 and ti >= 2.0
        mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        rows.append(dict(idea=idea, n_dev=len(d), R_dev=mu, t_dev=t, info=mi, t_info=ti, yrs="/".join(f"{q:+.2f}" for q in yrs),
                         win=(d.R > 0).mean(), n_val=len(v), R_val=mv, t_val=tv, dev_pass=ok, val_pass=ok and mv > 0 and tv >= 1.65,
                         nsdq=x[per(x, DEV) & (x.sym == "NSDQ")].R.mean(), gold=x[per(x, DEV) & (x.sym == "XAUUSD")].R.mean()))
    S = pd.DataFrame(rows); pd.set_option("display.width", 260)
    print(S.round(3).to_string(index=False))
    tv_ = S.t_dev.dropna()
    print(f"\nDEV t-values of {len(tv_)} ideas: mean {tv_.mean():+.2f}, sd {tv_.std():.2f}, positive {int((tv_ > 0).sum())}, t>1.65 {int((tv_ > 1.65).sum())}"
          f" (null expectation ~{0.05 * len(tv_):.1f}), t>3.09 {int((tv_ > 3.09).sum())}; DEV-positive means {int((S.R_dev > 0).sum())}")
    passers = S[S.val_pass.fillna(False).astype(bool)].idea.tolist()
    print("DEV + VAL passers:", passers or "none", "-> out-of-time check / hold-out look pending for these (pre-registered order)" if passers else "")
    top = S.dropna(subset=["t_dev"]).nlargest(5, "t_dev").idea.tolist()
    print("account view for the 5 best by DEV t:", top)
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1621)
    for idea in sorted(set(top + passers)):
        x = T[(T.idea == idea) & (T.day < "2026-01-01")]
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        for risk in (250, 500):
            s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
            st, ev, _ = account(r[bi], trd[bi], risk)
            print(f"  {idea} ${risk} ({len(x)} trades 2022-25, {x.R.mean():+.3f} R): " + "  ".join(
                f"{k} pass {100*np.mean((st==1)&(ev<h_)):.1f}% / breach {100*np.mean((st==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27")))
    S.to_csv("forex/ea_research/BRK50B_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
