"""
Round 298 (2026-10-02, PRE-REGISTERED): is there ANY day-of-week or hour-of-day filter -- a weekday, or a 30-minute slot of the day, in which a fixed-direction index trade has a positive mean AFTER the real spread, out of sample?
(the trader: "try to find any day of the week or hour of the day filter".)
Step 0 (ledger checked first, k = 1095): day-of-week was tested on ES/NQ/YM/RTY futures (Round 163: Monday short, Tuesday-Friday long: no edge), the turn of the month (Round 122), multi-day trend and turn of the month on MT5 (Round 253), 5-minute slots of the day on MNQ/MGC futures (Round 138, P1: no edge), the
location filters of the pass policy (Round 274: no gain). NOT tested: (a) weekday x 30-minute slot on MT5 broker's own CFD M1 bid/ask (real spreads) across the six index CFDs, (b) the weekday legs (overnight / intraday / close-to-close) on the 1990-2017 cash indices with the dip-reversal's cost model. This round does both.
PART A -- WEEKDAY LEGS, 8 cash indices (spx, ndx, dji, dax, ftse, cac, n225, hsi; Round 287 files). For each weekday w (Mon-Fri, of the day t) and leg: OVERNIGHT (previous close -> open of t), INTRADAY (open -> close of t), CLOSE-TO-CLOSE (previous close -> close of t); daily returns with |r| > 50% set to 0 (Round 287's rule); DATA-QUALITY RULE (added after the dry run showed 20% of the overnight legs exactly 0, i.e. open == previous close, from counts only): an index-day whose overnight leg is exactly 0 loses its overnight and intraday legs (close-to-close is kept). Per date the leg is the equal-weight mean over the indices trading
that day (>= 3). Cost per leg per trade: 2.0 bp + 3.3 bp per calendar night held (intraday 2.0; overnight and close-to-close 2.0 + 3.3 x nights since the previous close). Direction = the sign of the IN-SAMPLE mean of the leg on that weekday (long or short), then the same direction is tested OUT of sample. 5 weekdays x 3 legs = 15 hypotheses.
IS = 1990-01-01 .. 2005-12-31, OOS = 2006-01-01 .. 2017-12-27 (the span of the files used by Rounds 285-293).
PART B -- WEEKDAY x 30-MINUTE SLOT on MT5 M1 bid/ask (US100, US500, US30, GER40, FRA40, UK100 .cash; round271 loader, NY wall clock, 2021-10-04 .. 2026-09-30). Slot s = [03:00 + 30 s min, +30 min), s = 0..24 (03:00 .. 15:30, ends by 16:00 NY); the entry is the OPEN of the slot's first minute bar and the exit the OPEN of the next slot's first minute bar (a bar must exist at both times, else the day is skipped for that
slot); long = buy at the ask open, sell at the bid open; short = sell at the bid, buy at the ask; net bps = P&L / mid at entry x 10^4 after the real quoted spread; gross bps = mid-to-mid. Weekday group g in (Mon, Tue, Wed, Thu, Fri, all days). A POOLED hypothesis per (g, s) = the equal-weight mean over the six indices per date (>= 3 present) = 6 x 25 = 150 hypotheses; direction = the sign of the IS mean of the gross
bps (sign fixed on the gross series so that the cost cannot choose it); IS = 2021-10-04 .. 2024-06-30, OOS = 2024-07-01 .. 2026-09-30. Per-instrument cells (900) are reported as REPLICATION only (not hypotheses).
STATISTICS: per hypothesis n days, IS and OOS mean NET bps, mean gross bps, day-clustered bootstrap P(mean > 0) (4,000 draws, seed 2981). CANDIDATE (the repo's rule; K_TOTAL = 1095 + 15 + 150 = 1,260): IS P >= 0.95 AND OOS P >= 1 - 0.01/1260 AND OOS mean net > 0 AND OOS n >= 100 days, plus Benjamini-Hochberg at q = 0.10 over the OOS one-sided p-values of all 165 hypotheses
(p = 1 - OOS P, floored at 1/4000). PRACTICAL SECOND VERDICT: a candidate is usable as a FILTER for a daily one-trade policy only if its OOS mean net >= 2.0 bp and the same direction is positive OOS in >= 4 of 6 indices (Part B) / 5 of 8 (Part A). CHANCE CHECK (descriptive): the number of hypotheses with IS P >= 0.95 that are positive OOS, against the expected count under no effect.
PRIOR (stated now): no candidate. The sign is chosen in sample, so about 5-10% of the 165 hypotheses will look good in sample and about half of those stay positive out of sample before costs; the quoted CFD spread is 1.0-2.0 bp for a round trip on the index CFDs and a 30-minute move has a standard deviation of ~10-20 bp with ~600 OOS days (a standard error of ~0.5 bp), so a net edge needs a gross edge of
over 2 bp. Part A's overnight leg has a known positive mean on long indices (the overnight drift) but 5.3 bp of cost and swap leave little.
POWER_NOTES: 165 hypotheses is a large family against 600 OOS days (Part B); nothing under about 1.5 bp is detectable; the six indices are highly correlated, so the replication count is not six independent tests; the weekday effect, if real, may need futures-style costs, not CFD swaps (Part A uses 3.3 bp a night).
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round271_one_to_one_generator as M

CASH = ["spx", "ndx", "dji", "dax", "ftse", "cac", "n225", "hsi"]
CASH_DIR = os.path.join(ROOT, "futures", "data", "external_index_daily")
CFDS = ["US100.cash", "US500.cash", "US30.cash", "GER40.cash", "FRA40.cash", "UK100.cash"]
A_IS_END, A_FROM, A_TO = pd.Timestamp("2005-12-31"), pd.Timestamp("1990-01-01"), pd.Timestamp("2017-12-27")
B_FROM, B_IS_END, B_TO = pd.Timestamp("2021-10-04"), pd.Timestamp("2024-06-30"), pd.Timestamp("2026-09-30")
NSLOT = 25
BMIN = [180 + 30 * b for b in range(NSLOT + 1)]            # 03:00 .. 16:00 NY in minutes
GROUPS = ["Mon", "Tue", "Wed", "Thu", "Fri", "all"]
K_PRIOR, K_TOTAL, BOOT, SEED = 1095, 1095 + 15 + 150, 4000, 2981
SP_A, NIGHT_A = 2.0, 3.3


def pboot(x, rng):
    x = x[np.isfinite(x)]
    if len(x) < 20:
        return float("nan")
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float((x[idx].mean(axis=1) > 0).mean())


# ------------------------------------------------------------------ Part A
def cash_legs():
    legs = {"overnight": [], "intraday": [], "c2c": []}
    nights = []
    for name in CASH:
        d = pd.read_csv(os.path.join(CASH_DIR, name + ".csv"), parse_dates=["date"]).set_index("date").sort_index()
        d = d[(d.index >= A_FROM) & (d.index <= A_TO)]
        o, c = d["open"].astype(float), d["close"].astype(float)
        pc = c.shift()
        ov, intr, cc = (o / pc - 1.0), (c / o - 1.0), (c / pc - 1.0)
        bad = ov == 0.0                                                     # open == previous close exactly: the open is not a real print (data-quality rule fixed after the dry-run counts, no P&L seen)
        ov, intr = ov.mask(bad), intr.mask(bad)
        for s, v in (("overnight", ov), ("intraday", intr), ("c2c", cc)):
            legs[s].append(v.mask(v.abs() > 0.5, 0.0).rename(name))
        nights.append(pd.Series((d.index.to_series().diff().dt.days).values, index=d.index, name=name))
    out = {}
    for s, lst in legs.items():
        X = pd.concat(lst, axis=1)
        cnt = X.notna().sum(axis=1)
        out[s] = (X.mean(axis=1, skipna=True)[cnt >= 3] * 1e4, X[cnt >= 3])
    N = pd.concat(nights, axis=1).median(axis=1)
    return out, N


def part_a(rng):
    legs, N = cash_legs()
    rows = []
    for leg in ("overnight", "intraday", "c2c"):
        ser, X = legs[leg]
        ser = ser.dropna()
        cost = pd.Series(SP_A, index=ser.index) if leg == "intraday" else SP_A + NIGHT_A * N.reindex(ser.index).fillna(1.0)
        for w in range(5):
            m = ser.index.weekday == w
            s, cst = ser[m], cost[m]
            ins, oos = s.index <= A_IS_END, s.index > A_IS_END
            sign = 1.0 if s[ins].mean() > 0 else -1.0
            gi, go = sign * s[ins].values, sign * s[oos].values
            ni, no = gi - cst[ins].values, go - cst[oos].values
            per = X[m][oos].mul(sign * 1e4).sub(cst[oos].mean())            # per-index OOS net mean (replication)
            pos = int((per.mean() > 0).sum())
            rows.append(dict(part="A", leg=leg, weekday=GROUPS[w], dir=int(sign), n_is=int(ins.sum()), n_oos=int(oos.sum()),
                             IS=dict(net=float(ni.mean()), gross=float(gi.mean()), P=pboot(ni, rng)), OOS=dict(net=float(no.mean()), gross=float(go.mean()), P=pboot(no, rng)), indices_pos=pos, indices_n=int(per.shape[1])))
    return rows


# ------------------------------------------------------------------ Part B
def slot_arrays(sym):
    df = M.load(sym)
    mins = (df.index.hour * 60 + df.index.minute).values
    day = df.index.normalize()
    keep = np.isin(mins, BMIN) & (day >= B_FROM) & (day <= B_TO) & (day.weekday <= 4)
    d = df[keep]
    dd, mm = d.index.normalize(), (d.index.hour * 60 + d.index.minute).values
    days = np.array(sorted(set(dd)))
    pos = {x: i for i, x in enumerate(days)}
    bid = np.full((len(days), NSLOT + 1), np.nan)
    ask = np.full((len(days), NSLOT + 1), np.nan)
    col = {m: i for i, m in enumerate(BMIN)}
    di = np.array([pos[x] for x in dd])
    ci = np.array([col[m] for m in mm])
    bid[di, ci] = d["open"].values
    ask[di, ci] = d["ask_open"].values
    return days, bid, ask


def returns(bid, ask):
    mid = (bid + ask) / 2.0
    gross = (mid[:, 1:] - mid[:, :-1]) / mid[:, :-1] * 1e4                 # long, mid to mid
    long_net = (bid[:, 1:] - ask[:, :-1]) / mid[:, :-1] * 1e4
    short_net = (bid[:, :-1] - ask[:, 1:]) / mid[:, :-1] * 1e4
    return gross, long_net, short_net


def part_b(rng):
    allday = pd.date_range(B_FROM, B_TO, freq="D")
    G, L, S = [], [], []
    for sym in CFDS:
        days, bid, ask = slot_arrays(sym)
        g, l, s = returns(bid, ask)
        full = lambda a: pd.DataFrame(a, index=days).reindex(allday).values
        G.append(full(g)); L.append(full(l)); S.append(full(s))
    G, L, S = np.stack(G), np.stack(L), np.stack(S)                       # (inst, day, slot)
    wd = allday.weekday.values
    cnt = np.isfinite(G).sum(axis=0)
    ok = cnt >= 3
    Gp = np.where(ok, np.nanmean(np.where(np.isfinite(G), G, np.nan), axis=0), np.nan)
    Lp = np.where(ok, np.nanmean(np.where(np.isfinite(L), L, np.nan), axis=0), np.nan)
    Sp = np.where(ok, np.nanmean(np.where(np.isfinite(S), S, np.nan), axis=0), np.nan)
    ins = allday <= B_IS_END
    rows, rep = [], []
    for gi, gname in enumerate(GROUPS):
        gm = (wd <= 4) if gname == "all" else (wd == gi)
        for s in range(NSLOT):
            mi, mo = gm & ins, gm & ~ins
            gx = Gp[:, s]
            sign = 1.0 if np.nanmean(gx[mi]) > 0 else -1.0
            net = Lp[:, s] if sign > 0 else Sp[:, s]
            ni, no = net[mi], net[mo]
            gi_, go_ = sign * gx[mi], sign * gx[mo]
            # replication: per instrument OOS net mean in the same direction
            pos = 0
            for k in range(len(CFDS)):
                x = (L if sign > 0 else S)[k, :, s][mo]
                pos += int(np.nanmean(x) > 0) if np.isfinite(x).sum() >= 50 else 0
            ni_f, no_f = ni[np.isfinite(ni)], no[np.isfinite(no)]
            rows.append(dict(part="B", weekday=gname, slot=s, start=f"{(BMIN[s] // 60):02d}:{(BMIN[s] % 60):02d}", dir=int(sign), n_is=int(len(ni_f)), n_oos=int(len(no_f)),
                             IS=dict(net=float(ni_f.mean()), gross=float(np.nanmean(gi_)), P=pboot(ni_f, rng)), OOS=dict(net=float(no_f.mean()), gross=float(np.nanmean(go_)), P=pboot(no_f, rng)), indices_pos=pos, indices_n=len(CFDS)))
    return rows


def judge(rows):
    for r in rows:
        p = max(1.0 - r["OOS"]["P"], 1.0 / BOOT)
        r["p_oos"] = p
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p_oos"])
    thr = 0.0
    for rank, i in enumerate(order, 1):
        if rows[i]["p_oos"] <= 0.10 * rank / len(rows):
            thr = max(thr, rows[i]["p_oos"])
    for r in rows:
        r["bh"] = bool(r["p_oos"] <= thr and thr > 0)
        r["candidate"] = bool(r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["net"] > 0 and r["n_oos"] >= 100 and r["bh"])
        need = 5 if r["part"] == "A" else 4
        r["usable_filter"] = bool(r["candidate"] and r["OOS"]["net"] >= 2.0 and r["indices_pos"] >= need)
    return rows


def dry_run():
    legs, N = cash_legs()
    for leg, (ser, X) in legs.items():
        print(f"Part A {leg}: {len(ser)} dates, {int(X.notna().sum().sum()):,} index-days; IS dates {int((ser.index <= A_IS_END).sum())}, OOS {int((ser.index > A_IS_END).sum())}; share of exact-zero legs {float((X == 0).mean().mean()):.3f}")
    print("median nights since the previous close by weekday: " + ", ".join(f"{GROUPS[w]} {float(N[N.index.weekday == w].median()):.0f}" for w in range(5)))
    for sym in CFDS:
        days, bid, ask = slot_arrays(sym)
        have = np.isfinite(bid) & np.isfinite(ask)
        sp = np.nanmedian((ask - bid) / ((ask + bid) / 2) * 1e4, axis=0)
        print(f"{sym}: {len(days)} days, boundary coverage {have.mean():.2f}; median quoted spread bp at 03:00 / 09:30 / 15:30 NY: {sp[0]:.2f} / {sp[13]:.2f} / {sp[25]:.2f}")
    # consistency: a slow recomputation of one cell
    days, bid, ask = slot_arrays("US100.cash")
    g, l, s = returns(bid, ask)
    d = len(days) // 2
    while not (np.isfinite(bid[d, 13]) and np.isfinite(bid[d, 14])):
        d += 1
    df = M.load("US100.cash")
    t0 = days[d] + pd.Timedelta(hours=9, minutes=30); t1 = t0 + pd.Timedelta(minutes=30)
    b1, a0, mid0 = df.loc[t1, "open"], df.loc[t0, "ask_open"], (df.loc[t0, "open"] + df.loc[t0, "ask_open"]) / 2
    assert abs(l[d, 13] - (b1 - a0) / mid0 * 1e4) < 1e-9
    print(f"slow recomputation of US100 {days[d].date()} slot 09:30 long net bp equals the array value ({l[d, 13]:.3f})")
    rng = np.random.default_rng(1)
    print(f"bootstrap smoke: P(mean>0) of N(0.5,1) x 100 = {pboot(rng.normal(0.5, 1, 100), rng):.2f} (expected near 1)")
    print(f"K_TOTAL {K_TOTAL}; OOS P bar {1 - 0.01 / K_TOTAL:.6f}; hypotheses 15 + 150 = 165")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    A = part_a(rng)
    print(f"Part A done ({time.time() - t0:.0f}s)", flush=True)
    B = part_b(rng)
    print(f"Part B done ({time.time() - t0:.0f}s)", flush=True)
    rows = judge(A + B)
    cand = [r for r in rows if r["candidate"]]
    isg = [r for r in rows if r["IS"]["P"] >= 0.95]
    isg_pos = [r for r in isg if r["OOS"]["gross"] > 0]
    isg_net = [r for r in isg if r["OOS"]["net"] > 0]
    print(f"{len(rows)} hypotheses; IS P >= 0.95: {len(isg)} (expected under no effect ~{0.05 * len(rows):.0f}); of those positive OOS gross {len(isg_pos)}, positive OOS net {len(isg_net)}; CANDIDATES {len(cand)}; usable filters {sum(r['usable_filter'] for r in rows)}")
    top = sorted(rows, key=lambda r: -r["OOS"]["net"])[:10]
    for r in top:
        tag = f"A {r['leg']} {r['weekday']}" if r["part"] == "A" else f"B {r['weekday']} {r['start']}"
        print(f"   top OOS net: {tag:>22} dir {r['dir']:+d} | IS net {r['IS']['net']:+.2f} gross {r['IS']['gross']:+.2f} P {r['IS']['P']:.2f} | OOS net {r['OOS']['net']:+.2f} gross {r['OOS']['gross']:+.2f} P {r['OOS']['P']:.3f} (n {r['n_oos']}) | indices pos {r['indices_pos']}/{r['indices_n']}")
    out = {"K_TOTAL": K_TOTAL, "rows": rows, "n_hypotheses": len(rows), "is_significant": len(isg), "is_sig_oos_gross_pos": len(isg_pos), "is_sig_oos_net_pos": len(isg_net), "candidates": len(cand)}
    json.dump(out, open(os.path.join(HERE, "round298_results.json"), "w"), indent=1, default=float)
    print(f"Saved round298_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
