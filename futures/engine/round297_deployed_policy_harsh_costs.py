"""
Round 297 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no edge claim, no ledger row): the DEPLOYED 1-Step pass policy (forex/specs/round275_onestep_policy_risk1000.npz, the table forex/executor.py reads) re-measured on HARSH costs
(the trader: "yes re-measure it on harsh costs"). SIMULATION ONLY: nothing trades, buys or connects to anything.
BACKGROUND: Round 296 measured Round 270's heuristic (39.7% base / 26.1% harsh, 57 days). The executor does NOT run that heuristic: it runs Round 275's dynamic-programming policy with a $1,000 risk cap, measured 41.6% (breach 10%) on BASE costs over 62 days. This round gives that table its harsh-cost number.
COSTS (as Round 296): BASE = round249 BASE (spread x1, entry slip 1.0 pt, stop slip 0.5 pt); HARSH = spread x2, entry slip 5.0, stop slip 2.0. The 2026-10-02 free-trial probe (5 clean round trips, quiet overnight market, 0.01 lot) sits at or inside BASE and does not measure the 09:30 NY open.
POLICIES (two, fixed now): (A) THE DEPLOYED TABLE exactly as stored (solved on BASE outcomes, cap $1,000, payoff <= $5,000), run with the executor's table lookup; (B) the same dynamic programme RE-SOLVED on HARSH outcomes (cap $1,000, payoff <= $5,000) -- does knowing the costs are harsher change what to do? B is descriptive: the executor would need a new table to use it.
WINDOWS: 62 trading days (account started 2026-10-05, or today if ready before 09:30 NY: the table is indexed 0..61) and 57 (started 2026-10-12; the table is run for 57 days, the DP for B is solved for 57 days so B shortens its own horizon, A does not -- A is what the executor would do).
SCENARIOS: 2 cost levels x 2 windows x {A, B} (B only differs from A in solving on harsh outcomes). EVALUATION: 6,000 fresh 5-day-block bootstrap paths per (costs, window) (seed 2971), coin-flip direction, real per-lot outcomes of the matching cost level, the exact best-day rule (smallest ticket continues if unmet), Round 273's `run_policy`, SAME paths for A and B and
for the Round 270 heuristic (Round 296's policy, for the paired comparison). Reported: P(pass), P(breach), P(not passed by the deadline), +-1.96 se, paired differences.
CODE CHECKS (dry run): (1) the stored table equals a fresh BASE re-solve of the dynamic programme on the share of states printed (information only; ties may differ); (2) on BASE and 62 days, policy A on 300 paths = Round 273's `run_policy` on the same paths (same function, so identical) and the heuristic equals Round 270's `attempt1`;
(3) the harsh per-lot arrays differ from base. After the run: the BASE / 62-day result for A must lie within 2.4 points of Round 275's 41.6% (the code-reproduction check).
DECISION RULE (fixed now): the quoted harsh-cost number for the executor is A at 62 days (primary) and A at 57 days; B is quoted only as what a harsh-aware table would add, and it counts as a real improvement only if it beats A by more than 2 standard errors of the paired difference.
PRIOR (stated now): A on BASE 62 days about 41-42%; on HARSH about 27-32% (the heuristic fell 13 points; the $1,000 cap makes the stop distance a smaller share of room, so the harsh fall could be slightly different); B beats A by 0-2 points; the 57-day windows are within 2 points of the 62-day ones.
POWER_NOTES: +-1.2 points near 40%; one policy per cell, no selection on the evaluation paths; the executor adds guards the DP does not model (spread guard, risk <= 90% of room, MIN risk $250, safety close at $150 from the floor), the entry-grace window (09:45), no-trade dates (26-27 Nov, 24-25 Dec) and real order latency; direction is a coin flip.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import numpy as np
import round273_optimal_one_step_policy as M
import round296_bold_play_one_step_by_31_dec as S6

P, Q8, O1, KS, A = M.P, M.Q8, M.O1, M.KS, M.A
FULL = (250, 500, 750, 1000, 1500, 2000, 2500, 3000)
WINDOWS = (62, 57)
COSTS = ("BASE", "HARSH")
N, SEED = 6000, 2971
TABLE = os.path.join(ROOT, "mt5broker", "specs", "round275_onestep_policy_risk1000.npz")


def solve_cap1000(OUT, window):
    saved_r, saved_w = M.RGRID, M.W
    try:
        M.RGRID = tuple(r for r in FULL if r <= 1000)
        M.W = window
        _, pr, pk = M.solve(OUT, 5000)
        return pr, pk
    finally:
        M.RGRID, M.W = saved_r, saved_w


def run(Q, pr, pk, window):
    saved = M.W
    try:
        M.W = window
        return M.run_policy(Q, pr, pk)
    finally:
        M.W = saved


def heuristic(Q, window):
    return S6.attempt(Q, 1500, 0.75, window)[0]


def dry_run():
    z = np.load(TABLE)
    print(f"stored table {z['risk'].shape}, ks {list(z['ks'])}, max risk ${int(z['risk'].max())}")
    PL, days = S6.per_lot("BASE")
    n = len(days)
    OUT = M.outcomes(PL)
    t0 = time.time()
    pr, pk = solve_cap1000(OUT, 62)
    same = float(np.mean((pr == z["risk"]) & (pk == z["k_index"])))
    print(f"fresh BASE re-solve (cap $1,000, 62 days) in {time.time() - t0:.0f}s: equals the stored table on {same:.1%} of the {pr.size:,} states")
    rng = np.random.default_rng(3)
    eq = eqh = 0
    for _ in range(300):
        idxs, coin = P.boot_idx(rng, n, 62, P.BLOCK), rng.random(62) < 0.5
        Q = Q8.path_arrays(PL, A, idxs, coin)
        eq += run(Q, z["risk"], z["k_index"], 62) == M.run_policy(Q, z["risk"], z["k_index"])
        Q25 = Q8.path_arrays(PL, 0.25, idxs, coin)
        eqh += (heuristic(Q25, 62) == O1.attempt1(Q25, 1500, 0.75)[0])
    print(f"policy A = Round 273 run_policy on {eq} of 300 paths; heuristic = Round 270 attempt1 on {eqh} of 300 paths")
    assert eq == 300 and eqh == 300
    PLH, _ = S6.per_lot("HARSH")
    assert not np.allclose(np.nan_to_num(PL[(A, 2.5, 1)][0]), np.nan_to_num(PLH[(A, 2.5, 1)][0]))
    print(f"HARSH arrays differ from BASE; mean net R per ticket by k, BASE: {[round(float(o[0].mean()), 3) for o in OUT]}; HARSH: {[round(float(o[0].mean()), 3) for o in M.outcomes(PLH)]}")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    z = np.load(TABLE)
    tabA = (z["risk"], z["k_index"])
    out = {"scenarios": {}}
    se = lambda x: 1.96 * np.std(x, ddof=1) / np.sqrt(len(x))
    for cname in COSTS:
        PL, days = S6.per_lot(cname)
        n = len(days)
        OUT = M.outcomes(PL)
        tabB = {w: solve_cap1000(OUT, w) for w in WINDOWS}
        for w in WINDOWS:
            rng = np.random.default_rng(SEED + w)
            ra, rb, rh = [], [], []
            fa = oa = fb = ob = 0
            for _ in range(N):
                idxs, coin = P.boot_idx(rng, n, w, P.BLOCK), rng.random(w) < 0.5
                Q = Q8.path_arrays(PL, A, idxs, coin)
                a = run(Q, tabA[0], tabA[1], w)
                b = run(Q, tabB[w][0], tabB[w][1], w)
                ra.append(a == "pass"); rb.append(b == "pass"); fa += a == "fail"; oa += a == "open"; fb += b == "fail"; ob += b == "open"
                Q25 = Q8.path_arrays(PL, 0.25, idxs, coin)
                rh.append(heuristic(Q25, w) == "pass")
            a, b, h = (np.array(x, float) for x in (ra, rb, rh))
            out["scenarios"][f"{w}|{cname}"] = dict(window=w, costs=cname,
                A=dict(p=float(a.mean()), se=float(se(a)), breach=fa / N, open=oa / N),
                B=dict(p=float(b.mean()), se=float(se(b)), breach=fb / N, open=ob / N, diff_vs_A=float((b - a).mean()), diff_se=float(se(b - a))),
                heuristic=dict(p=float(h.mean()), se=float(se(h)), diff_A_minus_heur=float((a - h).mean()), diff_se=float(se(a - h))))
            print(f"window {w} costs {cname:>5} | A (deployed table) pass {a.mean():.1%} +- {se(a):.1%}, breach {fa / N:.1%}, not passed {oa / N:.1%} | B (re-solved on {cname}) {b.mean():.1%} +- {se(b):.1%} "
                  f"(vs A {100 * (b - a).mean():+.1f} +- {100 * se(b - a):.1f} pp), breach {fb / N:.1%} | Round 270 heuristic {h.mean():.1%} (A minus heuristic {100 * (a - h).mean():+.1f} +- {100 * se(a - h):.1f}) ({time.time() - t0:.0f}s)", flush=True)
    base62 = out["scenarios"]["62|BASE"]["A"]["p"]
    out["code_check_within_2_4_points_of_round275"] = bool(abs(base62 - 0.416) <= 0.024)
    print(f"CODE CHECK: A on BASE / 62 days {base62:.1%} vs Round 275's 41.6%: within 2.4 points = {out['code_check_within_2_4_points_of_round275']}")
    json.dump(out, open(os.path.join(HERE, "round297_results.json"), "w"), indent=1, default=float)
    print(f"Saved round297_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
