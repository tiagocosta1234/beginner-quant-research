"""Round 239 addendum (descriptive, added after the pre-registered run): the same
top-10 Stage-A designs at much larger edges, to translate 'what would it take'
into win rates. Not a search; same 4,000 Stage-B futures (seed 2390)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import round239_convexity_ceiling as C
import round236_600eur_goal_2026 as R
if __name__ == "__main__":
    res = json.load(open(os.path.join(C.HERE, "round239_results.json")))
    pols = []
    for r in res["stage_a_top"]:
        p = r["policy"]; p["eval"] = tuple(p["eval"]); p["fund"] = tuple(p["fund"]); pols.append(p)
    paths = R.make_paths(C.N_ROWS, 4000, C.T, 2390)
    out = {}
    for e in (0.25, 0.5, 1.0):
        rb = C.run(pols, e, paths, 2390)
        b = max(rb, key=lambda r: r["p_25k"])
        m = b["policy"]["fund"][1]
        out[str(e)] = b
        print(f"edge e={e}: best P(EUR25K) {b['p_25k']:.1%} P(5-stack) {b['p_5stack']:.1%} all spent {b['p_stuck']:.1%} | "
              f"live bracket {m:g}:1 must win {(1 + e) / (1 + m):.1%} of days (zero-edge {1 / (1 + m):.1%}) | {C.lbl(b['policy'])}", flush=True)
    json.dump(out, open(os.path.join(C.HERE, "round239_edge_addendum.json"), "w"), indent=1, default=str)
