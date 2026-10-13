"""SDS verifier (DESIGN.md, piece 4): separate from the proposers, not based on anyone's claim."""
from __future__ import annotations

from pathlib import Path

from forex.self_improving.sds import constraints as C, registry as R

AUDIT = ["by-hour concentration of the edge (server hours 23 and 0 must not carry it)", "one position per market, non-overlapping recomputation", "carry (1.5 bp/day) and latency (1 s) sensitivity",
         "ablation without non-MT5 inputs", "stability across sub-windows (halves of B and VAL)", "MT5 broker environment and add-on test against the installed system (+3 points pass at 44 bd, breach <= +1)",
         "the sealed window, once, after a written decision"]


def verdict(spec, calibrated, passes):
    if not calibrated: return "ENGINE_UNCALIBRATED"
    if passes is None: return "RUN_FAILED"
    if passes == 0: return "NO_FINDING"
    return "RESEARCH_ONLY_CANDIDATE_NEEDS_AUDIT" if not spec["mt5_native"] else "CANDIDATE_NEEDS_AUDIT"


def static_audit(spec):
    src = "".join((Path(__file__).resolve().parents[1] / f).read_text(encoding="utf-8", errors="ignore") for f in spec["files"] if (Path(__file__).resolve().parents[1] / f).exists())
    return C.audit_engine(spec, src)


def write_candidate(spec, run_tag, passes):
    f = R.CAND / f"{run_tag}.md"
    f.write_text(f"# CANDIDATE {run_tag}\n\nEngine {spec['name']} (code {spec['hash']}), {passes} passing unit(s), calibrated. MT5-native: {spec['mt5_native']}.\nNOT a trading instruction. Required audit before the trader sees it as a proposal:\n" + "".join(f"- [ ] {a}\n" for a in AUDIT) + "\nNothing here is applied to the account by the system.\n", encoding="utf-8")
    return f
