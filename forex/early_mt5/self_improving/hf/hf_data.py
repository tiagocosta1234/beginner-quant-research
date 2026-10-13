"""Tick features and execution labels for the frequent-trading family (PREREG_HF.md).
   python -m mt5broker.self_improving.hf.hf_data [--symbols EURUSD,SP] [--force]
Reads D:\\finance\\ticks\\<SYM>\\*.parquet (ticks before 2026-08-16 UTC only: the HOLD of this family is never loaded) and writes D:\\finance\\ticks_feat\\<SYM>.parquet."""
import sys
ARGV = sys.argv[1:]

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

TICKS = Path("D:/finance/ticks"); FEAT = Path("D:/finance/ticks_feat"); FEAT.mkdir(parents=True, exist_ok=True)
CUT = int(pd.Timestamp("2026-08-16", tz="UTC").value // 10**6)           # ms: nothing at or after this instant is loaded (sealed HOLD of this family)
SYMS = {"fx": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"], "cmd": ["XAUUSD"], "idx": ["SP", "NSDQ", "DOW", "DAX"], "crypto": ["BTCUSD"]}
HLIST = (1, 5, 15, 60); DLIST = (0.0, 1.0); LAT = 300; WAIT = 60000
WINS = {"a": ("2025-10-01", "2026-02-28"), "b": ("2026-03-01", "2026-05-31"), "val": ("2026-06-01", "2026-08-15")}
MOM = (1, 5, 15, 60, 300, 900, 3600, 14400)
FEATS = [f"mom{k}" for k in MOM] + ["rv5", "rv60", "rv300", "act5", "act60", "act300", "sp_bp", "sp_chg60", "sp_rel", "bu", "bd", "au", "ad", "net_dir", "asym", "d_hi", "d_lo", "hour", "minute", "dow",
                                    "cpi_to", "cpi_since", "nfp_to", "nfp_since", "fomc_to", "fomc_since", "any_to", "any_since"]
EVENT_NY = {"NFP": (8, 30), "CPI": (8, 30), "FOMC": (14, 0)}


def events_utc():
    cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); out = {}
    for k, (hh, mm) in EVENT_NY.items():
        out[k] = np.array(sorted(int((pd.Timestamp(f"{d} {hh:02d}:{mm:02d}").tz_localize("America/New_York").tz_convert("Europe/Athens").tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)) for d in cal[cal.kind == k].date))      # tick epoch = SERVER clock
    out["ANY"] = np.array(sorted(np.concatenate([out[k] for k in EVENT_NY]))); return out


def load(sym):
    parts = [pd.read_parquet(f, columns=["time_msc", "bid", "ask"]) for f in sorted((TICKS / sym).glob("*.parquet"))]
    d = pd.concat(parts, ignore_index=True); d = d[d.time_msc < CUT]; d = d.sort_values("time_msc", kind="stable"); return d.time_msc.values.astype(np.int64), d.bid.values.astype(np.float64), d.ask.values.astype(np.float64)


def at(t, x):
    """index of the last tick at or before x (x array of ms)."""
    return np.searchsorted(t, x, side="right") - 1


def build(sym):
    t0 = time.time(); t, bid, ask = load(sym); n = len(t); mid = (bid + ask) / 2; lm = np.log(mid)
    dm = np.diff(lm, prepend=lm[0]); cs_rv = np.cumsum(dm ** 2); db, da = np.diff(bid, prepend=bid[0]), np.diff(ask, prepend=ask[0])
    cs = {"bu": np.cumsum(db > 0), "bd": np.cumsum(db < 0), "au": np.cumsum(da > 0), "ad": np.cumsum(da < 0)}
    T = np.arange(((t[0] // 60000) + 2) * 60000, (t[-1] // 60000) * 60000, 60000, dtype=np.int64)
    iT = at(t, T); recent = (t[iT] >= T - 120000) & (iT - at(t, T - 300000) >= 1)
    dtm = pd.to_datetime(T, unit="ms"); hour = dtm.hour.values; ok = recent & ~np.isin(hour, (23, 0)) & (dtm.dayofweek.values < 5)       # the tick epoch is the SERVER clock already (Athens, naive)
    T, iT, hour = T[ok], iT[ok], hour[ok]; dtm = pd.to_datetime(T, unit="ms")
    X = pd.DataFrame(index=np.arange(len(T)))
    rv3600 = cs_rv[iT] - cs_rv[np.maximum(at(t, T - 3600000), 0)]
    for k in MOM:
        ik = at(t, T - k * 1000); mom = lm[iT] - np.where(ik >= 0, lm[np.maximum(ik, 0)], np.nan)
        X[f"mom{k}"] = mom / np.sqrt(np.maximum(rv3600, 1e-18) * k / 3600.0)
    for w in (5, 60, 300):
        iw = np.maximum(at(t, T - w * 1000), 0); X[f"rv{w}"] = (cs_rv[iT] - cs_rv[iw]) / np.maximum(rv3600 * w / 3600.0, 1e-18); X[f"act{w}"] = (iT - iw) / np.maximum((iT - np.maximum(at(t, T - 3600000), 0)) * w / 3600.0, 1e-9)
    spb = (ask[iT] - bid[iT]) / mid[iT] * 1e4; X["sp_bp"] = spb; i60 = np.maximum(at(t, T - 60000), 0); X["sp_chg60"] = spb - (ask[i60] - bid[i60]) / mid[i60] * 1e4
    X["sp_rel"] = spb / pd.Series(spb).rolling(60, min_periods=20).median().values
    i60 = np.maximum(at(t, T - 60000), 0)
    for k in ("bu", "bd", "au", "ad"): X[k] = cs[k][iT] - cs[k][i60]
    X["net_dir"] = (X.bu + X.au) - (X.bd + X.ad); X["asym"] = (X.bu - X.bd) - (X.au - X.ad)
    day = pd.to_datetime(T, unit="ms").normalize().values; s = pd.Series(mid[iT]); g = s.groupby(day)
    X["d_hi"] = np.log(mid[iT]) - np.log(g.cummax().values); X["d_lo"] = np.log(mid[iT]) - np.log(g.cummin().values)
    X["hour"] = hour; X["minute"] = dtm.minute.values; X["dow"] = dtm.dayofweek.values
    ev = events_utc(); Ts = T // 1000
    for kk, nm in (("CPI", "cpi"), ("NFP", "nfp"), ("FOMC", "fomc"), ("ANY", "any")):
        E = ev[kk]; i = np.searchsorted(E, Ts, side="left"); j = np.searchsorted(E, Ts, side="right") - 1
        X[f"{nm}_to"] = np.minimum(np.where(i < len(E), (E[np.minimum(i, len(E) - 1)] - Ts) / 60.0, 240.0), 240.0); X[f"{nm}_since"] = np.minimum(np.where(j >= 0, (Ts - E[np.maximum(j, 0)]) / 60.0, 240.0), 240.0)
    # ---- labels
    ie = at(t, T + LAT); entry_ask, entry_bid, mid_e = ask[ie], bid[ie], mid[ie]; lab = {}
    def exit_ok(tx): return (tx < t[-1]) & (tx < CUT) & ~np.isin(pd.to_datetime(tx, unit="ms").hour.values, (23, 0))
    for H in HLIST:
        tx = T + LAT + H * 60000 + LAT; ix = at(t, tx); ok_x = exit_ok(tx)
        for nm, v in (("mL", bid[ix] / entry_ask - 1), ("mS", entry_bid / ask[ix] - 1), ("mG", mid[ix] / mid_e - 1)): lab[f"{nm}{H}"] = np.where(ok_x, v, np.nan)
    ref_bid, ref_ask, ref_mid = bid[iT], ask[iT], mid[iT]; end = T + LAT + WAIT; jmax = int(min(1500, np.percentile(np.diff(np.searchsorted(t, T[::50] + WAIT)) if len(T) > 100 else [100], 95) * 1.6 + 50))
    for d in DLIST:
        for side in ("L", "S"):
            Lp = ref_bid - d * 1e-4 * ref_mid if side == "L" else ref_ask + d * 1e-4 * ref_mid; fill = np.full(len(T), -1, np.int64); alive = np.arange(len(T))
            for j in range(jmax):
                c = ie[alive] + j; v = (c < n) & (t[np.minimum(c, n - 1)] <= end[alive])
                hit = v & ((ask[np.minimum(c, n - 1)] <= Lp[alive]) if side == "L" else (bid[np.minimum(c, n - 1)] >= Lp[alive]))
                fill[alive[hit]] = c[hit]; alive = alive[v & ~hit]
                if len(alive) == 0: break
            filled = fill >= 0; tf = np.where(filled, t[np.maximum(fill, 0)], 0)
            for H in HLIST:
                tx = tf + H * 60000 + LAT; ix = at(t, tx); ok_x = filled & exit_ok(tx); v = (bid[ix] / Lp - 1) if side == "L" else (Lp / ask[ix] - 1)
                lab[f"l{int(d)}{side}{H}"] = np.where(ok_x, v, np.nan)
    L = pd.DataFrame(lab); out = pd.concat([pd.DataFrame({"t": T}), X.astype(np.float32), L.astype(np.float32)], axis=1)
    day_ = pd.to_datetime(T, unit="ms").normalize(); w = np.full(len(T), "", dtype=object)
    for k, (a, b) in WINS.items(): w[(day_ >= pd.Timestamp(a)) & (day_ <= pd.Timestamp(b))] = k
    out["win"] = w; out = out[out.win != ""].reset_index(drop=True); out["dayid"] = (out.t // 86400000).astype(np.int32); out.to_parquet(FEAT / f"{sym}.parquet", compression="zstd", index=False)
    print(f"[{sym}] {n:,} ticks -> {len(out):,} decisions ({', '.join(f'{k}={int((out.win==k).sum()):,}' for k in WINS)}) | fill rates d=0 {np.mean(np.isfinite(out['l0L5'])):.3f} d=1 {np.mean(np.isfinite(out['l1L5'])):.3f} | {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--symbols", default=",".join(s for v in SYMS.values() for s in v)); ap.add_argument("--force", action="store_true"); a = ap.parse_args(ARGV)
    for s in a.symbols.split(","):
        if (FEAT / f"{s}.parquet").exists() and not a.force: print(f"[{s}] exists"); continue
        build(s)
