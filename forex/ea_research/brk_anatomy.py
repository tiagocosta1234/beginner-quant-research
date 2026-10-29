"""BRK-ANATOMY (breakout day round 9, descriptive, no strategy): what happens after a session opening-range breakout on the 46 MT5,
compared with a random entry at the same place in the day. Same events as BRK-EXITS (round 1).
   python -m forex.ea_research.brk_anatomy     -> tables + data/scratch/charts/BRK_ANATOMY.png"""
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60


def path_stats(D, k, kend, side, e, R, Hb, Lb):
    n = kend - k
    if n < 30:
        return None
    if side > 0:
        fav, adv, mid = D["bh"][k:kend] - e, e - D["bl"][k:kend], (D["bc"][k:kend] + D["ac"][k:kend]) / 2
        back_in = mid < Hb
        x_end = D["bo"][kend]
    else:
        fav, adv, mid = e - D["al"][k:kend], D["ah"][k:kend] - e, (D["bc"][k:kend] + D["ac"][k:kend]) / 2
        back_in = mid > Lb
        x_end = D["ao"][kend]
    cf, ca = np.maximum.accumulate(fav) / R, np.maximum.accumulate(adv) / R
    out = dict(mfe30=cf[min(29, n - 1)], mfe60=cf[min(59, n - 1)], mfe_all=cf[-1], mae_all=ca[-1],
               t_mfe=int(np.argmax(fav)) if n else 0, close_R=side * (x_end - e) / R,
               back15=bool(back_in[:15].any()), back60=bool(back_in[:60].any()))
    i_s = np.flatnonzero(ca >= 1.0)
    for k_r in (1, 2, 3):
        i_t = np.flatnonzero(cf >= k_r)
        out[f"hit{k_r}R"] = bool(len(i_t) and (not len(i_s) or i_t[0] < i_s[0]))
    return out


def market(sym):
    D = load(sym, END)
    tz, op_s, cl_s = session(sym)
    lc = local_clock(D["t"], tz)
    t = D["t"]
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 17)
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1:
            continue
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        if not Hb > Lb:
            continue
        box = Hb - Lb
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        day = pd.Timestamp(d * 86400, unit="s")
        sp_med = np.median(D["ao"][i0:i1] - D["bo"][i0:i1])
        if not ((ku is None and kd is None) or (ku is not None and ku == kd)):
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd
            e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
            R = abs(e - (Lb if side > 0 else Hb))
            if k < kend and R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k]):
                s = path_stats(D, k, kend, side, e, R, Hb, Lb)
                if s:
                    rows.append(dict(mkt=sym, day=day, kind="BRK", cost_R=(D["ao"][k] - D["bo"][k]) / R, box_spreads=box / sp_med if sp_med > 0 else np.nan, **s))
        kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        if kc < kend and box >= 2 * (D["ao"][kc] - D["bo"][kc]):
            s = path_stats(D, kc, kend, sc, ec, box, ec + 1e12 if sc > 0 else -1e12, ec - 1e12 if sc < 0 else 1e12)
            if s:
                rows.append(dict(mkt=sym, day=day, kind="CTRL", cost_R=(D["ao"][kc] - D["bo"][kc]) / box, box_spreads=np.nan, **s))
    return rows


def main():
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, SYMS))
    df = pd.DataFrame([r for rr in res for r in rr])
    df = df[df.day >= "2022-01-01"]
    df["cls"], df["year"] = df.mkt.map(mclass), df.day.dt.year
    df.to_parquet("data/si_ledgers/BRK_ANATOMY.parquet")
    b, c = df[df.kind == "BRK"], df[df.kind == "CTRL"]
    pd.set_option("display.width", 220)
    cols = ["back15", "back60", "hit1R", "hit2R", "hit3R", "mfe60", "mfe_all", "mae_all", "close_R", "cost_R"]
    print("ALL MARKETS, breakout vs random entry (means; hit = target before -1R; back = mid back inside the box):")
    print(pd.DataFrame({"breakout": b[cols].mean(), "random": c[cols].mean()}).T.round(3).to_string())
    print("\nmedian minutes from the fill to the best price (breakouts):", int(b.t_mfe.median()), "| median box size in spreads:", round(b.box_spreads.median(), 1))
    print("\nBY CLASS (breakouts): ")
    print(b.groupby("cls")[cols].mean().round(3).to_string())
    print("\nBY YEAR, breakout minus random on close_R (the breakout's own information), and the false-breakout rate:")
    yy = pd.DataFrame({"brk close_R": b.groupby("year").close_R.mean(), "rnd close_R": c.groupby("year").close_R.mean(),
                       "false 60m": b.groupby("year").back60.mean(), "hit2R": b.groupby("year").hit2R.mean(), "cost R": b.groupby("year").cost_R.mean()})
    yy["info (brk-rnd)"] = yy["brk close_R"] - yy["rnd close_R"]
    print(yy.round(3).to_string())
    bi, ci = b[b.cls == "index"], c[c.cls == "index"]
    yi = pd.DataFrame({"idx brk": bi.groupby("year").close_R.mean(), "idx rnd": ci.groupby("year").close_R.mean(), "idx false 60m": bi.groupby("year").back60.mean()})
    yi["idx info"] = yi["idx brk"] - yi["idx rnd"]
    print("\nINDICES by year:"); print(yi.round(3).to_string())
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
    ax[0].bar(yy.index - 0.2, yy["info (brk-rnd)"], 0.4, label="all markets", color="#1f6feb")
    ax[0].bar(yi.index + 0.2, yi["idx info"], 0.4, label="indices", color="#2e7d32")
    ax[0].axhline(0, color="#666", lw=0.8); ax[0].set_title("Breakout information = breakout minus random entry (R/trade)", fontsize=10); ax[0].legend()
    ax[1].plot(yy.index, yy["brk close_R"], "o-", label="breakout, all markets", color="#1f6feb")
    ax[1].plot(yi.index, yi["idx brk"], "o-", label="breakout, indices", color="#2e7d32")
    ax[1].plot(yy.index, -yy["cost R"], "s--", label="minus spread cost (R)", color="#c62828")
    ax[1].axhline(0, color="#666", lw=0.8); ax[1].set_title("Net result per trade (hold to close) vs the cost of one spread", fontsize=10); ax[1].legend(fontsize=8)
    for a in ax: a.grid(alpha=0.25)
    plt.tight_layout(); plt.savefig("data/scratch/charts/BRK_ANATOMY.png", dpi=110)
    print("chart data/scratch/charts/BRK_ANATOMY.png")


if __name__ == "__main__":
    main()
