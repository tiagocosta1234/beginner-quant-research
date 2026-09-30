"""
Round 232 (2026-09-30): re-run the eleven scripts that import Round 192's
gross-of-costs `build_daily()` series, net of costs.

Round 231 showed Round 192's disciplined-bracket series never deducted costs
(~29% of its profit). Each downstream script is run TWICE, unmodified, in its
own process: once as-is (GROSS -- a control that should reproduce what the
repo already reported) and once with `round192_intraday_disciplined_bracket.
build_daily` replaced by `round231_round192_net_of_costs.build_daily_net`
(NET, repo cost convention $11.24 per NQ contract round trip) BEFORE the
script is loaded, so its own `from round192... import build_daily` picks up
the net series. Each run prints a marker line naming the series it received,
so a run that silently used the wrong one is visible. None of these scripts
write files (checked: stdout only), so nothing tracked is overwritten.

Full stdout for every run is saved to round232_outputs/<script>.<gross|net>.txt,
and a line-level diff of every numeric line that changed is written to
round232_results.json. Only Round 192's series changes; any other input a
script uses (e.g. round199's combined live-stage series in
split_strategy_monte_carlo) is untouched and is reported as a separate caveat
if it is itself gross.
"""
import os, sys, json, subprocess, difflib, re, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "round232_outputs")
SCRIPTS = ["capital_threshold_sweep", "career_roi_model", "goal_check", "eoy_goal_reality_check",
           "full_timeline_projection", "mature_steady_state_10k", "reinvestment_snowball",
           "round200_eval_strategy_fair_comparison", "snowball_backtest_real_year",
           "split_strategy_monte_carlo", "tier_mix_plan"]

WRAPPER = r"""
import os, sys, runpy
sys.path.insert(0, {here!r})
os.chdir({here!r})
import round192_intraday_disciplined_bracket as R192
_orig = R192.build_daily
_calls = [0]
def _patched(*a, **k):
    _calls[0] += 1
    if {net!r}:
        import round231_round192_net_of_costs as N
        print("[round232] build_daily -> NET series ($%.2f/contract)" % N.COST_CONV, flush=True)
        return N.build_daily_net()
    print("[round232] build_daily -> GROSS series (Round 192 as published)", flush=True)
    return _orig(*a, **k)
R192.build_daily = _patched
runpy.run_path(os.path.join({here!r}, {script!r} + ".py"), run_name="__main__")
print("[round232] build_daily calls: %d" % _calls[0], flush=True)
"""


def run_one(script, net):
    tag = "net" if net else "gross"
    code = WRAPPER.format(here=HERE, net=net, script=script)
    t0 = time.time()
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=3600,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    text = p.stdout + ("\n[stderr]\n" + p.stderr[-4000:] if p.returncode else "")
    with open(os.path.join(OUT, f"{script}.{tag}.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return script, tag, p.returncode, time.time() - t0


def numeric_diff(script):
    g = open(os.path.join(OUT, f"{script}.gross.txt"), encoding="utf-8").read().splitlines()
    n = open(os.path.join(OUT, f"{script}.net.txt"), encoding="utf-8").read().splitlines()
    pairs = []
    sm = difflib.SequenceMatcher(a=g, b=n, autojunk=False)
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            continue
        ga, nb = g[a0:a1], n[b0:b1]
        for i in range(max(len(ga), len(nb))):
            x = ga[i] if i < len(ga) else ""
            y = nb[i] if i < len(nb) else ""
            if "[round232]" in x or "[round232]" in y:
                continue
            if re.search(r"\d", x + y):
                pairs.append(dict(gross=x.strip(), net=y.strip()))
    return pairs


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = [(s, net) for s in SCRIPTS for net in (False, True)]
    status = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for script, tag, rc, secs in ex.map(lambda j: run_one(*j), jobs):
            status.setdefault(script, {})[tag] = dict(returncode=rc, seconds=round(secs, 1))
            print(f"{script:<42} {tag:<5} rc={rc} {secs:6.1f}s", flush=True)
    results = {}
    for s in SCRIPTS:
        ok = all(status[s][t]["returncode"] == 0 for t in ("gross", "net"))
        g_txt = open(os.path.join(OUT, f"{s}.gross.txt"), encoding="utf-8").read()
        n_txt = open(os.path.join(OUT, f"{s}.net.txt"), encoding="utf-8").read()
        results[s] = dict(status=status[s], ran_ok=ok,
                          gross_marker="GROSS series" in g_txt, net_marker="NET series" in n_txt,
                          changed_lines=numeric_diff(s) if ok else None)
    with open(os.path.join(HERE, "round232_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print("Saved round232_results.json")
