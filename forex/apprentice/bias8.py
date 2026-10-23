"""PREREG_BIAS8: forced 08:00 local long/short bias on GC, outcome shown after each locked call; target grid before a 1R stop.
Usage (from forex/apprentice): python bias8.py draw | dryrun | new | show | call L|S CONF "reason" | reveal | status | score"""
import os, sys, json, hashlib, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(HERE, "state_b8"); os.makedirs(ST, exist_ok=True)
ORDER = os.path.join(ST, "order.csv"); CALLS = os.path.join(HERE, "BIAS8_CALLS.csv"); CUR = os.path.join(ST, "current.json")
TICK, COMM = 0.1, 0.15
TGTS = (0.5, 1.0, 1.5, 2.0, 3.0); CUTS = ("12:00", "17:00")
RESERVED = [("2026-01-01", "2026-12-31"), ("2025-04-01", "2025-05-31"), ("2023-11-28", "2023-12-27"), ("2025-02-28", "2025-03-29")]
SEEN_FILES = ["state_t/order.csv", "state_t2/order.csv", "state_t3/order.csv", "APPRENTICE_LOG_GC.csv", "APPRENTICE_SHADOW_GC.csv",
              "MANUAL_READ_LOG.csv", "MANUAL_CALLS.csv", "LIVE_LOG.csv"]
H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)


def seen():
    s = set()
    for f in SEEN_FILES:
        x = pd.read_csv(os.path.join(HERE, f)); c = [k for k in x.columns if "date" in k.lower() or k.lower() == "day"]
        s |= set(pd.to_datetime(x[c[0]], errors="coerce").dropna().dt.strftime("%Y-%m-%d"))
    return s


def prev_wd(day):
    p = day - pd.Timedelta(days=1)
    while p.weekday() >= 5: p -= pd.Timedelta(days=1)
    return p


def day_data(d, day):
    """Previous weekday 08:00 .. today 16:59, with a playability verdict."""
    p = prev_wd(day); x = d[(d["lis"] >= p + H(8)) & (d["lis"] < day + H(17))].reset_index(drop=True)
    t = x[x["lis"] >= day]; core = t[(t["lis"] >= day + H(7)) & (t["lis"] < day + H(17))]
    pv = x[(x["lis"] >= p + H(8)) & (x["lis"] < p + H(22))]
    ok = len(core) == 600 and len(pv) >= 600 and (t["mc"].diff().abs().max() <= 8.0)
    return x, ok


def cmd_draw():
    if os.path.exists(ORDER): sys.exit("order already drawn")
    d = D.raw(); sn = seen(); days = pd.Series(d["lis"].dt.normalize().unique())
    cand = [x for x in days if x.weekday() < 5 and pd.Timestamp("2019-07-01") <= x <= pd.Timestamp("2025-12-31")
            and x.strftime("%Y-%m-%d") not in sn and not any(pd.Timestamp(a) <= x <= pd.Timestamp(b) for a, b in RESERVED)]
    rng = np.random.default_rng(20261025); ok = []
    for k in rng.permutation(len(cand)):
        if day_data(d, cand[k])[1]: ok.append(cand[k])
        if len(ok) == 200: break
    pd.DataFrame({"id": ["B%03d" % (i + 1) for i in range(200)], "date": [x.strftime("%Y-%m-%d") for x in ok]}).to_csv(ORDER, index=False)
    print("pool %d candidate weekdays; drew 200 (dates hidden in %s)" % (len(cand), os.path.relpath(ORDER, HERE)))


def bars(x, a, b, rule):
    w = x[(x["lis"] >= a) & (x["lis"] < b)].set_index("lis")
    return w.resample(rule, label="left", closed="left").agg({"mo": "first", "mh": "max", "ml": "min", "mc": "last", "v": "sum"}).dropna()


