"""Run the pre-registered grid for one phase and timeframe(s): every family x params x symbol, written to D:\\finance\\scratch\\lab\\results_<phase>_<tf>.csv.
Parallel by symbol (WORKERS processes; the trader: "use as much power as you wish ... not too much though": 4 of 16 cores, memory is the limit).
  python -m forex.intraday_lab.run_grid dev 5 15      (add  --only EURUSD  for a smoke test)
"""
from __future__ import annotations

import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab import families as F
from forex.intraday_lab.lab import ALL, Bars, run, stats

OUT = Path(r"D:\finance\scratch\lab"); OUT.mkdir(parents=True, exist_ok=True)
WORKERS = 4


def one_symbol(args):
    phase, tf, s = args
    rows = []; b = Bars(s, tf); mask = np.zeros(b.n, bool); mask[b.slice_idx(phase)] = True
    for fam, par in F.grid(tf):
        try:
            i, d, st, tpm, mb = F.FAMILIES[fam](b, **par)
            R, ent, ext, yrs, cst = run(b, i, d, st, tpm, mb, 0.0, mask)
            r = stats(R, yrs, cst)
        except Exception as e:                                                   # a failed cell is a result too
            r = dict(n=0, mean=np.nan, t=np.nan, pf=np.nan, win=np.nan, cost=np.nan); print("ERR", fam, par, s, e, flush=True)
        rows.append(dict(phase=phase, tf=tf, family=fam, params=str(sorted(par.items())), sym=s, **r))
    return rows


def main(phase: str, tfs: list[int], only: list[str] | None = None):
    for tf in tfs:
        t0 = time.time(); syms = only or list(ALL)
        with Pool(min(WORKERS, len(syms))) as p:
            res = p.map(one_symbol, [(phase, tf, s) for s in syms])
        rows = [r for x in res for r in x]
        pd.DataFrame(rows).to_csv(OUT / f"results_{phase}_{tf}{'_smoke' if only else ''}.csv", index=False)
        print(f"{phase} tf {tf}: {len(rows)} cells in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]; only = None
    if "--only" in a:
        k = a.index("--only"); only = a[k + 1].split(","); a = a[:k] + a[k + 2:]
    main(a[0], [int(x) for x in a[1:]], only)
