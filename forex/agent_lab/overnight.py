"""Unattended run of the research agent (started hidden with pythonw; output goes to a log on D:).
   pythonw -m forex.agent_lab.overnight [model] [until HH:MM] [max validations]      defaults: gemma4:latest 07:30 25"""
import sys
import time
from pathlib import Path

LOG = Path(f"data/llm_bench/agent_overnight_{time.strftime('%Y-%m-%d')}.log")
sys.stdout = open(LOG, "a", encoding="utf-8", buffering=1)
sys.stderr = sys.stdout
args = sys.argv[1:]
model = args[0] if len(args) > 0 else "gemma4:latest"
until = args[1] if len(args) > 1 else "07:30"
max_val = int(args[2]) if len(args) > 2 else 25
print(f"=== overnight start {time.strftime('%Y-%m-%d %H:%M:%S')} model {model} until {until} max validations {max_val}", flush=True)
from forex.agent_lab import agent as AG  # noqa: E402

try:
    AG.run_model(model, 10000, until, max_val)
except Exception as e:
    print("crashed:", repr(e), flush=True)
AG.board()
print(f"=== overnight end {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
