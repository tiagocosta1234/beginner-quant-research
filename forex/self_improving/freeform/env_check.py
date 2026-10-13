"""Sanity check of the MT5 broker environment on a known rule (R7) and on the installed system. python -m forex.self_improving.freeform.env_check"""
import time
import numpy as np
import pandas as pd

from forex.self_improving.freeform import ff5_data as D, ff5_agent as A, acct_env as E
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA

R7 = dict(cls="fx", side=-1, H=96, conds=[["z24", ">=", 5], ["z2", "<=", 5], ["z4", ">=", 6]])
t0 = time.time(); st = D.Stack("fx"); ev = A.Evaluator({"fx": st}); fr = {"fx": E.Frames(st)}; print(f"stack {time.time() - t0:.0f}s")
res = {}
for w, (a, b) in (("a", D.WA), ("b", D.WB), ("val", D.VAL)):
    t1 = time.time(); nm, t0s, sd = ev.rows(R7, w); paths = E.trade_paths(fr["fx"], nm, t0s, sd, R7["side"], R7["H"]); s = E.build_series(paths, a, b)
    pp, pb = E.pass_stats(s, 44, 20000); res[w] = s
    tr = np.array([p[2] for p in paths]); nt = np.array([p[4] for p in paths])
    print(f"R7 window {w}: signal rows {len(t0s)} -> trades {len(paths)} (accepted {s.attrs['taken']}, skipped by the notional cap {s.attrs['skipped']}) | mean P&L per trade USD {tr.mean():+.1f} (risk 500), win {100*(tr>0).mean():.0f}%, "
          f"mean notional {nt.mean():,.0f} | daily V mean {s.V.mean():+.1f} sd {s.V.std():.0f}, worst day {s.V.min():+.0f}, days with B<=-1500 {(s.B<=-1500).sum()} | standalone P(pass44)={100*pp:.1f}% P(breach44)={100*pb:.1f}% ({time.time()-t1:.0f}s)")

# the installed system (FT 2022-26 pool) and the add-on test on B+VAL days
t1 = time.time(); import forex.ea_research.event_macro as EM
G.EV = D.events()["CPI"]; DA.RISK = 500.0; Tk, bb = DA.trades(); Tk, Dd = DA.day_arrays(Tk, bb); Dd = Dd * 0.75
S_inst = G.add_dip(G.pair_series("FT", 1.5, 1.5, 1500.0), Dd, 1500.0); print(f"installed system series: {len(S_inst['days'])} days in {time.time()-t1:.0f}s")
lo, hi = D.ts(D.WB[0]), D.ts(D.VAL[1]) + 86400
both = pd.concat([res["b"], res["val"]]); both = both[~both.index.duplicated()]
(ip, ib), (cp, cb) = E.addon_stats(both, S_inst, lo, hi, G.add_dip)
print(f"B+VAL days: installed alone P(pass44) {100*ip:.1f}% breach {100*ib:.1f}%  |  + R7 add-on P(pass44) {100*cp:.1f}% breach {100*cb:.1f}%  -> delta pass {100*(cp-ip):+.1f} pts, delta breach {100*(cb-ib):+.1f} pts")