def pre(x, day):
    """Everything known at 07:59, rebased to 07:59 close = 1000."""
    p = prev_wd(day); c759 = x[x["lis"] == day + H(7, 59)]["mc"].iloc[0]; base = c759 - 1000.0
    q15 = bars(x, p + H(8), day + H(8), "15min"); tr = np.maximum(q15["mh"] - q15["ml"], np.maximum((q15["mh"] - q15["mc"].shift()).abs(), (q15["ml"] - q15["mc"].shift()).abs()))
    S = float(tr.iloc[-14:].mean())
    pv = x[(x["lis"] >= p + H(8)) & (x["lis"] < p + H(22))]; asia = x[(x["lis"] >= day) & (x["lis"] < day + H(8))]
    lv = {"S": round(S, 2), "prev_hi": pv["mh"].max() - base, "prev_lo": pv["ml"].min() - base, "prev_open0800": pv["mo"].iloc[0] - base,
          "prev_close": pv["mc"].iloc[-1] - base, "asia_hi": asia["mh"].max() - base, "asia_lo": asia["ml"].min() - base,
          "asia_open": asia["mo"].iloc[0] - base, "o0730": x[x["lis"] == day + H(7, 30)]["mo"].iloc[0] - base}
    return base, {k: round(v, 2) for k, v in lv.items()}


def load_cur():
    return json.load(open(CUR)) if os.path.exists(CUR) else None


def cmd_new():
    c = load_cur()
    if c and not c.get("revealed"): sys.exit("day %s still open (call / reveal it first)" % c["id"])
    o = pd.read_csv(ORDER); done = set(pd.read_csv(CALLS)["id"]) if os.path.exists(CALLS) else set()
    for r in o.itertuples():
        if r.id in done: continue
        x, ok = day_data(D.raw(), pd.Timestamp(r.date)); assert ok
        x.to_parquet(os.path.join(ST, "day.parquet")); json.dump({"id": r.id, "date": r.date}, open(CUR, "w"))
        print("new day %s (date hidden). Next: python bias8.py show" % r.id); return
    sys.exit("all 200 days called: run score")


def fmt(q, base):
    return "o %7.2f h %7.2f l %7.2f c %7.2f  v %6d" % (q.mo - base, q.mh - base, q.ml - base, q.mc - base, q.v)


def cmd_show():
    c = load_cur(); day = pd.Timestamp(c["date"]); x = pd.read_parquet(os.path.join(ST, "day.parquet"))
    x = x[x["lis"] < day + H(8)]  # causal cut: nothing at or after 08:00
    base, lv = pre(x, day); p = prev_wd(day)
    print("%s  rebased: 07:59 close = 1000.00   S (1R) = ATR14 15m = %.2f" % (c["id"], lv["S"]))
    print("levels:", "  ".join("%s %.2f" % (k, v) for k, v in lv.items() if k != "S"))
    print("-- previous day 08:00-21:59, 30m")
    for t, q in bars(x, p + H(8), p + H(22), "30min").iterrows(): print(t.strftime("%H:%M"), fmt(q, base))
    print("-- today 00:00-07:44, 15m")
    for t, q in bars(x, day, day + H(7, 45), "15min").iterrows(): print(t.strftime("%H:%M"), fmt(q, base))
    print("-- today 07:45-07:59, 1m")
    for q in x[x["lis"] >= day + H(7, 45)].itertuples(): print(q.lis.strftime("%H:%M"), fmt(q, base))


def cmd_call(a):
    c = load_cur()
    if not c or c.get("revealed"): sys.exit("no open day: run new")
    if os.path.exists(CALLS) and c["id"] in set(pd.read_csv(CALLS)["id"]): sys.exit("already called")
    side, conf, reason = a[0].upper(), int(a[1]), a[2]
    assert side in ("L", "S") and conf in (1, 2, 3) and len(reason) > 5
    pc = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    h = hashlib.sha256(("%s|%s|%s|%d|%s|%s" % (c["id"], c["date"], side, conf, reason, pc)).encode()).hexdigest()
    row = pd.DataFrame([{"id": c["id"], "date": c["date"], "side": side, "conf": conf, "reason": reason, "pc_time": pc, "sha256": h}])
    row.to_csv(CALLS, mode="a", header=not os.path.exists(CALLS), index=False)
    print("locked %s %s conf %d  sha %s...  Next: python bias8.py reveal" % (c["id"], side, conf, h[:12]))


