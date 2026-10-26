"""READ12 (PREREG_READ12.md): the 1:1 read on recent gold. Training on 40 days of Feb-May 2026 with a reveal after each call (lessons in READ12.md),
then a sealed test on every playable day of Jun-Sep 2026 in calendar order, drawn only after READ12.md is frozen; one look after the last call.
the trader's blind batch 2 days (ea_research/ema12/BLIND_BATCH2.csv) and January 2026 are excluded everywhere.
Bracket: X = the v9 the trader-style stop distance (manual_bracket level distance / 0.53, else 2.5 ATR / 0.53); stop and target both X from the signal close.
v9 constraints kept: with the 30-minute trend only, signal 08:02 or later, one trade a day or none.
Usage (from forex/apprentice): python read12.py train draw|new|scan|show|call L|S|none "reason"|reveal|status|score
                            python read12.py freeze | python read12.py test draw|new|scan|show|call ...|status|score"""
import os, sys, json, hashlib, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, manual_read as K

HERE = os.path.dirname(os.path.abspath(__file__))
PH = sys.argv[1] if len(sys.argv) > 1 else ""
ST = os.path.join(HERE, "state_r12" + ("x" if PH == "test" else "t")); os.makedirs(ST, exist_ok=True)
K.ST = ST
ORDER = os.path.join(ST, "order.csv"); CALLS = os.path.join(HERE, "READ12_%s_CALLS.csv" % ("TEST" if PH == "test" else "TRAIN"))
FROZEN = os.path.join(HERE, "READ12_FROZEN.sha256")
B2 = list(pd.read_csv(os.path.join(HERE, "..", "ea_research", "ema12", "BLIND_BATCH2.csv"))["date"])
EXCL = [("2026-01-01", "2026-01-31")] + [(x, x) for x in B2]
POOLS = {"train": {"T": [("2026-02-02", "2026-05-29")]}, "test": {"S": [("2026-06-01", "2026-09-25")]}}
N = {"train": 40, "test": 10 ** 6}; SEED = {"train": 20261027, "test": 20261028}   # test: every eligible day, calendar order


def playable(d, day):
    w = d[(d["lis"] >= day + pd.Timedelta(hours=7, minutes=45)) & (d["lis"] <= day + pd.Timedelta(hours=10))]
    return len(w) == 136


def cmd_draw():
    if os.path.exists(ORDER): sys.exit("order already drawn")
    if PH == "test" and not os.path.exists(FROZEN): sys.exit("READ12.md is not frozen: run 'python read12.py freeze' after training")
    d = D.raw(); days = pd.Series(d["lis"].dt.normalize().unique()); rng = np.random.default_rng(SEED[PH]); picks = {}
    for p, spans in POOLS[PH].items():
        inside = np.zeros(len(days), bool)
        for a, b in spans: inside |= (days >= a).values & (days <= b).values
        for a, b in EXCL: inside &= ~((days >= a).values & (days <= b).values)
        cand = list(days[inside & (days.dt.weekday < 5).values]); ok = []
        order = range(len(cand)) if PH == "test" else rng.permutation(len(cand))
        for k in order:
            if playable(d, cand[k]): ok.append(cand[k])
            if len(ok) == N[PH]: break
        picks[p] = ok
    rows = []
    for k in range(min(len(v) for v in picks.values())):
        for p in POOLS[PH]: rows.append({"id": "%s%03d" % ("X" if PH == "test" else "R", len(rows) + 1), "pool": p, "date": picks[p][k].strftime("%Y-%m-%d")})
    pd.DataFrame(rows).to_csv(ORDER, index=False); print("drew %d %s days (dates hidden in %s)" % (len(rows), PH, os.path.relpath(ORDER, HERE)))


def cmd_new():
    c = K.cur()
    if c and not c.get("done"): sys.exit("day %s still open" % c["id"])
    if c and PH == "train" and not c.get("revealed"): sys.exit("reveal %s first" % c["id"])
    o = pd.read_csv(ORDER); done = set(pd.read_csv(CALLS)["id"]) if os.path.exists(CALLS) else set()
    for r in o.itertuples():
        if r.id in done: continue
        y = K.frame_for(D.raw(), pd.Timestamp(r.date)); y.to_parquet(os.path.join(ST, "day.parquet"))
        K.save({"id": r.id, "date": r.date, "pool": r.pool}); print("new %s day %s (date hidden; 1:1 bracket; with the 30-min trend only, signal 08:02 or later). Next: scan" % (PH, r.id)); return
    sys.exit("all %s days called" % PH)


