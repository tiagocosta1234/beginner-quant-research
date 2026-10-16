"""VR round (PREREG_VOLREGIME.md): volatility-regime filter on opening-range breakouts and fades.
python -m forex.ea_research.volregime   -> VOLREGIME_OUTPUT.txt is written by redirecting stdout."""
import glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from zoneinfo import ZoneInfo

SRV = ZoneInfo("Europe/Athens")
SESS = {"LDN": (ZoneInfo("Europe/London"), (8, 0), (11, 0), (17, 0)),
        "NY": (ZoneInfo("America/New_York"), (9, 30), (12, 30), (15, 55))}
DEV_END, VAL_START, VAL_END = "2024-12-31", "2025-01-01", "2026-10-02"


def srv_min(day, tz, hm):
    t = pd.Timestamp(day.year, day.month, day.day, hm[0], hm[1], tz=tz).tz_convert(SRV)
    return t.hour * 60 + t.minute


def exit_r(side, entry, stop, i, bo, bl, bc, ao, ah, ac):
    for k in range(i, len(bo)):
        if side == 1 and bl[k] <= stop:
            return (min(stop, bo[k]) if k > i else stop) - entry
        if side == -1 and ah[k] >= stop:
            return entry - (max(stop, ao[k]) if k > i else stop)
    return (bc[-1] - entry) if side == 1 else (entry - ac[-1])


def run(path):
    sym = os.path.basename(path).replace("_M1_rates.parquet", "")
    d = pd.read_parquet(path)
    dt = pd.to_datetime(d.t, unit="s")
    d["day"] = dt.dt.normalize()
    d["hm"] = (dt.dt.hour * 60 + dt.dt.minute).to_numpy()
    rng = d.groupby("day").agg(h=("bh", "max"), l=("bl", "min"))
    rng = rng[rng.index.weekday < 5]
    dr = (rng.h - rng.l)
    v2 = (dr.rolling(20).mean() / dr.rolling(250).median()).shift(1)          # prior days only
    rows = []
    for day, g in d.groupby("day", sort=True):
        if day.weekday() >= 5:
            continue
        hm = g.hm.to_numpy()
        for sess, (tz, b, e, x) in SESS.items():
            b0, e_last, x_end = srv_min(day, tz, b), srv_min(day, tz, e), srv_min(day, tz, x)
            bm = (hm >= b0) & (hm < b0 + 30)
            if bm.sum() < 25:
                continue
            hi, lo = g.bh.to_numpy()[bm].max(), g.bl.to_numpy()[bm].min()
            am = (hm >= b0 + 30) & (hm < x_end)
            if am.sum() < 10 or hi <= lo:
                continue
            a = g[am]
            H = a.hm.to_numpy()
            bo, bl, bc, ao, ah, ac = (a[c].to_numpy() for c in ("bo", "bl", "bc", "ao", "ah", "ac"))
            for i in range(len(H)):
                if H[i] >= e_last:
                    break
                up, dn = ah[i] >= hi, bl[i] <= lo
                if not (up or dn):
                    continue
                sp = ao[i] - bo[i]
                if up:
                    e_b = max(hi, ao[i]); rb = exit_r(1, e_b, lo, i, bo, bl, bc, ao, ah, ac) / (e_b - lo)
                    e_f = e_b - sp; rf = exit_r(-1, e_f, e_f + (hi - lo), i, bo, bl, bc, ao, ah, ac) / (hi - lo)
                else:
                    e_b = min(lo, bo[i]); rb = exit_r(-1, e_b, hi, i, bo, bl, bc, ao, ah, ac) / (hi - e_b)
                    e_f = e_b + sp; rf = exit_r(1, e_f, e_f - (hi - lo), i, bo, bl, bc, ao, ah, ac) / (hi - lo)
                rows.append((sym, sess, day, hi - lo, v2.get(day, np.nan), rb, rf))
                break
    return rows


def clustered_t(df):
    """Mean R and market-clustered t (cluster = market; sessions of one market share a cluster)."""
    if len(df) < 30:
        return np.nan, np.nan, len(df)
    g = df.groupby("sym").R.agg(["sum", "count"])
    m = df.R.mean()
    resid = df.R - m
    cs = resid.groupby(df.sym).sum()
    G = len(cs)
    se = np.sqrt((cs ** 2).sum() * G / (G - 1)) / len(df) if G > 1 else np.nan
    return m, m / se if se else np.nan, len(df)


