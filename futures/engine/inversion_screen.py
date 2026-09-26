"""
Inversion screen: what would each ledger idea make if traded the other way round?

Flipping a trade flips its before-cost result but not its costs, so the inverse's
net per trade = -(gross) - cost = net - 2 x gross (cost = gross - net). An inverse can
only pay when the original LOST BEFORE COSTS by more than its costs.

This arithmetic is exact for time exits. For stop/target brackets it is only a guide:
when one bar touches both levels the harness counts the stop, so ties go against the
original and its inverse alike. Round 131's actual inverses came out anywhere from
-$24 to +$19 a trade away from this arithmetic (e.g. "toward LRL, stop 1:1": +$5.7
predicted, -$18.2 actual).

Selection warning: picking ideas to invert BECAUSE they lost is fitting to the results
already seen; an inverse chosen this way needs new data to count as evidence.

Usage: python inversion_screen.py   (reads docs/IDEA_LEDGER.md)
"""
import os, re

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "IDEA_LEDGER.md")


def screen():
    rows = []
    for line in open(LEDGER, encoding="utf-8"):
        if not (line.startswith("| ") and line[2:3].isdigit()):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        num = lambda s: re.match(r"^([+-]?\d+(?:\.\d+)?)(R)?", s.replace("$", "").replace(" ", ""))
        a, b = num(c[6]), num(c[7])
        if not a or not b or "replicat" in c[9]:
            continue
        net, gross = float(a.group(1)), float(b.group(1))
        rows.append(dict(n=int(c[0]), idea=c[2], trades=c[5], net=net, gross=gross, cost=gross - net,
                         inverse=net - 2 * gross, unit="R" if a.group(2) else "$"))
    return rows


if __name__ == "__main__":
    rows = screen()
    pos = sorted([r for r in rows if r["inverse"] > 0], key=lambda r: -(r["inverse"] * (300 if r["unit"] == "R" else 1)))
    print(f"{len(rows)} rows with net and gross; inverse positive by arithmetic: {len(pos)}")
    for r in pos:
        print(f"{r['n']:>4} {r['idea'][:70]:<70} {r['trades']:>6} net {r['net']:+8.3f} gross {r['gross']:+8.3f} "
              f"-> inverse {r['inverse']:+8.3f}{r['unit']}")
