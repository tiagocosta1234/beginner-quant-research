"""A4 value check (the trader 2026-10-09, "faz A e B"): what a CAP-AWARE pass lock is worth compared with no lock and with the old equity-based lock (the one that fired early).
   python -m forex.ea_research.clean_lock_capaware
Lock levels as in the guard: raw equity >= 108,300 (target 8% + 0.3% buffer). none = nothing, legacy = the EA's old rule (equity includes the part of today's profit above 2,000 that MT5 broker removes at rollover: a premature lock leaves the EA STUCK, locked for good with the test not passed), capaware = counted profit = closed counted profit + min(today's profit, 2,000) >= 8,300 (needs the new guard code).
Same bootstrap as clean_bootstrap.py (plan A, x1.2, 36 business days to 30 Nov, 52 to 22 Dec). 'stuck' = share of paths where the lock fired but the counted profit was below 8,000."""
from __future__ import annotations

from forex.ea_research import clean_bootstrap as BS


def main():
    for h in (1.0, 0.7):
        P = BS.pools(h); print(f"\n--- edge kept {h:.1f}")
        for w, lab in ((0.5, "50/50 mix"), (1.0, "12M only"), (0.0, "5Y only")):
            for lock in ("none", "legacy", "capaware"):
                m, lo, hi = BS.estimate(P, w, False, lock=lock)
                print(f"  {lab:10s} lock {lock:8s}: pass by 30 Nov {100*m[0]:5.1f}% [{100*lo[0]:5.1f}-{100*hi[0]:5.1f}] | by 22 Dec {100*m[1]:5.1f}% [{100*lo[1]:5.1f}-{100*hi[1]:5.1f}] | breach {100*m[2]:4.1f}% | stuck {100*m[4]:4.1f}%", flush=True)


if __name__ == "__main__":
    main()
