"""MT5 economic-calendar surprise study (PREREG_EVENTS.md).
   python -m forex.self_improving.events.event_lab [--placebo]"""
import sys
ARGV = sys.argv[1:]

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("forex/data_mt5")
CAL = "data/data_macro/mt5_calendar.csv"
CCY = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF"]
SIGN = {"USD": {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1, "USDJPY": 1, "USDCAD": 1, "USDCHF": 1, "XAUUSD": -1}, "EUR": {"EURUSD": 1}, "GBP": {"GBPUSD": 1}, "JPY": {"USDJPY": -1}, "AUD": {"AUDUSD": 1}, "CAD": {"USDCAD": -1}, "NZD": {"NZDUSD": 1}, "CHF": {"USDCHF": -1}}
TIER1 = ["Non-Farm", "Nonfarm", "Unemployment Rate", "Average Hourly Earnings", "CPI", "Retail Sales", "GDP", "Initial Jobless Claims", "PMI", "Fed Interest Rate", "FOMC"]
HS = (5, 15, 60); DELAYS = (1, 5); NPERM = 20000; BONF = 0.05 / 18


def load_events(placebo):
    d = pd.read_csv(CAL, low_memory=False, encoding="cp1252"); d["time"] = pd.to_datetime(d.time, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for c in ("actual", "forecast"): d[c] = pd.to_numeric(d[c], errors="coerce"); d.loc[d[c].abs() > 1e15, c] = np.nan
    h = d[(d.importance == 3) & d.actual.notna() & d.forecast.notna() & d.impact.isin([1, 2]) & (d.time < "2026-01-01") & d.currency.isin(CCY)].sort_values("time").copy()
    h["err"] = h.actual - h.forecast; h["sd"] = h.groupby("event_id").err.transform(lambda s: s.expanding().std().shift(1)); h["n_prev"] = h.groupby("event_id").cumcount(); h = h[(h.n_prev >= 8) & (h.sd > 0)]
    h["S"] = np.where(h.impact == 1, 1, -1) * h.err.abs() / h.sd; h = h[h.S.abs() >= 1.0].copy()
    t = h.time + (pd.Timedelta(days=7) if placebo else pd.Timedelta(0))
    h["sec"] = [int((x.tz_localize("UTC").tz_convert("Europe/Athens").tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)) for x in t]
    h["ts"] = h.sec; h["tier1"] = h.name.apply(lambda n: any(k.lower() in n.lower() for k in TIER1)); return h


def load_prices():
    out = {}
    for a in {a for m in SIGN.values() for a in m}:
        d = pd.read_parquet(DATA / f"{a}_M1_rates.parquet", columns=["t", "bo", "bc", "ao", "ac"]).sort_values("t").drop_duplicates("t"); out[a] = (d.t.values.astype(np.int64), d.bo.values, d.bc.values, d.ao.values, d.ac.values)
    return out


def trade(px, a, sec, delay, H):
    """(net if long, net if short) for asset a: entry at the first M1 bar starting at least `delay` minutes after the release, exit at the close of the bar that closes H minutes after it."""
    t, bo, bc, ao, ac = px[a]; te = sec + delay * 60; i = np.searchsorted(t, te)
    if i >= len(t) or t[i] - te > 60: return None
    tx = t[i] + (H - 1) * 60; j = np.searchsorted(t, tx)
    if j >= len(t) or t[j] != tx: return None
    return bc[j] / ao[i] - 1, bo[i] / ac[j] - 1


def basket(px, ev, delay, H):
    """For one event: (net if direction +1, net if direction -1) in bp, averaged over the mapped assets; direction +1 means 'currency strengthens'."""
    up, dn = [], []
    for a, sg in SIGN[ev.currency].items():
        r = trade(px, a, ev.sec, delay, H)
        if r is None: continue
        L, S = r; up.append(L if sg > 0 else S); dn.append(S if sg > 0 else L)
    need = 5 if ev.currency == "USD" else 1
    return (1e4 * np.mean(up), 1e4 * np.mean(dn)) if len(up) >= need else None


def perm_p(up, dn, sgn, block, rng):
    obs = np.where(sgn > 0, up, dn).mean(); u = np.unique(block); idx = {b: k for k, b in enumerate(u)}; bk = np.array([idx[b] for b in block]); flips = rng.choice([-1, 1], size=(NPERM, len(u)))[:, bk]
    null = np.where(flips * sgn > 0, up, dn).mean(axis=1); return obs, float((null >= obs).mean()), float(null.mean())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", action="store_true"); a = ap.parse_args(ARGV); rng = np.random.default_rng(5)
    ev = load_events(a.placebo); px = load_prices(); ev["dev"] = ev.time < "2025-01-01"; rows = []
    pools = {"P1 USD (basket of 8)": ev.currency == "USD", "P2 non-USD": ev.currency != "USD", "P3 tier-1 US": (ev.currency == "USD") & ev.tier1}
    print(f"{'PLACEBO calendar (+7 days)' if a.placebo else 'REAL calendar'}: strong events {len(ev)} (DEV {int(ev.dev.sum())}, 2025 {int((~ev.dev).sum())})", flush=True)
    for pn, mask in pools.items():
        for delay in DELAYS:
            for H in HS:
                res = {}
                for w, sel in (("DEV", mask & ev.dev), ("VAL", mask & ~ev.dev)):
                    up, dn, sg, bl = [], [], [], []
                    for ev_i in ev[sel].itertuples():
                        r = basket(px, ev_i, delay, H)
                        if r: up.append(r[0]); dn.append(r[1]); sg.append(np.sign(ev_i.S)); bl.append(ev_i.ts)
                    up, dn, sg, bl = map(np.array, (up, dn, sg, bl))
                    res[w] = perm_p(up, dn, sg, bl, rng) + (len(up),) if len(up) >= 10 else (np.nan, 1.0, np.nan, len(up))
                rows.append(dict(pool=pn, delay=delay, H=H, n_dev=res["DEV"][3], dev_net=res["DEV"][0], dev_p=res["DEV"][1], dev_null=res["DEV"][2], n_val=res["VAL"][3], val_net=res["VAL"][0], val_p=res["VAL"][1]))
                r = rows[-1]; print(f"{pn:22s} delay {delay}m H {H:2d}m | DEV n={r['n_dev']:3d} net {r['dev_net']:+7.2f} bp (random-direction mean {r['dev_null']:+.2f}) p={r['dev_p']:.4f} | 2025 n={r['n_val']:3d} net {r['val_net']:+7.2f} bp p={r['val_p']:.3f}", flush=True)
    df = pd.DataFrame(rows); df["pass_dev"] = (df.dev_p < BONF) & (df.dev_net > 0); df["pass_val"] = df.pass_dev & (df.val_p < 0.05) & (df.val_net > 0)
    df.to_csv(f"data/si_ledgers/EVENTS_{'placebo' if a.placebo else 'real'}.csv", index=False); print(f"DONE: DEV passes {int(df.pass_dev.sum())} of {len(df)} (Bonferroni p < {BONF:.4f}) | also pass 2025: {int(df.pass_val.sum())} | best DEV p {df.dev_p.min():.4f}")


if __name__ == "__main__":
    main()
