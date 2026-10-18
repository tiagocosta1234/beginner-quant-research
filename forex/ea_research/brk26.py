"""BRK26: 26 more new breakout concepts (named indicators and price-action patterns) on the 38 non-crypto MT5, BRK30's
machinery. Pre-registration: forex/ea_research/PREREG_BRK26.md.   python -m forex.ea_research.brk26 --dry-run | --run"""
import argparse, os, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.brk50 import Mkt, lt, LIS, NYZ, H, DEV, VAL, HOLD, NONC
from forex.ea_research.orbx import ct
from forex.ea_research.brk30 import (ema, sma, wilder, rmax, rmin, true_range, rsi, cross_up, cross_dn, bc_trades, bs_trade,
                                  enter_at, tag, epoch, ichimoku)

CACHE = "C:/work/scratch/brk26_trades.parquet"
IDEAS = [f"P{k:02d}" for k in range(1, 27)]
START = pd.Timestamp("2022-01-01")


def bars(M, tf):
    key = M.t // tf; st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], M.n]
    B = dict(st=st, en=en, oo=(M.D["bo"][st] + M.D["ao"][st]) / 2, hh=np.maximum.reduceat(M.mh, st), ll=np.minimum.reduceat(M.ml, st),
             cc=M.mc[en - 1], t0=key[st] * tf)
    B["atr"] = sma(true_range(B["hh"], B["ll"], B["cc"]), 14)
    return B


def sig(up, dn):
    return np.where(up, 1, np.where(dn, -1, 0))


