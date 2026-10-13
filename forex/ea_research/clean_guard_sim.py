"""CLEAN event-driven simulation of the account guard on the pair's real trade stream (replaces the carry-over approximation of mt5data_guard_carry.series, which kept counting the floating P&L of positions the guard had already closed: 'phantom' floating profit that re-triggered the profit cap on the following days and inflated every profit-cap result).
   python -m forex.ea_research.clean_guard_sim      (written 2026-10-09 after verify_guard_gain.py showed the phantom effect; the earlier deadline / lock / sizing tables that include the PROFIT cap are withdrawn)
Method: day by day (server days), the minute equity vs the day's start balance = realised P&L of trades closed that day + floating P&L of every OPEN position (longs marked at the bid, shorts at the ask = bid + the bar's spread, from MT5 broker's M1 gold bars).
At the first minute where equity <= -L (loss cap) or >= +P (profit cap) the guard flattens: positions open at that minute are CLOSED at that minute's market price (their P&L is realised then; their original later exit is discarded) and trades that would have been OPENED later that day are dropped; the day's P&L is the equity at that minute.
Later days start from the modified trade list, so a closed position never contributes again. Assumptions: the EAs' entry decisions do not depend on the guard's earlier actions; re-opened positions after a halt cost nothing (the real guard closes them within seconds). Validation: with no caps the total P&L must equal the sum of the trades' P&L."""
from __future__ import annotations

import sys
sys.argv = ["x", "--source", "mt5broker"]
import numpy as np
import pandas as pd

from forex.ea_batch.mt5_mc_config import CH
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch.mt5data_sizing_long import trades_mt5broker

A, CAPD, TARGET, LOCK = 100_000.0, 2_000.0, 8_000.0, 8_300.0
EPOCH = pd.Timestamp("1970-01-01")


def load_bars():
    M = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet", columns=["t", "bc", "sp"]).sort_values("t").reset_index(drop=True)
    return M.t.to_numpy("int64"), M.bc.to_numpy("float64"), M.sp.to_numpy("float64")


