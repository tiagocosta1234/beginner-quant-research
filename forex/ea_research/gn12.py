"""GN12: the breakout of the first 15 minutes after a scheduled US release, held to the close, on event days (K1 / K2: CPI, NFP,
FOMC; K3 / K4: Treasury auctions), Nasdaq and gold on MT5. Pre-registration: forex/ea_research/PREREG_GN12.md.
   python -m forex.ea_research.gn12 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn2 import info

NYZ = "America/New_York"
CAL = "forex/ea_research/EVENT_CALENDAR_2022_2026.csv"
AUC = "futures/data/events/treasury_coupon_auctions.csv"
# (box start, order window start, order window end) per event kind; exits per market below
TIMES = {"data": ((8, 30), (8, 45), (11, 0)), "fomc": ((14, 0), (14, 45), (15, 30)), "auction": ((13, 0), (13, 15), (14, 30))}
EXIT = {("NSDQ", "data"): (15, 55), ("XAUUSD", "data"): (13, 25)}          # every other (market, kind): 15:55
TRIALS = {"K1": ("NSDQ", "tier1"), "K2": ("XAUUSD", "tier1"), "K3": ("NSDQ", "auction"), "K4": ("XAUUSD", "auction")}
TBAR, NCT = 2.24, 5
SPAN = ("2022-01-03", "2026-10-16")
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
BIG = 1 << 40


def calendars():
    c = pd.read_csv(CAL, parse_dates=["date"])
    tier1 = {}
    for k, d in zip(c.kind, c.date):
        tier1.setdefault(d, set()).add("fomc" if k == "FOMC" else "data")
    a = pd.read_csv(AUC, parse_dates=["date"])
    auction = set(a.date[(a.date >= SPAN[0]) & (a.date <= SPAN[1])])
    return tier1, auction


def first(mask):
    k = np.flatnonzero(mask)
    return int(k[0]) if len(k) else BIG


def box_day(D, d, kind, xh, rng, ctrl=True):
    """the follow trade of the post-release box on day d (or None) and its random controls"""
    b0, b1, w1 = TIMES[kind]
    t = D["t"]; n = len(t)
    s0, s1, e1, xe = (ts(d.year, d.month, d.day, *hm, NYZ) for hm in (b0, b1, w1, xh))
    i0, i1, iw, ix = (int(x) for x in np.searchsorted(t, [s0, s1, e1, xe]))
    if i1 - i0 < 12 or iw - i1 < 0.8 * (e1 - s1) / 60 or ix >= n or ix <= iw or t[ix] - xe > 600:
        return None, []
    hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
    if W <= 0:
        return None, []
    sp = np.median(D["ao"][i0:i1] - D["bo"][i0:i1]); nr = ~D["roll"][i1:iw]; tr = None
    kl, ks = first((D["ah"][i1:iw] >= hi) & nr), first((D["bl"][i1:iw] <= lo) & nr)
    if kl != ks and min(kl, ks) < BIG:
        side = 1 if kl < ks else -1; k = i1 + min(kl, ks)
        e = max(hi, D["ao"][k]) if side == 1 else min(lo, D["bo"][k]); st = lo if side == 1 else hi
        if side * (e - st) > 0:
            ex, _ = walk(D, side, k, ix, st, None)
            tr = dict(day=d, kind=kind, side=side, t_entry=int(t[k]), entry=e, stop=st, W=W, wsp=W / sp if sp > 0 else np.nan,
                      R=side * (ex - e) / abs(e - st))
    cs = []
    if ctrl:
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCT, len(cand)), replace=False):
            k = i1 + int(j); s2 = int(rng.choice([1, -1])); e2 = D["ao"][k] if s2 == 1 else D["bo"][k]
            ex2, _ = walk(D, s2, k, ix, e2 - s2 * W, None); cs.append(dict(day=d, kind=kind, R=s2 * (ex2 - e2) / W))
    return tr, cs


def trial_rows(D, mkt, family, tier1, auction, end_day=SPAN[1]):
    """(event trades, controls, same rule on the other days)"""
    rng = np.random.default_rng(sum(map(ord, mkt + family)) * 7919)
    T, C, O = [], [], []
    for d in pd.bdate_range(SPAN[0], end_day):
        kinds = sorted(tier1.get(d, ())) if family == "tier1" else (["auction"] if d in auction else [])
        if kinds:
            for kd in kinds:
                tr, cs = box_day(D, d, kd, EXIT.get((mkt, kd), (15, 55)), rng); C += cs
                if tr:
                    T.append(tr)
        else:
            for kd in (("data", "fomc") if family == "tier1" else ("auction",)):
                tr, _ = box_day(D, d, kd, EXIT.get((mkt, kd), (15, 55)), rng, ctrl=False)
                if tr:
                    O.append(tr)
    return pd.DataFrame(T), pd.DataFrame(C), pd.DataFrame(O)


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def other_mean(T, O):
    """the other-days baseline weighted by the event-kind mix of T"""
    w = T.kind.value_counts(normalize=True)
    return float(sum(w[k] * O[O.kind == k].R.mean() for k in w.index if (O.kind == k).any()))


def cut_data(D, cut):
    k = int(np.searchsorted(D["t"], cut))
    return {key: (val[:k] if isinstance(val, np.ndarray) and len(val) == len(D["t"]) else val) for key, val in D.items()}


def dry_run():
    tier1, auction = calendars()
    ev = pd.Series([k for d, ks in tier1.items() if pd.Timestamp(SPAN[0]) <= d <= pd.Timestamp(SPAN[1]) for k in ks],
                   index=[d for d, ks in tier1.items() if pd.Timestamp(SPAN[0]) <= d <= pd.Timestamp(SPAN[1]) for k in ks])
    print("tier-1 events by year: " + " ".join(f"{y}: data {int((g == 'data').sum())} fomc {int((g == 'fomc').sum())}" for y, g in ev.groupby(ev.index.year))
          + " | auction days by year: " + " ".join(f"{y}: {n}" for y, n in pd.Series(sorted(auction)).dt.year.value_counts().sort_index().items()))
    data = {m: load(m) for m in ("NSDQ", "XAUUSD")}
    for tr, (mkt, fam) in TRIALS.items():
        T, C, O = trial_rows(data[mkt], mkt, fam, tier1, auction)
        print(f"{tr} {mkt} {fam}: trades DEV {len(per(T, DEV))} VAL {len(per(T, VAL))} HOLD {len(per(T, HOLD))} | other-day trades DEV {len(per(O, DEV))}"
              f" | median box {T.wsp.median():.0f} spreads | by kind " + " ".join(f"{k} {n}" for k, n in T.kind.value_counts().items()))
        r = T.iloc[len(T) // 3]
        loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
        print(f"   hand check {r.day.date()} {r.kind} side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, stop {r.stop:.2f}, box {r.W:.2f}")
        cut = ts(2023, 6, 30, 12, 0, NYZ)
        T2, C2, O2 = trial_rows(cut_data(data[mkt], cut), mkt, fam, tier1, auction, end_day="2023-06-29")
        ok = all(len(a[a.day <= "2023-06-29"]) == len(b) and np.allclose(a[a.day <= "2023-06-29"].R.to_numpy(), b.R.to_numpy())
                 for a, b in ((T, T2), (C, C2), (O, O2)))
        print(f"   truncation test (data cut 2023-06-30 12:00 NY): {'PASS' if ok else 'FAIL'}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    tier1, auction = calendars(); data = {m: load(m) for m in ("NSDQ", "XAUUSD")}
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)

    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))

    res = {}
    for tr, (mkt, fam) in TRIALS.items():
        T, C, O = trial_rows(data[mkt], mkt, fam, tier1, auction); res[tr] = T
        d, v, cD, cV = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL)
        md, td = ct(d); mv, tv = ct(v); iD, tiD = info(d, cD); iV, _ = info(v, cV); oD = other_mean(d, per(O, DEV))
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"])
        okd = len(d) >= 80 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and md > oD and (yc["mean"] > 0).sum() >= 2
        okv = mv > 0 and tv >= 1.65 and iV > 0
        line = (f"{tr} {mkt} {fam}: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | other days {oD:+.3f} | yrs " + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows())
                + " | by kind " + " ".join(f"{k} {g.R.mean():+.3f}({len(g)})" for k, g in d.groupby("kind"))
                + f" -> DEV {'PASS' if okd else 'FAIL'}\n     VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} other days {other_mean(v, per(O, VAL)):+.3f} -> {'PASS' if okv else 'FAIL'}")
        if okd and okv:
            h = per(T, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach% by date):")
    for tr, T in res.items():
        x = T[T.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
