"""Episode replay: the day ends ONLY at +2,000 or -1,500 of equity (no midnight reset), on the installed pair (SDB + XAU5 x m, CPI news flat).
At each barrier all open positions are closed at the minute quote and a new episode starts at once with the EAs' later signals. ManualDip (daily series) is not included.
python -m forex.ea_research.episode_replay [--mult 1.5] [--pool MT5]"""
import sys
ARGV = sys.argv[1:]
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import argparse
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L
from forex.ea_research.combo_grid import news_flat, bars, CH

UP, DN = 2000.0, 1500.0


def replay(pool, m):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    tr = L.merge(L.ea_trades(src, "sdb", CH["sdb"] * m, lo), L.ea_trades(src, "xau5", CH["xau5"] * m, lo)); tr = news_flat(tr, G.EV, bars)
    tm, bc, sp = bars; in_s, out_s, side, entry, q = tr["in_s"], tr["out_s"].copy(), tr["side"], tr["entry"], tr["q"]; pl = tr["pl"].copy()
    t_cur = lo * 86400; t_end = (hi + 1) * 86400; eps = []; n = len(tm)
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
            if b0 >= n: break
        if found is None:
            eps.append(dict(start=t_cur, end=np.nan, res=0, pnl=float(P[-1]) if 'P' in dir() and len(P) else 0.0)); break
        i, t_m, bid, ask, P, sel = found; tmi = int(t_m[i])
        for j in sel:
            if in_s[j] <= tmi < out_s[j]:
                mk = bid[i] if side[j] > 0 else ask[i]; pl[j] = side[j] * (mk - entry[j]) * q[j]; out_s[j] = tmi
        eps.append(dict(start=t_cur, end=tmi, res=1 if P[i] >= UP else -1, pnl=float(P[i]), trades=int(sum(1 for j in sel if in_s[j] <= tmi))))
        t_cur = tmi + 60
    return pd.DataFrame(eps)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mult", type=float, default=1.5); ap.add_argument("--pool", default="MT5"); ap.add_argument("--dn", type=float, default=1500.0); ap.add_argument("--up", type=float, default=2000.0); ap.add_argument("--quiet", action="store_true"); a = ap.parse_args(ARGV)
    global UP, DN; UP, DN = a.up, a.dn
    e = replay(a.pool, a.mult); e["start_dt"] = pd.to_datetime(e.start, unit="s"); e["end_dt"] = pd.to_datetime(e.end, unit="s"); e["hours"] = (e.end - e.start) / 3600.0
    e.to_csv(f"D:/finance/si_ledgers/EPISODES_{a.pool}_x{a.mult}" + ("" if (a.up, a.dn) == (2000.0, 1500.0) else f"_u{int(a.up)}_d{int(a.dn)}") + ".csv", index=False)
    d = e[e.res != 0]; print(f"{a.pool} x{a.mult} up {a.up:.0f} dn {a.dn:.0f}: {len(d)} closed episodes | +2000: {int((d.res == 1).sum())} ({100 * (d.res == 1).mean():.0f}%) | -1500: {int((d.res == -1).sum())} | median length {d.hours.median():.0f} h, mean {d.hours.mean():.0f} h | net {d.pnl.sum():+,.0f}")
    if not a.quiet: print(e[e.start_dt >= "2026-08-25"][["start_dt", "end_dt", "res", "pnl", "hours", "trades"]].round(0).to_string(index=False))
    # time to a +8000 account result: from every starting episode, cumulate +2000 / -1500 results; pass at >= +8000, breach at <= -8000
    r = d.res.values; steps = np.where(r > 0, UP, -DN); t_end = d.end.values; t_st = d.start.values; out = []
    for k in range(len(steps)):
        c = 0.0
        for j in range(k, len(steps)):
            c += steps[j]
            if c >= 8000: out.append(("pass", (t_end[j] - t_st[k]) / 86400.0)); break
            if c <= -8000: out.append(("breach", (t_end[j] - t_st[k]) / 86400.0)); break
    if out:
        o = pd.DataFrame(out, columns=["res", "days"]); ps = o[o.res == "pass"]; print(f"\nfrom every start episode: {len(o)} resolved, pass {100 * (o.res == 'pass').mean():.0f}% / breach {100 * (o.res == 'breach').mean():.0f}% | calendar days to pass: median {ps.days.median():.0f}, mean {ps.days.mean():.0f} (business days about x0.71)")


if __name__ == "__main__":
    main()
