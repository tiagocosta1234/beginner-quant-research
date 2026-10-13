"""FXS: intraday session scan over the 28 MT5 FX pairs (PREREG_FX_SESSIONS.md).   env FXS=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path
from forex.ea_research import setup_scan as SC, fincept_mt5_verify as V

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
NONFX = {"SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX", "XAUUSD", "XAGUSD", "WTI", "BRENT", "BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD", "XRPUSD", "ADAUSD", "BNBUSD", "BCHUSD"}
PAIRS = sorted(p.name.split("_M1_rates")[0] for p in DATA.glob("*_M1_rates.parquet") if p.name.split("_M1_rates")[0] not in NONFX)


def load(m):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True)
    utc = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.tz_localize(None); ok = utc.notna(); d = d[ok].reset_index(drop=True); utc = utc[ok].reset_index(drop=True)
    sp = (d.ao - d.bo).values; real = (utc >= "2025-10-01").values; floor = float(np.median(sp[real])) if real.sum() > 1000 else float(np.median(sp)); sp = np.maximum(sp, floor)
    bo, bl, bc = d.bo.values, d.bl.values, d.bc.values; bh = np.maximum(bo, bc); ud = ((utc - pd.Timestamp("1970-01-01")).dt.days).values; um = (utc.dt.hour * 60 + utc.dt.minute).values
    return dict(bo=bo, bl=bl, bc=bc, bh=bh, sp=sp, ud=ud, um=um, utc=utc, key=ud * 1440 + um)


def scan(D, j0, side, entry, tp, sl, jx):
    bo, bl, bh, sp = D["bo"], D["bl"], D["bh"], D["sp"]
    for j in range(j0, jx + 1):
        if j == jx and j > j0: px = bo[j] if side > 0 else bo[j] + sp[j]; break
        if side > 0:
            if sl is not None and bl[j] <= sl: px = bo[j] if bo[j] <= sl else sl; break
            if tp is not None and bh[j] >= tp: px = bo[j] if bo[j] >= tp else tp; break
        else:
            if sl is not None and bh[j] + sp[j] >= sl: px = bo[j] + sp[j] if bo[j] + sp[j] >= sl else sl; break
            if tp is not None and bl[j] + sp[j] <= tp: px = bo[j] + sp[j] if bo[j] + sp[j] <= tp else tp; break
    else: px = bo[jx] if side > 0 else bo[jx] + sp[jx]
    return (px / entry - 1) if side > 0 else (entry / px - 1)


def entry_px(D, j, side): return D["bo"][j] + D["sp"][j] if side > 0 else D["bo"][j]


def pair_trades(m):
    D = load(m); key = D["key"]; ud = D["ud"]; days = np.unique(ud); out = {v: {} for v in ("ASIA_BRK", "ASIA_FADE", "LON_MOM", "LON_REV", "NY_MOM", "NY_REV", "PDHL")}
    starts = np.searchsorted(key, days * 1440); ends = np.r_[starts[1:], len(key)]; prev_hi = prev_lo = None
    def at(day, minute, side="first"):
        i = np.searchsorted(key, day * 1440 + minute, side="left"); return i if i < len(key) and key[i] == day * 1440 + minute else None
    for d, s, e in zip(days, starts, ends):
        seg = slice(s, e); this_hi, this_lo = D["bh"][seg].max(), D["bl"][seg].min(); ts = pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(d))
        if ts.dayofweek >= 5: prev_hi, prev_lo = this_hi, this_lo; continue
        a0, a1 = at(d, 0), at(d, 419)
        if a0 is not None and a1 is not None and a1 - a0 >= 300:
            hi, lo = D["bh"][a0:a1 + 1].max(), D["bl"][a0:a1 + 1].min(); R = hi - lo; jx = at(d, 960) or (e - 1)
            if R > 0:
                for hh in range(7, 11):
                    j = at(d, hh * 60 + 59)
                    if j is None: continue
                    c = D["bc"][j]; side = 1 if c > hi else (-1 if c < lo else 0)
                    if side == 0: continue
                    jn = j + 1; ep = entry_px(D, jn, side); tp = ep + R if side > 0 else ep - R; sl = lo if side > 0 else hi
                    if (side > 0 and sl < ep) or (side < 0 and sl > ep): out["ASIA_BRK"][ts] = scan(D, jn, side, ep, tp, sl, jx)
                    fs = -side; ef = entry_px(D, jn, fs); tpf = ef + R if fs > 0 else ef - R; slf = ef - R if fs > 0 else ef + R; out["ASIA_FADE"][ts] = scan(D, jn, fs, ef, tpf, slf, jx)
                    break
        o, c1, j8, j12 = at(d, 420), at(d, 479), at(d, 480), at(d, 720)
        if None not in (o, c1, j8, j12):
            mv = D["bc"][c1] - D["bo"][o]
            if mv != 0:
                side = 1 if mv > 0 else -1
                for nm, sd in (("LON_MOM", side), ("LON_REV", -side)): out[nm][ts] = scan(D, j8, sd, entry_px(D, j8, sd), None, None, j12)
        o, c2, j13, j17 = at(d, 420), at(d, 779), at(d, 780), at(d, 1020)
        if None not in (o, c2, j13, j17):
            mv = D["bc"][c2] - D["bo"][o]
            if mv != 0:
                side = 1 if mv > 0 else -1
                for nm, sd in (("NY_MOM", side), ("NY_REV", -side)): out[nm][ts] = scan(D, j13, sd, entry_px(D, j13, sd), None, None, j17)
        if prev_hi is not None:
            jx = at(d, 960) or (e - 1)
            for hh in range(7, 11):
                j = at(d, hh * 60 + 59)
                if j is None: continue
                c = D["bc"][j]; side = 1 if c > prev_hi else (-1 if c < prev_lo else 0)
                if side == 0: continue
                jn = j + 1; out["PDHL"][ts] = scan(D, jn, side, entry_px(D, jn, side), None, None, jx); break
        prev_hi, prev_lo = this_hi, this_lo
    # H4RSI2 on UTC 4-hour bars
    b4 = key // 240; idx = pd.Series(np.arange(len(key))); g = idx.groupby(b4); i0, i1 = g.min().values, g.max().values; cl = pd.Series(D["bc"][i1]); r2 = V.rsi(cl); s5 = cl.rolling(5).mean(); res = {}; i = 5
    while i < len(cl) - 6:
        side = 1 if r2.iat[i] < 10 else (-1 if r2.iat[i] > 90 else 0)
        if side and i0[i + 1] - i1[i] <= 3:
            j = i + 1
            while j < len(cl) - 1 and not ((cl.iat[j] > s5.iat[j]) if side > 0 else (cl.iat[j] < s5.iat[j])) and j - i < 5: j += 1
            jn, jx = i1[i] + 1, min(i1[j] + 1, len(key) - 1); ep = entry_px(D, jn, side); ts = D["utc"].iat[jn].normalize(); res[ts + pd.Timedelta(seconds=len(res))] = scan(D, jn, side, ep, None, None, jx); i = j + 1
        else: i += 1
    out["H4RSI2"] = res
    return {k: pd.Series(v, dtype=float).sort_index() for k, v in out.items()}


if __name__ == "__main__":
    mode = os.environ.get("FXS"); rows = []
    for m in PAIRS:
        T = pair_trades(m)
        for v, s in T.items():
            dd, va, ho = SC.st(s, SC.DEV), SC.st(s, SC.VAL), SC.st(s, SC.HOLD); rows.append(dict(pair=m, variant=v, dev_n=dd["n"], dev_mean=dd["mean"], dev_t=dd["t"], dev_p=dd["p"], val_n=va["n"], val_mean=va["mean"], hold_n=ho["n"], hold_mean=ho["mean"], hold_t=ho["t"]))
        print(m, "done", flush=True)
    R = pd.DataFrame(rows); R["dev_p"] = R.dev_p.fillna(1.0)
    if mode == "dry": print("tests", len(R), R.groupby("variant").dev_n.sum().to_dict())
    if mode == "run":
        el = R[R.dev_n >= 100].copy(); el["bh"] = SC.bh(el.dev_p.values, 0.10); R = R.merge(el[["pair", "variant", "bh"]], on=["pair", "variant"], how="left"); R["bh"] = R.bh.fillna(False).astype(bool); R["survivor"] = R.bh & (R.dev_mean >= 1.5) & (R.val_n >= 30) & (R.val_mean > 0)
        L = [f"tests {len(R)} ({len(el)} with >= 100 DEV trades) | nominally positive in DEV {int((R.dev_mean > 0).sum())}, p < 0.05: {int((R.dev_p < 0.05).sum())} (luck about {0.05 * len(el):.0f}) | BH q 0.10 passed DEV: {int(R.bh.sum())} | survivors: {int(R.survivor.sum())}"]
        L.append("\ntop 10 by DEV t:\n" + R.sort_values("dev_t", ascending=False).head(10)[["pair", "variant", "dev_n", "dev_mean", "dev_t", "val_n", "val_mean", "hold_n", "hold_mean"]].round(2).to_string(index=False))
        def pool(g, w): n = g[f"{w}_n"].fillna(0); return (n * g[f"{w}_mean"].fillna(0)).sum() / n.sum() if n.sum() else np.nan
        P = pd.DataFrame([dict(variant=v, dev_n=int(g.dev_n.sum()), dev_bp=pool(g, "dev"), val_bp=pool(g, "val"), hold_bp=pool(g, "hold")) for v, g in R.groupby("variant")]); L.append("\npooled over the 28 pairs (bp per trade, DEV / VAL / HOLD):\n" + P.round(2).to_string(index=False))
        sv = R[R.survivor]; L.append("\nSURVIVORS:\n" + sv.round(2).to_string(index=False) if len(sv) else "\nno survivors")
        txt = "\n".join(L); print(txt); R.to_csv(os.path.join(os.path.dirname(__file__), "FX_SESSIONS_TESTS.csv"), index=False); open(os.path.join(os.path.dirname(__file__), "FX_SESSIONS_RESULT.txt"), "w").write(txt)
