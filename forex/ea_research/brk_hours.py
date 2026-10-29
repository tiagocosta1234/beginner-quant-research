"""BRK-HOURS exactly as in PREREG_BRK_HOURS.md: 60-minute box breakouts at every server hour 1..20 on 46 markets.
   python -m forex.ea_research.brk_hours --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
HOURS = range(1, 21)


def hold(D, k, kend, side, e, R):
    """stop at 1R, else exit at kend's open; net R."""
    if kend <= k:
        return np.nan
    if side > 0:
        hit = np.flatnonzero(D["bl"][k:kend] <= e - R)
        px = min(e - R, D["bo"][k + hit[0]]) if len(hit) else D["bo"][kend]
        return (px - e) / R
    hit = np.flatnonzero(D["ah"][k:kend] >= e + R)
    px = max(e + R, D["ao"][k + hit[0]]) if len(hit) else D["ao"][kend]
    return (e - px) / R


def hold_fill(D, k, kend, side, e, R):
    """as hold(), but a stop order filled inside minute k cannot be stopped by prices of that minute that came before the fill:
    if e is the minute's open (market entry) the whole minute counts; otherwise the fill minute stops the trade only if it CLOSES
    beyond the stop (exit at the stop), and the regular check starts at minute k + 1."""
    if kend <= k:
        return np.nan
    if side > 0:
        stop = e - R
        if e == D["ao"][k]:
            return hold(D, k, kend, side, e, R)
        if D["bc"][k] <= stop:
            return -1.0
        hit = np.flatnonzero(D["bl"][k + 1:kend] <= stop)
        px = min(stop, D["bo"][k + 1 + hit[0]]) if len(hit) else D["bo"][kend]
        return (px - e) / R
    stop = e + R
    if e == D["bo"][k]:
        return hold(D, k, kend, side, e, R)
    if D["ac"][k] >= stop:
        return -1.0
    hit = np.flatnonzero(D["ah"][k + 1:kend] >= stop)
    px = max(stop, D["ao"][k + 1 + hit[0]]) if len(hit) else D["ao"][kend]
    return (e - px) / R


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 25)
    rows = []
    for d in np.unique(t // 86400):
        base = d * 86400
        for h in HOURS:
            i0, i1 = np.searchsorted(t, base + h * H), np.searchsorted(t, base + (h + 1) * H)
            w1 = np.searchsorted(t, base + (h + 3) * H)
            kend = min(np.searchsorted(t, base + min((h + 7) * H, 22 * H + 55 * M)), len(t) - 1)
            if i1 - i0 < 40 or w1 - i1 < 60 or kend <= w1 or t[kend] // 86400 != d:
                continue
            Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
            if not Hb > Lb:
                continue
            up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
            dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
            ku = i1 + up[0] if len(up) else None
            kd = i1 + dn[0] if len(dn) else None
            if (ku is None and kd is None) or (ku is not None and ku == kd):
                continue
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd
            e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
            R = abs(e - (Lb if side > 0 else Hb))
            sp = D["ao"][k] - D["bo"][k]
            if not (R > 0 and R >= 2 * sp):
                continue
            kc = int(rng.integers(i1, w1))
            sc = 1 if rng.random() < 0.5 else -1
            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
            rows.append((sym, base, h, side, int(t[k]), hold(D, k, kend, side, e, R), hold(D, kc, kend, sc, ec, R), (Hb - Lb) / max(sp, 1e-12)))
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=["mkt", "d", "h", "side", "t_entry", "R", "C", "box_sp"])
    df["day"] = pd.to_datetime(df.d, unit="s")
    df["c"] = df.mkt.map(mclass)
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("events", len(df), "| per class", df.c.value_counts().to_dict(), "| median per cell DEV", int(df[(df.day <= DEV[1])].groupby(["h", "c"]).size().median()))
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
    f, p = f[f[4] < cut - 86400].reset_index(drop=True), p[p[4] < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[5].to_numpy(), p[5].to_numpy(), equal_nan=True)
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")
    x = df[(df.mkt == "EURUSD") & (df.day == "2024-06-12")]
    print("hand check EURUSD 2024-06-12:", x[["h", "side", "R", "C", "box_sp"]].round(3).to_dict("records")[:5])


def run():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_HOURS.parquet")
    per = {"DEV": DEV, "VAL": VAL, "2026": Y26}
    out = []
    for (h, c), g in df.groupby(["h", "c"]):
        r = dict(h=h, c=c)
        for lab, (a, b) in per.items():
            s = g[(g.day >= a) & (g.day <= b)]
            r[f"n_{lab}"], r[lab], r[f"t_{lab}"], r[f"ctl_{lab}"] = len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean()
        r["pass"] = (r["DEV"] >= 0.05 and r["t_DEV"] >= 3.48) and (r["VAL"] > 0 and r["t_VAL"] >= 1.65) and (r["DEV"] - r["ctl_DEV"] >= 0.05 and r["VAL"] - r["ctl_VAL"] >= 0.05)
        out.append(r)
    T = pd.DataFrame(out)
    T.to_csv("data/si_ledgers/BRK_HOURS_cells.csv", index=False)
    print("cells passing:", int(T["pass"].sum()), "of", len(T))
    show = T.sort_values("t_DEV", ascending=False).head(12)
    print("top 12 cells by DEV t:")
    print(show[["c", "h", "n_DEV", "DEV", "t_DEV", "ctl_DEV", "VAL", "t_VAL", "ctl_VAL", "2026", "ctl_2026"]].round(3).to_string(index=False))
    for lab in per:
        piv = T.pivot(index="c", columns="h", values=lab)
        print(f"\nnet R {lab} (rows class, columns server hour of the box):")
        print(piv.round(2).to_string())
        piv = T.assign(v=T[lab] - T[f"ctl_{lab}"]).pivot(index="c", columns="h", values="v")
        print(f"information {lab} (net minus random):")
        print(piv.round(2).to_string())
    fig, ax = plt.subplots(2, 3, figsize=(18, 7))
    for j, lab in enumerate(per):
        for i, title in enumerate(("net R", "information (net - random)")):
            v = T[lab] if i == 0 else T[lab] - T[f"ctl_{lab}"]
            piv = T.assign(v=v).pivot(index="c", columns="h", values="v")
            im = ax[i, j].imshow(piv.to_numpy(), cmap="RdYlGn", vmin=-0.25, vmax=0.25, aspect="auto")
            ax[i, j].set_xticks(range(len(piv.columns)))
            ax[i, j].set_xticklabels(piv.columns)
            ax[i, j].set_yticks(range(len(piv.index)))
            ax[i, j].set_yticklabels(piv.index)
            ax[i, j].set_title(f"{lab}: {title}")
            ax[i, j].set_xlabel("server hour of the 60-min box (London = server - 2)")
            for (yy, xx), val in np.ndenumerate(piv.to_numpy()):
                ax[i, j].text(xx, yy, f"{val:+.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, shrink=0.6)
    fig.suptitle("BRK-HOURS: 60-minute box breakouts by hour of day, MT5 broker real bid/ask, hold up to 6 h (R per trade)")
    fig.savefig("data/scratch/charts/BRK_HOURS.png", dpi=110, bbox_inches="tight")
    print("chart data/scratch/charts/BRK_HOURS.png")


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
