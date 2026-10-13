"""Consensus surprises at tick resolution (PREREG_TICK_EVENTS.md).
   python -m mt5broker.self_improving.events.tick_event_lab [--placebo]"""
import sys
ARGV = sys.argv[1:]

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.self_improving.events import event_lab as EL

TICKS = Path("D:/finance/ticks")
CUT = int(pd.Timestamp("2026-08-16").value // 10**6)                      # sealed: nothing at or after this instant is loaded
START = int(pd.Timestamp("2025-10-01").value // 10**6)
LAT = 300; BONF = 0.05 / 4; DELAYS = (10, 30); HOLDS = (60, 300)
OFFS = (-60, -10, -1, 1, 2, 5, 10, 30, 60, 300, 900)


def events(placebo):
    d = pd.read_csv(EL.CAL, low_memory=False, encoding="cp1252"); d["time"] = pd.to_datetime(d.time, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for c in ("actual", "forecast"): d[c] = pd.to_numeric(d[c], errors="coerce"); d.loc[d[c].abs() > 1e15, c] = np.nan
    h = d[(d.importance == 3) & d.actual.notna() & d.forecast.notna() & d.impact.isin([1, 2]) & d.currency.isin(EL.CCY)].sort_values("time").copy()
    h["err"] = h.actual - h.forecast; h["sd"] = h.groupby("event_id").err.transform(lambda s: s.expanding().std().shift(1)); h["n_prev"] = h.groupby("event_id").cumcount(); h = h[(h.n_prev >= 8) & (h.sd > 0)]
    h["S"] = np.where(h.impact == 1, 1, -1) * h.err.abs() / h.sd; h = h[(h.S.abs() >= 1.0) & (h.time >= "2025-10-01") & (h.time < "2026-08-16")].copy()
    t = h.time + (pd.Timedelta(days=7) if placebo else pd.Timedelta(0)); h["ms"] = [int((pd.Timestamp(x, tz="UTC").tz_convert("Europe/Athens").tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta(milliseconds=1)) for x in t]; h["ts"] = h.ms // 1000      # calendar times are UTC, the tick epoch is the SERVER clock (Athens, naive)
    h["tier1"] = h.name.apply(lambda n: any(k.lower() in n.lower() for k in EL.TIER1)); h = h[h.ms < CUT]; return h


def load_ticks():
    out = {}
    for a in {a for m in EL.SIGN.values() for a in m}:
        parts = [pd.read_parquet(f, columns=["time_msc", "bid", "ask"]) for f in sorted((TICKS / a).glob("2025-1*.parquet")) + sorted((TICKS / a).glob("2026-0[1-8].parquet"))]
        d = pd.concat(parts, ignore_index=True); d = d[(d.time_msc >= START) & (d.time_msc < CUT)].sort_values("time_msc", kind="stable"); out[a] = (d.time_msc.values.astype(np.int64), d.bid.values, d.ask.values)
    return out


def quote(tk, a, ms):
    t, b, k = tk[a]; i = np.searchsorted(t, ms, side="right") - 1
    return None if i < 0 or ms - t[i] > 600000 else (b[i], k[i])


def trade(tk, a, rel_ms, delay, hold):
    e = quote(tk, a, rel_ms + delay * 1000 + LAT); x = quote(tk, a, rel_ms + (delay + hold) * 1000 + 2 * LAT)
    return None if e is None or x is None else (x[0] / e[1] - 1, e[0] / x[1] - 1)          # (long, short) net


def basket(tk, ev, delay, hold):
    up, dn = [], []
    for a, sg in EL.SIGN[ev.currency].items():
        r = trade(tk, a, ev.ms, delay, hold)
        if r is None: continue
        L, S = r; up.append(L if sg > 0 else S); dn.append(S if sg > 0 else L)
    return (1e4 * np.mean(up), 1e4 * np.mean(dn)) if len(up) >= (5 if ev.currency == "USD" else 1) else None


def profile(tk, ev_df):
    rows = []
    for ev in ev_df.itertuples():
        for a, sg in EL.SIGN[ev.currency].items():
            q0 = quote(tk, a, ev.ms - 1000)
            if q0 is None: continue
            m0 = (q0[0] + q0[1]) / 2; r = {}
            for o in OFFS:
                q = quote(tk, a, ev.ms + o * 1000)
                if q: r[f"m{o}"] = np.sign(ev.S) * sg * ((q[0] + q[1]) / 2 / m0 - 1) * 1e4; r[f"s{o}"] = (q[1] - q[0]) / ((q[0] + q[1]) / 2) * 1e4
            rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", action="store_true"); a = ap.parse_args(ARGV); rng = np.random.default_rng(9)
    ev = events(a.placebo); tk = load_ticks(); usd = ev[ev.currency == "USD"]; print(f"{'PLACEBO (+7 days)' if a.placebo else 'REAL'}: strong events {len(ev)} (USD {len(usd)}, tier-1 USD {int(usd.tier1.sum())}), window 2025-10-01..2026-08-15, ticks loaded to {pd.to_datetime(CUT - 1, unit='ms')} server clock", flush=True)
    rows = []
    for delay in DELAYS:
        for hold in HOLDS:
            up, dn, sg, bl = [], [], [], []
            for e in usd.itertuples():
                r = basket(tk, e, delay, hold)
                if r: up.append(r[0]); dn.append(r[1]); sg.append(np.sign(e.S)); bl.append(e.ts)
            up, dn, sg, bl = map(np.array, (up, dn, sg, bl)); obs, p, nm = EL.perm_p(up, dn, sg, bl, rng) if len(up) >= 10 else (np.nan, 1.0, np.nan)
            x = np.where(sg > 0, up, dn); rows.append(dict(delay=delay, hold=hold, n=len(up), net=obs, p=p, nullmean=nm, win=float((x > 0).mean()) if len(x) else np.nan, sd=float(x.std(ddof=1)) if len(x) > 2 else np.nan))
            print(f"USD pool | delay {delay:2d}s hold {hold:3d}s | events {len(up):3d} | net {obs:+7.2f} bp (random-direction mean {nm:+.2f}) win {rows[-1]['win']*100:4.1f}% sd {rows[-1]['sd']:.1f} | p={p:.4f}", flush=True)
    df = pd.DataFrame(rows); df["pass"] = (df.p < BONF) & (df.net > 0) & (df.n >= 40); df.to_csv(f"D:/finance/si_ledgers/TICKEVENTS_{'placebo' if a.placebo else 'real'}.csv", index=False)
    print(f"DONE: passing {int(df['pass'].sum())} of {len(df)} (Bonferroni p < {BONF:.4f}, >= 40 events)")
    if not a.placebo:
        for name, sel in (("all strong USD events", usd), ("tier-1 USD events", usd[usd.tier1])):
            pr = profile(tk, sel); print(f"\nPROFILE {name} (n events {len(sel)}): mean signed mid move vs the quote 1 s before the release, follow direction, bp  |  mean spread bp")
            print("  offset(s) : " + " ".join(f"{o:>7d}" for o in OFFS)); print("  move (bp) : " + " ".join(f"{pr[f'm{o}'].mean():+7.2f}" for o in OFFS)); print("  spread bp : " + " ".join(f"{pr[f's{o}'].mean():7.2f}" for o in OFFS))


if __name__ == "__main__":
    main()