def prep(trs: list[pd.DataFrame]) -> dict:
    T = pd.concat(trs, ignore_index=True).sort_values("t_in").reset_index(drop=True); move = T.exit - T.entry
    side = np.where(T.pl * move >= 0, 1.0, -1.0); side[(move == 0).to_numpy()] = 1.0
    ts = lambda s: ((pd.to_datetime(s) - EPOCH) // pd.Timedelta(seconds=1)).astype("int64").to_numpy()
    return dict(in_s=ts(T.t_in), out_s=ts(T.t_out), side=side, entry=T.entry.to_numpy("float64"), exit=T.exit.to_numpy("float64"), q=100.0 * T.vol.to_numpy("float64"), pl=T.pl.to_numpy("float64"))


def simulate(bars, tr: dict, d_lo: int, d_hi: int, P, L):
    tm, bc, sp = bars; in_s, out_s, side, entry, q = tr["in_s"], tr["out_s"].copy(), tr["side"], tr["entry"], tr["q"]; pl = tr["pl"].copy(); alive = np.ones(len(in_s), bool)
    days, V, B, Hi, halts = [], [], [], [], []
    for d in range(d_lo, d_hi + 1):
        d0, d1 = d * 86400, (d + 1) * 86400; a = int(np.searchsorted(tm, d0)); b = int(np.searchsorted(tm, d1))
        if b - a < 60: continue
        t_m = tm[a:b]; bid = bc[a:b]; ask = bc[a:b] + sp[a:b]; eq = np.zeros(b - a); sel = np.nonzero(alive & (out_s >= d0) & (in_s < d1))[0]
        for j in sel:
            op = (t_m >= in_s[j]) & (t_m < out_s[j]); mark = bid if side[j] > 0 else ask
            eq[op] += side[j] * (mark[op] - entry[j]) * q[j]
            if out_s[j] < d1: eq[t_m >= out_s[j]] += pl[j]
        trig = None
        if P is not None and (eq >= P).any(): trig = ("profit", int(np.argmax(eq >= P)))
        if L is not None and (eq <= -L).any():
            il = int(np.argmax(eq <= -L))
            if trig is None or il < trig[1]: trig = ("loss", il)
        if trig is not None:
            kind, i = trig; tmi = t_m[i]
            for j in sel:
                if in_s[j] > tmi: alive[j] = False
                elif out_s[j] > tmi:
                    mk = bid[i] if side[j] > 0 else ask[i]; pl[j] = side[j] * (mk - entry[j]) * q[j]; out_s[j] = tmi
            days.append(d); V.append(float(eq[i])); B.append(float(eq[:i + 1].min())); Hi.append(float(eq[:i + 1].max())); halts.append(kind)
        else:
            closed_today = sum(pl[j] for j in sel if d0 <= out_s[j] < d1)
            days.append(d); V.append(float(closed_today)); B.append(float(min(eq.min(), 0.0))); Hi.append(float(max(eq.max(), 0.0))); halts.append(None)
    return dict(days=np.array(days), V=np.array(V), B=np.array(B), Hi=np.array(Hi), ev=halts, total_pl=float(pl[alive].sum()))


def deadline(V, B, Hi, idx, H, lock):
    out = {"pass": 0, "breach": 0, "run": 0}; n = 0
    for i0 in idx:
        if i0 + H > len(V): continue
        n += 1; bal, cnt, res = A, 0.0, "run"
        for j in range(H):
            k = i0 + j
            if B[k] <= -0.025 * A or bal + B[k] <= 0.92 * A: res = "breach"; break
            if lock and cnt + min(Hi[k], CAPD) >= LOCK: res = "pass"; break
            x = min(V[k], CAPD) if V[k] > 0 else V[k]; bal += x; cnt += x
            if cnt >= TARGET: res = "pass"; break
        out[res] += 1
    return out, n


def main():
    bars = load_bars(); dd = lambda s: (pd.Timestamp(s) - EPOCH).days
    pools = {"ALL 2022-26 (MT5 broker trades scaled to 4,100 / price, MT5 broker bars)": ("mt5broker", dd("2022-01-01"), dd("2026-09-30")), "LAST 12 MONTHS (MT5 broker trades + MT5 broker bars)": ("mt5", dd("2025-10-01"), dd("2026-09-30"))}
    for pname, (src, d_lo, d_hi) in pools.items():
        print(f"\n##### {pname}", flush=True)
        for m in (1.0, 1.2, 1.4):
            lots = {k: v * m for k, v in CH.items()}
            trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
            tr = prep(trs)
            if src == "mt5broker":
                keep = (tr["out_s"] >= d_lo * 86400); [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]
                f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f                        # same % risk as 0.12 lot at 4,100: lots scale with 1 / price (as the pipeline's lam_frozen does)
            base_total = float(tr["pl"].sum())
            for nm, P, L in (("no guard", None, None), ("loss cap only", None, CAPD), ("profit cap only", CAPD, None), ("both caps", CAPD, CAPD)):
                r = simulate(bars, tr, d_lo, d_hi, P, L); V, B, Hi = r["V"], r["B"], r["Hi"]; n_idx = len(V); H = 37
                idx = list(range(n_idx)); a, n = deadline(V, B, Hi, idx, H, False); b, _ = deadline(V, B, Hi, idx, H, True); ev = [e for e in r["ev"] if e]
                chk = f"| total P&L {V.sum():9,.0f} (trade list {base_total:9,.0f})" if nm == "no guard" else f"| total P&L {V.sum():9,.0f}"
                print(f"  x{m} {nm:16s} halts loss {ev.count('loss'):3d} profit {ev.count('profit'):3d} {chk} | by 30 Nov (37 bd): pass {100*a['pass']/n:5.1f}% breach {100*a['breach']/n:5.1f}% | with pass lock {100*b['pass']/n:5.1f}% [starts {n}]", flush=True)


if __name__ == "__main__":
    main()
