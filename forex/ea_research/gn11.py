"""GN11: BRK-WEEK's metals previous-week breakout (M1 = W2 on GC + SI) and index month-opening-range breakout (M2 = W4 on NQ + ES),
rules unchanged, on 2020-21 CME futures with the MT5 broker cost model. Pre-registration: forex/ea_research/PREREG_GN11.md.
   python -m forex.ea_research.gn11 --dry-run | --run"""
import argparse, zlib, numpy as np, pandas as pd
from forex.ea_research.brk_week import trade, COLS
from forex.ea_research.ict2 import nw_t
from forex.ea_research.brk_patterns import load
from forex.ea_research.gn5 import load_fut, roll_mondays
from forex.ea_research.gn6 import bad_minutes

FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
H, M = 3600, 60
MT5OF = {"GC": "XAUUSD", "SI": "XAGUSD", "NQ": "NSDQ", "ES": "SP"}
TRIALS = {"M1": ("W2", ("GC", "SI")), "M2": ("W4", ("NQ", "ES"))}
START = pd.Timestamp("2020-01-01")
OOT_END = pd.Timestamp("2022-01-01")
W2_FIRST = pd.Timestamp("2020-01-13")


def epoch(ts_naive):
    return int((ts_naive - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def mt5_session_spread(mkt):
    E = load(mkt); s = E["sod"]
    m = (s >= H) & (s < 23 * H) & (E["t"] >= epoch(pd.Timestamp("2022-01-01")))
    return float(np.median(E["sp"][m]))


def cut(D, lo=None, hi=None):
    t = D["t"]; a = int(np.searchsorted(t, lo)) if lo is not None else 0; b = int(np.searchsorted(t, hi)) if hi is not None else len(t)
    return {k: (v[a:b] if isinstance(v, np.ndarray) and len(v) == len(t) else v) for k, v in D.items()}


def switch_epochs():
    """server epochs of 00:00 UTC on each NQ / ES roll Monday"""
    return sorted(epoch(pd.Timestamp(d.year, d.month, d.day, tz="UTC").tz_convert("Europe/Athens").tz_localize(None)) for d in roll_mondays())


def back_adjust(D):
    """difference back-adjustment at the roll minutes; returns the adjusted copy and the list of (date, gap)"""
    t = D["t"]; adj = np.zeros(len(t)); gaps = []
    for s in switch_epochs():
        k = int(np.searchsorted(t, s))
        if k <= 0 or k >= len(t) or t[k] - s > 3 * H:
            continue
        g = D["bo"][k] - D["bc"][k - 1]; adj[:k] += g
        gaps.append((pd.Timestamp(s, unit="s").date(), round(float(g), 2)))
    E = dict(D)
    for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"):
        E[c] = D[c] + adj
    return E, gaps


def market_on(D, sym, cell, bad=None, skip_months=()):
    """brk_week.market's W2 / W4 logic on a given data dict; a week / month with a bad minute between order start and exit is skipped"""
    t = D["t"]
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 99)
    day, sod = t // 86400, t % 86400
    st = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); en = np.r_[st[1:], len(t)]
    rows, info = [], {}
    for a, b in zip(st, en):
        w = np.arange(a, b)[(sod[a:b] >= H) & (sod[a:b] < 23 * H)]
        if len(w) < 300:
            continue
        d = int(day[a])
        info[d] = dict(a=a, b=b, hi=D["bh"][w].max(), lo=D["bl"][w].min(), wd=(d + 3) % 7,
                       k_open=a + np.searchsorted(sod[a:b], H + 5 * M), k_close=a + np.searchsorted(sod[a:b], 21 * H + 55 * M),
                       k_last=a + np.searchsorted(sod[a:b], 22 * H + 55 * M))
    days = sorted(d for d in info if info[d]["wd"] < 5)

    def clean(wa, kend):
        return bad is None or not len(bad) or np.searchsorted(bad, t[wa]) >= np.searchsorted(bad, t[min(kend, len(t) - 1)] + 60)

    if cell == "W2":
        weeks = {}
        for d in days:
            weeks.setdefault((d + 3) // 7, []).append(d)
        wkeys = sorted(weeks)
        for n_, wk in enumerate(wkeys):
            ds = weeks[wk]; by = {info[d]["wd"]: d for d in ds}
            if 4 not in by or n_ == 0 or wkeys[n_ - 1] != wk - 1:
                continue
            kend = min(info[by[4]]["k_close"], len(t) - 1)
            pw = weeks[wkeys[n_ - 1]]
            ph, pl = max(info[d]["hi"] for d in pw), min(info[d]["lo"] for d in pw)
            first = info[ds[0]]; thu = info[by.get(3, by[max(k for k in by if k < 4)])]; mid = (ph + pl) / 2
            if clean(first["k_open"], kend):
                rows += [(sym,) + r for r in trade(D, rng, "W2", first["k_open"], thu["k_last"], kend, ph, pl, mid, mid, ds[0])]
    else:
        months = {}
        for d in days:
            months.setdefault(pd.Timestamp(d * 86400, unit="s").to_period("M"), []).append(d)
        for mth, ds in sorted(months.items()):
            if len(ds) < 10 or mth.month in skip_months:        # amendment 1: quarterly roll months skipped (NQ / ES)
                continue
            box = ds[:3]; hb, lb = max(info[d]["hi"] for d in box), min(info[d]["lo"] for d in box)
            fifteenth = [d for d in ds[3:] if pd.Timestamp(d * 86400, unit="s").day <= 15]
            if not fifteenth:
                continue
            wa, wb = info[ds[3]]["k_open"], info[fifteenth[-1]]["k_last"]; kend = min(info[ds[-1]]["k_close"], len(t) - 1)
            if clean(wa, kend):
                rows += [(sym,) + r for r in trade(D, rng, "W4", wa, wb, kend, hb, lb, lb, hb, ds[3])]
    return pd.DataFrame(rows, columns=COLS)


def prepare(root):
    sp = mt5_session_spread(MT5OF[root])
    D = cut(load_fut(FUTP.format(root), sp), lo=epoch(START))
    if root in ("NQ", "ES"):
        _, gaps = back_adjust(D); bad = None            # amendment 1: gaps printed for the record only; roll months are skipped
    else:
        gaps = None; bad = bad_minutes(D)
    return D, bad, gaps, sp


def rows_for(trial, data=None, upto=None):
    cell, roots = TRIALS[trial]; out = []
    for r in roots:
        D, bad, _, _ = data[r] if data else prepare(r)
        if upto is not None:
            D = cut(D, hi=upto); bad = bad[bad < upto] if bad is not None else None
        x = market_on(D, r, cell, bad, (3, 6, 9, 12) if r in ("NQ", "ES") else ())
        x = x[(x.day >= (W2_FIRST if cell == "W2" else START)) & (x.day < OOT_END)]
        out.append(x)
    return pd.concat(out, ignore_index=True)


def dry_run():
    data = {r: prepare(r) for r in ("GC", "SI", "NQ", "ES")}
    for r, (D, bad, gaps, sp) in data.items():
        line = f"{r}: MT5 broker session median spread ({MT5OF[r]}) {sp:.4f}"
        if gaps is not None:
            g = [x for x in gaps if pd.Timestamp("2019-12-01").date() <= x[0] < pd.Timestamp("2022-01-31").date()]
            line += " | roll gaps 2020-21: " + " ".join(f"{d:%Y-%m-%d} {v:+.2f}" for d, v in g)
        else:
            bd = sorted({pd.Timestamp(x, unit="s").date() for x in bad if START.timestamp() <= x < OOT_END.timestamp()})
            line += f" | switch / flip dates 2020-21 ({len(bd)}): " + " ".join(f"{d:%m-%d-%y}" for d in bd)
        print(line)
    for tr, (cell, roots) in TRIALS.items():
        x = rows_for(tr, data)
        print(f"{tr} {cell} {'+'.join(roots)}: trades " + " ".join(f"{m} {y}:{len(g)}" for (m, y), g in x.groupby([x.mkt, x.day.dt.year]))
              + f" | total {len(x)}, entry weeks {x.day.dt.to_period('W').nunique()}")
        r = x.iloc[len(x) // 2]
        print(f"   hand check {r.mkt} {r.cell} window start {r.day.date()} side {r.side:+d} entry at {pd.Timestamp(r.t_entry, unit='s')} server")
        cutp = epoch(pd.Timestamp("2021-06-30 12:00"))
        y = rows_for(tr, data, upto=cutp)
        a = x[x.t_entry < cutp - 40 * 86400].sort_values(["mkt", "t_entry"]).reset_index(drop=True)
        b = y[y.t_entry < cutp - 40 * 86400].sort_values(["mkt", "t_entry"]).reset_index(drop=True)
        ok = len(a) == len(b) and np.allclose(a[["E_close", "E_2R"]].to_numpy(), b[["E_close", "E_2R"]].to_numpy(), equal_nan=True)
        print(f"   truncation test (data cut 2021-06-30 12:00 server, trades entered 40 days earlier): {'PASS' if ok else 'FAIL'} ({len(a)} trades)")


def run():
    data = {r: prepare(r) for r in ("GC", "SI", "NQ", "ES")}
    for tr, (cell, roots) in TRIALS.items():
        x = rows_for(tr, data); x["wk"] = x.day.dt.to_period("W")
        m = x.E_close.mean(); t = nw_t(x.groupby("wk").E_close.mean().to_numpy()); c = x.C_close.mean()
        yrs = x.groupby(x.day.dt.year).E_close.mean()
        ok = m > 0 and t >= 1.65 and m - c >= 0.05 and (yrs > 0).all()
        print(f"{tr} {cell} {'+'.join(roots)} 2020-21 futures: n {len(x)} {m:+.3f} R (NW t {t:+.2f}) win {(x.E_close > 0).mean():.0%} | control {c:+.3f}"
              f" (breakout - control {m - c:+.3f}) | yrs " + "/".join(f"{y}:{v:+.3f}" for y, v in yrs.items()) + f" -> {'PASS' if ok else 'FAIL'}")
        print("   by market: " + " | ".join(f"{k} {g.E_close.mean():+.3f} (n {len(g)}, control {g.C_close.mean():+.3f}, longs {g[g.side > 0].E_close.mean():+.3f}"
                                         f" n {int((g.side > 0).sum())}, shorts {g[g.side < 0].E_close.mean():+.3f})" for k, g in x.groupby("mkt"))
              + f" | 2R exit {x.E_2R.mean():+.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
