"""
Health check for Knowledge_Base/CURRENT_STATE.md: flags when the page no longer
matches the repo, so no agent plans around stale facts.

    python futures/engine/kb_health_check.py

Checks, against the page's `kb-state` line:
  1. the idea ledger's row count equals ledger_k, and no ledger row is a CANDIDATE
     (a candidate must be written up on the page by hand)
  2. no round script newer than last_round exists
  3. live_bot/manual_strategy.py's TOD_RISK / VWAPZ_RISK match the page
  4. no journal heading was added after journal_last_heading (lists any, and
     marks headings that claim an edge or a breakthrough)
  5. no round script after Round 119 uses a resolver that holds past the session
     close, except where it is only reproducing old results (ALLOWED)
  6. origin/master still points at the recorded commit (the desktop agent hasn't
     pushed new rounds that the page doesn't cover)
Exits 1 if anything needs attention.
"""
import os, re, sys, glob, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PAGE = os.path.join(ROOT, "Knowledge_Base", "CURRENT_STATE.md")
LEDGER = os.path.join(ROOT, "futures", "docs", "IDEA_LEDGER.md")
JOURNAL = os.path.join(ROOT, "futures", "docs", "TRADING_JOURNAL.md")
ENGINE = os.path.join(ROOT, "futures", "engine")
MANUAL = os.path.join(ROOT, "live_bot", "manual_strategy.py")
# resolvers that hold positions past the session close, by the module that defines them
UNBOUNDED = {"round19_random_entry": "resolve_trailing", "round69_true_2000_daily_cap": "resolve_true_risk_with_day_cap",
             "round113_concurrent_positions_search": "resolve_concurrent_trailing",
             "round119_multi_account_snowball_mc": "build_daily_series"}  # round119's series come from round113
ALLOWED = {  # post-119 scripts that call an unbounded resolver on purpose
    "round120a_round119_horizon_and_netting_check.py": "reproduces Round 119 as run",
    "round120b_overnight_hold_check.py": "reproduces round69 to show the artifact",
    "round120_goal_judge.py": "self-test checks the judge against Round 119's simulator",
}
CLAIMS = re.compile(r"breakthrough|clears|validated edge|edge found|real edge|goal met", re.I)


def state():
    m = re.search(r"<!-- kb-state: (.*?) -->", open(PAGE, encoding="utf-8").read())
    if not m:
        sys.exit("CURRENT_STATE.md has no kb-state line")
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', m.group(1)))


def main():
    s = {k: v.strip('"') for k, v in state().items()}
    issues, ok = [], []

    rows = [l for l in open(LEDGER, encoding="utf-8") if re.match(r"\| \d+ \|", l)]
    (ok if len(rows) == int(s["ledger_k"]) else issues).append(
        f"ledger has {len(rows)} rows; page says k={s['ledger_k']}")
    cands = [l.split("|")[3].strip() for l in rows if "CANDIDATE" in l]
    (issues if cands else ok).append(f"ledger candidates: {cands or 'none'}")

    rounds = [int(m.group(1)) for f in glob.glob(os.path.join(ENGINE, "round*.py"))
              if (m := re.match(r"round(\d+)", os.path.basename(f)))]
    newest = max(rounds)
    (ok if newest <= int(s["last_round"]) else issues).append(
        f"newest round script is {newest}; page covers through {s['last_round']}")

    manual = open(MANUAL, encoding="utf-8").read()
    for key, name in [("tod_risk", "TOD_RISK"), ("vwapz_risk", "VWAPZ_RISK")]:
        m = re.search(rf"^{name}\s*=\s*([\d.]+)", manual, re.M)
        val = float(m.group(1)) if m else None
        (ok if val == float(s[key]) else issues).append(f"live_bot {name} = {val}; page says {s[key]}")

    heads = [l.strip() for l in open(JOURNAL, encoding="utf-8") if l.startswith("## ")]
    idx = next((i for i, h in enumerate(heads) if s["journal_last_heading"] in h), None)
    if idx is None:
        issues.append(f"journal heading '{s['journal_last_heading']}' not found")
    else:
        newer = heads[idx + 1:]
        if newer:
            issues.append("journal entries newer than the page:\n" + "\n".join(
                f"      {'[CLAIM] ' if CLAIMS.search(h) else ''}{h}" for h in newer))
        else:
            ok.append("no journal entries newer than the page")

    bad = []
    for f in sorted(glob.glob(os.path.join(ENGINE, "round*.py"))):
        m = re.match(r"round(\d+)", os.path.basename(f))
        if int(m.group(1)) <= 119 or os.path.basename(f) in ALLOWED:
            continue
        src = open(f, encoding="utf-8").read()
        hits = []
        for mod, fn in UNBOUNDED.items():
            if re.search(rf"from {mod} import [^\n]*\b{fn}\b", src):
                hits.append(fn)
            for alias in re.findall(rf"import {mod}(?: as (\w+))?", src):
                if re.search(rf"\b{alias or mod}\.{fn}\b", src):
                    hits.append(fn)
        if hits:
            bad.append(f"{os.path.basename(f)}: {', '.join(hits)}")
    (issues if bad else ok).append("post-119 scripts using session-unbounded resolvers: " + (", ".join(bad) or "none"))

    r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "origin/master"], capture_output=True, text=True)
    head = r.stdout.strip()
    if not head:
        issues.append("could not read origin/master (run: git fetch origin master)")
    else:
        (ok if head.startswith(s["master"]) or s["master"].startswith(head) else issues).append(
            f"origin/master is {head}; page recorded {s['master']}")

    for line in ok:
        print(f"  OK    {line}")
    for line in issues:
        print(f"  CHECK {line}")
    print("\nCURRENT_STATE.md is", "up to date" if not issues else "OUT OF DATE -- update the page and its kb-state line")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
