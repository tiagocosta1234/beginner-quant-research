"""CLEAN guard simulation at TICK level on MT5 broker's real gold ticks (Oct 2025 - Sep 2026), the check that the minute-close model (clean_guard_sim.py) could not do.
   python -m forex.ea_research.clean_guard_tick      (the trader 2026-10-09: '(original wording omitted)': tick-level breach check at x1.0 / 1.2 / 1.5 / 1.8)
Same event-driven logic as clean_guard_sim.simulate (the guard flattens the positions open at the trigger at that moment's market price, trades that would open later that day are dropped, closed positions never contribute again), but on the days where the minute-close path came within 1,000 USD of the loss cap the equity path is rebuilt TICK BY TICK (longs marked at the bid, shorts at the ask) from the FIFO-paired real trades: the guard triggers at the first tick with equity <= -L and flattens at the first tick at or after trigger + delay. The minute-close path misses the intra-minute lows.
Outputs per size: the lowest tick-level day equity, days that touched the MT5 -2,500 line, guard triggers, and P(pass by 30 Nov / 22 Dec) / breach with the loss cap only (no lock, no profit cap) on the 12-month window."""
import sys
sys.argv = ["x", "--source", "mt5broker"]
import numpy as np
import pandas as pd

from forex.ea_research import clean_guard_sim as C
from forex.ea_batch.mt5_mc_config import CH
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch import mt5data_guard_speed as GS

A, CAPD, TARGET = C.A, C.CAPD, C.TARGET
DELAY_MS, CAND = 1000, -1000.0
EPOCH = C.EPOCH


def simulate_tick(bars, tr: dict, d_lo: int, d_hi: int, L: float, mt5, delay_ms=DELAY_MS, cand=CAND):
    tm, bc, sp = bars; in_s, out_s, side, entry, q = tr["in_s"], tr["out_s"].copy(), tr["side"], tr["entry"], tr["q"]; pl = tr["pl"].copy(); alive = np.ones(len(in_s), bool)
    days, V, B, Hi, ev, tickdays, notick, lows = [], [], [], [], [], 0, 0, []
    for d in range(d_lo, d_hi + 1):
        d0, d1 = d * 86400, (d + 1) * 86400; a = int(np.searchsorted(tm, d0)); b = int(np.searchsorted(tm, d1))
        if b - a < 60: continue
        t_m = tm[a:b]; bid = bc[a:b]; ask = bc[a:b] + sp[a:b]; eq = np.zeros(b - a); sel = np.nonzero(alive & (out_s >= d0) & (in_s < d1))[0]
        for j in sel:
            op = (t_m >= in_s[j]) & (t_m < out_s[j]); mark = bid if side[j] > 0 else ask; eq[op] += side[j] * (mark[op] - entry[j]) * q[j]
            if out_s[j] < d1: eq[t_m >= out_s[j]] += pl[j]
        use_tick = False
        if eq.min() <= cand:                                                      # the minute-close path came close to the cap: rebuild it tick by tick
            tk = GS.fetch_day(mt5, pd.Timestamp(EPOCH + pd.Timedelta(days=d)))
            if len(tk) >= 1000:
                use_tick = True; tickdays += 1; ms = tk.ms.to_numpy(); tbid = tk.bid.to_numpy(); task = tk.ask.to_numpy(); eqt = np.zeros(len(ms))
                for j in sel:
                    op = (ms >= in_s[j] * 1000) & (ms < out_s[j] * 1000); mark = tbid if side[j] > 0 else task; eqt[op] += side[j] * (mark[op] - entry[j]) * q[j]
                    if out_s[j] < d1: eqt[ms >= out_s[j] * 1000] += pl[j]
            else:
                notick += 1
        if use_tick:
            lows.append((d, float(eqt.min())))
            hit = np.nonzero(eqt <= -L)[0]
            if len(hit):
                i = int(hit[0]); jf = min(int(np.searchsorted(ms, ms[i] + delay_ms, side="left")), len(ms) - 1); tmi = ms[jf]
                for j in sel:
                    if in_s[j] * 1000 > tmi: alive[j] = False
                    elif out_s[j] * 1000 > tmi:
                        mk = tbid[jf] if side[j] > 0 else task[jf]; pl[j] = side[j] * (mk - entry[j]) * q[j]; out_s[j] = tmi // 1000
                days.append(d); V.append(float(eqt[jf])); B.append(float(eqt[:jf + 1].min())); Hi.append(float(eqt[:jf + 1].max())); ev.append("loss"); continue
            closed = sum(pl[j] for j in sel if d0 <= out_s[j] < d1); days.append(d); V.append(float(closed)); B.append(float(min(eqt.min(), 0.0))); Hi.append(float(max(eqt.max(), 0.0))); ev.append(None); continue
        hit = np.nonzero(eq <= -L)[0]
        if len(hit):
            i = int(hit[0]); tmi = t_m[i]
            for j in sel:
                if in_s[j] > tmi: alive[j] = False
                elif out_s[j] > tmi:
                    mk = bid[i] if side[j] > 0 else ask[i]; pl[j] = side[j] * (mk - entry[j]) * q[j]; out_s[j] = tmi
            days.append(d); V.append(float(eq[i])); B.append(float(eq[:i + 1].min())); Hi.append(float(eq[:i + 1].max())); ev.append("loss")
        else:
            closed = sum(pl[j] for j in sel if d0 <= out_s[j] < d1); days.append(d); V.append(float(closed)); B.append(float(min(eq.min(), 0.0))); Hi.append(float(max(eq.max(), 0.0))); ev.append(None)
    return dict(days=np.array(days), V=np.array(V), B=np.array(B), Hi=np.array(Hi), ev=ev, tickdays=tickdays, notick=notick, lows=lows)


