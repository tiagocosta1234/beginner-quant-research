"""
Round 299b (2026-10-02, POST-HOC CONTROL, DESCRIPTIVE -- written after seeing Round 299's results and committed before it is run): is Round 299's gain from skipping days really the volatility information, or just from solving the dynamic programme with a tradable-day probability q < 1?
WHAT ROUND 299 SHOWED (BASE costs, OOS paths, paired against the IS-solved all-days baseline of 37.4%): skipping the bottom third of F1 / F2 / F3 gave +5.2 / +6.1 / +9.0 points, skipping the TOP third +1.5 / +3.9 / +3.1, keeping only the top half or third lost 10-23 points. Both tails helping, and the DEPLOYED table (solved on all days, including the OOS days)
scoring 49.5% unfiltered on the same paths against 37.4% for the IS-solved baseline, mean the baseline is a poor fit to the OOS days and a q < 1 table may simply fit them better by accident. This control removes the information and keeps the rest.
DESIGN (fixed now): the same IS-solved dynamic programme, the same 6,000 OOS paths (same seed 2991, so the same paths), BASE costs, but the tradable days are chosen AT RANDOM: for q in (0.65, 0.50, 0.33) and 5 seeds each (15 random masks): a random day-level mask with probability q over the IS days (to solve the programme: the outcomes of the masked-in IS days, tradable probability q), and an independent random mask with probability q
over the OOS days (to evaluate). Reported per q: the mean, min and max paired difference to the same baseline (37.4%, recomputed) across the 5 masks. A volatility filter shows INFORMATION only if its Round 299 paired difference exceeds the MAXIMUM of the 5 random masks at its q by more than 2 points (q = 0.65 for the skip-a-third filters, 0.50 for above-median, 0.33 for top-third-only).
PRIOR (stated now): random skipping does not help by itself (it loses opportunities); the expectation is a difference of about -3 to +2 points at q = 0.65 and clearly negative at q = 0.33. If random masks at q = 0.65 give +4 or more, Round 299's gains are mostly an artifact of how the tables are solved and no volatility filter has been shown to help.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import round273_optimal_one_step_policy as M
import round296_bold_play_one_step_by_31_dec as S6
import round299_volatility_filter_pass_policy as V

P, Q8, A, WINDOW, N, SEED = V.P, V.Q8, V.A, V.WINDOW, V.N, V.SEED
QS, NSEED = (0.65, 0.50, 0.33), 5


def main():
    t0 = time.time()
    cfd, days, rng_, cls, opn = V.day_frames()
    is_mask = days <= V.IS_END
    i_oos = int(is_mask.sum())
    n_oos = len(days) - i_oos
    z = np.load(V.TABLE)
    PL, _ = S6.per_lot("BASE")
    OUT0 = M.outcomes(V.sub(PL, slice(0, i_oos)))
    prb, pkb = V.solve_q(OUT0, 1.0, WINDOW)
    PL_oos0 = V.sub(PL, slice(i_oos, None))
    rng = np.random.default_rng(SEED)
    paths = [(P.boot_idx(rng, n_oos, WINDOW, P.BLOCK), rng.random(WINDOW) < 0.5) for _ in range(N)]
    b = np.array([V.run(Q8.path_arrays(PL_oos0, A, i, c), prb, pkb, WINDOW) == "pass" for i, c in paths], float)
    print(f"baseline (IS-solved, all days) P(pass) {b.mean():.1%} (Round 299: 37.4%)", flush=True)
    se = lambda x: 1.96 * np.std(x, ddof=1) / np.sqrt(len(x))
    out = {"baseline": float(b.mean()), "random": {}}
    for q in QS:
        diffs, ps = [], []
        for s in range(NSEED):
            r = np.random.default_rng(7000 + int(q * 100) * 10 + s)
            mi, mo = r.random(i_oos) < q, r.random(n_oos) < q
            prf, pkf = V.solve_q(M.outcomes(V.sub(PL, slice(0, i_oos), mi)), float(mi.mean()), WINDOW)
            PLf = V.sub(PL, slice(i_oos, None), mo)
            f = np.array([V.run(Q8.path_arrays(PLf, A, i, c), prf, pkf, WINDOW) == "pass" for i, c in paths], float)
            diffs.append(float((f - b).mean())); ps.append(float(f.mean()))
            print(f"q {q:.2f} random mask {s}: IS share {mi.mean():.2f}, OOS share {mo.mean():.2f}, P(pass) {f.mean():.1%}, vs baseline {100 * (f - b).mean():+.1f} +- {100 * se(f - b):.1f} pp ({time.time() - t0:.0f}s)", flush=True)
        out["random"][str(q)] = dict(diffs=diffs, p=ps, mean=float(np.mean(diffs)), min=float(np.min(diffs)), max=float(np.max(diffs)))
        print(f"== q {q:.2f}: mean {100 * np.mean(diffs):+.1f}, min {100 * np.min(diffs):+.1f}, max {100 * np.max(diffs):+.1f} pp", flush=True)
    r9 = json.load(open(os.path.join(HERE, "round299_results.json")))
    verdict = {}
    for nm, v in r9["filters"].items():
        q = 0.65 if ("skip_" in nm) else (0.50 if "above_median" in nm else 0.33)
        mx = out["random"][str(q)]["max"]
        d = v["BASE"]["diff"]
        verdict[nm] = dict(q=q, filter_diff=d, random_max=mx, informative=bool(d - mx > 0.02))
        print(f"{nm:>40}: filter {100 * d:+.1f} pp vs max of 5 random masks at q {q:.2f} {100 * mx:+.1f} pp -> informative beyond random skipping: {verdict[nm]['informative']}")
    out["verdict"] = verdict
    json.dump(out, open(os.path.join(HERE, "round299b_results.json"), "w"), indent=1, default=float)
    print(f"Saved round299b_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
