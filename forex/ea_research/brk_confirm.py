"""BRK_CONFIRM: candle-close confirmation (5 / 15 min) vs first-touch entries on the trader's London and New York 30-min boxes.
Pre-registration: forex/ea_research/PREREG_BRK_CONFIRM.md.  --dry-run: counts, truncation test, hand check (no R).  --run: results."""
import argparse, glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from zoneinfo import ZoneInfo
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.orbx import ct, CRYPTO
from forex.ea_research.analog import mclass

SRV, LIS, NY = ZoneInfo("Europe/Athens"), ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
DATA = "forex/data_mt5/"
CACHE = "data/scratch/brk_confirm_trades.parquet"
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
MODES = {"TOUCH": None, "C5": 5, "C15": 15}
TRIALS = [("LDN", "C5"), ("LDN", "C15"), ("NY", "C5"), ("NY", "C15")]


def srv(day, h, m, tz):
    return int(pd.Timestamp(day.year, day.month, day.day, h, m, tz=tz).tz_convert(SRV).tz_localize(None).timestamp())


def boxes(day):
    return {"LDN": (srv(day, 8, 0, LIS), srv(day, 8, 30, LIS), srv(day, 11, 0, LIS), srv(day, 17, 0, LIS)),
            "NY": (srv(day, 9, 30, NY), srv(day, 10, 0, NY), srv(day, 12, 0, NY), srv(day, 16, 0, NY))}


def entry(D, mode, i1, iw, hi, lo, b1, e_end):
    """(entry index, side, entry price, confirming-candle close or None) or None"""
    t = D["t"]
    if mode == "TOUCH":
        up = np.flatnonzero(D["ah"][i1:iw] >= hi); dn = np.flatnonzero(D["bl"][i1:iw] <= lo)
        ku = i1 + up[0] if len(up) else None; kd = i1 + dn[0] if len(dn) else None
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            return None
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        return k, side, (max(hi, D["ao"][k]) if side > 0 else min(lo, D["bo"][k])), None
    m = MODES[mode] * 60
    mc = D["mc"]
    j = (t[i1:iw] - b1) // m                                         # clock-aligned candle number inside the window
    n_c = (e_end - b1) // m
    for c in range(int(n_c)):
        sel = np.flatnonzero(j == c)
        if len(sel) < 0.6 * MODES[mode]:
            continue
        close = mc[i1 + sel[-1]]
        if close > hi or close < lo:
            side = 1 if close > hi else -1
            k = int(np.searchsorted(t, b1 + (c + 1) * m))             # first minute after the candle closed
            if k >= len(t):
                return None
            return k, side, (D["ao"][k] if side > 0 else D["bo"][k]), close
    return None


