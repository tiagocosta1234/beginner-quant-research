"""
Round 275 (2026-10-01, DESCRIPTIVE sensitivity, no edge claim, no ledger row): what does respecting MT5 broker's recommended risk per trade
cost the 1-Step pass policy? the trader: "check if we're allowed to take trades on a 100k account with 2% risk". MT5 (blog, read 2026-10-01):
no hard limit on the share of the account risked per trade, but "the maximum recommended risk on one trading position is 1% to 1.5% of
the initial account balance"; above it MT5 broker may start "high-risk monitoring" (contact, protective measures); it describes tossing a coin
in the hope of scoring as gambling. Round 273's policy risks up to 2% ($2,000) a ticket.

DESIGN: Round 273's dynamic programme re-solved with the risk grid capped at $1,000 / $1,500 / $2,000 (r x k <= $5,000 unchanged), each
evaluated on the SAME 6,000 fresh block-bootstrap paths (seed 2751, coin-flip direction, base costs, exact best-day rule) against the
unrestricted Round 273 policy (cap $3,000, in practice mostly $2,000). Reported: pass, breach, out-of-days shares and the paired
difference. One policy per cap, no selection.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import round273_optimal_one_step_policy as M

P, Q8, R, W, A = M.P, M.Q8, M.R, M.W, M.A
FULL = (250, 500, 750, 1000, 1500, 2000, 2500, 3000)
CAPS = (1000, 1500, 2000)
N, SEED = 6000, 2751


def main():
    raw, cfd = R.load_cfd()
    _, per, _, _ = R.data_checks(raw, cfd)
    skip, _ = R.calendar_check(per)
    PL, days = Q8.per_lot_arrays(cfd, skip)
    n_days = len(days)
    OUT = M.outcomes(PL)
    npz = np.load(os.path.join(HERE, "..", "..", "mt5broker", "specs", "round273_onestep_policy_cap5000.npz"))
    pols = {"unrestricted (cap $3,000)": (npz["risk"], npz["k_index"])}
    for cap in CAPS:
        M.RGRID = tuple(r for r in FULL if r <= cap)
        t0 = time.time()
        _, pr, pk = M.solve(OUT, 5000)
        pols[f"risk <= ${cap:,}"] = (pr, pk)
        print(f"solved risk <= ${cap:,} in {time.time() - t0:.0f}s", flush=True)
    rng = np.random.default_rng(SEED)
    res = {k: [] for k in pols}
    shares = {k: [0, 0] for k in pols}
    for _ in range(N):
        idxs, coin = P.boot_idx(rng, n_days, W, P.BLOCK), rng.random(W) < 0.5
        Q = Q8.path_arrays(PL, A, idxs, coin)
        for k, (pr, pk) in pols.items():
            r = M.run_policy(Q, pr, pk)
            res[k].append(r == "pass"); shares[k][0] += r == "fail"; shares[k][1] += r == "open"
    base = np.array(res["unrestricted (cap $3,000)"], float)
    se = lambda x: 1.96 * np.std(x, ddof=1) / np.sqrt(len(x))
    out = {}
    print(f"\n=== {N} fresh paths: P(pass by 30 Dec), one $100K 1-Step evaluation ===")
    for k in pols:
        a = np.array(res[k], float); d = a - base
        out[k] = dict(p=float(a.mean()), se=float(se(a)), diff=float(d.mean()), diff_se=float(se(d)), breach=shares[k][0] / N, open=shares[k][1] / N)
        print(f"{k:>26}: pass {a.mean():.1%} +- {se(a):.1%} | breach {shares[k][0] / N:.1%} | out of days {shares[k][1] / N:.1%} | vs unrestricted {d.mean() * 100:+.1f} pp +- {se(d) * 100:.1f}")
    json.dump(out, open(os.path.join(HERE, "round275_results.json"), "w"), indent=1)
    print("Saved round275_results.json")


if __name__ == "__main__":
    main()
