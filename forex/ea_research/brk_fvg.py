"""BRK_FVG: an unmitigated 5-min fair value gap between entry and stop as a confluence for FOLLOW / FADE trades at the first touch
of the trader's London / New York boxes (events and trades from brk_twoway). Pre-registration: forex/ea_research/PREREG_BRK_FVG.md.
--dry-run: counts, truncation test, hand check (no P&L).  --run: results."""
import argparse, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.brk_patterns import load
from forex.ea_research.brk_confirm import srv, LIS
from forex.ea_research.brk_twoway import build as build_events
from forex.ea_research.orbx import ct

DEV_Y, VAL_Y = (2022, 2023, 2024), 2025
CACHE = "C:/work/scratch/brk_fvg_flags.parquet"


def fvgs(D):
    """all 5-min mid FVGs: arrays (formed_at, kind +1 bullish / -1 bearish, bottom, top)"""
    t = D["t"]; key = t // 300
    mh, ml = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    k = key[st]; H = np.maximum.reduceat(mh, st); L = np.minimum.reduceat(ml, st)
    c = np.arange(2, len(k)); ok = (k[c] - k[c - 2]) == 2                    # three consecutive 5-min candles
    c = c[ok]
    bull = L[c] > H[c - 2]; bear = H[c] < L[c - 2]
    formed = (k[c] + 1) * 300
    F = pd.DataFrame({"formed": np.r_[formed[bull], formed[bear]], "kind": np.r_[np.ones(bull.sum()), -np.ones(bear.sum())],
                      "bot": np.r_[H[c - 2][bull], H[c][bear]], "top": np.r_[L[c][bull], L[c - 2][bear]]})
    return F.sort_values("formed").reset_index(drop=True)


def flags(sym, ev, cut=None):
    D = load(sym, cut); t = D["t"]
    mh, ml = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2
    F = fvgs(D); fo = F.formed.to_numpy()
    out = []
    for r in ev.itertuples():
        if cut is not None and r.t_touch >= cut:
            continue
        hi, lo = (r.level, r.level - r.W) if r.side > 0 else (r.level + r.W, r.level)
        spb = r.W / r.box_spread
        d0 = srv(r.day, 0, 0, LIS)
        a, b = np.searchsorted(fo, [d0, r.t_touch], side="left"); b = np.searchsorted(fo, r.t_touch, side="right")
        cand = F.iloc[a:b]
        cand = cand[(cand.top - cand.bot) >= spb]
        kt = int(np.searchsorted(t, r.t_touch, side="right"))               # through the end of the touch minute
        res = {}
        for leg in ("follow", "fade"):
            if leg == "follow":
                kind = r.side; zlo, zhi = lo, hi
            else:
                kind = -r.side; zlo, zhi = (hi, hi + r.W) if r.side > 0 else (lo - r.W, lo)
            z = cand[(cand.kind == kind) & (cand.bot >= zlo) & (cand.top <= zhi)]
            n_un, best = 0, None
            for g in z.itertuples():
                j0 = int(np.searchsorted(t, g.formed))
                if kind > 0:
                    unm = j0 >= kt or ml[j0:kt].min() >= g.top
                else:
                    unm = j0 >= kt or mh[j0:kt].max() <= g.bot
                if unm:
                    n_un += 1; best = best or (g.formed, g.bot, g.top)
            res[f"{leg}_fvg"] = n_un > 0; res[f"{leg}_fvg_mitigated_only"] = (len(z) > 0) and n_un == 0
            res[f"{leg}_gap"] = best
        out.append(dict(sym=sym, day=r.day, box=r.box, t_touch=r.t_touch, **{k: v for k, v in res.items() if not k.endswith("_gap")},
                        follow_gap=str(res["follow_gap"]), fade_gap=str(res["fade_gap"])))
    return pd.DataFrame(out)


def _job(args):
    sym, ev, cut = args
    return flags(sym, ev, cut)


def all_flags(E):
    import os
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    jobs = [(s, g, None) for s, g in E.groupby("sym")]
    with Pool(4) as p:
        Fl = pd.concat(p.map(_job, jobs), ignore_index=True)
    Fl.to_parquet(CACHE)
    return Fl


