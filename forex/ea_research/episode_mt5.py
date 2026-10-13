"""Episode game with MT5 broker's daily loss rule ENFORCED. The account only ever ends an episode at +UP or -DN of equity since the episode started (multi-day, no midnight reset, all positions closed at the barrier,
new episode at once). Each server day the equity change since 00:00 is tracked (floating included); a drop of 2,500 or more inside any server day is an MT5 broker hard breach and is flagged on the episode in which it happens.
Pair only (SDB + XAU5 x size, CPI flat), ManualDip not included.  python -m forex.ea_research.episode_mt5 --size 1.5 [--pool MT5] (appends one row per (UP, DN) to D:/finance/si_ledgers/EP8_<size>_<pool>.csv)"""
import sys
ARGV = sys.argv[1:]
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import argparse
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L
from forex.ea_research.combo_grid import news_flat, bars, CH

DAYLIM = 2500.0


def replay(pool, m, UP, DN, tr0=None):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    tr = tr0 if tr0 is not None else news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"] * m, lo), L.ea_trades(src, "xau5", CH["xau5"] * m, lo)), G.EV, bars)
    tm, bc, sp = bars; in_s, out_s, side, entry, q = tr["in_s"], tr["out_s"].copy(), tr["side"], tr["entry"], tr["q"]; pl = tr["pl"].copy()
    t_cur = lo * 86400; t_end = (hi + 1) * 86400; n = len(tm); cum = 0.0; day_id = None; day_start = 0.0; eps = []
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
        if found is None: break
        i, t_m, bid, ask, P, sel = found; tmi = int(t_m[i]); eq = cum + P[: i + 1]; did = t_m[: i + 1] // 86400
        blocks = np.nonzero(np.r_[True, did[1:] != did[:-1]])[0]; ends = np.r_[blocks[1:], len(did)]; ds = np.empty(len(eq))
        for s0, e0 in zip(blocks, ends): ds[s0:e0] = day_start if (day_id is not None and did[s0] == day_id) else eq[s0]
        rel = eq - ds; worst = float(rel.min()); breach = bool(worst <= -DAYLIM)
        day_id = int(did[-1]); day_start = float(ds[-1])
        for j in sel:
            if in_s[j] <= tmi < out_s[j]:
                mk = bid[i] if side[j] > 0 else ask[i]; pl[j] = side[j] * (mk - entry[j]) * q[j]; out_s[j] = tmi
        eps.append(dict(start=t_cur, end=tmi, res=1 if P[i] >= UP else -1, pnl=float(P[i]), worst_day=worst, breach=breach)); cum += P[i]; t_cur = tmi + 60
    return pd.DataFrame(eps)


def account(e, UP, DN):
    """From every starting episode: pass when the cumulative result reaches +8,000 (counted before MT5 broker's 2,000-a-day cap), breach at -8,000 or at an episode flagged with a daily-loss breach."""
    r = e.res.values; steps = np.where(r > 0, UP, -DN); br = e.breach.values; out = []
    for k in range(len(steps)):
        c = 0.0
        for j in range(k, len(steps)):
            if br[j]: out.append(("breach", (e.end.values[j] - e.start.values[k]) / 86400.0)); break
            c += steps[j]
            if c >= 8000: out.append(("pass", (e.end.values[j] - e.start.values[k]) / 86400.0)); break
            if c <= -8000: out.append(("breach", (e.end.values[j] - e.start.values[k]) / 86400.0)); break
    return pd.DataFrame(out, columns=["r", "d"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--size", type=float, required=True); ap.add_argument("--pool", default="MT5"); ap.add_argument("--ups", default="1000,1500,2000,2500"); ap.add_argument("--dns", default="1000,1500,2000,2500"); a = ap.parse_args(ARGV)
    out = f"D:/finance/si_ledgers/EP8_{a.size}_{a.pool}.csv"; src, aa, bb = L.POOLS[a.pool]; lo = L.day(aa)
    tr = news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"] * a.size, lo), L.ea_trades(src, "xau5", CH["xau5"] * a.size, lo)), G.EV, bars)
    for DN in map(float, a.dns.split(",")):
        for UP in map(float, a.ups.split(",")):
            e = replay(a.pool, a.size, UP, DN, {k: (v.copy() if hasattr(v, "copy") else v) for k, v in tr.items()}); o = account(e, UP, DN); ps = o[o.r == "pass"]
            row = dict(pool=a.pool, size=a.size, up=UP, dn=DN, episodes=len(e), hit=100 * (e.res == 1).mean(), ep_hours=(e.end - e.start).median() / 3600, daily_breach_episodes=int(e.breach.sum()), worst_day=e.worst_day.min(), starts=len(o), pass_pct=100 * (o.r == "pass").mean() if len(o) else np.nan,
                       breach_pct=100 * (o.r == "breach").mean() if len(o) else np.nan, median_days=ps.d.median() if len(ps) else np.nan, median_bd=0.71 * ps.d.median() if len(ps) else np.nan)
            pd.DataFrame([row]).to_csv(out, mode="a", header=not os.path.exists(out), index=False); print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)


if __name__ == "__main__":
    main()
