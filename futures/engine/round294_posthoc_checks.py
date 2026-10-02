"""
Round 294, POST-HOC CHECKS (2026-10-02; written AFTER the pre-registered run, descriptive only, no ledger row, no new verdict).
Why: in sample, 377 parameter sets met the trader's goal numbers against 49 in the no-edge placebo, and the before-cost R per trade of a set in the first half predicts its second half (rank correlation +0.383 against
-0.003 in the placebo). The placebo randomises each gap's SIGN, so it also removes the market's own drift: NQ roughly tripled over 2019-2026, and a long position held to the close earns that drift without any
signal. These checks ask where the in-sample winners come from:
  (A) composition of the goal-meeting sets (instrument, target, side, mode);
  (B) before-cost R per trade of long-only and short-only sets, and the first-half / second-half rank correlation WITHIN one side (if the persistence is the long-short split, it shrinks inside a side);
  (C) two benchmarks for chosen sets, same side, same stop distance, same exit rule, same cost:
        B1 "same clock time, another day": the entry moved to the same session minute of a random other trading day within +-20 trading days (keeps the era's drift and volatility, removes the signal);
        B2 "same day, a random LATER time": the entry moved to a random later minute of the SAME day, up to 15:50 (keeps the day and the side the signal chose, removes the gap-touch timing; later only,
           because an earlier entry in the direction of a later signal would use information from the future -- a first version that drew from the whole segment did exactly that and is discarded).
      10 draws per trade for each. If the real trades make no more than the benchmarks, the profit is the market's drift and the clock, not the indicator.
  (D) the one change that helps in the one-parameter table -- no target, hold to 15:55 -- on the as-written cell of every instrument and candle: per half-year, in the ledger's own split, with its drawdown.
  (E) what the trader's goal means as a Sharpe ratio (pure simulation, no market data; the table quoted in the pre-registration's POWER_NOTES, reproduced here with its code).
Needs the cache of the real run (round294's --out directory, default %TEMP%/r294_cache).
"""
import os, sys, json, pickle, tempfile, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from types import SimpleNamespace as NS
import round294_fvg_vwap_killzone_sentinel as R

CACHE = sys.argv[sys.argv.index("--cache") + 1] if "--cache" in sys.argv else os.path.join(tempfile.gettempdir(), "r294_cache")
NDRAW = 10


def cfg_mask(code, cfg):
    k, v, s, a, d, p = np.unravel_index(int(cfg), R.CFG_SHAPE)
    seg, vw, sz, ag, dr, cs = np.unravel_index(code, R.CELL_SHAPE)
    return (R.KZ[k, seg] > 0) & (R.VW[v, vw] > 0) & (R.SZ[s, sz] > 0) & (R.AG[a, ag] > 0) & (R.DR[d, dr] > 0) & (R.CS[p, cs] > 0)


