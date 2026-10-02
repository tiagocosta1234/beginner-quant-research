"""
Round 301 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no edge claim, no ledger row): which drawn LEVELS on the 1-minute US100 chart have a higher chance of a REBOUND than a random price line? (the trader: "drop to the 1 minute chart, minimize as much as you can and determine levels
(lines with 2px size) that have a high chance of getting a rebound".) The honest prior: levels that look obvious do not rebound more often than random lines (Round 148: breakouts through intraday levels beat the random walk by 2-3 points, Round 290: sweeps/reclaims carry no direction,
Round 298/299: no slot or volatility filter). This round measures it so the lines drawn on the chart come with a number.
DATA: MT5 US100.cash M1 bid OHLC, NY wall clock (round271 loader), session days 2021-10-04 .. 2026-09-30; the active window of day D is 09:30 .. 15:55 NY; IS = to 2024-06-30, OOS = 2024-07-01 onward.
LEVEL TYPES (all known at the 09:30 NY open of D, bid prices): PDH / PDL = previous RTH (09:30-16:00) high / low; PWH / PWL = highest high / lowest low of the previous 5 RTH sessions; ONH / ONL = high / low of 18:00 NY the previous evening .. 09:29 NY; R100 = multiples of 100 index points; R50 = odd multiples of 50;
SW1 = 15-minute fractal swing high/low (3 bars each side, from the 15-minute bars of the previous 2 RTH sessions plus the overnight session) that price has not crossed since it formed; SW2 = a swing level with another swing of the same kind within 8 points (clustered, level = their mean; each cluster once);
RND = the placebo, 12 random price lines per day. Only levels within +-250 points of the 09:30 open are used (reachable).
EVENT: side from the 09:30 open price O: a level below O is SUPPORT, above O RESISTANCE. The FIRST touch of the day = the first 1-minute bar from 09:30 whose low (support) / high (resistance) comes within 1.0 point of the level. After the touch bar (the touch bar itself can break the level but cannot count as a rebound, which is pessimistic for rebounds and
identical for every type, the placebo included): REBOUND = price reaches level +15 (support) / -15 (resistance) before it trades through the level by 10 (break); neither within 60 one-minute bars after the touch = TIMEOUT (reported, excluded from the rate). P(rebound) = rebounds / (rebounds + breaks). A random line has P(rebound) about 10 / (10 + 15) = 40% by the gambler's-ruin
rule, so the PLACEBO (RND, same logic) is the comparison, not 50%. No costs (a descriptive reference for drawing, not a trade).
STATISTICS: per type, IS and OOS: events, P(rebound), the placebo's P, the difference, and a day-clustered bootstrap 95% interval of the difference (4,000 draws, seed 3011). A type shows REAL ADVANTAGE only if its OOS difference is >= +3.0 points with the lower 95% bound > 0 AND its IS difference is positive; there are 9 types, so a type clearing this is a lead, not a finding.
SECOND LOOK (descriptive): the same by touch count: a level the day has already touched once before (re-touch) vs a first touch is not measured (first touch only, by design).
PRIOR (stated now): every type within +-3 points of the placebo; PDH/PDL/ONH/ONL the closest to a small advantage or disadvantage; round numbers neutral; clustered swings (SW2) no better than single swings. The answer for the chart: 'no drawn level has a measured high chance of rebound'.
POWER_NOTES: ~1,290 days x a handful of events per type; a standard error of the difference of ~2-3 points per type OOS; the 15 / 10 / 60-minute geometry is one choice (asymmetric on purpose, so a rebound is a clear move); first touch only; one instrument; the OANDA chart's prices differ from MT5 broker's by a few points.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round271_one_to_one_generator as M

AWAY, THROUGH, NEAR, TOL, HORIZON = 15.0, 10.0, 250.0, 1.0, 60
IS_END = pd.Timestamp("2024-06-30")
FIRST, LAST = pd.Timestamp("2021-10-04"), pd.Timestamp("2026-09-30")
TYPES = ["PDH", "PDL", "PWH", "PWL", "ONH", "ONL", "R100", "R50", "SW1", "SW2", "RND"]
BOOT, SEED, NRAND = 4000, 3011, 12
OPEN_M, CLOSE_M = 9 * 60 + 30, 16 * 60


def load_days():
    df = M.load("US100.cash")
    t = df.index
    mins = (t.hour * 60 + t.minute).values
    day = t.normalize()
    out = {}
    for d in pd.DatetimeIndex(day.unique()):
        if d < FIRST - pd.Timedelta(days=12) or d > LAST:
            continue
        m = day == d
        g = df[m]
        mm = mins[m]
        out[d] = dict(rth=g[(mm >= OPEN_M) & (mm < CLOSE_M)], pre=g[mm < OPEN_M], evening=g[mm >= 18 * 60])
    return out


def keys_of(days):
    return sorted(d for d, v in days.items() if d.weekday() <= 4 and len(v["rth"]) >= 300)


def swings15(bars):
    """Fractal swing highs/lows (3 bars each side) of the 15-minute bars of a 1-minute frame; returns [(time of confirmation, kind, price)]."""
    g = bars.resample("15min", label="left", closed="left")
    b = pd.DataFrame({"h": g["high"].max(), "l": g["low"].min()}).dropna()
    h, l = b["h"].values, b["l"].values
    res = []
    for i in range(3, len(b) - 3):
        if h[i] == h[i - 3:i + 4].max() and h[i] > h[i - 1] and h[i] > h[i + 1]:
            res.append((b.index[i + 3], "H", float(h[i])))
        if l[i] == l[i - 3:i + 4].min() and l[i] < l[i - 1] and l[i] < l[i + 1]:
            res.append((b.index[i + 3], "L", float(l[i])))
    return res


def levels_for(D, days, keys, k, rng):
    """All levels of day D (index k in keys) known at 09:30. Returns {type: [prices]} (unfiltered by distance)."""
    prev = days[keys[k - 1]]
    last5 = [days[keys[j]]["rth"] for j in range(max(0, k - 5), k)]
    lv = {"PDH": [float(prev["rth"]["high"].max())], "PDL": [float(prev["rth"]["low"].min())],
          "PWH": [max(float(r["high"].max()) for r in last5)], "PWL": [min(float(r["low"].min()) for r in last5)]}
    cur = days[D]
    eve = days[D - pd.Timedelta(days=1)]["evening"] if (D - pd.Timedelta(days=1)) in days else prev["evening"]
    on = pd.concat([eve, cur["pre"]])
    lv["ONH"] = [float(on["high"].max())] if len(on) else []
    lv["ONL"] = [float(on["low"].min())] if len(on) else []
    o = float(cur["rth"]["open"].iloc[0])
    lo100, hi100 = int((o - NEAR) // 100) * 100, int((o + NEAR) // 100 + 1) * 100
    lv["R100"] = [float(x) for x in range(lo100, hi100 + 1, 100)]
    lv["R50"] = [float(x) for x in range(lo100 + 50, hi100, 100)]
    # swings from the previous 2 RTH sessions plus the overnight session (formed and confirmed before 09:30 of D)
    frames = [days[keys[j]]["rth"] for j in range(max(0, k - 2), k)] + [on]
    hist = pd.concat([days[keys[j]]["rth"] for j in range(max(0, k - 2), k)] + [on]).sort_index()
    sw = swings15(hist)
    px = hist
    sw1 = []
    for tconf, kind, p in sw:
        after = px[px.index >= tconf]
        if len(after) == 0 or (kind == "H" and after["high"].max() > p + 1e-9) or (kind == "L" and after["low"].min() < p - 1e-9):
            continue
        sw1.append((kind, p))
    lv["SW1"] = [p for _, p in sw1]
    sw2, used = [], set()
    for i, (ki, pi) in enumerate(sw1):
        if i in used:
            continue
        grp = [i] + [j for j, (kj, pj) in enumerate(sw1) if j != i and j not in used and kj == ki and abs(pj - pi) <= 8.0]
        if len(grp) >= 2:
            used.update(grp)
            sw2.append(float(np.mean([sw1[j][1] for j in grp])))
    lv["SW2"] = sw2
    lv["RND"] = [float(o + rng.uniform(-NEAR, NEAR)) for _ in range(NRAND)]
    return lv, o


def event(level, o, lo, hi):
    """First-touch outcome for one level on one day: 1 rebound, 0 break, -1 timeout, None no touch. lo / hi = 1-minute bid lows / highs from 09:30."""
    n = len(lo)
    if level < o - TOL:                                    # support
        idx = np.flatnonzero(lo <= level + TOL)
        if idx.size == 0:
            return None
        i = int(idx[0])
        if lo[i] <= level - THROUGH:
            return 0
        j1 = min(n, i + 1 + HORIZON)
        for j in range(i + 1, j1):
            if lo[j] <= level - THROUGH:
                return 0
            if hi[j] >= level + AWAY:
                return 1
        return -1
    if level > o + TOL:                                    # resistance
        idx = np.flatnonzero(hi >= level - TOL)
        if idx.size == 0:
            return None
        i = int(idx[0])
        if hi[i] >= level + THROUGH:
            return 0
        j1 = min(n, i + 1 + HORIZON)
        for j in range(i + 1, j1):
            if hi[j] >= level + THROUGH:
                return 0
            if lo[j] <= level - AWAY:
                return 1
        return -1
    return None


def build_events(days):
    keys = keys_of(days)
    rng = np.random.default_rng(SEED)
    ev = []                                                # (day index, type, outcome)
    dlist = []
    for k, D in enumerate(keys):
        if D < FIRST or k < 6:
            continue
        lv, o = levels_for(D, days, keys, k, rng)
        r = days[D]["rth"]
        mm = (r.index.hour * 60 + r.index.minute).values
        r = r[mm < CLOSE_M - 5]
        lo, hi = r["low"].values.astype(float), r["high"].values.astype(float)
        di = len(dlist)
        dlist.append(D)
        for t, prices in lv.items():
            for p in prices:
                if abs(p - o) > NEAR:
                    continue
                out = event(p, o, lo, hi)
                if out is not None:
                    ev.append((di, t, out))
    return dlist, ev


def pboot(dlist, ev, t, mask_days, rng_w):
    """P(rebound) of type t and of the placebo over the days in mask_days, with a day-clustered bootstrap of the difference."""
    nd = len(dlist)
    def tab(tt):
        r, n = np.zeros(nd), np.zeros(nd)
        for di, ty, out in ev:
            if ty == tt and out >= 0 and mask_days[di]:
                n[di] += 1
                r[di] += out
        return r, n
    rt, nt = tab(t)
    rp, npl = tab("RND")
    if nt.sum() == 0:
        return None
    pt, pp = rt.sum() / nt.sum(), rp.sum() / npl.sum()
    w = rng_w
    d = (w @ rt) / np.maximum(w @ nt, 1e-9) - (w @ rp) / np.maximum(w @ npl, 1e-9)
    return dict(events=int(nt.sum()), p=float(pt), placebo=float(pp), diff=float(pt - pp), lo=float(np.quantile(d, 0.025)), hi=float(np.quantile(d, 0.975)))


def dry_run():
    # outcome logic on synthetic bars
    lo = np.array([100., 99.5, 99.0, 98.0, 99.0, 112.0, 90.0]); hi = lo + 3.0
    assert event(100.0, 130.0, lo, hi) is not None
    sup_lo = np.array([105, 100.5, 101, 104, 118, 120, 90.0]); sup_hi = sup_lo + 2
    assert event(100.0, 110.0, sup_lo, sup_hi) == 1, "support rebound to +15 before -10"
    brk_lo = np.array([105, 100.5, 95, 88, 118, 120, 90.0]); brk_hi = brk_lo + 2
    assert event(100.0, 110.0, brk_lo, brk_hi) == 0, "support break through by 10 first"
    res_hi = np.array([95, 99.5, 98, 84, 80, 80.0]); res_lo = res_hi - 2
    assert event(100.0, 90.0, res_lo, res_hi) == 1, "resistance rebound to -15"
    flat = np.full(100, 107.0)
    assert event(100.0, 110.0, flat - 1, flat + 1) is None, "no touch"
    t_lo = np.array([105, 100.5] + [101.0] * 70); assert event(100.0, 110.0, t_lo, t_lo + 2) == -1, "timeout"
    tb = np.array([105, 89.0, 120.0]); assert event(100.0, 110.0, tb, tb + 2) == 0, "the touch bar itself can break"
    print("event logic tests passed (support rebound, support break, resistance rebound, no touch, timeout, touch-bar break)")
    days = load_days()
    keys = keys_of(days)
    print(f"{len(keys)} loaded session days (incl. warm-up), first {keys[0].date()} last {keys[-1].date()}")
    k = len(keys) // 2
    lv, o = levels_for(keys[k], days, keys, k, np.random.default_rng(1))
    print(f"day {keys[k].date()}: open {o:.1f}; levels per type: " + ", ".join(f"{t} {len(v)}" for t, v in lv.items()))
    # causality: the levels of day D must not change if every bar from 09:30 of D onward is removed
    D = keys[k]
    cut = dict(days)
    cut[D] = dict(rth=days[D]["rth"].iloc[:1], pre=days[D]["pre"], evening=days[D]["evening"])
    lv2, o2 = levels_for(D, cut, keys, k, np.random.default_rng(1))
    for t in TYPES:
        a, b = np.array(lv[t]), np.array(lv2[t])
        assert len(a) == len(b) and np.allclose(a, b), f"level type {t} depends on data after 09:30"
    print("causality: every level type of the day is unchanged when all bars after the 09:30 open are removed")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    days = load_days()
    dlist, ev = build_events(days)
    print(f"{len(dlist)} event days, {len(ev)} events ({time.time() - t0:.0f}s)", flush=True)
    d_idx = pd.DatetimeIndex(dlist)
    is_m, oos_m = d_idx <= IS_END, d_idx > IS_END
    rng = np.random.default_rng(SEED)
    out = {"n_days": len(dlist), "types": {}}
    wB = {}
    for name, m in (("IS", is_m), ("OOS", oos_m)):
        n = int(m.sum())
        idx = rng.integers(0, n, (BOOT, n))
        W = np.zeros((BOOT, len(dlist)))
        pos = np.flatnonzero(m)
        for b in range(BOOT):
            np.add.at(W[b], pos[idx[b]], 1.0)
        wB[name] = W
    for t in TYPES:
        row = {}
        for name, m in (("IS", is_m), ("OOS", oos_m)):
            row[name] = pboot(dlist, ev, t, m, wB[name])
        tm = [(di, ty, o) for di, ty, o in ev if ty == t]
        row["timeout_share"] = float(np.mean([o < 0 for _, _, o in tm])) if tm else None
        out["types"][t] = row
        if row["OOS"]:
            print(f"{t:>5}: IS n {row['IS']['events']:>5} P {row['IS']['p']:.1%} (placebo {row['IS']['placebo']:.1%}, diff {100 * row['IS']['diff']:+.1f}) | OOS n {row['OOS']['events']:>5} P {row['OOS']['p']:.1%} (placebo {row['OOS']['placebo']:.1%}) diff {100 * row['OOS']['diff']:+.1f} [{100 * row['OOS']['lo']:+.1f}, {100 * row['OOS']['hi']:+.1f}] | timeouts {row['timeout_share']:.0%}", flush=True)
    real = {t: r for t, r in out["types"].items() if t != "RND" and r["OOS"] and r["IS"]}
    adv = [t for t, r in real.items() if r["OOS"]["diff"] >= 0.03 and r["OOS"]["lo"] > 0 and r["IS"]["diff"] > 0]
    out["real_advantage"] = adv
    print(f"TYPES WITH A REAL ADVANTAGE (OOS diff >= +3.0 pts, lower bound > 0, IS diff > 0): {adv if adv else 'none'}")
    json.dump(out, open(os.path.join(HERE, "round301_results.json"), "w"), indent=1, default=float)
    print(f"Saved round301_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
