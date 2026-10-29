"""Recommended combination (the trader 2026-10-13): episodes (a session/day ends ONLY at +2,000 or -L of equity since its start, multi-day, all positions closed at the barrier), x1.5, loss lock 2,000, SDB 'runner' (a winning SDB trade is kept to break-even stop or 22:00 of its exit day).
MT5 broker pool, MT5 broker's -2,500 server-day loss enforced inside episodes (episode_mt5.replay). Fixed comparison, nothing tuned. python -m forex.self_improving.session.session_episode_combo"""
import numpy as np, pandas as pd
from forex.ea_research import episode_mt5 as E
from forex.self_improving.session import session_sdbrunner as R, session_mgmt as M


def scaled(tr, m):
    t = {k: np.array(v, copy=True) for k, v in tr.items()}; t["q"] = t["q"] * m; t["pl"] = t["pl"] * m; return t


def main():
    tr, lo, hi = R.load_flag("MT5"); rows = []
    for L in (1500.0, 2000.0):
        for nm, t in (("no runner", tr), ("runner SDB only", R.runner_leg(tr, 0, "sdb")), ("runner both legs", M.runner(tr, 0))):
            e = E.replay("MT5", 1.5, 2000.0, L, scaled(t, 1.5)); o = E.account(e, 2000.0, L); ps = o[o.r == "pass"]
            row = dict(L=L, variant=nm, episodes=len(e), hit=100 * (e.res == 1).mean(), ep_days=(e.end - e.start).median() / 86400, daily_breach_eps=int(e.breach.sum()), worst_day=e.worst_day.min(), starts=len(o), pass_pct=100 * (o.r == "pass").mean(), breach_pct=100 * (o.r == "breach").mean(), med_cal_days=ps.d.median(), med_bd=0.71 * ps.d.median())
            rows.append(row); print({k: (round(float(v), 1) if not isinstance(v, str) else v) for k, v in row.items()}, flush=True)
    pd.DataFrame(rows).to_csv("data/si_ledgers/SESSION_episode_combo.csv", index=False)


if __name__ == "__main__":
    main()
