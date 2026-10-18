"""BRK50: 54 untested breakout ideas (levels, exchange opens, volatility states, cross-asset, calendar, bar channels, crypto) in one
pre-registered round. Pre-registration: forex/ea_research/PREREG_BRK50.md.  --dry-run: counts, truncation test, hand check.  --run."""
import argparse, functools, glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.orbx import ct, CRYPTO
from forex.ea_research.analog import mclass

DATA = "forex/data_mt5/"
CACHE = "C:/work/scratch/brk50_trades.parquet"
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
LIS, NYZ, JST, SYD, UTC = "Europe/London", "America/New_York", "Asia/Tokyo", "Australia/Sydney", "UTC"
H = 3600
ALLS = sorted(os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet"))
NONC = [s for s in ALLS if s not in CRYPTO]
FX = [s for s in NONC if mclass(s) == "fx"]
USD = ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
JPYX = ["AUDJPY", "CADJPY", "CHFJPY", "EURJPY", "GBPJPY", "NZDJPY"]
USIDX = ["DOW", "NSDQ", "SP"]
MET, ENE, CRY = ["XAUUSD", "XAGUSD"], ["BRENT", "WTI"], sorted(CRYPTO)
UNIV = {"I30": [s for s in FX if s.startswith(("EUR", "GBP")) or s.endswith("CHF")] + ["DAX"], "I31": USD + ["XAUUSD"],
        "I32": USD + ["XAUUSD"] + USIDX, "I33": MET, "I34": ENE, "I35": JPYX + ["USDJPY", "NIKKEI"],
        "I36": ["ASX"] + [s for s in FX if s.startswith(("AUD", "NZD"))], "I37": FX + MET, "I38": USIDX + USD + MET, "I39": JPYX,
        "I40": ["DAX", "ASX", "NIKKEI"], "I41": ["USDCAD"], "I42": MET, "I43": USIDX + USD, "I52": CRY, "I53": CRY, "I54": CRY}
IDEAS = [f"I{k:02d}" for k in range(1, 55)]
for i in IDEAS:
    UNIV.setdefault(i, NONC)
PARTNER = {"I39": "NSDQ", "I40": "NSDQ", "I41": "WTI"}


@functools.lru_cache(maxsize=None)
def ts(y, mo, d, h, mi, tz):
    """server-clock epoch seconds of local time y-mo-d h:mi in tz"""
    return int(pd.Timestamp(y, mo, d, h, mi, tz=tz).tz_convert("Europe/Athens").tz_localize(None).timestamp())


class Mkt:
    def __init__(self, sym, cut=None):
        D = load(sym, cut); self.D = D; self.sym = sym
        t = D["t"]; self.t = t; self.n = len(t)
        self.end = cut if cut is not None else int(t[-1]) + 60
        self.mh, self.ml = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2
        self.mc = (D["bc"] + D["ac"]) / 2
        sod = t % 86400; ok = (sod >= H) & (sod < 23 * H)                 # day values exclude the rollover window
        day = t // 86400
        df = pd.DataFrame({"d": day[ok], "h": self.mh[ok], "l": self.ml[ok], "c": self.mc[ok]})
        g = df.groupby("d")
        Dd = pd.DataFrame({"H": g.h.max(), "L": g.l.min(), "C": g.c.last(), "O": g.c.first(), "n": g.size()})
        Dd = Dd[Dd.n >= 300]
        if sym not in CRYPTO:
            Dd = Dd[pd.to_datetime(Dd.index * 86400, unit="s").weekday < 5]
        Dd["atr"] = (Dd.H - Dd.L).shift(1).rolling(20, min_periods=15).mean()
        dt = pd.to_datetime(Dd.index * 86400, unit="s")
        Dd["wk"] = (Dd.index.to_numpy() + 3) // 7; Dd["mo"] = dt.year * 12 + dt.month; Dd["q"] = dt.year * 4 + (dt.month - 1) // 3
        Dd["wd"] = dt.weekday
        self.Dd = Dd; self.days = Dd.index.to_numpy()
        self.pos = {d: i for i, d in enumerate(self.days)}
        for per in ("wk", "mo", "q"):                                     # previous period H / L / C per day
            P = Dd.groupby(per).agg(H=("H", "max"), L=("L", "min"), C=("C", "last"))
            prev = P.shift(1)
            Dd[f"p{per}H"] = Dd[per].map(prev.H); Dd[f"p{per}L"] = Dd[per].map(prev.L); Dd[f"p{per}C"] = Dd[per].map(prev.C)
            Dd[f"pp{per}H"] = Dd[per].map(P.shift(2).H); Dd[f"pp{per}L"] = Dd[per].map(P.shift(2).L)
            Dd[f"first_{per}"] = Dd[per] != Dd[per].shift(1)
            Dd[f"last_{per}"] = Dd[per] != Dd[per].shift(-1)

    # ------------------------------------------------------------------ helpers
    def idx(self, x):
        return int(np.searchsorted(self.t, x))

    def rng(self, a, b):
        i, j = self.idx(a), self.idx(b)
        if j - i < 5:
            return None
        return self.mh[i:j].max(), self.ml[i:j].min()

    def box(self, a, b, need):
        i, j = self.idx(a), self.idx(b)
        if j - i < need:
            return None
        return self.D["bh"][i:j].max(), self.D["bl"][i:j].min()

    def mid_at(self, x):
        i = self.idx(x)
        return self.mc[i] if i < self.n and self.t[i] - x < 600 else np.nan

    def at2045(self, dpos):
        d = pd.Timestamp(int(self.days[dpos]) * 86400, unit="s"); return ts(d.year, d.month, d.day, 20, 45, LIS)

    def x_after(self, T, k):
        """20:45 local of the trading day k days after the day of time T (k = 0: the same day, or the next if T is past 20:45)"""
        p = int(np.searchsorted(self.days, T // 86400, side="right")) - 1
        if p < 0:
            return None
        if T >= self.at2045(p):
            p += 1
        p += k
        return self.at2045(p) if p < len(self.days) else None

    def exit_idx(self, x_end):
        """exclusive end index; exits never in the rollover window (moved to 01:05 server)"""
        if x_end is None or x_end > self.end:
            return None
        j = self.idx(x_end)
        if j <= 0 or j > self.n:
            return None
        k = j - 1
        if self.D["roll"][k]:
            while k < self.n and (self.D["roll"][k] or self.D["sod"][k] < 3900):
                k += 1
            if k >= self.n:
                return None
        return k + 1

    def trade(self, side, kk, e, stop, ix):
        D = self.D
        if kk >= ix - 1 or side * (e - stop) <= 0:
            return None
        risk = abs(e - stop)
        ex, _ = walk(D, side, kk, ix, stop, None)
        f2 = kk + 1; ms = -side
        em = D["ao"][f2] if ms > 0 else D["bo"][f2]
        exm, _ = walk(D, ms, f2, ix, em - ms * risk, None)
        return dict(t_entry=int(self.t[kk]), side=side, R=(ex - e) * side / risk, Rm=(exm - em) * ms / risk,
                    wsp=risk / max(D["sp"][kk], 1e-12))

    def level(self, U, L, w0, w1, mode="follow", slU=None, slL=None, dist=None, x_end=None, xk=None):
        """first touch of U / L in [w0, w1); FOLLOW stop order or FADE at the next minute; stop absolute (slU when U is touched,
        slL when L is touched) or `dist` from the entry; exit at x_end, or (xk = k) at 20:45 of the k-th day after the touch day"""
        D, t = self.D, self.t
        i0, i1 = self.idx(w0), self.idx(w1)
        if i1 - i0 < 5 or i0 >= self.n:
            return None
        m0 = self.mc[i0]
        if U is not None and not (m0 < U):
            U = None
        if L is not None and not (m0 > L):
            L = None
        if U is None and L is None:
            return None
        sl = slice(i0, i1); nr = ~D["roll"][sl]
        up = np.flatnonzero((D["ah"][sl] >= U) & nr) if U is not None else np.array([], int)
        dn = np.flatnonzero((D["bl"][sl] <= L) & nr) if L is not None else np.array([], int)
        ku = i0 + up[0] if len(up) else None; kd = i0 + dn[0] if len(dn) else None
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            return None
        hitU = kd is None or (ku is not None and ku < kd)
        k = ku if hitU else kd
        if mode == "follow":
            side = 1 if hitU else -1; kk = k
            e = max(U, D["ao"][k]) if hitU else min(L, D["bo"][k])
        else:
            side = -1 if hitU else 1; kk = k + 1
            if kk >= self.n or D["roll"][kk]:
                return None
            e = D["bo"][kk] if side < 0 else D["ao"][kk]
        stop = (slU if hitU else slL)
        if stop is None:
            stop = e - side * dist
        xe = x_end if xk is None else self.x_after(int(t[k]), xk)
        ix = self.exit_idx(xe)
        if ix is None:
            return None
        return self.trade(side, kk, e, stop, ix)


def lt(d, h, m, tz=LIS):
    return ts(d.year, d.month, d.day, h, m, tz)


# ---------------------------------------------------------------------- idea definitions (day-based)
def day_ideas(M, p, partners):
    """trades of all day-based ideas for day index p of market M"""
    out = []
    Dd = M.Dd; r = Dd.iloc[p]; d = pd.Timestamp(int(M.days[p]) * 86400, unit="s")
    if p < 1:
        return out
    y = Dd.iloc[p - 1]; atr = r.atr
    if not (atr > 0):
        return out
    sym = M.sym; crypto = sym in CRYPTO
    o1 = int(M.days[p]) * 86400 + H                                     # 01:00 server
    x20, x17 = lt(d, 20, 45), lt(d, 17, 0)
    w08, w19 = lt(d, 8, 0), lt(d, 19, 0)

    def add(idea, res, **kw):
        if res is not None and sym in UNIV[idea]:
            res.update(idea=idea, sym=sym, day=d, **kw); out.append(res)

    if not crypto:
        # I01-I04 PDH / PDL
        add("I01", M.level(y.H, y.L, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
        add("I02", M.level(y.H, y.L, w08, w19, "fade", dist=0.5 * atr, x_end=x20))
        add("I03", h1_close(M, y.H, y.L, w08, w19, 0.5 * atr, x20))
        cp = (y.C - y.L) / (y.H - y.L) if y.H > y.L else np.nan
        if cp >= 0.8:
            add("I04", M.level(y.H, None, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
        elif cp <= 0.2:
            add("I04", M.level(None, y.L, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
        # weekly / monthly / quarterly (on the first trading day of the period)
        if r.first_wk and pd.notna(r.pwkH):
            wend = last_of(M, p, "wk")
            if wend is not None:
                W0, W1 = w08, lt(wend, 19, 0)
                add("I05", M.level(r.pwkH, r.pwkL, W0, W1, "follow", dist=0.5 * atr, x_end=lt(wend, 20, 45)))
                add("I06", M.level(r.pwkH, r.pwkL, W0, W1, "fade", dist=0.5 * atr, xk=0))
                if pd.notna(r.ppwkH) and r.pwkH < r.ppwkH and r.pwkL > r.ppwkL:
                    add("I10", M.level(r.pwkH, r.pwkL, W0, W1, "follow", dist=1.0 * atr, x_end=lt(wend, 20, 45)))
                Pw = (r.pwkH + r.pwkL + r.pwkC) / 3
                add("I15", M.level(2 * Pw - r.pwkL, 2 * Pw - r.pwkH, W0, W1, "follow", dist=0.5 * atr, xk=0))
        if r.first_mo and pd.notna(r.pmoH):
            mend = last_of(M, p, "mo")
            if mend is not None:
                add("I07", M.level(r.pmoH, r.pmoL, w08, lt(mend, 19, 0), "follow", dist=1.0 * atr, xk=5))
                add("I08", M.level(r.pmoH, r.pmoL, w08, lt(mend, 19, 0), "fade", dist=0.5 * atr, xk=0))
        if r.first_q and pd.notna(r.pqH):
            qend = last_of(M, p, "q")
            if qend is not None:
                add("I09", M.level(r.pqH, r.pqL, w08, lt(qend, 19, 0), "follow", dist=1.5 * atr, xk=10))
        # pivots
        P = (y.H + y.L + y.C) / 3; R1, S1 = 2 * P - y.L, 2 * P - y.H; R2, S2 = P + (y.H - y.L), P - (y.H - y.L)
        add("I11", M.level(R1, S1, w08, w19, "follow", slU=P, slL=P, x_end=x20))
        add("I12", M.level(R1, S1, w08, w19, "fade", slU=R2, slL=S2, x_end=x20))
        rg = y.H - y.L
        H4, L4, H3, L3 = y.C + 1.1 * rg / 2, y.C - 1.1 * rg / 2, y.C + 1.1 * rg / 4, y.C - 1.1 * rg / 4
        add("I13", M.level(H4, L4, w08, w19, "follow", slU=H3, slL=L3, x_end=x20))
        add("I14", M.level(H3, L3, w08, w19, "fade", slU=H4, slL=L4, x_end=x20))
        # body, 3-day, outside day, expansion
        bU, bL = max(y.O, y.C), min(y.O, y.C)
        if bU - bL >= 0.1 * atr:
            add("I16", M.level(bU, bL, w08, w19, "follow", slU=bL, slL=bU, x_end=x20))
        if p >= 3:
            h3, l3 = Dd.H.iloc[p - 3:p].max(), Dd.L.iloc[p - 3:p].min()
            add("I17", M.level(h3, l3, w08, w19, "follow", slU=(h3 + l3) / 2, slL=(h3 + l3) / 2, x_end=x20))
        if p >= 2:
            yy = Dd.iloc[p - 2]
            if y.H > yy.H and y.L < yy.L and y.H > y.L:
                if cp >= 0.7:
                    add("I18", M.level(y.H, None, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
                elif cp <= 0.3:
                    add("I18", M.level(None, y.L, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
        if y.atr > 0 and (y.H - y.L) > 1.8 * y.atr:
            add("I19", M.level(y.H, y.L, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
            add("I20", M.level(y.H, y.L, w08, w19, "fade", dist=0.5 * atr, x_end=x20))
        # I21 Crabel stretch
        if p >= 11:
            Z = Dd.iloc[p - 10:p]; stretch = np.minimum(Z.H - Z.O, Z.O - Z.L).mean()
            O = M.mid_at(o1)
            if stretch > 0 and np.isfinite(O):
                add("I21", M.level(O + stretch, O - stretch, o1 + 300, w19, "follow", slU=O, slL=O, x_end=x20))
        # intraday ranges
        m12 = M.rng(o1, lt(d, 12, 0)); m11 = M.rng(o1, lt(d, 11, 0))
        if m12:
            hi, lo = m12
            if hi - lo > 1.0 * atr:
                add("I22", M.level(hi, lo, lt(d, 12, 0), w19, "follow", dist=0.5 * atr, x_end=x20))
            add("I24", M.level(hi, lo, lt(d, 12, 0), w19, "follow", slU=(hi + lo) / 2, slL=(hi + lo) / 2, x_end=x20))
            if r.wd == 4:
                add("I45", M.level(hi, lo, lt(d, 12, 0), w19, "follow", slU=(hi + lo) / 2, slL=(hi + lo) / 2, x_end=x20))
        if m11 and m11[0] - m11[1] < 0.3 * atr:
            hi, lo = m11
            add("I23", M.level(hi, lo, lt(d, 11, 0), w19, "follow", slU=lo, slL=hi, x_end=x20))
        yd = pd.Timestamp(int(M.days[p - 1]) * 86400, unit="s")
        ny = M.rng(lt(yd, 14, 30), lt(yd, 21, 0))
        if ny:
            hi, lo = ny
            if hi - lo <= atr:
                add("I25", M.level(hi, lo, w08, lt(d, 12, 0), "follow", slU=lo, slL=hi, x_end=x17))
            else:
                add("I25", M.level(hi, lo, w08, lt(d, 12, 0), "follow", dist=0.5 * atr, x_end=x17))
        asia = M.rng(lt(d, 1, 0), lt(d, 7, 0)); lbox = M.box(w08, lt(d, 8, 30), 24)
        if asia and asia[0] - asia[1] < 0.25 * atr:
            ah_, al_ = asia
            add("I27", M.level(ah_, al_, lt(d, 7, 0), lt(d, 11, 0), "follow", slU=al_, slL=ah_, x_end=x17))
            if lbox and lbox[0] - lbox[1] < 0.10 * atr:
                add("I26", M.level(lbox[0], lbox[1], lt(d, 8, 30), lt(d, 11, 0), "follow", slU=lbox[1], slL=lbox[0], x_end=x17))
        add("I28", twap(M, d, "follow")); add("I29", twap(M, d, "fade"))
        # exchange opens
        def obox(idea, tz, bh0, bm0, bh1, bm1, wh, wm, xh, xm):
            if sym not in UNIV[idea]:
                return
            b = M.box(lt(d, bh0, bm0, tz), lt(d, bh1, bm1, tz), 20)
            if b and b[0] > b[1]:
                add(idea, M.level(b[0], b[1], lt(d, bh1, bm1, tz), lt(d, wh, wm, tz), "follow", slU=b[1], slL=b[0], x_end=lt(d, xh, xm, tz)))
        obox("I30", LIS, 7, 0, 7, 30, 9, 30, 16, 0)
        obox("I31", NYZ, 8, 0, 8, 30, 10, 0, 16, 0)
        obox("I32", NYZ, 7, 30, 8, 30, 10, 0, 16, 0)
        obox("I33", NYZ, 8, 20, 8, 50, 11, 0, 13, 30)
        obox("I34", NYZ, 9, 0, 9, 30, 11, 30, 14, 30)
        obox("I35", JST, 9, 0, 9, 30, 11, 30, 15, 0)
        obox("I36", SYD, 10, 0, 10, 30, 12, 30, 16, 0)
        obox("I37", LIS, 15, 30, 16, 0, 17, 30, 20, 45)
        obox("I38", NYZ, 12, 0, 13, 30, 15, 0, 15, 55)
        # cross-asset (London box 08:00-08:30, NY box 09:30-10:00 NY)
        if sym in UNIV["I39"] + UNIV["I40"] and lbox and "NSDQ" in partners:
            N = partners["NSDQ"]; mv = N.mid_at(w08) - N.mid_at(o1)
            if np.isfinite(mv) and mv != 0:
                U, L = (lbox[0], None) if mv > 0 else (None, lbox[1])
                res = M.level(U, L, lt(d, 8, 30), lt(d, 11, 0), "follow", slU=lbox[1], slL=lbox[0], x_end=x17)
                add("I39" if sym in UNIV["I39"] else "I40", res)
        if sym == "USDCAD" and "WTI" in partners:
            b = M.box(lt(d, 9, 30, NYZ), lt(d, 10, 0, NYZ), 20)
            if b:
                res = M.level(b[0], b[1], lt(d, 10, 0, NYZ), lt(d, 12, 0, NYZ), "follow", slU=b[1], slL=b[0], x_end=lt(d, 16, 0, NYZ))
                if res is not None:
                    W = partners["WTI"]; mv = W.mid_at(res["t_entry"]) - W.mid_at(lt(d, 9, 30, NYZ))
                    if np.isfinite(mv) and np.sign(mv) == -res["side"]:
                        add("I41", res)
        if sym in MET and lbox and "OTHERMET" in partners:
            res = M.level(lbox[0], lbox[1], lt(d, 8, 30), lt(d, 11, 0), "follow", slU=lbox[1], slL=lbox[0], x_end=x17)
            if res is not None:
                Om = partners["OTHERMET"]; mv = Om.mid_at(res["t_entry"]) - Om.mid_at(lt(d, 8, 30))
                if np.isfinite(mv) and np.sign(mv) == res["side"]:
                    add("I42", res)
        if sym in UNIV["I43"]:
            nb0 = lt(d, 9, 30, NYZ); q = M.rng(w08, nb0); b = M.box(nb0, lt(d, 10, 0, NYZ), 20)
            if q and b and q[0] - q[1] < 0.5 * atr:
                add("I43", M.level(b[0], b[1], lt(d, 10, 0, NYZ), lt(d, 12, 0, NYZ), "follow", slU=b[1], slL=b[0], x_end=lt(d, 16, 0, NYZ)))
        if r.wd == 0 and y.wd == 4:
            add("I44", M.level(y.H, y.L, w08, w19, "follow", dist=0.5 * atr, x_end=x20))
        if lbox:
            add("I46", rebreak(M, lbox, lt(d, 8, 30), lt(d, 11, 0), x17))
            if lbox[0] - lbox[1] >= 0.4 * atr:
                Wb = lbox[0] - lbox[1]
                add("I47", M.level(lbox[0], lbox[1], lt(d, 8, 30), lt(d, 11, 0), "fade", dist=0.5 * Wb, x_end=x17))
    else:
        u0 = lt(d, 0, 0, UTC)
        b = M.box(u0, u0 + H, 40)
        if b and b[0] > b[1]:
            add("I53", M.level(b[0], b[1], u0 + H, lt(d, 8, 0, UTC), "follow", slU=b[1], slL=b[0], x_end=lt(d, 20, 0, UTC)))
        if d.weekday() == 0:
            wk = M.rng(lt(d - pd.Timedelta(days=2), 0, 0, UTC), u0)
            fri = d + pd.Timedelta(days=4)
            if wk:
                hi, lo = wk
                add("I54", M.level(hi, lo, u0, lt(fri, 20, 0, UTC), "follow", slU=(hi + lo) / 2, slL=(hi + lo) / 2, x_end=lt(fri, 20, 0, UTC)))
    return out


def last_of(M, p, per):
    Dd = M.Dd; key = Dd[per].iloc[p]; q = p
    while q + 1 < len(Dd) and Dd[per].iloc[q + 1] == key:
        q += 1
    if not Dd[f"last_{per}"].iloc[q]:
        return None
    return pd.Timestamp(int(M.days[q]) * 86400, unit="s")


def h1_close(M, U, L, w0, w1, dist, x_end):
    D, t = M.D, M.t
    i0, i1 = M.idx(w0), M.idx(w1)
    if i1 - i0 < 60 or not (L < M.mc[i0] < U):
        return None
    hb = t[i0:i1] // H
    st = i0 + np.flatnonzero(np.r_[True, hb[1:] != hb[:-1]])
    for a, b in zip(st, np.r_[st[1:], i1]):
        if b >= i1 and t[i1 - 1] // H == t[b - 1] // H and i1 < M.n and t[i1] // H == t[b - 1] // H:
            break                                                        # last candle not complete inside the window
        c = M.mc[b - 1]
        if c > U or c < L:
            side = 1 if c > U else -1
            k = b
            if k >= M.n or D["roll"][k]:
                return None
            e = D["ao"][k] if side > 0 else D["bo"][k]
            ix = M.exit_idx(x_end)
            return None if ix is None else M.trade(side, k, e, e - side * dist, ix)
    return None


def twap(M, d, mode):
    D, t = M.D, M.t
    a, s9, s16 = M.idx(lt(d, 8, 0)), M.idx(lt(d, 9, 0)), M.idx(lt(d, 16, 0))
    if s16 - a < 200:
        return None
    x = M.mc[a:s16]; n = np.arange(1, len(x) + 1)
    cm = np.cumsum(x) / n; cs = np.sqrt(np.maximum(np.cumsum(x * x) / n - cm ** 2, 0))
    for j in range(s9, s16):
        q = j - a - 1                                                     # stats of the minutes before j
        mu, sd = cm[q], cs[q]
        if sd <= 0 or D["roll"][j]:
            continue
        up, dn = mu + 2 * sd, mu - 2 * sd
        hu, hd = D["ah"][j] >= up, D["bl"][j] <= dn
        if hu and hd:
            return None
        if hu or hd:
            ix = M.exit_idx(lt(d, 17, 0))
            if ix is None:
                return None
            if mode == "follow":
                side = 1 if hu else -1; e = max(up, D["ao"][j]) if hu else min(dn, D["bo"][j])
                return M.trade(side, j, e, mu, ix)
            side = -1 if hu else 1; k = j + 1
            if k >= M.n or D["roll"][k]:
                return None
            e = D["bo"][k] if side < 0 else D["ao"][k]
            return M.trade(side, k, e, mu + 3 * sd if side < 0 else mu - 3 * sd, ix)
    return None


def rebreak(M, box, w0, w1, x_end):
    D, t = M.D, M.t
    hi, lo = box
    i0, i1 = M.idx(w0), M.idx(w1)
    if i1 - i0 < 30:
        return None
    sl = slice(i0, i1)
    up = np.flatnonzero(D["ah"][sl] >= hi); dn = np.flatnonzero(D["bl"][sl] <= lo)
    ku = up[0] if len(up) else None; kd = dn[0] if len(dn) else None
    if (ku is None and kd is None) or (ku is not None and ku == kd):
        return None
    side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
    k1 = i0 + (ku if side > 0 else kd)
    back = np.flatnonzero(M.mh[k1 + 1:i1] < hi) if side > 0 else np.flatnonzero(M.ml[k1 + 1:i1] > lo)
    if not len(back):
        return None
    k2 = k1 + 1 + back[0]
    ag = np.flatnonzero((D["ah"][k2 + 1:i1] >= hi) & ~D["roll"][k2 + 1:i1]) if side > 0 else np.flatnonzero((D["bl"][k2 + 1:i1] <= lo) & ~D["roll"][k2 + 1:i1])
    if not len(ag):
        return None
    k3 = k2 + 1 + ag[0]
    opp = np.flatnonzero(D["bl"][k1:k3] <= lo) if side > 0 else np.flatnonzero(D["ah"][k1:k3] >= hi)
    if len(opp):
        return None                                                       # the other side broke in between: no clean re-break
    e = max(hi, D["ao"][k3]) if side > 0 else min(lo, D["bo"][k3])
    ix = M.exit_idx(x_end)
    return None if ix is None else M.trade(side, k3, e, lo if side > 0 else hi, ix)


# ---------------------------------------------------------------------- bar-close ideas (I48-I52)
def bar_ideas(M):
    out = []; D, t = M.D, M.t; sym = M.sym
    specs = [("I48", H, "keltner", 24), ("I49", H, "boll", 24), ("I50", H, "bfade", 12), ("I51", 4 * H, "donch", 30), ("I52", 4 * H, "donch", 30)]
    for idea, tf, kind, nb in specs:
        if sym not in UNIV[idea]:
            continue
        key = t // tf; st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], M.n]
        hh = np.maximum.reduceat(M.mh, st); ll = np.minimum.reduceat(M.ml, st); cc = M.mc[en - 1]
        pc = np.r_[cc[0], cc[:-1]]; tr = np.maximum(hh, pc) - np.minimum(ll, pc)
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        ema = pd.Series(cc).ewm(span=20, adjust=False).mean().to_numpy()
        sma = pd.Series(cc).rolling(20).mean().to_numpy(); sd = pd.Series(cc).rolling(20).std().to_numpy()
        busy = -1
        for b in range(21, len(st) - nb - 1):
            if b <= busy or not np.isfinite(atr[b]) or atr[b] <= 0:
                continue
            side = 0; kk = None; e = None
            if kind == "keltner":
                u, l_ = ema[b] + 2 * atr[b], ema[b] - 2 * atr[b]; u1, l1 = ema[b - 1] + 2 * atr[b - 1], ema[b - 1] - 2 * atr[b - 1]
                side = 1 if (cc[b] > u and cc[b - 1] <= u1) else (-1 if (cc[b] < l_ and cc[b - 1] >= l1) else 0)
            elif kind == "boll":
                u, l_ = sma[b] + 2 * sd[b], sma[b] - 2 * sd[b]; u1, l1 = sma[b - 1] + 2 * sd[b - 1], sma[b - 1] - 2 * sd[b - 1]
                side = 1 if (cc[b] > u and cc[b - 1] <= u1) else (-1 if (cc[b] < l_ and cc[b - 1] >= l1) else 0)
            elif kind == "bfade":
                u, l_ = sma[b] + 2 * sd[b], sma[b] - 2 * sd[b]; u1, l1 = sma[b - 1] + 2 * sd[b - 1], sma[b - 1] - 2 * sd[b - 1]
                side = -1 if (cc[b - 1] > u1 and cc[b] < u) else (1 if (cc[b - 1] < l1 and cc[b] > l_) else 0)
            if kind in ("keltner", "boll", "bfade"):
                if side == 0:
                    continue
                kk = en[b]
                if kk >= M.n or D["roll"][kk]:
                    continue
                e = D["ao"][kk] if side > 0 else D["bo"][kk]
                stop = e - side * 1.5 * atr[b]; xb = b + 1 + nb
            else:
                U, L = hh[b - 20:b].max(), ll[b - 20:b].min()
                a0, a1 = st[b], en[b]
                if not (L < M.mc[a0] < U):
                    continue
                nr = ~D["roll"][a0:a1]
                up = np.flatnonzero((D["ah"][a0:a1] >= U) & nr); dn = np.flatnonzero((D["bl"][a0:a1] <= L) & nr)
                ku = a0 + up[0] if len(up) else None; kd = a0 + dn[0] if len(dn) else None
                if (ku is None and kd is None) or (ku is not None and ku == kd):
                    continue
                side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                kk = ku if side > 0 else kd; e = max(U, D["ao"][kk]) if side > 0 else min(L, D["bo"][kk])
                stop = e - side * 2 * atr[b - 1]; xb = b + nb
            if xb >= len(st):
                continue
            ix = M.exit_idx(int(t[st[xb]]))
            if ix is None:
                continue
            res = M.trade(side, kk, e, stop, ix)
            if res is not None:
                res.update(idea=idea, sym=sym, day=pd.Timestamp(int(t[kk]) // 86400 * 86400, unit="s")); out.append(res)
                busy = int(np.searchsorted(st, ix, side="right")) - 1
    return out


def market(sym, cut=None):
    M = Mkt(sym, cut); partners = {}
    if sym in UNIV["I39"] + UNIV["I40"]:
        partners["NSDQ"] = Mkt("NSDQ", cut)
    if sym == "USDCAD":
        partners["WTI"] = Mkt("WTI", cut)
    if sym in MET:
        partners["OTHERMET"] = Mkt("XAGUSD" if sym == "XAUUSD" else "XAUUSD", cut)
    out = []
    for p in range(len(M.days)):
        if M.days[p] * 86400 < pd.Timestamp("2022-01-01").timestamp():
            continue
        out += day_ideas(M, p, partners)
    out += bar_ideas(M)
    T = pd.DataFrame(out)
    return T


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    with Pool(4) as pl:
        T = pd.concat(pl.map(market, ALLS), ignore_index=True)
    T = T[T.day >= "2022-01-01"]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    T = build()
    print(f"trades {len(T)}, markets {T.sym.nunique()}, {T.day.min().date()}..{T.day.max().date()}")
    c = T.assign(per=np.select([per(T, DEV), per(T, VAL)], ["DEV", "VAL"], "HOLD")).groupby(["idea", "per"]).size().unstack().reindex(IDEAS)
    c["markets"] = T.groupby("idea").sym.nunique(); c["long%"] = (T.groupby("idea").side.apply(lambda s: (s > 0).mean()) * 100).round(0)
    c["wsp_med"] = T.groupby("idea").wsp.median().round(0)
    print(c.to_string())
    rng = np.random.default_rng(8)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = T[T.sym == sym]
        cut = int(rng.uniform(full.t_entry.quantile(.4), full.t_entry.quantile(.8)))
        tr = market(sym, cut); cd = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=35)
        cols = ["idea", "t_entry", "side", "R", "Rm"]
        a = full[full.day < cd][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        b = tr[tr.day < cd][cols].sort_values(["idea", "t_entry"]).reset_index(drop=True)
        same = len(a) == len(b) and (a[["idea", "t_entry", "side"]].values == b[["idea", "t_entry", "side"]].values).all() and np.allclose(a[["R", "Rm"]], b[["R", "Rm"]])
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')}, trades entered >= 35 days before the cut {len(a)} vs {len(b)}, identical {same}")
        if not same and len(a) and len(b):
            m = a.merge(b, on=["idea", "t_entry", "side"], how="outer", indicator=True)
            print(m[m._merge != "both"].groupby(["idea", "_merge"]).size().head(20).to_string())
    for idea in ("I01", "I05", "I11", "I13", "I21", "I28", "I35", "I46", "I49", "I54"):
        x = T[T.idea == idea]
        if len(x):
            r = x.sample(1, random_state=3).iloc[0]
            print(f"  {idea} {r.sym} entry {pd.Timestamp(r.t_entry, unit='s')} server side {r.side:+d} stop width {r.wsp:.0f} spreads")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T = build()
    rows = []
    for idea in IDEAS:
        x = T[T.idea == idea]
        if not len(x):
            rows.append(dict(idea=idea)); continue
        d, v = x[per(x, DEV)], x[per(x, VAL)]
        mu, t = ct(d) if len(d) > 2 else (np.nan, np.nan)
        inf = d.assign(R=d.R - d.Rm); mi, ti = ct(inf) if len(d) > 2 else (np.nan, np.nan)
        yrs = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 150 and mu > 0 and t >= 3.12 and (yrs > 0).sum() >= 2 and mi > 0 and ti >= 2.0
        mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        okv = ok and mv > 0 and tv >= 1.65
        row = dict(idea=idea, n_dev=len(d), R_dev=mu, t_dev=t, info=mi, t_info=ti, yrs="/".join(f"{q:+.2f}" for q in yrs), win=(d.R > 0).mean(),
                   n_val=len(v), R_val=mv, t_val=tv, dev_pass=ok, val_pass=okv)
        if okv:
            h = x[per(x, HOLD)]; mh_, th = ct(h); row.update(R_hold=mh_, t_hold=th, hold_pass=mh_ > 0 and th >= 1.65)
        rows.append(row)
    S = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(S.round(3).to_string(index=False))
    tv_ = S.t_dev.dropna()
    print(f"\nDEV t-values of {len(tv_)} ideas: mean {tv_.mean():+.2f}, sd {tv_.std():.2f}, positive {int((tv_ > 0).sum())}, t>1.65 {int((tv_ > 1.65).sum())}"
          f" (null expectation ~{0.05*len(tv_):.1f}), t>3.12 {int((tv_ > 3.12).sum())}; DEV-positive ideas {int((S.R_dev > 0).sum())}")
    top = S.dropna(subset=["t_dev"]).nlargest(5, "t_dev").idea.tolist()
    passers = S[S.get("hold_pass", pd.Series(False, index=S.index)).fillna(False).astype(bool)].idea.tolist() if "hold_pass" in S else []
    print("\nfull passers:", passers or "none", "| account view for the 5 best by DEV t:", top)
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1620)
    for idea in sorted(set(top + passers)):
        x = T[(T.idea == idea) & (T.day < "2026-01-01")]
        for label, sel, risk, cap in (("NSDQ+XAUUSD $250", x[x.sym.isin(["NSDQ", "XAUUSD"])], 250, 10), ("universe $50, max 5/day", x, 50, 5)):
            if not len(sel):
                continue
            sel = sel.sort_values("t_entry").groupby("day").head(cap)
            Rd = sel.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
            s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
            st, ev, _ = account(r[bi], trd[bi], risk)
            print(f"  {idea} {label} ({len(sel)} trades 2022-25, {sel.R.mean():+.3f} R): " + "  ".join(
                f"{k} pass {100*np.mean((st==1)&(ev<h_)):.1f}% / breach {100*np.mean((st==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    S.to_csv("forex/ea_research/BRK50_SUMMARY.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
