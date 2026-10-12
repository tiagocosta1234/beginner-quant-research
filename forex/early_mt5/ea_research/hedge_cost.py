"""What does holding both long and short gold cost (and earn) in the live pair? SDB x1.5 + XAU5 x1.5, CPI/NFP/FOMC news-flat, per pool.
the trader 2026-10-12: "que jeito estarmos long e short no ouro?". Descriptive, read-only; the live config is unchanged.
Counts, per pool: share of trading time with both sides open, hedged ounces, and the effect of the no-hedge rule (drop the NEWER trade whose side is
opposite to a trade already open; it would be closed within about a second, costing the spread instead of its P&L).   python -m mt5broker.ea_research.hedge_cost"""
import os
import numpy as np, pandas as pd
from mt5broker.ea_research import combo_grid as G, clean_boot_lib as L
from mt5broker.ea_batch.mt5_mc_config import CH

tm, bc, sp = G.bars


def pool_trades(pool):
    src, a, b = L.POOLS[pool]; lo = L.day(a)
    s = L.ea_trades(src, "sdb", CH["sdb"] * 1.5, lo); x = L.ea_trades(src, "xau5", CH["xau5"] * 1.5, lo)
    tr = L.merge(s, x); tr["ea"] = np.concatenate([np.zeros(len(s["in_s"]), int), np.ones(len(x["in_s"]), int)])
    keep = np.ones(len(tr["in_s"]), bool)                                  # news_flat only needs the standard keys; carry ea through the same mask
    nf = G.news_flat({k: v for k, v in tr.items() if k != "ea"}, G.EV, G.bars)
    return nf, tr


def analyse(pool):
    nf, tr = pool_trades(pool)
    key = lambda d: set(zip(d["in_s"].tolist(), d["side"].tolist(), np.round(d["q"], 6).tolist()))
    in_s, out_s, side, q, pl = nf["in_s"], nf["out_s"], nf["side"], nf["q"], nf["pl"]
    order = np.argsort(in_s, kind="stable"); in_s, out_s, side, q, pl = in_s[order], out_s[order], side[order], q[order], pl[order]
    n = len(in_s); spr = sp[np.clip(np.searchsorted(tm, in_s), 0, len(sp) - 1)]
    # time with both sides open, and hedged ounces x time
    ev = np.concatenate([np.stack([in_s, side, q], 1), np.stack([out_s, side, -q], 1)]); ev = ev[np.argsort(ev[:, 0], kind="stable")]   # (time, side, +q open / -q close)
    lng = sht = 0.0; both = anyp = 0.0; hedged_oz_s = gross_oz_s = 0.0; last = ev[0, 0]
    for t, sd, dq in ev:
        dt = t - last
        if dt > 0:
            if lng > 1e-9 or sht > 1e-9: anyp += dt; gross_oz_s += dt * (lng + sht)
            if lng > 1e-9 and sht > 1e-9: both += dt; hedged_oz_s += dt * 2 * min(lng, sht)
        last = t
        if sd > 0: lng = max(lng + dq, 0.0)
        else: sht = max(sht + dq, 0.0)
    # no-hedge rule: drop a trade if, at its entry, an earlier-opened trade of the opposite side is still open
    dropped = np.zeros(n, bool)
    for i in range(n):
        j = np.nonzero((~dropped[:i]) & (in_s[:i] <= in_s[i]) & (out_s[:i] > in_s[i]) & (side[:i] == -side[i]))[0]
        if len(j): dropped[i] = True
    cost_each = spr * q
    out = dict(pool=pool, trades=n, dropped=int(dropped.sum()), pct_dropped=100 * dropped.mean(), pl_all=pl.sum(), pl_dropped=pl[dropped].sum(), pl_kept=pl[~dropped].sum(),
               spread_dropped=cost_each[dropped].sum(), pct_time_both=100 * both / anyp if anyp else 0, pct_oz_hedged=100 * hedged_oz_s / gross_oz_s if gross_oz_s else 0,
               nohedge_net_vs_live=pl[~dropped].sum() - cost_each[dropped].sum() - pl.sum())
    return out


if __name__ == "__main__":
    rows = [analyse(p) for p in ("MT5", "FT")]; R = pd.DataFrame(rows).set_index("pool").T
    txt = R.to_string(float_format=lambda v: f"{v:,.1f}"); print(txt); open(os.path.join(os.path.dirname(__file__), "HEDGE_COST_OUTPUT.txt"), "w").write(txt)