def outcomes(V, B, H):
    p = b = N = 0
    for i0 in range(len(V) - 53 + 1):
        N += 1; cnt = 0.0; res = None
        for j in range(53):
            k = i0 + j
            if B[k] <= -0.025 * A or A + cnt + B[k] <= 0.92 * A: res = ("breach", j); break
            cnt += min(V[k], CAPD) if V[k] > 0 else V[k]
            if cnt >= TARGET: res = ("pass", j); break
        yield res, N


def table(r):
    V, B = r["V"], r["B"]; n = len(V); out = {}
    for H, lab in ((37, "30 Nov"), (53, "22 Dec")):
        p = b = N = 0
        for i0 in range(n - 53 + 1):
            N += 1; cnt = 0.0
            for j in range(53):
                k = i0 + j
                if B[k] <= -0.025 * A or A + cnt + B[k] <= 0.92 * A:
                    b += j < H; break
                cnt += min(V[k], CAPD) if V[k] > 0 else V[k]
                if cnt >= TARGET:
                    p += j < H; break
        out[lab] = (100 * p / N, 100 * b / N)
    return out


def main():
    import MetaTrader5 as mt5
    bars = C.load_bars(); dd = lambda s: (pd.Timestamp(s) - EPOCH).days; lo, hi = dd("2025-10-01"), dd("2026-09-30")
    if not mt5.initialize(path=GS.TERM, portable=True, timeout=120000):
        raise SystemExit(f"cannot attach to {GS.TERM}: {mt5.last_error()}")
    try:
        for m in (1.0, 1.2, 1.5, 1.8):
            lots = {k: v * m for k, v in CH.items()}; tr = C.prep([GS.with_side(GC.trades("77900", lots["sdb"])).drop(columns=["side", "in_ms", "out_ms"]), GS.with_side(GC.trades("mkt_xau5min", lots["xau5"])).drop(columns=["side", "in_ms", "out_ms"])])
            rm = C.simulate(bars, tr, lo, hi, None, CAPD); rt = simulate_tick(bars, tr, lo, hi, CAPD, mt5)
            tm, tt = table(rm), table(rt); worst = min(rt["lows"], key=lambda x: x[1]) if rt["lows"] else (None, float("nan")); ib = int(np.argmin(rt["B"])); breach_days = [(str((EPOCH + pd.Timedelta(days=int(d))).date()), round(float(v))) for d, v in zip(rt["days"], rt["B"]) if v <= -2500]
            print(f"x{m}: SDB {lots['sdb']:.3f} + XAU5 {lots['xau5']:.3f} | candidate days replayed at tick level {rt['tickdays']} (no ticks: {rt['notick']}) | lowest UNGUARDED tick-level day path {worst[1]:+,.0f} on {(EPOCH + pd.Timedelta(days=int(worst[0]))).date() if worst[0] is not None else '-'} | lowest day equity WITH the guard (1 s reaction) {rt['B'][ib]:+,.0f} on {(EPOCH + pd.Timedelta(days=int(rt['days'][ib]))).date()} | guarded days at or below -2,500: {breach_days}", flush=True)
            print(f"      loss-cap triggers: minute model {sum(1 for e in rm['ev'] if e)} | tick model {sum(1 for e in rt['ev'] if e)} | pass / breach by 30 Nov: minute {tm['30 Nov'][0]:4.1f}% / {tm['30 Nov'][1]:4.1f}%  tick {tt['30 Nov'][0]:4.1f}% / {tt['30 Nov'][1]:4.1f}% | by 22 Dec: minute {tm['22 Dec'][0]:4.1f}% / {tm['22 Dec'][1]:4.1f}%  tick {tt['22 Dec'][0]:4.1f}% / {tt['22 Dec'][1]:4.1f}%", flush=True)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
