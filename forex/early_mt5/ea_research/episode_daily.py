"""Daily equity of the episode game (+up / -dn, multi-day) on the installed pair: marks the equity (closed episodes + the open episode's floating P&L) at the last bar of every server day.
python -m mt5broker.ea_research.episode_daily --pool MT5 --mult 5.0 --dn 2000     writes D:/finance/si_ledgers/DAILY_<pool>_x<m>_dn<dn>.csv  (date, equity, pnl, episode_closed)"""
import sys
ARGV = sys.argv[1:]
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import argparse
import numpy as np, pandas as pd
from mt5broker.ea_research import combo_grid as G, clean_boot_lib as L
from mt5broker.ea_research.combo_grid import news_flat, bars, CH


def daily(pool, m, UP, DN):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    tr = L.merge(L.ea_trades(src, "sdb", CH["sdb"] * m, lo), L.ea_trades(src, "xau5", CH["xau5"] * m, lo)); tr = news_flat(tr, G.EV, bars)
    tm, bc, sp = bars; in_s, out_s, side, entry, q = tr["in_s"], tr["out_s"].copy(), tr["side"], tr["entry"], tr["q"]; pl = tr["pl"].copy()
    t_cur = lo * 86400; t_end = (hi + 1) * 86400; n = len(tm); cum = 0.0; rec = {}; closed = {}
    while t_cur < t_end:
        a0 = int(np.searchsorted(tm, t_cur)); found = None
        for span in (3, 10, 40, 400):
            b0 = min(int(np.searchsorted(tm, t_cur + span * 86400)), n)
            if b0 - a0 < 5: break
            t_m = tm[a0:b0]; bid = bc[a0:b0]; ask = bid + sp[a0:b0]; P = np.zeros(b0 - a0); sel = np.nonzero((in_s >= t_cur) & (in_s < t_m[-1]) & (out_s > t_cur))[0]
            for j in sel:
                op = (t_m >= in_s[j]) & (t_m < out_s[j]); mark = bid if side[j] > 0 else ask; P[op] += side[j] * (mark[op] - entry[j]) * q[j]; P[t_m >= out_s[j]] += pl[j]
            hit = np.nonzero((P >= UP) | (P <= -DN))[0]
            if len(hit): found = (int(hit[0]), t_m, bid, ask, P, sel); break
            if b0 >= n:
                did = t_m // 86400; last = np.nonzero(np.diff(did))[0]
                for k in last: rec[int(did[k])] = cum + P[k]
                rec[int(did[-1])] = cum + P[-1]; break
        if found is None: break
        i, t_m, bid, ask, P, sel = found; tmi = int(t_m[i]); did = t_m[: i + 1] // 86400
        for k in np.nonzero(np.diff(did))[0]: rec[int(did[k])] = cum + P[k]
        for j in sel:
            if in_s[j] <= tmi < out_s[j]:
                mk = bid[i] if side[j] > 0 else ask[i]; pl[j] = side[j] * (mk - entry[j]) * q[j]; out_s[j] = tmi
        cum += P[i]; rec[int(tmi // 86400)] = cum; closed[int(tmi // 86400)] = closed.get(int(tmi // 86400), 0) + (1 if P[i] >= UP else -1); t_cur = tmi + 60
    d = pd.DataFrame(dict(day=sorted(rec))); d["equity"] = [rec[k] for k in d.day]; d["pnl"] = d.equity.diff().fillna(d.equity); d["date"] = pd.to_datetime(d.day * 86400, unit="s").dt.date
    d["closed"] = [closed.get(k, 0) for k in d.day]; return d[["date", "equity", "pnl", "closed"]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--pool", default="MT5"); ap.add_argument("--mult", type=float, default=1.5); ap.add_argument("--up", type=float, default=2000.0); ap.add_argument("--dn", type=float, default=1500.0); a = ap.parse_args(ARGV)
    d = daily(a.pool, a.mult, a.up, a.dn); d.to_csv(f"D:/finance/si_ledgers/DAILY_{a.pool}_x{a.mult}_dn{int(a.dn)}.csv", index=False)
    y = d[pd.to_datetime(d.date) >= "2026-01-01"]; print(f"{a.pool} x{a.mult} dn{int(a.dn)}: days {len(d)}, 2026 days {len(y)}, 2026 pnl {y.pnl.sum():+,.0f}, best day {y.pnl.max():+,.0f}, worst day {y.pnl.min():+,.0f}, +2000 / -dn closes in 2026: {int((y.closed > 0).sum())} / {int((y.closed < 0).sum())}")


if __name__ == "__main__":
    main()