def sim(x, day, side, S, T, cut):
    """Entry 08:00 open 1 tick worse; stop S, target T*S; both in one bar = stop; exit at the cutoff bar's open."""
    L = side == "L"; w = x[(x["lis"] >= day + H(8))].reset_index(drop=True)
    e = w["mo"][0] + (TICK if L else -TICK); st = e - S if L else e + S; tg = e + T * S if L else e - T * S
    ch, cm = map(int, cut.split(":"))
    for q in w.itertuples():
        if q.lis >= day + H(ch, cm): return "time", ((q.mo - e) if L else (e - q.mo)) - COMM
        if (L and q.ml <= st) or (not L and q.mh >= st): return "stop", -S - TICK - COMM
        if (L and q.mh >= tg + TICK) or (not L and q.ml <= tg - TICK): return "target", T * S - COMM
    raise RuntimeError("no cutoff bar")


def outcome(x, day):
    o = x[x["lis"] == day + H(8)]["mo"].iloc[0]; c = x[x["lis"] == day + H(11, 59)]["mc"].iloc[0]
    return c - o


def cmd_reveal():
    c = load_cur(); k = pd.read_csv(CALLS); r = k[k["id"] == c["id"]]
    if r.empty: sys.exit("call first")
    side = r["side"].iloc[0]; day = pd.Timestamp(c["date"]); x = pd.read_parquet(os.path.join(ST, "day.parquet"))
    base, lv = pre(x[x["lis"] < day + H(8)], day); S = lv["S"]; mv = outcome(x, day)
    ok = (mv > 0 and side == "L") or (mv < 0 and side == "S")
    print("%s you said %s -> 08:00-11:59 move %+.2f (%+.2f R): %s" % (c["id"], side, mv, mv / S, "CORRECT" if ok else "wrong"))
    for cut in CUTS:
        print("  cut %s: " % cut + "  ".join("%.1fR %s %+.2fR" % (T, *(lambda z: (z[0][:4], z[1] / S))(sim(x, day, side, S, T, cut))) for T in TGTS))
    print("-- 08:00-11:59 15m (rebased)")
    for t, q in bars(x, day + H(8), day + H(12), "15min").iterrows(): print(t.strftime("%H:%M"), fmt(q, base))
    c["revealed"] = True; json.dump(c, open(CUR, "w"))


def cmd_status():
    n = len(pd.read_csv(CALLS)) if os.path.exists(CALLS) else 0; c = load_cur()
    print("called %d / 200; open day: %s" % (n, (c["id"] + (" revealed" if c.get("revealed") else " NOT revealed")) if c else "none"))


def table(d, rows, side_fn, ids):
    out = {}
    for T in TGTS:
        for cut in CUTS:
            rs = []; hit = 0
            for r in rows:
                if r["id"] not in ids: continue
                day = pd.Timestamp(r["date"]); x = d[r["id"]]; S = r["S"]; res, pts = sim(x, day, side_fn(r), S, T, cut)
                rs.append(pts / S); hit += res == "target"
            out[(T, cut)] = (hit / len(rs), float(np.mean(rs)), np.array(rs))
    return out


def boot_p(a, seed=7, n=20000):
    rng = np.random.default_rng(seed); m = np.array([rng.choice(a - a.mean(), len(a)).mean() for _ in range(n)])
    return float((m >= a.mean()).mean())