def lag(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


def wma(x, n):
    w = np.arange(1, n + 1, dtype=float)
    return pd.Series(x).rolling(n, min_periods=n).apply(lambda a: np.dot(a, w) / w.sum(), raw=True).to_numpy()


def reg_slope(y, n=20):
    s = pd.Series(y.astype(float)); xbar = (n - 1) / 2; sxx = ((np.arange(n) - xbar) ** 2).sum()
    return s.rolling(n, min_periods=n).apply(lambda a: np.dot(np.arange(n) - xbar, a - a.mean()) / sxx, raw=True).to_numpy()


def fisher(hh, ll, n=10):
    mp = (hh + ll) / 2; mx, mn = rmax(mp, n), rmin(mp, n); v = np.zeros(len(mp)); f = np.zeros(len(mp))
    for i in range(1, len(mp)):
        if not (np.isfinite(mx[i]) and mx[i] > mn[i]):
            v[i], f[i] = v[i - 1], f[i - 1]; continue
        v[i] = np.clip(0.66 * ((mp[i] - mn[i]) / (mx[i] - mn[i]) - 0.5) + 0.67 * v[i - 1], -0.999, 0.999)
        f[i] = 0.5 * np.log((1 + v[i]) / (1 - v[i])) + 0.5 * f[i - 1]
    return f


def smooth_half(x):
    out = np.full(len(x), np.nan); prev = np.nan
    for i, v in enumerate(x):
        if np.isfinite(v):
            prev = v if not np.isfinite(prev) else prev + 0.5 * (v - prev)
        out[i] = prev
    return out


def stoch_of(x, n):
    lo, hi = rmin(x, n), rmax(x, n)
    return 100 * (x - lo) / np.where(hi - lo > 0, hi - lo, np.nan)


def bs_loop(M, B, cand, fn, idea):
    out = []; busy = -1; b0 = int(np.searchsorted(B["t0"], epoch(START)))
    for b in cand:
        if b < max(b0, 60) or b <= busy:
            continue
        res, ix = fn(b)
        if res is not None:
            res["idea"] = idea; out.append(res); busy = int(np.searchsorted(B["t0"], M.t[min(ix, M.n - 1)], side="right")) - 1
    return out


def bar_ideas(M):
    out = []; B1, B4 = bars(M, H), bars(M, 4 * H)
    for B, k, N, tag_ in ((B4, 2, 30, "H4"), (B1, 1.5, 24, "H1")):
        hh, ll, cc, oo = B["hh"], B["ll"], B["cc"], B["oo"]; mp = (hh + ll) / 2
        if tag_ == "H4":
            e3 = ema(ema(ema(cc, 15), 15), 15); trix = 100 * (e3 / lag(e3, 1) - 1)
            out += bc_trades(M, B, sig(cross_up(trix, 0 * trix), cross_dn(trix, 0 * trix)), k, N, "P01")
            pc, ph, pl = lag(cc, 1), lag(hh, 1), lag(ll, 1); tr = np.maximum(hh, pc) - np.minimum(ll, pc)
            vp = pd.Series(np.abs(hh - pl)).rolling(14).sum().to_numpy(); vm = pd.Series(np.abs(ll - ph)).rolling(14).sum().to_numpy()
            st_ = pd.Series(tr).rolling(14).sum().to_numpy(); vip, vim = vp / st_, vm / st_
            out += bc_trades(M, B, sig(cross_up(vip, vim), cross_dn(vip, vim)), k, N, "P03")
            bp = cc - np.minimum(ll, pc); a7, a14, a28 = (pd.Series(bp).rolling(n).sum().to_numpy() / pd.Series(tr).rolling(n).sum().to_numpy() for n in (7, 14, 28))
            uo = 100 * (4 * a7 + 2 * a14 + a28) / 7
            out += bc_trades(M, B, sig(cross_up(uo, np.full_like(uo, 70.0)), cross_dn(uo, np.full_like(uo, 30.0))), k, N, "P05")
            f = fisher(hh, ll); trig = lag(f, 1); lo_prev, hi_prev = lag(f, 1) < -1.5, lag(f, 1) > 1.5
            out += bc_trades(M, B, sig(cross_up(f, trig) & lo_prev, cross_dn(f, trig) & hi_prev), k, N, "P06")
            r9 = ema(hh - ll, 9); mi = pd.Series(r9 / ema(r9, 9)).rolling(25).sum().to_numpy()
            bulge = pd.Series(mi > 27).rolling(10, min_periods=1).max().shift(1).fillna(0).to_numpy().astype(bool)
            rev = bulge & cross_dn(mi, np.full_like(mi, 26.5)); e9 = ema(cc, 9); slope = e9 - lag(e9, 1)
            out += bc_trades(M, B, sig(rev & (slope > 0), rev & (slope < 0)), k, N, "P07")
            e13 = ema(cc, 13); bull, bear = hh - e13, ll - e13
            longs = (e13 > lag(e13, 1)) & (bull > 0) & (bull > lag(bull, 1)); shorts = (e13 < lag(e13, 1)) & (bear < 0) & (bear < lag(bear, 1))
            atr = B["atr"]
            out += bs_loop(M, B, np.flatnonzero((longs | shorts) & (atr > 0)), lambda b: bs_trade(M, B, b, hh[b] if longs[b] else None,
                                                                                                ll[b] if (shorts[b] and not longs[b]) else None, None, None, 1, 30, "P10", dist=2 * atr[b]), "P10")
            hma = wma(2 * wma(cc, 27) - wma(cc, 55), 7); d1, d0 = hma - lag(hma, 1), lag(hma, 1) - lag(hma, 2)
            out += bc_trades(M, B, sig((d1 > 0) & (d0 <= 0), (d1 < 0) & (d0 >= 0)), k, N, "P11")
            ao = sma(mp, 5) - sma(mp, 34)
            out += bc_trades(M, B, sig(cross_up(ao, 0 * ao), cross_dn(ao, 0 * ao)), k, N, "P15")
            ten = (rmax(hh, 9) + rmin(ll, 9)) / 2; kij = (rmax(hh, 26) + rmin(ll, 26)) / 2; sa, sb = (ten + kij) / 2, (rmax(hh, 52) + rmin(ll, 52)) / 2
            _, _, top, bot = ichimoku(hh, ll)
            out += bc_trades(M, B, sig(cross_up(sa, sb) & (cc > top), cross_dn(sa, sb) & (cc < bot)), k, N, "P17")
            er = ema(hh - ll, 10); cv = 100 * (er / lag(er, 10) - 1); clv = (cc - ll) / np.where(hh > ll, hh - ll, np.nan)
            ex = cross_up(cv, np.full_like(cv, 50.0))
            out += bc_trades(M, B, sig(ex & (clv >= 0.75), ex & (clv <= 0.25)), k, N, "P18")
            sl = reg_slope(cc, 20)
            out += bc_trades(M, B, sig(cross_up(sl, 0 * sl), cross_dn(sl, 0 * sl)), k, N, "P19")
            m = ema(cc, 23) - ema(cc, 50); stc = smooth_half(stoch_of(smooth_half(stoch_of(m, 10)), 10))
            out += bc_trades(M, B, sig(cross_up(stc, np.full_like(stc, 25.0)), cross_dn(stc, np.full_like(stc, 75.0))), k, N, "P20")
            co, hl = cc - oo, hh - ll
            num = (co + 2 * lag(co, 1) + 2 * lag(co, 2) + lag(co, 3)) / 6; den = (hl + 2 * lag(hl, 1) + 2 * lag(hl, 2) + lag(hl, 3)) / 6
            rvi = sma(num, 10) / np.where(sma(den, 10) > 0, sma(den, 10), np.nan); rs = (rvi + 2 * lag(rvi, 1) + 2 * lag(rvi, 2) + lag(rvi, 3)) / 6
            out += bc_trades(M, B, sig(cross_up(rvi, rs), cross_dn(rvi, rs)), k, N, "P21")
            bop = sma(co / np.where(hl > 0, hl, np.nan), 14)
            out += bc_trades(M, B, sig(cross_up(bop, np.full_like(bop, 0.2)), cross_dn(bop, np.full_like(bop, -0.2))), k, N, "P22")
            blag = lambda x, k: np.r_[np.zeros(k, bool), x[:-k]]                 # boolean lag (gaps are False, not NaN)
            down0, up0 = blag(cc < oo, 2), blag(cc > oo, 2)
            tbr_u = down0 & (lag(ll, 1) < lag(ll, 2)) & (cc > oo) & (cc > lag(hh, 2))
            tbr_d = up0 & (lag(hh, 1) > lag(hh, 2)) & (cc < oo) & (cc < lag(ll, 2))
            out += bc_trades(M, B, sig(tbr_u, tbr_d), k, N, "P24")
            maru = (np.abs(co) >= 0.9 * hl) & (hl >= atr) & (atr > 0)
            out += bs_loop(M, B, np.flatnonzero(maru), lambda b: bs_trade(M, B, b, hh[b] if co[b] > 0 else None, ll[b] if co[b] < 0 else None,
                                                                           ll[b], hh[b], 2, 30, "P25"), "P25")
        else:
            e3 = ema(ema(ema(cc, 15), 15), 15); trix = 100 * (e3 / lag(e3, 1) - 1); ts_ = ema(np.nan_to_num(trix), 9)
            out += bc_trades(M, B, sig(cross_up(trix, ts_) & (trix > 0), cross_dn(trix, ts_) & (trix < 0)), k, N, "P02")
            d = np.diff(cc, prepend=cc[0]); su = pd.Series(np.maximum(d, 0)).rolling(14).sum().to_numpy(); sd = pd.Series(np.maximum(-d, 0)).rolling(14).sum().to_numpy()
            cmo = 100 * (su - sd) / np.where(su + sd > 0, su + sd, np.nan)
            out += bc_trades(M, B, sig(cross_up(cmo, np.full_like(cmo, 50.0)), cross_dn(cmo, np.full_like(cmo, -50.0))), k, N, "P04")
            t1 = ema(cc, 20); t2 = ema(t1, 20); t3 = ema(t2, 20); tema = 3 * t1 - 3 * t2 + t3
            out += bc_trades(M, B, sig(cross_up(cc, tema), cross_dn(cc, tema)), k, N, "P12")
            wr = -100 * (rmax(hh, 14) - cc) / np.where(rmax(hh, 14) - rmin(ll, 14) > 0, rmax(hh, 14) - rmin(ll, 14), np.nan)
            lo5 = pd.Series(wr).shift(1).rolling(5, min_periods=5).min().to_numpy(); hi5 = pd.Series(wr).shift(1).rolling(5, min_periods=5).max().to_numpy()
            out += bc_trades(M, B, sig(cross_up(wr, np.full_like(wr, -20.0)) & (lo5 < -80), cross_dn(wr, np.full_like(wr, -80.0)) & (hi5 > -20)), k, N, "P13")
            r_ = rsi(cc); kk = sma(stoch_of(r_, 14), 3)
            lo10 = pd.Series(kk).shift(1).rolling(10, min_periods=10).min().to_numpy(); hi10 = pd.Series(kk).shift(1).rolling(10, min_periods=10).max().to_numpy()
            out += bc_trades(M, B, sig(cross_up(kk, np.full_like(kk, 80.0)) & (lo10 < 20), cross_dn(kk, np.full_like(kk, 20.0)) & (hi10 > 80)), k, N, "P14")
            out += high2(M, B)
    return out


def high2(M, B):
    """P26 Al Brooks High 2 / Low 2 on H1"""
    out = []; hh, ll, cc, atr, t0 = B["hh"], B["ll"], B["cc"], B["atr"], B["t0"]; e20 = ema(cc, 20)
    busy = -1; b0 = int(np.searchsorted(t0, epoch(START))); state = dict(dir=0, swing=None, plow=None, cnt=0, in_pb=False)
    for b in range(2, len(cc) - 26):
        up = cc[b] > e20[b] and e20[b] > e20[b - 1]; dn = cc[b] < e20[b] and e20[b] < e20[b - 1]
        d_ = 1 if up else (-1 if dn else 0)
        if d_ != state["dir"]:
            state = dict(dir=d_, swing=hh[b] if d_ > 0 else ll[b], plow=None, cnt=0, in_pb=False); continue
        if d_ == 0:
            continue
        if d_ > 0:
            if hh[b] > state["swing"]:
                state.update(swing=hh[b], plow=None, cnt=0, in_pb=False); continue
            if hh[b] < hh[b - 1]:
                state["in_pb"] = True
            state["plow"] = ll[b] if state["plow"] is None else min(state["plow"], ll[b])
            if state["in_pb"] and hh[b] > hh[b - 1]:
                state["cnt"] += 1
                if state["cnt"] == 2 and b >= max(b0, 60) and b > busy and atr[b] > 0:
                    res, ix = bs_trade(M, B, b, hh[b], None, state["plow"], None, 1, 24, "P26")
                    if res is not None:
                        res["idea"] = "P26"; out.append(res); busy = int(np.searchsorted(t0, M.t[min(ix, M.n - 1)], side="right")) - 1
                    state.update(cnt=0, in_pb=False)
        else:
            if ll[b] < state["swing"]:
                state.update(swing=ll[b], plow=None, cnt=0, in_pb=False); continue
            if ll[b] > ll[b - 1]:
                state["in_pb"] = True
            state["plow"] = hh[b] if state["plow"] is None else max(state["plow"], hh[b])
            if state["in_pb"] and ll[b] < ll[b - 1]:
                state["cnt"] += 1
                if state["cnt"] == 2 and b >= max(b0, 60) and b > busy and atr[b] > 0:
                    res, ix = bs_trade(M, B, b, None, ll[b], None, state["plow"], 1, 24, "P26")
                    if res is not None:
                        res["idea"] = "P26"; out.append(res); busy = int(np.searchsorted(t0, M.t[min(ix, M.n - 1)], side="right")) - 1
                    state.update(cnt=0, in_pb=False)
    return out


def day_ideas(M):
    out = []; Dd = M.Dd; Hd, Ld, Cd, Od = (Dd[c].to_numpy() for c in ("H", "L", "C", "O"))
    dpo = Cd - lag(sma(Cd, 20), 11); s08 = sig(cross_up(dpo, 0 * dpo), cross_dn(dpo, 0 * dpo))
    roc = lambda n: 100 * (Cd / lag(Cd, n) - 1)
    kst = sma(roc(10), 10) + 2 * sma(roc(15), 10) + 3 * sma(roc(20), 10) + 4 * sma(roc(30), 15); ks = sma(kst, 9)
    s09 = sig(cross_up(kst, ks), cross_dn(kst, ks))
    c4 = lag(Cd, 4); bset = pd.Series((Cd < c4).astype(int)).rolling(9).sum().to_numpy() == 9; sset = pd.Series((Cd > c4).astype(int)).rolling(9).sum().to_numpy() == 9
    busy = {}; orders = []                                                     # TDST orders: (level, side, last day index)
    for p in range(60, len(M.days)):
        d = pd.Timestamp(int(M.days[p]) * 86400, unit="s")
        if d < START:
            continue
        atr = Dd.atr.iloc[p]
        if not (atr > 0):
            continue
        w08, w19, x20 = lt(d, 8, 0), lt(d, 19, 0), lt(d, 20, 45)

        def add(idea, res, xe=None):
            if res is not None:
                res.update(idea=idea, sym=M.sym, day=d); out.append(res)
                if xe is not None:
                    ix = M.exit_idx(xe); busy[idea] = int(M.t[min(ix, M.n - 1)]) if ix else 0
        for idea, s_, stp, k in (("P08", s08, 1.0, 4), ("P09", s09, 1.5, 9)):
            s = int(s_[p - 1])
            if s and busy.get(idea, 0) <= w08:
                xe = M.x_after(w08, k); add(idea, enter_at(M, s, w08, dist=stp * atr, x_end=xe), xe)
        if bset[p - 1] and not bset[p - 2] and not np.isnan(c4[p - 1]):      # the day the count first reaches 9
            orders.append([Hd[p - 9:p].max(), 1, p + 9])
        if sset[p - 1] and not sset[p - 2] and not np.isnan(c4[p - 1]):
            orders.append([Ld[p - 9:p].min(), -1, p + 9])
        keep = []
        for lvl, side, last in orders:
            if p > last:
                continue
            if busy.get("P16", 0) > w08:
                keep.append([lvl, side, last]); continue
            res = M.level(lvl if side > 0 else None, lvl if side < 0 else None, w08, w19, "follow", dist=atr, xk=4)
            if res is not None:
                add("P16", res, M.x_after(res["t_entry"], 4))
            else:
                keep.append([lvl, side, last])
        orders = keep
        if p >= 4:
            ins = lambda i: Hd[i] < Hd[i - 1] and Ld[i] > Ld[i - 1]; outs = lambda i: Hd[i] > Hd[i - 1] and Ld[i] < Ld[i - 1]
            if ins(p - 3) and outs(p - 2) and ins(p - 1):
                add("P23", M.level(Hd[p - 1], Ld[p - 1], w08, w19, "follow", dist=0.5 * atr, x_end=x20))
    return out


def market(args):
    sym, cut = args
    M = Mkt(sym, cut); out = day_ideas(M) + bar_ideas(M)
    T = pd.DataFrame(out)
    if len(T):
        T["sym"] = sym; T = T[T.day >= START] if "day" in T else T
    return T


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
    c["mkts"] = T.groupby("idea").sym.nunique(); c["long%"] = (T.groupby("idea").side.apply(lambda s: (s > 0).mean()) * 100).round(0)
    c["stop_sp"] = T.groupby("idea").wsp.median().round(0); pd.set_option("display.width", 200); print(c.to_string())
    rng = np.random.default_rng(26)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = T[T.sym == sym]; cut = int(rng.uniform(full.t_entry.quantile(.4), full.t_entry.quantile(.8)))
        tr = market((sym, cut)); cdy = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[full.day < cdy][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[tr.day < cdy][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')} server, trades >= 35 days before the cut {len(a)} vs {len(b)}, identical {same}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("P01", "P06", "P10", "P16", "P20", "P23", "P25", "P26"):
        x = T[T.idea == idea]
        if len(x):
            r = x.sample(1, random_state=9).iloc[0]; loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens")
            print(f"  hand check {idea} {r.sym} entry {loc.tz_convert(LIS):%Y-%m-%d %H:%M} LIS side {r.side:+d} stop {r.wsp:.0f} spreads")


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
        ok = len(d) >= 150 and mu > 0 and t >= 2.89 and (yrs > 0).sum() >= 2 and mi > 0 and ti >= 2.0
        mv_, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        row = dict(idea=idea, n_dev=len(d), R_dev=mu, t_dev=t, info=mi, t_info=ti, yrs="/".join(f"{q:+.2f}" for q in yrs), win=(d.R > 0).mean(),
                   n_val=len(v), R_val=mv_, t_val=tv, dev_pass=ok, val_pass=ok and mv_ > 0 and tv >= 1.65)
        if row["val_pass"]:
            h = x[per(x, HOLD)]; mh, th = ct(h); row.update(R_hold=mh, t_hold=th, hold_pass=mh > 0 and th >= 1.65)
        rows.append(row)
    S = pd.DataFrame(rows); pd.set_option("display.width", 240); print(S.round(3).to_string(index=False))
    tv_ = S.t_dev.dropna()
    print(f"\nDEV t-values of {len(tv_)} ideas: mean {tv_.mean():+.2f}, sd {tv_.std():.2f}, positive {int((tv_ > 0).sum())}, t>1.65 {int((tv_ > 1.65).sum())}"
          f" (null ~{0.05 * len(tv_):.1f}), t>2.89 {int((tv_ > 2.89).sum())}")
    passers = S[S.get("hold_pass", pd.Series(False, index=S.index)).fillna(False).astype(bool)].idea.tolist() if "hold_pass" in S else []
    print("DEV + VAL passers:", S[S.val_pass.fillna(False).astype(bool)].idea.tolist() or "none", "| full passers:", passers or "none")
    top = S.dropna(subset=["t_dev"]).nlargest(5, "t_dev").idea.tolist(); print("account view for the 5 best by DEV t:", top)
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1726)
    for idea in sorted(set(top + passers)):
        x = T[(T.idea == idea) & (T.day < "2026-01-01")].sort_values("t_entry").groupby("day").head(5)
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); rr = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(rr) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st_, ev, _ = account(rr[bi], trd[bi], 50)
        print(f"  {idea} universe $50, max 5/day ({len(x)} trades 2022-25, {x.R.mean():+.3f} R): " + "  ".join(
            f"{k} pass {100*np.mean((st_==1)&(ev<h_)):.1f}% / breach {100*np.mean((st_==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    S.to_csv("forex/ea_research/BRK26_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
