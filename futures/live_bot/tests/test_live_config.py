"""Plain-Python tests for two bugs found on the first live Practice trade
(2026-09-30). No pytest dependency.

Run with: python live_bot/tests/test_live_config.py

1. account_update balance extraction: the real event is a raw dict with the
   balance nested under "data" (payload copied from the live log below).
2. .env must be loaded before strategy modules read their tier sizing at import.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from live_bot.broker_client import BrokerClient, BrokerConfig  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


# Verbatim shape of the first real account_update on ACCOUNT-ID.
REAL_EVENT = {"action": 1, "data": {"id": 28075594, "name": "ACCOUNT-ID", "balance": 149637.84,
                                    "canTrade": True, "isVisible": True, "simulated": True}}


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def extracted(event):
    b = BrokerClient(BrokerConfig())
    asyncio.run(b._on_account_update(event))
    return b._latest_live_balance


def main() -> int:
    got = extracted(REAL_EVENT)
    check("real nested payload -> balance extracted", got == 149637.84, repr(got))
    got = extracted({"balance": 150000.0})
    check("flat dict payload still works", got == 150000.0, repr(got))
    got = extracted(Obj(data={"balance": 149000.0}))
    check("event object with .data dict still works", got == 149000.0, repr(got))
    got = extracted({"action": 1, "data": {"id": 1}})
    check("payload without a balance leaves it unset", got is None, repr(got))

    # Import order: after importing live_bot.main, the strategy's sizing must match
    # the (now-loaded) environment, whatever live_bot/.env contains.
    env = {k: v for k, v in os.environ.items() if not k.startswith("BRACKET_")}
    code = ("import os, live_bot.main, live_bot.disciplined_bracket_strategy as d; "
            "print(d.RISK_PER_TRADE, float(os.environ.get('BRACKET_RISK_PER_TRADE', '300')), "
            "d.CAP_WIN_DOLLARS, float(os.environ.get('BRACKET_CAP_WIN_DOLLARS', '1650')))")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
    vals = out.stdout.split()
    ok = len(vals) == 4 and float(vals[0]) == float(vals[1]) and float(vals[2]) == float(vals[3])
    check("strategy sizing matches .env after importing live_bot.main", ok, out.stdout.strip() or out.stderr[-300:])

    failed = [r for r in RESULTS if not r[1]]
    for name, ok_, detail in RESULTS:
        print(f"{'PASS' if ok_ else 'FAIL'}  {name}" + (f"   [{detail}]" if not ok_ else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