def cmd_score(dry=False):
    k = pd.read_csv(CALLS) if os.path.exists(CALLS) else None
    if not dry and (k is None or len(k) < 200): sys.exit("score refuses before B200")
    o = pd.read_csv(ORDER); raw = D.raw(); d = {}; rows = []
    for i, r in enumerate(o.itertuples()):
        day = pd.Timestamp(r.date); x, ok = day_data(raw, day); assert ok; d[r.id] = x
        base, lv = pre(x[x["lis"] < day + H(8)], day); mv = outcome(x, day)
        side = (k.set_index("id")["side"].get(r.id) if k is not None else None) if not dry else ("L" if np.random.default_rng(i).random() < .5 else "S")
        conf = k.set_index("id")["conf"].get(r.id) if (k is not None and not dry) else 1
        rows.append({"id": r.id, "date": r.date, "i": i, "S": lv["S"], "mv": mv, "side": side, "conf": conf,
                     "b_long": "L", "b_prev": "L" if lv["prev_close"] > lv["prev_open0800"] else "S",
                     "b_night": "L" if 1000.0 > lv["asia_open"] else "S", "b_30": "L" if 1000.0 > lv["o0730"] else "S"})
    R = pd.DataFrame(rows); cor = lambda col: ((R["mv"] > 0) & (R[col] == "L")) | ((R["mv"] < 0) & (R[col] == "S"))
    R["ok"] = cor("side"); from math import comb
    hits = int(R["ok"].sum()); p_bin = sum(comb(200, j) for j in range(hits, 201)) / 2 ** 200
    base = {b: int(cor(b).sum()) for b in ("b_long", "b_prev", "b_night", "b_30")}
    print("== bias: %d / %d hits (%.1f%%), one-sided binomial P %.4f" % (hits, len(R), 100 * hits / len(R), p_bin))
    print("   baselines on the same days:", base)
    print("   PASS" if hits >= 112 and all(hits > v for v in base.values()) else "   FAIL (bar: >= 112 and above every baseline)")
    ok = R["ok"].astype(float).values; idx = np.arange(len(ok)); r0 = np.corrcoef(idx, ok)[0, 1] if ok.std() > 0 else 0.0
    rng = np.random.default_rng(7); perm = np.array([np.corrcoef(idx, rng.permutation(ok))[0, 1] for _ in range(20000)]) if ok.std() > 0 else np.zeros(1)
    p_l = float((perm >= r0).mean()); blocks = [ok[j:j + 40].mean() for j in range(0, 200, 40)]
    print("== learning: corr %+.3f, permutation P %.4f, blocks %s" % (r0, p_l, " ".join("%.2f" % b for b in blocks)))
    print("   IMPROVES" if p_l <= 0.05 and blocks[4] > blocks[0] else "   no significant improvement")
    print("   hit rate by conf:", R.groupby("conf")["ok"].agg(["mean", "size"]).round(3).to_dict("index"))
    rr = R.to_dict("records"); dev = set(R["id"][:100]); val = set(R["id"][100:])
    flip = lambda s: "S" if s == "L" else "L"
    for name, fn in (("my side", lambda r: r["side"]), ("mirror", lambda r: flip(r["side"])), ("always long", lambda r: "L")):
        t = table(d, rr, fn, set(R["id"]))
        print("== targets, %s (all 200): T/cut hit%% meanR" % name)
        print("   " + "  ".join("%.1fR@%s %4.1f%% %+.3f" % (T, cut, 100 * v[0], v[1]) for (T, cut), v in t.items()))
    td = table(d, rr, lambda r: r["side"], dev); best = max(td, key=lambda kk: td[kk][1])
    tv = table(d, rr, lambda r: r["side"], val)[best]; pv = boot_p(tv[2])
    print("== DEV pick %.1fR @ %s (DEV mean %+.3f R); VAL mean %+.3f R, hit %.1f%%, bootstrap P %.4f -> %s" % (
        best[0], best[1], td[best][1], tv[1], 100 * tv[0], pv, "PASS" if tv[1] > 0 and pv <= 0.05 else "FAIL"))
    print("   the trader's live bar: +0.5 R a trade. VAL mean %+.3f R." % tv[1])


def cmd_dryrun():
    """Counts, causality check and fill check on the drawn days with RANDOM sides; prints no P&L."""
    o = pd.read_csv(ORDER); raw = D.raw(); yrs = pd.to_datetime(o["date"]).dt.year.value_counts().sort_index().to_dict()
    print("drawn %d days, by year %s; overlap with seen days: %d" % (len(o), yrs, len(set(o["date"]) & seen())))
    Ss = []
    for r in o.head(20).itertuples():
        day = pd.Timestamp(r.date); x, ok = day_data(raw, day); assert ok
        b1, l1 = pre(x[x["lis"] < day + H(8)], day); b2, l2 = pre(x, day)
        assert l1 == l2, "pre() uses data at/after 08:00"  # truncation causality test
        Ss.append(l1["S"])
        for T in TGTS:
            for cut in CUTS: assert sim(x, day, "L", l1["S"], T, cut)[0] in ("stop", "target", "time")
    print("causality test passed on 20 days (levels identical with and without post-08:00 bars); S median %.2f, range %.2f-%.2f" % (
        np.median(Ss), min(Ss), max(Ss)))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"draw": cmd_draw, "dryrun": cmd_dryrun, "new": cmd_new, "show": cmd_show, "reveal": cmd_reveal, "status": cmd_status,
     "score": cmd_score}.get(a[0], lambda: cmd_call(a[1:]) if a[0] == "call" else sys.exit(__doc__))() if a else sys.exit(__doc__)
