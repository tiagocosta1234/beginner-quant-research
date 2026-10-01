"""
Round 282 (2026-10-01, PRE-REGISTERED): SESSION-RELAY LEAD-LAG across index CFDs (idea 1 of the brainstorm the trader approved: "work on that suggested order").
Why: MT5 broker's index CFDs trade ~23 hours a day, so there is no clean "US close -> Europe open" gap; but the day passes through three regional sessions
and information that arrives in one may be under-reacted to in the next. This round tests the relay at SEGMENT level with real bid/ask fills. It is a
breadth idea: if a relay existed it would exist across several index pairs at once. Prior (stated now): the ledger found no edge in ES/NQ lead-lag
(Round 195) and late-afternoon continuation was real before costs but not tradable on the CFD (Round 251); the honest expectation is no survivor.

SEGMENTS (New York wall clock; MT5 broker server = NY + 7 h; 'D' is the calendar date on which the segment starts):
  EUR(D): 03:00 -> 09:30   US(D): 09:30 -> 16:00   ASIA(D): 19:00 (D) -> 03:00 (D+1).
  A segment is valid only if its first bar starts within 5 minutes of the segment start, its last bar within 6 minutes of the segment end, and it has
  >= 80% of the minutes. This drops holidays, half-days and weekends automatically. Position held only inside one segment, so no swap and flat well
  before any rollover.
FEATURE: segment return = bid close(last bar) / bid open(first bar) - 1, divided by the instrument's trailing standard deviation of that segment's return
  over the previous 60 valid observations (>= 40 needed) = z. For the multi-instrument features the z's of the member instruments are averaged
  (all members needed).
TRADE: one position per cell per day in the TARGET segment: entry at the first bar of the target segment (long at ask open, short at bid open), exit at
  the last bar's close (long at bid close, short at ask close); measured MT5 broker costs (fills at the quote, no added slippage, indices commission 0).
  Net bps = P&L / entry price x 10,000.
PAIRS (feature -> target), 4 relays x 3 targets:
  P1  US(D) own z                          -> ASIA(D)      for US100, US500, US30           (a strong US day continues / fades overnight)
  P2  ASIA(D-1) own z                      -> EUR(D)       for GER40, FRA40, UK100           (Asia-hours move carries into the European morning)
  P3  EUR(D) mean z of GER40, FRA40, UK100 -> US(D)        for US100, US500, US30            (the European morning leads the US session)
  P4  US(D) mean z of US100, US500, US30   -> EUR(D+1)     for GER40, FRA40, UK100           (the US session leads the next European morning)
SIGN: s = +1 (continuation: trade in the direction of the feature) or s = -1 (fade). FILTER: ALL (any non-zero z) or STRONG (|z| >= 1).
CELLS: 4 pairs x 3 targets x 2 signs x 2 filters = 48; ledger k = 774 + 48 = 822. No parameter is tuned (60-day window, 1 SD, segment times are fixed).
SAMPLE: trade dates 2022-01-01 .. 2026-09-30 (the first months of M1 data are the z warm-up). IS = to 2024-06-30, OOS = 2024-07-01 .. 2026-09-30.
STATISTICS: per cell trades, win rate, mean net bps, mean cost bps (= minus the mean of long+short P&L / 2, the round-trip cost), bootstrap P(mean > 0) (4,000
  draws). Pooled per (pair, sign, filter): the daily mean over the three targets, day bootstrap (cross-instrument correlation makes per-trade pooling
  overstate significance), reported with annualised Sharpe of the daily series. CANDIDATE (the repo's rule, fixed now): IS P >= 0.95 AND OOS P >= 1 - 0.01/822
  AND OOS mean net bps > 0 AND OOS trades >= 150; also Benjamini-Hochberg q = 0.10 over the 48 OOS one-sided p-values (cells with OOS n >= 150).
PLACEBO (dry-run): random signs must give a mean of about minus the cost.
POWER_NOTES: mean absolute segment moves are 18-53 bps (US session 36-88 bps), i.e. standard deviations of ~25-110 bps; ~400-1,100 trades per cell give standard
  errors of ~2-5 bps against a round-trip cost of 0.5-2 bps, so only an edge of roughly 8 bps per trade or more is detectable in one cell (the dry-run's random-sign placebo
  means were within noise of minus the cost). FRA40 has only ~465 valid ASIA segments (it barely trades in Asian hours), so P1/P2 cells for it are smaller.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round271_one_to_one_generator as M

US = ["US100.cash", "US500.cash", "US30.cash"]
EU = ["GER40.cash", "FRA40.cash", "UK100.cash"]
SEGS = {"EUR": ((3, 0), (9, 30), 0, 0), "US": ((9, 30), (16, 0), 0, 0), "ASIA": ((19, 0), (3, 0), 0, 1)}   # start hm, end hm, start day offset, end day offset
FIRST, OOS_FROM, LAST = pd.Timestamp("2022-01-01"), pd.Timestamp("2024-07-01"), pd.Timestamp("2026-09-30")
PAIRS = {"P1": (US, "US", "ASIA", 0), "P2": (EU, "ASIA", "EUR", -1), "P3": (EU, "EUR", "US", 0), "P4": (US, "US", "EUR", 1)}   # members, feature seg, target seg, target date offset
TARGETS = {"P1": US, "P2": EU, "P3": US, "P4": EU}
K_TOTAL = 774 + 48
STRONG = 1.0


def arrays(sym):
    df = M.load(sym)
    return dict(t=df.index.values.astype("datetime64[ns]").astype(np.int64), bo=df["open"].values, bc=df["close"].values, ao=df["ask_open"].values, ac=df["ask_close"].values)


def seg_values(A, day, name):
    (sh, sm), (eh, em), so, eo = SEGS[name]
    s = pd.Timestamp(day) + pd.Timedelta(days=so, hours=sh, minutes=sm)
    e = pd.Timestamp(day) + pd.Timedelta(days=eo, hours=eh, minutes=em)
    t = A["t"]
    i0 = int(np.searchsorted(t, s.value, "left"))
    if i0 >= len(t) or t[i0] - s.value > 5 * 60 * 10 ** 9:
        return None
    i1 = int(np.searchsorted(t, e.value, "left")) - 1
    if i1 <= i0 or e.value - t[i1] > 6 * 60 * 10 ** 9 or t[i1] < s.value:
        return None
    mins = (e - s).total_seconds() / 60
    if (i1 - i0 + 1) < 0.8 * mins:
        return None
    bo, bc, ao, ac = A["bo"][i0], A["bc"][i1], A["ao"][i0], A["ac"][i1]
    if not (bo > 0 and bc > 0 and ao > 0 and ac > 0):
        return None
    return dict(ret=bc / bo - 1.0, long=(bc - ao) / ao * 1e4, short=(bo - ac) / bo * 1e4, t_start=s, t_end=e)


def build():
    days = pd.date_range("2021-11-15", "2026-10-01", freq="D")
    table = {}
    for sym in US + EU:
        A = arrays(sym)
        for seg in SEGS:
            rows = {}
            for d in days:
                v = seg_values(A, d, seg)
                if v is not None:
                    rows[d] = v
            ser = pd.Series({d: v["ret"] for d, v in rows.items()})
            z = ser / ser.shift(1).rolling(60, min_periods=40).std()
            for d, v in rows.items():
                v["z"] = z.get(d, np.nan)
            table[(sym, seg)] = rows
    return table


def trades(table, pair):
    members, fseg, tseg, off = PAIRS[pair]
    out = {t: [] for t in TARGETS[pair]}
    for d in pd.date_range(FIRST - pd.Timedelta(days=2), LAST, freq="D"):
        # feature date: for P2 the ASIA segment of the day BEFORE the trade date; others use the same date D with the target offset
        if pair == "P2":
            fd, td = d - pd.Timedelta(days=1), d
        elif pair == "P4":
            fd, td = d, d + pd.Timedelta(days=1)
        else:
            fd, td = d, d
        zs = []
        for m in members:
            v = table[(m, fseg)].get(fd)
            if v is None or not np.isfinite(v["z"]):
                zs = None; break
            zs.append(v["z"])
        if zs is None:
            continue
        z = float(np.mean(zs))
        fend = max(table[(m, fseg)][fd]["t_end"] for m in members)
        for tgt in TARGETS[pair]:
            v = table[(tgt, tseg)].get(td)
            if v is None or td < FIRST or td > LAST:
                continue
            assert v["t_start"] >= fend, "feature not complete before entry"
            out[tgt].append(dict(date=td, z=z, long=v["long"], short=v["short"]))
    return {k: pd.DataFrame(v) for k, v in out.items()}


def cell(df, sign, filt):
    if df.empty:
        return pd.DataFrame()
    x = df[df["z"] != 0].copy()
    if filt == "STRONG":
        x = x[x["z"].abs() >= STRONG]
    side = np.sign(x["z"]) * sign
    x["net"] = np.where(side > 0, x["long"], x["short"])
    x["cost"] = -(x["long"] + x["short"]) / 2.0
    return x


def pstat(x, lo, hi):
    y = x[(x["date"] >= lo) & (x["date"] <= hi)]
    if len(y) < 5:
        return dict(n=int(len(y)), mean=float("nan"), P=float("nan"), win=float("nan"), cost=float("nan"))
    return dict(n=int(len(y)), mean=float(y["net"].mean()), P=M.boot_p(y["net"].values), win=float((y["net"] > 0).mean()), cost=float(y["cost"].mean()))


def pooled(parts, lo, hi):
    """parts: list of per-target frames for ONE (pair, sign, filter); daily mean across targets, day bootstrap."""
    d = pd.concat([p[["date", "net"]] for p in parts if not p.empty])
    d = d[(d["date"] >= lo) & (d["date"] <= hi)].groupby("date")["net"].mean()
    if len(d) < 20:
        return dict(n=int(len(d)), mean=float("nan"), P=float("nan"), sharpe=float("nan"))
    return dict(n=int(len(d)), mean=float(d.mean()), P=M.boot_p(d.values), sharpe=float(d.mean() / d.std() * np.sqrt(252)))


def bh(ps, q=0.10):
    p = np.array(ps, float); o = np.argsort(p); m = len(p)
    ok = np.zeros(m, bool); thr = -1
    for r, i in enumerate(o, 1):
        if p[i] <= q * r / m:
            thr = r
    if thr > 0:
        ok[o[:thr]] = True
    return ok


def dry_run():
    t0 = time.time()
    table = build()
    print(f"built segment table ({time.time() - t0:.0f}s)")
    for sym in US + EU:
        print(f"  {sym:>11}: " + ", ".join(f"{seg} {len(table[(sym, seg)])} valid days, mean |ret| {np.mean([abs(v['ret']) for v in table[(sym, seg)].values()]) * 1e4:.0f} bps" for seg in SEGS))
    rng = np.random.default_rng(3)
    for pair in PAIRS:
        tr = trades(table, pair)
        rows = []
        for tgt, df in tr.items():
            x = cell(df, 1, "ALL")
            x["net"] = np.where(rng.random(len(x)) < 0.5, x["long"], x["short"])      # placebo: random side
            rows.append((tgt, len(x), x["net"].mean(), x["cost"].mean()))
        print(f"{pair}: " + "; ".join(f"{t} n={n} placebo mean {m:+.2f} bps (cost {c:.2f})" for t, n, m, c in rows))
    print("causality asserts passed (every entry after the feature segment ended)")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    table = build()
    res, rows, pool = {}, [], []
    for pair in PAIRS:
        tr = trades(table, pair)
        for sign in (1, -1):
            for filt in ("ALL", "STRONG"):
                parts = {}
                for tgt, df in tr.items():
                    x = cell(df, sign, filt)
                    parts[tgt] = x
                    if x.empty:
                        continue
                    i = pstat(x, FIRST, OOS_FROM - pd.Timedelta(days=1)); o = pstat(x, OOS_FROM, LAST)
                    rows.append(dict(pair=pair, tgt=tgt, sign=sign, filt=filt, IS=i, OOS=o))
                pi = pooled(list(parts.values()), FIRST, OOS_FROM - pd.Timedelta(days=1)); po = pooled(list(parts.values()), OOS_FROM, LAST)
                pool.append(dict(pair=pair, sign=sign, filt=filt, IS=pi, OOS=po))
    print(f"{'pair':>4} {'target':>11} {'side':>5} {'filt':>6} | {'IS n':>5} {'mean':>6} {'P':>5} | {'OOS n':>5} {'mean':>6} {'win':>5} {'cost':>5} {'P':>5}")
    for r in rows:
        i, o = r["IS"], r["OOS"]
        print(f"{r['pair']:>4} {r['tgt']:>11} {'cont' if r['sign'] > 0 else 'fade':>5} {r['filt']:>6} | {i['n']:>5} {i['mean']:>+6.2f} {i['P']:>5.2f} | {o['n']:>5} {o['mean']:>+6.2f} {o['win']:>5.1%} {o['cost']:>5.2f} {o['P']:>5.2f}")
    cand = [r for r in rows if r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["mean"] > 0 and r["OOS"]["n"] >= 150]
    elig = [r for r in rows if r["OOS"]["n"] >= 150]
    ok = bh([1 - r["OOS"]["P"] for r in elig], 0.10)
    print(f"\nCANDIDATES (IS P >= 0.95, OOS P >= {1 - 0.01 / K_TOTAL:.6f}, OOS mean > 0, n >= 150): {len(cand)} of {len(rows)}; Benjamini-Hochberg q=0.10 over {len(elig)} cells: {int(ok.sum())}")
    print("\nPooled (daily mean across the three targets):")
    print(f"{'pair':>4} {'side':>5} {'filt':>6} | {'IS days':>7} {'mean':>6} {'P':>5} | {'OOS days':>8} {'mean':>6} {'P':>5} {'Sharpe':>7}")
    for p in pool:
        i, o = p["IS"], p["OOS"]
        print(f"{p['pair']:>4} {'cont' if p['sign'] > 0 else 'fade':>5} {p['filt']:>6} | {i['n']:>7} {i['mean']:>+6.2f} {i['P']:>5.2f} | {o['n']:>8} {o['mean']:>+6.2f} {o['P']:>5.2f} {o['sharpe']:>+7.2f}")
    allm = np.array([r["OOS"]["mean"] for r in rows if np.isfinite(r["OOS"]["mean"])])
    print(f"\nOOS mean net bps over all {len(allm)} cells: mean {allm.mean():+.2f}, positive in {np.mean(allm > 0):.0%}")
    json.dump(dict(rows=rows, pooled=pool, n_candidates=len(cand), n_bh=int(ok.sum()), k_total=K_TOTAL), open(os.path.join(HERE, "round282_results.json"), "w"), indent=1, default=float)
    print(f"Saved round282_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