def dry_run():
    E = build_events(); Fl = all_flags(E)
    M = E.merge(Fl, on=["sym", "day", "box", "t_touch"])
    print(f"events {len(E)}, flagged rows {len(M)}")
    for box in ("LDN", "NY"):
        for leg in ("follow", "fade"):
            x = M[M.box == box]
            c = x.groupby(x.year)[f"{leg}_fvg"].agg(["sum", "mean"])
            mo = x.groupby(x.year)[f"{leg}_fvg_mitigated_only"].mean()
            print(f"{box} {leg.upper():6s} with unmitigated FVG by year: " + ", ".join(f"{y}: {int(s)} ({m:.1%})" for y, (s, m) in c.iterrows())
                  + " | zone FVGs all mitigated: " + ", ".join(f"{y} {v:.1%}" for y, v in mo.items()))
    rng = np.random.default_rng(6)
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        ev = E[E.sym == sym]; full = flags(sym, ev)
        cut = int(rng.uniform(ev.t_touch.quantile(.3), ev.t_touch.quantile(.9))); cd = pd.Timestamp(cut // 86400 * 86400, unit="s")
        tr = flags(sym, ev, cut)
        cols = ["day", "box", "follow_fvg", "fade_fvg", "follow_gap", "fade_gap"]
        a = full[full.day < cd][cols].reset_index(drop=True); b = tr[tr.day < cd][cols].reset_index(drop=True)
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')}, events before the cut day {len(a)} vs {len(b)}, identical {a.equals(b)}")
    for leg in ("follow", "fade"):
        for _, r in M[M[f"{leg}_fvg"]].sample(2, random_state=7).iterrows():
            print(f"  {leg} {r.sym} {r.day.date()} {r.box} side {r.side:+d} level {r.level:.5g} W {r.W:.5g} touch {pd.Timestamp(r.t_touch, unit='s'):%H:%M} server"
                  f" | FVG (formed, bottom, top) = {r[f'{leg}_gap']}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    E = build_events(); Fl = all_flags(E)
    M = E.merge(Fl, on=["sym", "day", "box", "t_touch"])
    M["year"] = M.day.dt.year
    print(f"events {len(M)}")
    for box in ("LDN", "NY"):
        for leg in ("follow", "fade"):
            x = M[M.box == box]; R = x[f"R_{leg}"]
            w = x[x[f"{leg}_fvg"]].assign(R=lambda z: z[f"R_{leg}"]); wo = x[~x[f"{leg}_fvg"]].assign(R=lambda z: z[f"R_{leg}"])
            d, dw = w[w.year.isin(DEV_Y)], wo[wo.year.isin(DEV_Y)]
            mu, t = ct(d); diff = d.R.mean() - dw.R.mean()
            se = np.sqrt(d.R.var() / len(d) + dw.R.var() / len(dw)); td = diff / se
            yrs = d.groupby(d.year).R.mean()
            ok = len(d) >= 300 and mu > 0 and t >= 2.5 and diff > 0 and td >= 2.0 and (yrs > 0).sum() >= 2
            v = w[w.year == VAL_Y]; mv, tv = ct(v); okv = ok and mv > 0 and tv >= 1.65
            line = (f"{box:3s}-{leg.upper():6s}-FVG | DEV n {len(d)} net {mu:+.3f} t {t:+.2f} win {(d.R > 0).mean():.3f} | without FVG n {len(dw)} {dw.R.mean():+.3f}"
                    f" win {(dw.R > 0).mean():.3f} | diff {diff:+.3f} (t {td:+.2f}) | yrs {'/'.join(f'{y:+.2f}' for y in yrs)} -> {'PASS' if ok else 'FAIL'}"
                    f" | VAL n {len(v)} {mv:+.3f} t {tv:+.2f} (without {wo[wo.year == VAL_Y].R.mean():+.3f})")
            if okv:
                h = w[w.year == 2026]; mh_, th = ct(h); line += f" | HOLD n {len(h)} {mh_:+.3f} t {th:+.2f} -> {'PASS' if mh_ > 0 and th >= 1.65 else 'FAIL'}"
            else:
                line += " | HOLD sealed"
            print(line)
            A = w[(w.year <= VAL_Y) & w.sym.isin(["NSDQ", "XAUUSD"])]
            days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1619)
            Rd = A.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
            s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
            st, ev, _ = account(r[bi], trd[bi], 250)
            print(f"     account NSDQ+XAU $250 ({len(A)} trades 2022-25, {A.R.mean():+.3f} R): " + "  ".join(
                f"{k} pass {100*np.mean((st==1)&(ev<h_)):.1f}% / breach {100*np.mean((st==2)&(ev<h_)):.0f}%" for k, h_ in HZ.items() if k in ("22 Dec", "30 Jun 27")))
    from forex.ea_research.analog import mclass
    dv = M[M.year <= VAL_Y].assign(cls=lambda z: z.sym.map(mclass))
    print("\nDescriptive (2022-25): R by class, with / without the confluence")
    for leg in ("follow", "fade"):
        print(f" {leg}:\n" + dv.pivot_table(index=["box", f"{leg}_fvg"], columns="cls", values=f"R_{leg}", aggfunc="mean").round(3).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