def main():
    files = sorted(glob.glob("forex/data_mt5/*_M1_rates.parquet"))
    with Pool(12) as p:
        rows = [r for rs in p.map(run, files) for r in rs]
    t = pd.DataFrame(rows, columns=["sym", "sess", "day", "box", "v2", "R_break", "R_fade"]).sort_values("day")
    t["v1"] = t.groupby(["sym", "sess"]).box.transform(lambda s: s / s.shift(1).rolling(20).median())
    t["period"] = np.where(t.day <= DEV_END, "DEV", np.where((t.day >= VAL_START) & (t.day <= VAL_END), "VAL", "pre"))
    t = t[t.period != "pre"]
    for v in ("v1", "v2"):                                                     # DEV-fixed terciles per stream
        q = t[t.period == "DEV"].groupby(["sym", "sess"])[v].quantile([1 / 3, 2 / 3]).unstack()
        q.columns = ["q1", "q2"]
        tt = t.join(q, on=["sym", "sess"])
        t[v + "_terc"] = np.select([tt[v] <= tt.q1, tt[v] <= tt.q2, tt[v] > tt.q2], ["low", "mid", "high"], "na")
    print(f"rows {len(t):,}; streams {t.groupby(['sym', 'sess']).ngroups * 2}; DEV {t.day[t.period == 'DEV'].min().date()}.."
          f"{DEV_END}, VAL {VAL_START}..{t.day.max().date()}")

    print("\n## 1. Pooled effect (all 46 markets x 2 sessions), mean R per trade [market-clustered t] (n)")
    pooled = []
    for kind in ("break", "fade"):
        for v in ("v1", "v2"):
            for terc in ("low", "mid", "high", "all"):
                row = {"stream": kind, "measure": v, "tercile": terc}
                for per in ("DEV", "VAL"):
                    x = t[(t.period == per) & ((t[v + "_terc"] == terc) if terc != "all" else (t[v + "_terc"] != "na"))]
                    m, tc, n = clustered_t(x.assign(R=x["R_" + kind]))
                    row[per] = f"{m:+.3f} [{tc:+.2f}] ({n})"
                    row[per + "_m"], row[per + "_t"] = m, tc
                pooled.append(row)
    P = pd.DataFrame(pooled)
    print(P[["stream", "measure", "tercile", "DEV", "VAL"]].to_string(index=False))
    passes = []
    for (kind, v), g in P[P.tercile != "all"].groupby(["stream", "measure"]):
        bd, bv = g.loc[g.DEV_m.idxmax()], g.loc[g.VAL_m.idxmax()]
        ok = bd.tercile == bv.tercile and bv.VAL_m > 0 and bv.VAL_t >= 2
        passes.append(f"{kind}/{v}: best DEV tercile {bd.tercile}, best VAL tercile {bv.tercile}, "
                      f"VAL {bv.VAL_m:+.3f} t {bv.VAL_t:+.2f} -> {'PASS' if ok else 'fail'}")
    print("\n".join(passes))

    print("\n## 2. Cell selection: 184 streams x 2 measures x 3 terciles = 1,104 cells")
    cells = []
    for (sym, sess), g in t.groupby(["sym", "sess"]):
        for kind in ("break", "fade"):
            for v in ("v1", "v2"):
                for terc in ("low", "mid", "high"):
                    x = g[g[v + "_terc"] == terc]
                    dv, vl = x[x.period == "DEV"]["R_" + kind], x[x.period == "VAL"]["R_" + kind]
                    if len(dv) < 2:
                        continue
                    cells.append(dict(sym=sym, sess=sess, kind=kind, measure=v, terc=terc, dev_n=len(dv), dev_m=dv.mean(),
                                      dev_t=dv.mean() / dv.std() * np.sqrt(len(dv)), val_n=len(vl), val_m=vl.mean(),
                                      val_t=vl.mean() / vl.std() * np.sqrt(len(vl)) if len(vl) > 2 else np.nan))
    C = pd.DataFrame(cells)
    dev_pass = C[(C.dev_t >= 3.9) & (C.dev_n >= 60)]
    both = dev_pass[(dev_pass.val_m > 0) & (dev_pass.val_t >= 2)]
    print(f"cells: {len(C)}; DEV passes (t >= 3.9, n >= 60): {len(dev_pass)}; DEV+VAL passes: {len(both)}")
    print("top 8 cells by DEV t, with VAL:")
    print(C.sort_values("dev_t", ascending=False).head(8).round(3).to_string(index=False))
    print(f"\ncells with DEV t >= 2: {int((C.dev_t >= 2).sum())} (expected by chance ~{0.023 * len(C):.0f}); their VAL mean "
          f"{C[C.dev_t >= 2].val_m.mean():+.3f}, share VAL > 0: {(C[C.dev_t >= 2].val_m > 0).mean():.0%}")
    if len(dev_pass):
        print(dev_pass.round(3).to_string(index=False))

    print("\n## 3. Flagships by tercile (mean R, n)")
    for sym, sess, kind in (("USDJPY", "LDN", "break"), ("EURJPY", "LDN", "fade")):
        g = t[(t.sym == sym) & (t.sess == sess)]
        for v in ("v1", "v2"):
            parts = []
            for terc in ("low", "mid", "high"):
                for per in ("DEV", "VAL"):
                    x = g[(g.period == per) & (g[v + "_terc"] == terc)]["R_" + kind]
                    parts.append(f"{terc}/{per} {x.mean():+.3f} ({len(x)})")
            print(f"{sym} {sess} {kind} {v}: " + "  ".join(parts))
    C.to_csv("D:/finance/scratch/volregime_cells.csv", index=False)


if __name__ == "__main__":
    main()