def cmd_show():
    c = K.cur(); y = pd.read_parquet(os.path.join(ST, "day.parquet")); until = c.get("shown_until", "07:58")
    print("%s shown until %s" % (c["id"], until))
    for q in y.itertuples():
        t = D.hm(q.lis)
        if "07:30" <= t <= until and q.lis.day == 3:
            up = q.mh - max(q.mo, q.mc); dn = min(q.mo, q.mc) - q.ml
            print("%s o %8.2f h %8.2f l %8.2f c %8.2f ema %8.2f atr %4.2f b/atr %+5.2f upw %4.2f dnw %4.2f c-ema %+5.2f volx %4.1f" % (
                t, q.mo, q.mh, q.ml, q.mc, q.ema, q.atr, (q.mc - q.mo) / q.atr, up, dn, q.mc - q.ema, q.v / q.vmed if q.vmed else float("nan")))


def bracket11(y, i, i0, side):
    b = K.manual_bracket(y, i, i0, side); c = y["mc"][i]; L = side == "L"
    X = (b["D"] if b else 2.5 * y["atr"][i]) / 0.53
    return round(c - X if L else c + X, 2), round(c + X if L else c - X, 2), (b["what"] if b else "no level: 2.5 ATR") + ", 1:1 at %.2f" % X


def cmd_call(a):
    c = K.cur()
    if not c or c.get("done") or c.get("call"): sys.exit("no open, uncalled day")
    if a[0].lower() == "none":
        call = {"side": "none", "signal": "", "stop": None, "target": None, "level": "", "reason": " ".join(a[1:])}
    else:
        side = a[0].upper(); sig = c.get("shown_until")
        if side not in ("L", "S") or not sig: sys.exit("call L|S on the candle just shown, or none")
        y = pd.read_parquet(os.path.join(ST, "day.parquet")); i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6)))
        i = int(np.where(y["lis"] == K.DAY0 + pd.Timedelta(hours=int(sig[:2]), minutes=int(sig[3:])))[0][0])
        t30 = y["mc"][i] - y["mc"][i - 30]
        if sig < "08:02": sys.exit("no signal candle before 08:02")
        if (t30 > 0) != (side == "L") or t30 == 0: sys.exit("with the 30-minute trend only (trend %+.2f)" % t30)
        stop, tgt, what = bracket11(y, i, i0, side)
        call = {"side": side, "signal": sig, "stop": stop, "target": tgt, "level": what, "reason": " ".join(a[1:])}
    call["pc_time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    call["sha256"] = hashlib.sha256(json.dumps({**call, "id": c["id"]}, sort_keys=True).encode()).hexdigest()
    row = {"id": c["id"], "pool": c["pool"], "date": c["date"], **call}
    pd.DataFrame([row]).to_csv(CALLS, mode="a", header=not os.path.exists(CALLS), index=False)
    c["call"] = call; c["done"] = True; K.save(c)
    print("locked %s %s: %s %s stop %s target %s (%s)" % (c["id"], call["sha256"][:16], call["side"], call["signal"], call["stop"], call["target"], call["level"]))


def pair(y, side, sig, sd, td):
    import manual_read_baselines as B
    try: return B.pair(y, side, sig, sd, td)
    except TypeError: return None


def cmd_reveal():
    if PH != "train": sys.exit("no reveal in the test phase")
    import manual_read_baselines as B
    c = K.cur()
    if not c or not c.get("done"): sys.exit("call the day first")
    y = pd.read_parquet(os.path.join(ST, "day.parquet")); k = c["call"]
    if k["side"] in ("L", "S"):
        cl = y["mc"][B.idx(y, k["signal"])]; X = abs(cl - k["stop"]); p = pair(y, k["side"], k["signal"], X, X)
        sim = D.simulate(y, k["side"], k["signal"], k["stop"], k["target"])
        print("%s %s %s: %s at %s, R %+.3f (mirror %+.3f)" % (c["id"], k["side"], k["signal"], sim["result"], sim["exit_time"], p[0], p[1]) if p else "%s: no fill (Amendment 1)" % c["id"])
    else:
        print("%s: no trade" % c["id"])
    i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6))); i8 = B.idx(y, "08:00"); s = "L" if y["mc"][i8] > y["mc"][i8 - 30] else "S"
    st, tg, _ = bracket11(y, i8, i0, s); X = abs(y["mc"][i8] - st); n = pair(y, s, "08:00", X, X)
    print("naive 08:00 %s 1:1 X %.2f: R %s" % (s, X, "%+.3f (mirror %+.3f)" % n if n else "no fill"))
    z = y[(y["lis"] >= K.DAY0 + pd.Timedelta(hours=7, minutes=30)) & (y["lis"] < K.DAY0 + pd.Timedelta(hours=14))].copy()
    z["q"] = z["lis"].dt.floor("15min")
    for t, g in z.groupby("q"):
        print("  %s o %8.2f h %8.2f l %8.2f c %8.2f" % (D.hm(t), g["mo"].iloc[0], g["mh"].max(), g["ml"].min(), g["mc"].iloc[-1]))
    c["revealed"] = True; K.save(c)