def market(sym, cut=None, with_r=True):
    D = load(sym, cut); t = D["t"]; out = []
    D["mc"] = (D["bc"] + D["ac"]) / 2
    rng = np.random.default_rng(sum(map(ord, sym)) * 104729)
    mh, ml = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2
    for dnum in np.unique(t // 86400):
        day = pd.Timestamp(int(dnum) * 86400, unit="s")
        if day < pd.Timestamp("2022-01-01") or day.weekday() >= 5:
            continue
        for box, (b0, b1, e_end, x_end) in boxes(day).items():
            i0, i1, iw, ix = np.searchsorted(t, [b0, b1, e_end, x_end])
            if i1 - i0 < 24 or ix >= len(t) or iw - i1 < 30 or ix - i1 < 60:
                continue                                              # box incomplete or session not finished in the data
            hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
            if hi <= lo:
                continue
            for mode in MODES:
                en = entry(D, mode, i1, iw, hi, lo, b1, e_end)
                if en is None:
                    continue
                k, side, e, cclose = en
                if k >= ix - 1:
                    continue
                sl = lo if side > 0 else hi
                if side * (e - sl) <= 0:
                    continue
                row = dict(sym=sym, day=day, box=box, mode=mode, side=side, t_entry=int(t[k]), entry=e, sl=sl, cclose=cclose,
                           delay=int((t[k] - b1) // 60), wsp=abs(e - sl) / max(D["sp"][k], 1e-12), hi=hi, lo=lo)
                if with_r:
                    risk = abs(e - sl)
                    ex, _ = walk(D, side, k, ix, sl, None)
                    row["R"] = (ex - e) * side / risk
                    ex1, _ = walk(D, side, k, ix, sl, e + side * risk)
                    row["cont1R"] = bool((ex1 - e) * side >= 0.999 * risk)
                    w60 = int(np.searchsorted(t, t[k] + 3600))
                    w60 = min(w60, ix)
                    row["back60"] = bool((ml[k + 1:w60] < hi).any() if side > 0 else (mh[k + 1:w60] > lo).any())
                    kc = int(rng.integers(i1, iw))                    # random-timing control: same day, side, SL level, exit
                    ec = D["ao"][kc] if side > 0 else D["bo"][kc]
                    if side * (ec - sl) > 0 and kc < ix - 1:
                        exc, _ = walk(D, side, kc, ix, sl, None); row["Rc"] = (exc - ec) * side / abs(ec - sl)
                    else:
                        row["Rc"] = np.nan
                out.append(row)
    return out


def syms():
    return sorted(s for s in (os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet")) if s not in CRYPTO)


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    with Pool(4) as p:
        T = pd.DataFrame([r for rows in p.map(market, syms()) for r in rows])
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    S = syms(); print("markets", len(S))
    with Pool(4) as p:
        T = pd.DataFrame([r for rows in p.starmap(market, [(s, None, False) for s in S]) for r in rows])
    for box in ("LDN", "NY"):
        for mode in MODES:
            x = T[(T.box == box) & (T["mode"] == mode)]
            print(f"{box:3s} {mode:5s} DEV {int(per(x, DEV).sum()):6d}  VAL {int(per(x, VAL).sum()):5d}  HOLD {int(per(x, HOLD).sum()):5d}"
                  f"  long share {np.mean(x.side == 1):.2f}  median delay {x.delay.median():.0f} min  median width/spread {x.wsp.median():.0f}")
        k = T[T.box == box].pivot_table(index=["sym", "day"], columns="mode", values="side", aggfunc="first")
        for m in ("C5", "C15"):
            print(f"   {box} {m}: fires without a touch {int((k[m].notna() & k['TOUCH'].isna()).sum())}, touch without {m} {int((k['TOUCH'].notna() & k[m].isna()).sum())},"
                  f" same side as touch {np.mean(k[m] == k['TOUCH'])*100:.0f}% of days with both")
    rng = np.random.default_rng(3)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        full = pd.DataFrame(market(sym, None, False))
        cut = int(rng.uniform(full.t_entry.quantile(.3), full.t_entry.quantile(.9)))
        tr = pd.DataFrame(market(sym, cut, False))
        cutday = pd.Timestamp(cut // 86400 * 86400, unit="s")
        cols = ["day", "box", "mode", "side", "t_entry", "entry", "sl"]
        a = full[full.day < cutday][cols].reset_index(drop=True); b = tr[tr.day < cutday][cols].reset_index(drop=True)
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')}, entries before the cut day {len(a)} vs {len(b)}, identical {a.equals(b)}")
    for mode in ("C5", "C15"):
        for _, r in T[T["mode"] == mode].sample(3, random_state=2).iterrows():
            print(f"  {mode} {r.sym} {r.day.date()} {r.box} side {r.side:+d} box {r.hi:.5g}/{r.lo:.5g} confirming close {r.cclose:.5g} "
                  f"entry {r.entry:.5g} at {pd.Timestamp(r.t_entry, unit='s'):%H:%M} server (delay {r.delay} min) sl {r.sl:.5g}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T = build()
    print(f"trades {len(T)}, markets {T.sym.nunique()}, {T.day.min().date()}..{T.day.max().date()}")
    passed = []
    for box, mode in TRIALS:
        x = T[(T.box == box) & (T["mode"] == mode)]; tch = T[(T.box == box) & (T["mode"] == "TOUCH")]
        d, v = x[per(x, DEV)], x[per(x, VAL)]
        mu, t = ct(d)
        pr = d.merge(tch[per(tch, DEV)][["sym", "day", "R"]], on=["sym", "day"], suffixes=("", "_t"))
        dm, dt_ = ct(pr.assign(R=pr.R - pr.R_t))
        yrs = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 500 and mu > 0 and t >= 2.5 and dm > 0 and dt_ >= 2.0 and mu > d.Rc.mean() and (yrs > 0).sum() >= 2
        mv, tv = ct(v); okv = ok and mv > 0 and tv >= 1.65
        line = (f"{box:3s}-{mode:4s} | DEV n {len(d):5d} net {mu:+.3f} t {t:+.2f} | vs TOUCH {dm:+.3f} (t {dt_:+.2f}, n {len(pr)}) | control {d.Rc.mean():+.3f}"
                f" | yrs {'/'.join(f'{y:+.2f}' for y in yrs)} -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} t {tv:+.2f}")
        if okv:
            h = x[per(x, HOLD)]; mh_, th = ct(h); line += f" | HOLD n {len(h)} {mh_:+.3f} t {th:+.2f} -> {'PASS' if mh_ > 0 and th >= 1.65 else 'FAIL'}"
            if mh_ > 0 and th >= 1.65:
                passed.append((box, mode))
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nyardsticks (TOUCH): " + " | ".join(f"{b} DEV {T[(T.box==b)&(T['mode']=='TOUCH')&per(T,DEV)].R.mean():+.3f} VAL {T[(T.box==b)&(T['mode']=='TOUCH')&per(T,VAL)].R.mean():+.3f}" for b in ("LDN", "NY")))
    print("\nDescriptive (DEV + VAL): bounce = back inside the box within 60 min after entry; cont = +1R before -1R")
    dv = T[per(T, (DEV[0], VAL[1]))]
    g = dv.groupby(["box", "mode"]).agg(n=("R", "size"), win=("R", lambda s: (s > 0).mean()), bounce=("back60", "mean"), cont1R=("cont1R", "mean"),
                                        R=("R", "mean"), delay=("delay", "median"), wsp=("wsp", "median"))
    print(g.round(3).to_string())
    print("\nby class (DEV + VAL), mean R:")
    print(dv.assign(cls=dv.sym.map(mclass)).pivot_table(index=["box", "mode"], columns="cls", values="R", aggfunc="mean").round(3).to_string())
    print("\nby year, mean R:")
    print(T.pivot_table(index=["box", "mode"], columns=T.day.dt.year, values="R", aggfunc="mean").round(3).to_string())
    # account environment for the trader's two markets (standing rule), every mode incl. TOUCH, $250 a trade
    print("\nAccount environment, NSDQ + XAUUSD, $250 a trade, from 95,472 (pass% / breach%, bootstrap | replay):")
    days = pd.bdate_range("2022-01-03", "2026-10-16"); H = max(HZ.values()); rng = np.random.default_rng(1617)
    for box in ("LDN", "NY"):
        for mode in MODES:
            x = T[(T.box == box) & (T["mode"] == mode) & T.sym.isin(["NSDQ", "XAUUSD"])]
            R = x.groupby("day").R.sum().reindex(days); tr = R.notna().to_numpy(); r = R.fillna(0).to_numpy()
            s = rng.integers(0, len(r) - 5, size=(20000, H // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :H]
            st, ev, _ = account(r[bi], tr[bi], 250)
            idx = np.arange(len(r))[:, None] + np.arange(H)[None, :]; full = (idx < len(r)).all(1); st2, ev2, _ = account(r[idx[full]], tr[idx[full]], 250)
            print(f"  {box}-{mode:5s} {x.R.mean():+.3f} R/trade ({len(x)} trades): " + "   ".join(
                f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f} | {100*np.mean((st2==1)&(ev2<h)):.1f}/{100*np.mean((st2==2)&(ev2<h)):.0f}"
                for k, h in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    print("\npassed all gates:", passed or "none")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