def cboot(days, x, nb=4000, seed=7):
    u, inv = np.unique(days, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    ix = rng.integers(0, len(u), (nb, len(u)))
    m = s[ix].sum(1) / c[ix].sum(1)
    return float((m > 0).mean()), float(m.std())


def bench(B, f_new, d, dist, q, ts):
    """Market entry at the open of bar f_new, stop `dist` ticks away, the block's target / time stop; returns before-cost R (the same cost applies to real and benchmark)."""
    fill = B.o[f_new]
    S = fill - d * dist.astype(np.int64)
    tps = fill[:, None] + d[:, None] * np.rint(R.RRS[None, :] * dist[:, None]).astype(np.int64)
    day = B.day[f_new]
    SC = NS(n=len(f_new), f=f_new, d=d, day=day, fill=fill, ref=fill, S=S, dist=dist.astype(float), x=B.X[day], pflat=B.pflat[day], tps=tps, cost=0.0)
    SC.sc = R.scan(B, SC.f, SC.x, SC.d, SC.S, SC.tps, False)
    Rn, _ = R.outcome(B, SC, q, ts, 0)
    return Rn


def check_set(sym, tf, blk, cfg, label, rng, cache={}):
    key = (sym, tf)
    if key not in cache:
        cache.clear()
        B = R.load_1m(sym); T = R.tf_bars(B, tf); cache[key] = (B, T, R.detect(T))
    B, T, G = cache[key]
    depth, mode, stop, q, ts, inv = blk
    assert not inv
    for b, SC, Rn, cR, code, _, _ in R.job_blocks(B, T, G, only=[blk]):
        m = cfg_mask(code, cfg)
        f, d, dist, day, gross, net = SC.f[m], SC.d[m], SC.dist[m], SC.day[m], (Rn + cR)[m], Rn[m]
        n = len(f)
        key1 = B.day * 2000 + B.sess
        good_days = np.flatnonzero(B.d_last >= B.d_first)
        pos = np.searchsorted(good_days, day)
        res = {}
        for name in ("B1 same clock time, another day", "B2 same day, a random later time"):
            tot = np.zeros(n); cnt = np.zeros(n)
            for _ in range(NDRAW):
                if name.startswith("B1"):
                    off = rng.integers(1, 21, n) * rng.choice(np.array([-1, 1]), n)
                    dd = good_days[np.clip(pos + off, 0, len(good_days) - 1)]
                    sm = B.sess[f]
                else:
                    dd = day
                    lo = B.sess[f] + 1
                    sm = lo + (rng.random(n) * np.maximum(R.CUT_S - lo, 1)).astype(np.int64)
                fn = np.searchsorted(key1, dd * 2000 + sm, "left")
                fn = np.minimum(fn, B.n - 1)
                ok = (B.day[fn] == dd) & (B.sess[fn] - sm <= 5) & (fn < B.X[dd]) & (B.sess[fn] < R.CUT_S) & (dd != day if name.startswith("B1") else fn != f)
                r = bench(B, fn[ok], d[ok], dist[ok], q, ts)
                tot[ok] += r; cnt[ok] += 1
            has = cnt > 0
            bm = tot[has] / cnt[has]
            diff = gross[has] - bm
            p, se = cboot(day[has], diff)
            res[name] = dict(n=int(has.sum()), bench_gross=float(bm.mean()), real_gross=float(gross[has].mean()), diff=float(diff.mean()), se=se, p_diff_pos=p,
                             diff_long=float(diff[d[has] > 0].mean()) if (d[has] > 0).any() else float("nan"), diff_short=float(diff[d[has] < 0].mean()) if (d[has] < 0).any() else float("nan"))
        out = dict(label=label, sym=sym, tf=tf, block=R.block_name(blk), filters=R.cfg_name(cfg), n=int(n), gross=float(gross.mean()), net=float(net.mean()), cost=float((gross - net).mean()),
                   long_n=int((d > 0).sum()), long_gross=float(gross[d > 0].mean()) if (d > 0).any() else float("nan"), short_n=int((d < 0).sum()), short_gross=float(gross[d < 0].mean()) if (d < 0).any() else float("nan"),
                   monthly_net_R=float(net.sum() / R.MONTHS_ALL), benchmarks=res)
        print(f"\n{label}: {sym} {tf}-min | {out['block']} | {out['filters']}")
        print(f"   {n:,} trades: before costs {out['gross']:+.3f}R, cost {out['cost']:.3f}R, net {out['net']:+.3f}R ({out['monthly_net_R']:+.1f}R a month); longs {out['long_n']:,} at {out['long_gross']:+.3f}R, shorts {out['short_n']:,} at {out['short_gross']:+.3f}R before costs")
        for name, v in res.items():
            print(f"   {name:<34}: benchmark {v['bench_gross']:+.3f}R before costs vs real {v['real_gross']:+.3f}R -> the signal adds {v['diff']:+.3f}R (se {v['se']:.3f}, P(> 0) {v['p_diff_pos']:.2f}; longs {v['diff_long']:+.3f}, shorts {v['diff_short']:+.3f})")
        return out


def main():
    metas = {(s, tf): pickle.load(open(os.path.join(CACHE, f"meta_{s}_{tf}.pkl"), "rb")) for s in R.SYMS for tf in R.TFS}
    out = {}
    # (A) composition of the goal-meeting sets
    comp = {k: {} for k in ("instrument", "candle", "target", "side", "bet", "entry", "stop", "killzone", "vwap")}
    n_goal = 0
    side_rows = []
    samp = {k: [] for k in ("both", "long", "short")}
    rng = np.random.default_rng(29401)
    best_sets = []
    for (s, tf), me in metas.items():
        summ = np.load(os.path.join(CACHE, f"summ_{s}_{tf}.npy"))
        mon = summ[..., 0].astype(np.float64) / R.MONTHS_ALL
        goal = (summ[..., 2] >= 500) & (mon > 0) & (summ[..., 1] <= 10 * mon)
        bi, ci = np.nonzero(goal)
        n_goal += len(bi)
        for b_, c_ in zip(bi, ci):
            depth, mode, stop, q, ts, inv = me["blocks"][b_]
            k, v, sz, a, d, p = np.unravel_index(int(c_), R.CFG_SHAPE)
            for key, val in (("instrument", s), ("candle", f"{tf}-min"), ("target", "none" if q == R.NRR else f"{R.RRS[q]:g}R"), ("side", R.DR_NAMES[d]), ("bet", "inverted" if inv else "normal"),
                             ("entry", f"{mode} at depth {depth:g}"), ("stop", stop), ("killzone", R.KZ_NAMES[k]), ("vwap", R.VW_NAMES[v])):
                comp[key][val] = comp[key].get(val, 0) + 1
            best_sets.append((float(mon[b_, c_] / max(summ[b_, c_, 1], 1e-9)), s, tf, tuple(me["blocks"][b_]), int(c_)))
        # (B) before-cost R per trade by side, all hours, VWAP off, no other filter, normal bets
        n1, n2 = summ[..., 8].astype(np.float64), summ[..., 9].astype(np.float64)
        gross = (summ[..., 10] * n1 + summ[..., 11] * n2) / np.maximum(n1 + n2, 1.0)
        for b_, blk in enumerate(me["blocks"]):
            depth, mode, stop, q, ts, inv = blk
            if inv or ts or mode != "close" or depth != 0.0 or stop != "struct":
                continue
            for dname, didx in (("long", 1), ("short", 2)):
                c_ = np.ravel_multi_index((6, 1, 0, 0, didx, 0), R.CFG_SHAPE)
                side_rows.append(dict(sym=s, tf=tf, target="none" if q == R.NRR else f"{R.RRS[q]:g}R", side=dname, gross=float(gross[b_, c_]), n=float(n1[b_, c_] + n2[b_, c_]),
                                      gross_h1=float(summ[b_, c_, 10]), gross_h2=float(summ[b_, c_, 11])))
        # rank correlation of before-cost R per trade between halves, within a side
        e12 = (summ[..., 8] >= 300) & (summ[..., 9] >= 300)
        dr = np.unravel_index(np.arange(R.NCFG), R.CFG_SHAPE)[4]
        for name, didx in (("both", 0), ("long", 1), ("short", 2)):
            mm = e12 & (dr == didx)[None, :]
            idx = np.flatnonzero(mm.ravel())
            if len(idx):
                pick = rng.choice(idx, min(25000, len(idx)), replace=False)
                samp[name].append(np.stack([summ[..., 10].ravel()[pick], summ[..., 11].ravel()[pick]], axis=1))
    out["A_goal_sets"] = dict(n=n_goal, composition=comp)
    print(f"(A) the {n_goal} parameter sets that meet the goal numbers in sample, by setting:")
    for key, dct in comp.items():
        print(f"    {key:<10}: " + ", ".join(f"{k} {v}" for k, v in sorted(dct.items(), key=lambda z: -z[1])))
    sr = pd.DataFrame(side_rows)
    out["B_side"] = {}
    print("\n(B) before-cost R per trade, close entry at the gap edge, struct stop, all hours, no VWAP or other filter (mean over the five candle sizes; first half / second half):")
    for s in R.SYMS:
        for tgt in ("1R", "none"):
            row = {}
            for side in ("long", "short"):
                x = sr[(sr["sym"] == s) & (sr["target"] == tgt) & (sr["side"] == side)]
                row[side] = dict(gross=float(np.average(x["gross"], weights=x["n"])), h1=float(x["gross_h1"].mean()), h2=float(x["gross_h2"].mean()), n=float(x["n"].sum()))
            out["B_side"][f"{s}|{tgt}"] = row
            print(f"    {s} target {tgt:>4}: longs {row['long']['gross']:+.3f}R ({row['long']['h1']:+.3f} / {row['long']['h2']:+.3f}), shorts {row['short']['gross']:+.3f}R ({row['short']['h1']:+.3f} / {row['short']['h2']:+.3f})")
    out["B_corr"] = {}
    for name, parts in samp.items():
        x = np.concatenate(parts)
        rho = float(pd.Series(x[:, 0]).corr(pd.Series(x[:, 1]), method="spearman"))
        out["B_corr"][name] = dict(rho=rho, n=int(len(x)))
    print("    rank correlation of the before-cost R per trade, first half vs second half, within one side: " + ", ".join(f"{k} sides {v['rho']:+.3f}" if k == "both" else f"{k} only {v['rho']:+.3f}" for k, v in out["B_corr"].items()))
    # (C) benchmarks
    res = json.load(open(os.path.join(HERE, "round294_results.json")))
    b = res["in_sample"]["best"]
    rng = np.random.default_rng(29402)
    sets = [("best in-sample set", b["sym"], b["tf"], tuple(b["blk"]), b["cfg"])]
    for sym in R.SYMS:
        for tf in ((1, 2, 3, 5, 15) if sym == "NQ" else (3, 5, 15)):
            sets.append((f"as written but no target, {sym} {tf}-min", sym, tf, (0.0, "close", "struct", R.NRR, 0, 0), 0))
    sets.append(("as written, NQ 5-min", "NQ", 5, R.AS_WRITTEN, 0))
    sets.append(("as written, NQ 15-min", "NQ", 15, R.AS_WRITTEN, 0))
    sets.sort(key=lambda z: (z[1], z[2]))
    print("\n(C) real trades against two benchmarks with the same side, stop distance, exit rule and cost:")
    out["C_benchmarks"] = [check_set(sym, tf, blk, cfg, label, rng) for label, sym, tf, blk, cfg in sets]
    # (D) as written but no target, per half-year
    print("\n(D) as written but NO TARGET (hold to 15:55), every signal at 1R: net R per half-year, then the ledger's own statistics")
    print(f"    {'':<10}" + "".join(f"{str(d.date())[2:7]:>7}" for d in R.CAL[R.SEG_START]) + "   total  /month  maxDD  Sharpe  P IS/OOS")
    out["D_no_target"] = {}
    split = int(R.SEG_START[R.OOS_SEG0])
    for sym in R.SYMS:
        for tf in R.TFS:
            x = R.block_daily(sym, tf, (0.0, "close", "struct", R.NRR, 0, 0), [0])[0]
            row = R.judge(f"as written, no target, {sym} {tf}-min", x["daily"], x["cnt_seg"].sum(), x["cost_seg"].sum(), 0, R.D, R.MONTHS_ALL, split)
            hy = np.add.reduceat(x["daily"], R.SEG_START)
            row["half_years"] = hy.tolist()
            row["annual_sharpe"] = float(row["daily_sharpe"] * np.sqrt(252))
            out["D_no_target"][f"{sym}|{tf}"] = row
            print(f"    {sym} {tf:>2}-min " + "".join(f"{v:>+7.0f}" for v in hy) + f" {row['total_R']:>+7.0f} {row['monthly_R']:>+7.1f} {row['maxdd_R']:>6.0f}  {row['annual_sharpe']:>+6.2f}  {row['p_is']:.2f}/{row['p_oos']:.3f}")
    # (E) the goal as a Sharpe ratio
    print("\n(E) P(max drawdown <= 10 months of average profit) for independent normal daily returns, by annualised Sharpe (and <= 5 months, the $50K-account version):")
    out["E_goal_sharpe"] = {}
    rs = np.random.default_rng(1)
    for months in (60, 84):
        n = int(months * 21)
        for S in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            x = rs.normal(S / np.sqrt(252), 1.0, (4000, n))
            cum = np.cumsum(x, axis=1)
            dd = (np.maximum(np.maximum.accumulate(cum, axis=1), 0) - cum).max(axis=1)
            mon = cum[:, -1] / months
            v = dict(p10=float(((mon > 0) & (dd <= 10 * mon)).mean()), p5=float(((mon > 0) & (dd <= 5 * mon)).mean()), median_dd_months=float(np.median(dd[mon > 0] / mon[mon > 0])))
            out["E_goal_sharpe"][f"{months}|{S}"] = v
            print(f"    {months} months, Sharpe {S:.1f}: {v['p10']:6.1%} (<= 5 months {v['p5']:6.1%}); median drawdown {v['median_dd_months']:.1f} months of profit")
    json.dump(out, open(os.path.join(HERE, "round294_posthoc.json"), "w"), indent=1, default=float)
    print("\nSaved round294_posthoc.json")


if __name__ == "__main__":
    main()