def cmd_freeze():
    p = os.path.join(HERE, "READ12.md")
    if not os.path.exists(p): sys.exit("write READ12.md first")
    if os.path.exists(FROZEN): sys.exit("already frozen")
    h = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest() for f in ("READ12.md", "read12.py", "manual_read.py", "PREREG_READ12.md", "READ11.md")}
    open(FROZEN, "w").write("frozen %s\n" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "".join("%s  %s\n" % (v, k) for k, v in h.items()))
    print(open(FROZEN).read())


def cmd_status():
    n = len(pd.read_csv(CALLS)) if os.path.exists(CALLS) else 0
    t = pd.read_csv(CALLS) if n else None; tot = len(pd.read_csv(ORDER)) if os.path.exists(ORDER) else 0
    print("%s: %d of %d days called%s" % (PH, n, tot, "" if not n else "; trades %d, none %d" % ((t.side != "none").sum(), (t.side == "none").sum())))


def cmd_score():
    import manual_read_baselines as B
    t = pd.read_csv(CALLS); tot = len(pd.read_csv(ORDER))
    if PH == "test" and len(t) < tot: sys.exit("only %d of %d test calls locked: no look before the last one (PREREG_READ12.md)" % (len(t), tot))
    d = D.raw(); me = ([], [], []); nv = ([], [], []); alw = []; sides = []; both = []; dropped = {"read": 0, "naive": 0}
    for r in t.itertuples():
        y = K.frame_for(d, pd.Timestamp(r.date)); i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6))); i8 = B.idx(y, "08:00")
        s = "L" if y["mc"][i8] > y["mc"][i8 - 30] else "S"; st, _, _ = bracket11(y, i8, i0, s); X8 = abs(y["mc"][i8] - st)
        n2 = pair(y, s, "08:00", X8, X8)
        if n2: nv[0].append(n2[0]); nv[1].append(n2[1]); nv[2].append(r.pool)
        else: dropped["naive"] += 1
        i2 = B.idx(y, "08:02"); stl, _, _ = bracket11(y, i2, i0, "L"); Xl = abs(y["mc"][i2] - stl); l2 = pair(y, "L", "08:02", Xl, Xl)   # Amendment 1
        if l2: alw.append(l2[0])
        if r.side in ("L", "S"):
            cl = y["mc"][B.idx(y, r.signal)]; X = abs(cl - r.stop); m2 = pair(y, r.side, r.signal, X, X)
            if not m2: dropped["read"] += 1; continue
            me[0].append(m2[0]); me[1].append(m2[1]); me[2].append(r.pool); sides.append(r.side)
            if n2: both.append(((m2[0] - m2[1]) / 2) - ((n2[0] - n2[1]) / 2))
    out = ["%s phase, %d days; pairs dropped (Amendment 1): read %d, naive %d" % (PH, len(t), dropped["read"], dropped["naive"])]
    for name, (a, b, p) in (("read12", me), ("naive_trend30", nv)):
        if not a: continue
        obs, mir, exc, pv = B.signflip(a, b); a_ = np.array(a)
        aw = a_[a_ > 0].mean() if (a_ > 0).any() else float("nan"); al = -a_[a_ <= 0].mean() if (a_ <= 0).any() else float("nan")
        out.append("%-14s n %3d  mean R %+.3f  mirror %+.3f  excess %+.3f  wins %d / %d  avg win %.2f / avg loss %.2f = %.2f:1  P %.4f" % (
            name, len(a), obs, mir, exc, (a_ > 0).sum(), len(a), aw, al, aw / al, pv))
        for pool in sorted(set(p)):
            aa = [x for x, q in zip(a, p) if q == pool]; bb = [x for x, q in zip(b, p) if q == pool]
            o2, m2, e2, p2 = B.signflip(aa, bb); out.append("    pool %s     n %3d  mean R %+.3f  excess %+.3f  P %.4f" % (pool, len(aa), o2, e2, p2))
    if both: out.append("read excess minus naive excess on the days the read trades: %+.3f (n %d)" % (np.mean(both), len(both)))
    alm = float(np.mean(alw)) if alw else float("nan")
    out.append("always long 08:02, same 1:1 bracket, every day: n %d  mean R %+.3f  wins %d / %d (Amendment 1)" % (len(alw), alm, sum(x > 0 for x in alw), len(alw)))
    for sd in ("L", "S"):
        a = [x for x, q in zip(me[0], sides) if q == sd]; b = [x for x, q in zip(me[1], sides) if q == sd]
        if a: o2, m2, e2, p2 = B.signflip(a, b); out.append("    read %s only  n %3d  mean R %+.3f  excess %+.3f  P %.4f" % (sd, len(a), o2, e2, p2))
    for hn, (a, b, _) in (("H1 read12", me), ("H2 naive", nv)):   # PREREG_READ12 Amendment 1: two hypotheses, P <= 0.015 each, n >= 30
        if not a: continue
        obs, mir, exc, pv = B.signflip(a, b)
        ok = exc >= 0.10 and pv <= 0.015 and obs > 0 and len(a) >= 30 and obs > alm
        out.append("PRIMARY %s: excess %+.3f, P %.4f, mean R %+.3f vs always-long %+.3f, n %d -> %s (bar: excess >= +0.10, P <= 0.015, mean R > 0, mean R > always-long, n >= 30)" % (
            hn, exc, pv, obs, alm, len(a), ("SUPPORTED" if ok else "NOT SHOWN") if PH == "test" else "training only, no verdict"))
    txt = "\n".join(out); print(txt)
    if PH == "test": open(os.path.join(HERE, "READ12_TEST_OUTPUT.txt"), "w").write(txt + "\n")


