"""NQ3: the three Nasdaq strategies of the Matio video on MT5 NSDQ data (PREREG_NQ3.md).   env NQ3=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data_mt5"; PT = 20.0                                   # USD per index point for 1 NQ
SLIP = float(os.environ.get("NQ3_SLIP", "0")); FLOOR = float(os.environ.get("NQ3_FLOOR", "0"))                # slippage (points, against us on market fills) and spread floor (points)
W22, DEV, VAL, HOLD = ("2022-01-01", "2022-12-31"), ("2023-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-09-30")


def load():
    d = pd.read_parquet(DATA / "NSDQ_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True)
    ct = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/Chicago"); d = d[ct.notna()].reset_index(drop=True); ct = ct[ct.notna()].reset_index(drop=True)
    d["ct"] = ct.dt.tz_localize(None); d["dn"] = (d.ct.dt.normalize() - pd.Timestamp("1970-01-01")).dt.days; d["hm"] = d.ct.dt.hour * 100 + d.ct.dt.minute
    d["bh"] = np.maximum(d.bo, d.bc); d["sp"] = d.ao - d.bo
    if FLOOR: d["sp"] = np.maximum(d.sp, FLOOR); d["ao"] = d.bo + d.sp
    d["key"] = d.dn * 10000 + d.hm; return d


def adx(h, l, c, n=14):
    h, l, c = pd.Series(h), pd.Series(l), pd.Series(c); pc = c.shift(); tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1); up, dn = h - h.shift(), l.shift() - l
    pdm, mdm = np.where((up > dn) & (up > 0), up, 0.0), np.where((dn > up) & (dn > 0), dn, 0.0); a = 1.0 / n; atr = tr.ewm(alpha=a, adjust=False).mean()
    pdi, mdi = 100 * pd.Series(pdm).ewm(alpha=a, adjust=False).mean() / atr, 100 * pd.Series(mdm).ewm(alpha=a, adjust=False).mean() / atr
    return (100 * (pdi - mdi).abs() / (pdi + mdi)).ewm(alpha=a, adjust=False).mean().values


def bars(d, size):
    mod = (d.hm // 100) * 60 + d.hm % 100; key = (d.dn * 1440 + mod) // size; g = d.groupby(key); idx = d.index.to_series()
    out = pd.DataFrame(dict(i0=idx.groupby(key).min(), i1=idx.groupby(key).max(), h=g.bh.max(), l=g.bl.min(), c=g.bc.last(), dn=g.dn.first(), hm=g.hm.first(), n=g.size())); return out.reset_index(drop=True)


class Ctx:
    def __init__(self):
        d = self.d = load(); self.bo, self.bl, self.bc, self.bh, self.sp, self.ao, self.key, self.hm, self.dn = (d[k].values for k in ("bo", "bl", "bc", "bh", "sp", "ao", "key", "hm", "dn"))
        typ = (d.bh + d.bl + d.bc) / 3.0; self.twap = (typ.groupby(d.dn).cumsum() / (typ.groupby(d.dn).cumcount() + 1)).values
        ses = d[d.hm < 1600].groupby("dn").agg(H=("bh", "max"), L=("bl", "min"), C=("bc", "last")); pc = ses.C.shift(); tr = pd.concat([ses.H - ses.L, (ses.H - pc).abs(), (ses.L - pc).abs()], axis=1).max(axis=1)
        self.a15 = tr.shift(1).rolling(15).mean().to_dict(); self.adx1 = adx(self.bh, self.bl, self.bc); self.starts = np.r_[0, np.nonzero(np.diff(self.dn))[0] + 1]; self.ends = np.r_[self.starts[1:], len(d)]

    def at_or_after(self, dn, hm): i = np.searchsorted(self.key, dn * 10000 + hm, side="left"); return i if i < len(self.key) and self.dn[i] == dn else None

    def walk(self, j0, side, entry, tp, sl, j_exit):
        bo, bl, bh, sp = self.bo, self.bl, self.bh, self.sp; mae = mfe = 0.0; j = j0
        while j <= j_exit:
            if j == j_exit and j > j0: px = (bo[j] - SLIP) if side > 0 else (bo[j] + sp[j] + SLIP); return j, px, "time", mae, mfe
            if side > 0:
                mae, mfe = max(mae, entry - bl[j]), max(mfe, bh[j] - entry)
                if bl[j] <= sl: return j, (bo[j] if bo[j] <= sl else sl) - SLIP, "stop", mae, mfe
                if bh[j] >= tp: return j, (bo[j] if bo[j] >= tp else tp), "target", mae, mfe
            else:
                ah, al, ao_ = bh[j] + sp[j], bl[j] + sp[j], bo[j] + sp[j]; mae, mfe = max(mae, ah - entry), max(mfe, entry - al)
                if ah >= sl: return j, (ao_ if ao_ >= sl else sl) + SLIP, "stop", mae, mfe
                if al <= tp: return j, (ao_ if ao_ <= tp else tp), "target", mae, mfe
            j += 1
        return j_exit, ((bo[j_exit] - SLIP) if side > 0 else (bo[j_exit] + sp[j_exit] + SLIP)), "time", mae, mfe


def rec(cx, name, side, j_in, entry, j_out, px, how, mae, mfe):
    pts = (px - entry) if side > 0 else (entry - px); return dict(strat=name, side=side, entry=cx.d.ct.iat[j_in], exit=cx.d.ct.iat[j_out], dn=int(cx.dn[j_in]), pts=pts, mae=mae, mfe=mfe, how=how)


def s1(cx):
    out = []; b30 = bars(cx.d, 30)
    for dn, grp in b30.groupby("dn"):
        a = cx.a15.get(dn); j0 = cx.at_or_after(dn, 0)
        if a is None or np.isnan(a) or j0 is None or cx.hm[j0] != 0: continue
        N = cx.bo[j0] + 0.30 * a; je = cx.at_or_after(dn, 1430)
        if je is None: continue
        n_tr = 0; busy_until = -1
        for _, b in grp.iterrows():
            if not (930 <= b.hm <= 1330) or b.i0 <= busy_until or n_tr >= 3: continue
            if b.c > N and b.c > cx.twap[int(b.i1)]:
                j_in = int(b.i1) + 1
                if j_in >= len(cx.d) or cx.dn[j_in] != dn or cx.hm[j_in] >= 1430: continue
                entry = cx.ao[j_in] + SLIP; j_out, px, how, mae, mfe = cx.walk(j_in, 1, entry, entry + 40.0, entry - 75.0, je); out.append(rec(cx, "S1", 1, j_in, entry, j_out, px, how, mae, mfe)); n_tr += 1; busy_until = j_out
    return out


def s2(cx):
    out = []
    for s, e in zip(cx.starts, cx.ends):
        dn = cx.dn[s]; hm = cx.hm[s:e]; i830 = s + np.searchsorted(hm, 830); i900 = s + np.searchsorted(hm, 900)
        if i900 - i830 < 20 or e - i900 < 60: continue
        ORH = cx.bh[i830:i900].max(); je = cx.at_or_after(dn, 1555)
        if je is None: continue
        armed = touched = False; j = i900
        while j < min(e, je) - 1:
            if cx.hm[j] > 1550: break
            if not armed and cx.bc[j] > ORH: armed = True
            if armed and cx.bl[j] <= cx.twap[j]: touched = True
            if armed and touched and cx.bc[j] > cx.twap[j] and cx.adx1[j] > 20 and cx.adx1[j] <= cx.adx1[j - 1] and j >= 20:
                j_in = j + 1; entry = cx.ao[j_in] + SLIP; tp, sl = cx.bh[j - 4:j + 1].max(), cx.bl[j - 19:j + 1].min()
                if sl < entry:
                    j_out, px, how, mae, mfe = cx.walk(j_in, 1, entry, max(tp, entry + 0.25), sl, je); out.append(rec(cx, "S2", 1, j_in, entry, j_out, px, how, mae, mfe)); j = j_out
                armed = touched = False
            j += 1
    return out


def s3(cx):
    out = []; b15 = bars(cx.d, 15); adx15 = adx(b15.h.values, b15.l.values, b15.c.values); b15["adx"] = adx15
    for dn, grp in b15.groupby("dn"):
        a = cx.a15.get(dn); jo = cx.at_or_after(dn, 830); jstart = cx.at_or_after(dn - 1, 2300)
        if a is None or np.isnan(a) or jo is None or cx.hm[jo] != 830 or jstart is None or cx.hm[jstart] < 2300: continue
        rng = slice(jstart, jo); hi, lo = cx.bh[rng].max(), cx.bl[rng].min()
        if hi <= lo: continue
        pos = (cx.bo[jo] - lo) / (hi - lo); side = 1 if pos >= 2 / 3 else (-1 if pos <= 1 / 3 else 0)
        if side == 0: continue
        orb = grp[grp.hm == 830]; je = cx.at_or_after(dn, 1430)
        if orb.empty or je is None or orb.n.iloc[0] < 10: continue
        ORH, ORL = orb.h.iloc[0], orb.l.iloc[0]; dist = 0.30 * a
        for _, b in grp.iterrows():
            if not (845 <= b.hm <= 1400) or b.adx <= 20: continue
            if (side > 0 and b.c > ORH) or (side < 0 and b.c < ORL):
                j_in = int(b.i1) + 1
                if j_in >= len(cx.d) or cx.dn[j_in] != dn or cx.hm[j_in] >= 1430: break
                entry = (cx.ao[j_in] + SLIP) if side > 0 else (cx.bo[j_in] - SLIP); tp, sl = (entry + 3 * dist, entry - dist) if side > 0 else (entry - 3 * dist, entry + dist)
                j_out, px, how, mae, mfe = cx.walk(j_in, side, entry, tp, sl, je); out.append(rec(cx, "S3", side, j_in, entry, j_out, px, how, mae, mfe)); break
    return out


def win(df, w): return df[(df.entry >= w[0]) & (df.entry <= pd.Timestamp(w[1]) + pd.Timedelta(days=1))]


def summ(df, w):
    d = win(df, w)
    if d.empty: return dict(n=0)
    u = d.pts * PT; g = u.groupby(d.entry.dt.normalize()).mean(); wn, ls = u[u > 0].sum(), -u[u < 0].sum()
    return dict(n=len(d), win=100 * (u > 0).mean(), avg=u.mean(), pf=wn / ls if ls else np.inf, tot=u.sum(), t=g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan, pts=d.pts.mean())


def f(s): return f"trades {s['n']:4d} | win {s['win']:3.0f}% | avg {s['avg']:+7.0f} USD ({s['pts']:+.1f} pts) | PF {s['pf']:.2f} | total {s['tot']:+10,.0f} | t {s['t']:.2f}" if s["n"] else "no trades"


def daily_series(df, k):
    rows = {}
    for dn, g in df.groupby("dn"):
        g = g.sort_values("entry"); run = 0.0; B = Hi = 0.0
        for _, t in g.iterrows(): B = min(B, run - t.mae * k); Hi = max(Hi, run + t.mfe * k); run += t.pts * k
        rows[dn] = (run, min(B, run), max(Hi, run))
    return pd.DataFrame(rows, index=["V", "B", "Hi"]).T


if __name__ == "__main__":
    mode = os.environ.get("NQ3"); cx = Ctx(); T = {"S1": pd.DataFrame(s1(cx)), "S2": pd.DataFrame(s2(cx)), "S3": pd.DataFrame(s3(cx))}
    if mode == "dry":
        for k, df in T.items(): print(k, "trades", len(df), "2022", len(win(df, W22)), "DEV", len(win(df, DEV)), "VAL", len(win(df, VAL)), "HOLD", len(win(df, HOLD)))
    if mode == "run":
        lines = []
        for k, df in T.items():
            d, v = summ(df, DEV), summ(df, VAL); acc = bool(d["n"] >= 40 and d["avg"] >= 30 and d["pf"] >= 1.2 and d["t"] >= 1.65 and v["avg"] > 0)
            lines.append(f"{k}\n  2022 (reported)  : {f(summ(df, W22))}\n  DEV 2023-24      : {f(d)}\n  VAL 2025         : {f(v)}\n  accepted: {acc}")
            if acc: lines.append(f"  HOLD 2026        : {f(summ(df, HOLD))}")
            lines.append("  exits: " + str(df.how.value_counts().to_dict()) + " | by year (trades, avg USD): " + str({int(y): (len(x), round((x.pts * PT).mean())) for y, x in df.groupby(df.entry.dt.year)}) + "\n")
        os.environ["DA_Z"] = "1.5"
        from mt5broker.ea_research import combo_grid as G, pass70 as P
        Ds = {k: daily_series(df, PT * 0.5) for k, df in T.items()}; idx = sorted(set().union(*[d.index for d in Ds.values()])); D = sum(d.reindex(idx).fillna(0.0) for d in Ds.values())
        lines.append("PORTFOLIO at 0.5 NQ per strategy (5 micro each), daily series, guard 1,500, fresh account, MIX of pools:")
        P.C0 = 0.0
        res = {pool: P.simulate([G.add_dip(G.pair_series(pool, 0, 0, 1500.0), D, 1500.0)] * len(P.MULTS), P.I12, 90) for pool in ("MT5", "FT")}
        for n in (22, 44, 60): lines.append(f"  within {n} business days: pass {50 * sum(np.mean((res[p][0] == 1) & (res[p][1] < n)) for p in res):5.1f}% | breach {50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < n)) for p in res):4.1f}%")
        cor = pd.concat({k: d.V for k, d in Ds.items()}, axis=1).reindex(idx).fillna(0.0).corr(); lines.append("  daily correlation of V between the three strategies:\n" + cor.round(2).to_string())
        tot = D.V; lines.append(f"  portfolio mean per day {tot.mean():.0f} USD over {len(tot)} days; best day {tot.max():.0f}, worst realised day {tot.min():.0f}, worst floating day {D.B.min():.0f}")
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "NQ3_RESULT.txt"), "w").write(txt)
