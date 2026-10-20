"""EMA1000 follow-up, DESCRIPTIVE ONLY (PREREG_EMA1000.md reports section: per-market table and the random-side comparison; extended here from the top 5 to all 1,000 variants, never a bar, no new candidate can come from it).
python ema1000_followup.py     same 1,000 variants x 46 markets, each trade also simulated on the MIRROR side (same minute, same distances); skill = (R_rule - R_mirror) / 2 = excess over a random side.
Reads EMA1000_TRIALS.csv / EMA1000_MARKETS.csv (from the run) and writes EMA1000_FOLLOWUP_OUTPUT.txt."""
import time, numpy as np, pandas as pd
from multiprocessing import Pool
from ema1000 import *
def run_mirror(m):
    t0 = time.time(); M = load_market(m); bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}; cc = {}; sg = {}; out = {}
    for v in VARIANTS:
        ck = (v["tf"], v["ema"], v["body"], v["trend"])
        if ck not in cc: cc[ck] = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"])
        sk = (v["ses"], v["win"], v["tgt"]) + ck
        if sk not in sg: sg[sk] = signals(M, bars[v["tf"]], cc[ck][0], cc[ck][1], v["ses"], v["win"], v["tgt"])
        s = sg[sk]; sm = [(dy, e, -sd, (M["bo"][e] if sd > 0 else M["ao"][e]), d, t) for (dy, e, sd, entry, d, t) in s]
        out[v["id"]] = (np.array([x[0] for x in s], dtype=np.int32), simulate(M, s, v["stop"]).astype(np.float32), simulate(M, sm, v["stop"]).astype(np.float32))
    return m, out, time.time() - t0
if __name__ == "__main__":
    t0 = time.time(); res = {}
    with Pool(8) as p:
        for m, r, sec in p.imap_unordered(run_mirror, MARKETS): res[m] = r
    ms = sorted(res); T = pd.read_csv("EMA1000_TRIALS.csv"); rows = []
    for v in VARIANTS:
        d = np.concatenate([res[m][v["id"]][0] for m in ms]); Rr = np.concatenate([res[m][v["id"]][1] for m in ms]).astype(float); Rm = np.concatenate([res[m][v["id"]][2] for m in ms]).astype(float); sk = (Rr - Rm) / 2
        dev = (d >= D0) & (d <= DEV_END); val = (d > DEV_END) & (d <= VAL_END); a, b = cstats(d[dev], sk[dev]), cstats(d[val], sk[val])
        rows.append(dict(id=v["id"], dev_net=Rr[dev].mean(), dev_random_side=((Rr + Rm) / 2)[dev].mean(), dev_skill=a["mean"], dev_skill_t=a["t"], val_net=Rr[val].mean(), val_skill=b["mean"], val_skill_t=b["t"]))
    F = pd.DataFrame(rows).merge(T[["id", "ema", "tf", "body", "win", "tgt", "stop", "ses", "trend", "dev_n", "dev_t"]], on="id"); F.to_csv("EMA1000_FOLLOWUP.csv", index=False); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("follow-up finished in %.1f min | variants %d" % ((time.time() - t0) / 60, len(F)))
    print("\nMEAN R OF A RANDOM SIDE on the same entries (this is the cost / structure drag): median over variants %+.4f (min %+.4f, max %+.4f)" % (F.dev_random_side.median(), F.dev_random_side.min(), F.dev_random_side.max()))
    print("DIRECTION SKILL of the rule = excess over a random side (DEV, day-clustered): median %+.4f R | share of variants with skill > 0: %.0f%% | skill t: min %.2f, 5%% %.2f, median %.2f, 95%% %.2f, max %.2f | t >= 3.72: %d | t >= 2.58: %d" % (F.dev_skill.median(), 100 * (F.dev_skill > 0).mean(), F.dev_skill_t.min(), *F.dev_skill_t.quantile([.05]), F.dev_skill_t.median(), F.dev_skill_t.quantile(.95), F.dev_skill_t.max(), (F.dev_skill_t >= 3.72).sum(), (F.dev_skill_t >= 2.58).sum()))
    print("VAL 2025: median skill %+.4f R, share positive %.0f%%, median net %+.4f" % (F.val_skill.median(), 100 * (F.val_skill > 0).mean(), F.val_net.median()))
    print("\nthe 5 registered 'top 5 by DEV t' (random-side comparison):"); print(F.sort_values("dev_t", ascending=False).head(5)[["id", "tf", "ses", "tgt", "stop", "dev_n", "dev_net", "dev_random_side", "dev_skill", "dev_skill_t", "val_skill", "val_skill_t"]].round(4).to_string(index=False))
    print("\ntop 10 variants by DEV skill t (descriptive; a skill that is positive but smaller than the drag still loses money):"); print(F.sort_values("dev_skill_t", ascending=False).head(10)[["id", "ema", "tf", "body", "win", "tgt", "stop", "ses", "trend", "dev_n", "dev_net", "dev_random_side", "dev_skill", "dev_skill_t", "val_skill", "val_skill_t"]].round(4).to_string(index=False))
    for ax in ("tf", "tgt", "stop", "ses"): print("\nmedian DEV skill by %s:" % ax, F.groupby(ax).dev_skill.median().round(4).to_dict(), "| median random-side R:", F.groupby(ax).dev_random_side.median().round(4).to_dict())
    Mk = pd.read_csv("EMA1000_MARKETS.csv"); g = Mk.groupby("market").agg(med_dev_R=("dev_R", "median"), best_dev_R=("dev_R", "max"), n_pos=("dev_R", lambda x: int((x > 0).sum())), med_n=("dev_n", "median")).sort_values("med_dev_R", ascending=False)
    print("\nper market, over the 1,000 variants (DEV mean R): the 10 least negative and the 6 most negative:"); print(pd.concat([g.head(10), g.tail(6)]).round(4).to_string())
    print("markets with a positive MEDIAN DEV mean R over the 1,000 variants:", list(g.index[g.med_dev_R > 0]) or "none")