def cmd_h2():
    """Amendment 3: H2 (naive 08:00 30-minute trend, 1:1 at X) on every drawn test day, mechanically, once."""
    import manual_read_baselines as B
    if PH != "test" or not os.path.exists(ORDER): sys.exit("draw the test pool first")
    outp = os.path.join(HERE, "READ12_TEST_H2_OUTPUT.txt")
    if os.path.exists(outp): sys.exit("H2 already scored (one look): %s" % outp)
    o = pd.read_csv(ORDER); d = D.raw(); nv = ([], [], []); alw = []; drop = 0
    for r in o.itertuples():
        y = K.frame_for(d, pd.Timestamp(r.date)); i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6))); i8 = B.idx(y, "08:00")
        s = "L" if y["mc"][i8] > y["mc"][i8 - 30] else "S"; st, _, _ = bracket11(y, i8, i0, s); X8 = abs(y["mc"][i8] - st)
        n2 = pair(y, s, "08:00", X8, X8)
        if n2: nv[0].append(n2[0]); nv[1].append(n2[1]); nv[2].append(r.pool)
        else: drop += 1
        i2 = B.idx(y, "08:02"); stl, _, _ = bracket11(y, i2, i0, "L"); Xl = abs(y["mc"][i2] - stl); l2 = pair(y, "L", "08:02", Xl, Xl)
        if l2: alw.append(l2[0])
    a, b, p = nv; a_ = np.array(a); obs, mir, exc, pv = B.signflip(a, b); alm = float(np.mean(alw))
    aw = a_[a_ > 0].mean(); al = -a_[a_ <= 0].mean()
    out = ["H2 naive_trend30 on the sealed test pool: %d days, dropped %d (Amendment 1 of test 2)" % (len(o), drop),
           "naive  n %3d  mean R %+.3f  mirror %+.3f  excess %+.3f  wins %d / %d  avg win %.2f / avg loss %.2f = %.2f:1  P %.4f" % (
               len(a), obs, mir, exc, (a_ > 0).sum(), len(a), aw, al, aw / al, pv)]
    for pool in sorted(set(p)):
        aa = [x for x, q in zip(a, p) if q == pool]; bb = [x for x, q in zip(b, p) if q == pool]
        o2, m2, e2, p2 = B.signflip(aa, bb); out.append("    pool %s  n %3d  mean R %+.3f  excess %+.3f  P %.4f" % (pool, len(aa), o2, e2, p2))
    out.append("always long 08:02, same bracket: n %d  mean R %+.3f  wins %d / %d" % (len(alw), alm, sum(x > 0 for x in alw), len(alw)))
    ok = exc >= 0.10 and pv <= 0.015 and obs > 0 and len(a) >= 40 and obs > alm
    out.append("PRIMARY H2: excess %+.3f, P %.4f, mean R %+.3f vs always-long %+.3f, n %d -> %s (bar: excess >= +0.10, P <= 0.015, mean R > 0, mean R > always-long, n >= 40)" % (
        exc, pv, obs, alm, len(a), "SUPPORTED" if ok else "NOT SHOWN"))
    txt = "\n".join(out); print(txt); open(outp, "w").write(txt + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "freeze": cmd_freeze(); sys.exit()
    if len(a) < 2 or a[0] not in ("train", "test"): sys.exit(__doc__)
    {"draw": cmd_draw, "new": cmd_new, "scan": lambda: K.cmd_scan(False), "show": cmd_show, "call": lambda: cmd_call(a[2:]), "reveal": cmd_reveal,
     "status": cmd_status, "score": cmd_score, "h2": cmd_h2}[a[1]]()
