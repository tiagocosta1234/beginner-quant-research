"""SDS engines: the research labs behind one uniform contract (DESIGN.md).
An engine = a module with a CLI that takes `--placebo SEED` (calibration world) and `--tag NAME`, and prints a line the parser can read. `run_engine` executes it at below-normal priority, logs, and returns the number of passing units."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

from mt5broker.self_improving.sds import registry as R

SI = Path(__file__).resolve().parents[1]; LOGS = Path(__file__).resolve().parent / "logs"; LOGS.mkdir(exist_ok=True)
PY = sys.executable
ENGINES = {
    "ml": dict(family="ml", module="mt5broker.self_improving.ml.ml_lab", files=["ml/ml_lab.py", "freeform/ff6_data.py"], real=["--jobs", "6"], placebo=["--jobs", "4"], parse=r"cells passing (\d+) of (\d+)", mt5_native=True, heavy=False,
               data=["D:/finance/si_cache"], note="XGBoost on raw 15-minute windows, 12 cells"),
    "slow": dict(family="slow", module="mt5broker.self_improving.slow.slow_lab", files=["slow/slow_lab.py", "freeform/ff5_data.py", "freeform/ff6_data.py"], real=["--jobs", "6"], placebo=["--jobs", "4"], parse=r"cells passing (\d+) of (\d+)", mt5_native=False, heavy=False, rollover_exempt="decides once a day at 12:00 server time: never inside the rollover hours by construction",
                 data=["D:/finance/data_macro/alfred", "D:/finance/data_macro/cot"], note="COT + ALFRED surprises + cross-asset, horizons 1/5/20 days (external data: research only)"),
    "hf": dict(family="hf", module="mt5broker.self_improving.hf.hf_lab", files=["hf/hf_lab.py", "hf/hf_data.py"], real=["--jobs", "6"], placebo=["--jobs", "4"], parse=r"cells passing (\d+) of (\d+)", mt5_native=True, heavy=False,
               data=["D:/finance/ticks_feat"], note="tick microstructure, market and limit entries, 48 cells"),
    "regime": dict(family="regime", module="mt5broker.self_improving.regime.regime_lab", files=["regime/regime_lab.py"], real=["--policies", "100000"], placebo=["--policies", "100000"], parse=r"passing: (\d+)", mt5_native=False, heavy=False, rollover_exempt="only scales the installed system by day; it has no entries of its own",
                   data=["D:/finance/scratch/si_cache"], note="size factor on the installed system by macro/gold/own-P&L regime (uses VIX etc.: research only)"),
    "freeform": dict(family="freeform", module="mt5broker.self_improving.freeform.ff6_agent", files=["freeform/ff6_agent.py", "freeform/ff6_data.py", "freeform/acct_env.py"], real=["--gens", "100", "--pop", "2000", "--seed", "1"], placebo=["--gens", "20", "--pop", "2000", "--seed", "1"],
                     parse=r"S2 passes (\d+)", mt5_native=True, heavy=True, env={"FF6_MT5ONLY": "1"}, data=["D:/finance/si_cache"], note="free-form rule search, MT5-only features (77), MT5 broker environment"),
}
for n, s in ENGINES.items(): s["name"] = n; s["hash"] = R.code_hash([SI / f for f in s["files"]])


def parse_passes(spec, text):
    m = re.findall(spec["parse"], text)
    if not m: return None
    last = m[-1]; return int(last[0] if isinstance(last, tuple) else last)


def run_engine(spec, kind, seed=None, timeout_h=4.0):
    """Run one placebo world or the real experiment; returns (passes, log path)."""
    tag = f"sds_{spec['name']}_{kind}{seed or ''}_{spec['hash']}"; log = LOGS / f"{tag}.log"
    cmd = [PY, "-W", "ignore", "-m", spec["module"]] + (spec["placebo"] if kind == "placebo" else spec["real"]) + (["--placebo", str(seed)] if kind == "placebo" else []) + ["--tag", tag]
    env = dict(os.environ, **spec.get("env", {})); t0 = time.time()
    with open(log, "w", encoding="utf-8") as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd="D:/finance/beginner-quant-research", env=env, creationflags=0x00004000)       # BELOW_NORMAL priority
        try: p.wait(timeout=timeout_h * 3600)
        except subprocess.TimeoutExpired: p.kill(); return None, log
    return parse_passes(spec, log.read_text(encoding="utf-8", errors="ignore")), log
