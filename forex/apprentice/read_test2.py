"""Pre-registered test of the apprentice's read v9 (PREREG_READ_TEST2.md): v8 plus two coded constraints (with the 30-minute trend only, signal 08:02 or later). Days are played blind with manual_read.py's v8 scanner; calls are hashed and
logged with a mechanical bracket; NO outcome is shown until all 100 calls are locked (`score` refuses before that).
Usage (from forex/apprentice): python read_test.py draw | new | scan | show | call L|S | call none "reason" | status | score"""
import os, sys, json, hashlib, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, manual_read as K

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(HERE, "state_t2"); os.makedirs(ST, exist_ok=True)
K.ST = ST  # manual_read's cur / save / scan / call now use the test's own state folder
ORDER = os.path.join(ST, "order.csv"); CALLS = os.path.join(HERE, "READ_TEST2_CALLS.csv")
POOLS = {"A": ("2022-01-03", "2022-12-30"), "B": ("2024-01-02", "2024-05-31")}
N_PER_POOL = 50


def playable(d, day):
    w = d[(d["lis"] >= day + pd.Timedelta(hours=7, minutes=45)) & (d["lis"] <= day + pd.Timedelta(hours=10))]
    return len(w) == 136


def cmd_draw():
    if os.path.exists(ORDER): sys.exit("order already drawn")
    d = D.raw(); days = pd.Series(d["lis"].dt.normalize().unique()); rng = np.random.default_rng(20261023); picks = {}
    for p, (a, b) in POOLS.items():
        cand = [x for x in days[(days >= a) & (days <= b) & (days.dt.weekday < 5)]]
        perm = [cand[k] for k in rng.permutation(len(cand))]; ok = []
        for x in perm:
            if playable(d, x): ok.append(x)
            if len(ok) == N_PER_POOL: break
        picks[p] = ok
    rows = []
    for k in range(N_PER_POOL):
        for p in ("A", "B"): rows.append({"id": "T%03d" % (len(rows) + 1), "pool": p, "date": picks[p][k].strftime("%Y-%m-%d")})
    pd.DataFrame(rows).to_csv(ORDER, index=False); print("drew %d days (dates hidden in %s)" % (len(rows), os.path.relpath(ORDER, HERE)))


def cmd_new():
    c = K.cur()
    if c and not c.get("done"): sys.exit("day %s still open" % c["id"])
    o = pd.read_csv(ORDER); done = set(pd.read_csv(CALLS)["id"]) if os.path.exists(CALLS) else set()
    for r in o.itertuples():
        if r.id in done: continue
        y = K.frame_for(D.raw(), pd.Timestamp(r.date)); y.to_parquet(os.path.join(ST, "day.parquet"))
        K.save({"id": r.id, "date": r.date, "pool": r.pool}); print("new test day %s (date hidden; v9: with the 30-min trend only, signal 08:02 or later). Next: scan" % r.id); return
    sys.exit("all 100 test days called: run score")


def cmd_show():
    c = K.cur(); y = pd.read_parquet(os.path.join(ST, "day.parquet")); until = c.get("shown_until", "07:58")
    print("%s shown until %s" % (c["id"], until))
    for q in y.itertuples():
        t = D.hm(q.lis)
        if "07:30" <= t <= until and q.lis.day == 3:
            up = q.mh - max(q.mo, q.mc); dn = min(q.mo, q.mc) - q.ml
            print("%s o %8.2f h %8.2f l %8.2f c %8.2f ema %8.2f atr %4.2f b/atr %+5.2f upw %4.2f dnw %4.2f c-ema %+5.2f volx %4.1f" % (
                t, q.mo, q.mh, q.ml, q.mc, q.ema, q.atr, (q.mc - q.mo) / q.atr, up, dn, q.mc - q.ema, q.v / q.vmed if q.vmed else float("nan")))


def bracket(y, i, i0, side):
    b = K.manual_bracket(y, i, i0, side); c = y["mc"][i]; L = side == "L"
    td = b["D"] if b else 2.5 * y["atr"][i]; sd = td / 0.53
    return round(c - sd if L else c + sd, 2), round(c + td if L else c - td, 2), (b["what"] if b else "no level: 2.5 ATR")


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
        if sig < "08:02": sys.exit("v9: no signal candle before 08:02")
        if (t30 > 0) != (side == "L") or t30 == 0: sys.exit("v9: with the 30-minute trend only (trend %+.2f)" % t30)
        stop, tgt, what = bracket(y, i, i0, side)
        call = {"side": side, "signal": sig, "stop": stop, "target": tgt, "level": what, "reason": " ".join(a[1:])}
    call["pc_time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    call["sha256"] = hashlib.sha256(json.dumps({**call, "id": c["id"]}, sort_keys=True).encode()).hexdigest()
    row = {"id": c["id"], "pool": c["pool"], "date": c["date"], **call}
    pd.DataFrame([row]).to_csv(CALLS, mode="a", header=not os.path.exists(CALLS), index=False)
    c["call"] = call; c["done"] = True; K.save(c)
    print("locked %s %s: %s %s stop %s target %s (%s)" % (c["id"], call["sha256"][:16], call["side"], call["signal"], call["stop"], call["target"], call["level"]))


def cmd_status():
    n = len(pd.read_csv(CALLS)) if os.path.exists(CALLS) else 0
    t = pd.read_csv(CALLS) if n else None
    print("%d of 100 test days called%s" % (n, "" if not n else "; trades %d, none %d" % ((t.side != "none").sum(), (t.side == "none").sum())))


def cmd_score():
    t = pd.read_csv(CALLS)
    if len(t) < 100 and "--force" not in sys.argv: sys.exit("only %d of 100 calls locked: no look before T100 (PREREG_READ_TEST2.md)" % len(t))
    import manual_read_baselines as B

    def pair(y, side, sig, sd, td):  # Amendment 1: a bracket the next open already crossed (simulate -> None) counts as no trade
        try: return B.pair(y, side, sig, sd, td)
        except TypeError: return None
    d = D.raw(); me = ([], [], []); nv = ([], [], []); both = []; dropped = {"read": 0, "naive": 0}
    for r in t.itertuples():
        y = K.frame_for(d, pd.Timestamp(r.date)); i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6))); i8 = B.idx(y, "08:00")
        s = "L" if y["mc"][i8] > y["mc"][i8 - 30] else "S"; st, tg, _ = bracket(y, i8, i0, s); c8 = y["mc"][i8]
        n2 = pair(y, s, "08:00", abs(c8 - st), abs(tg - c8))
        if n2: nv[0].append(n2[0]); nv[1].append(n2[1]); nv[2].append(r.pool)
        else: dropped["naive"] += 1
        if r.side in ("L", "S"):
            cl = y["mc"][B.idx(y, r.signal)]
            m2 = pair(y, r.side, r.signal, abs(cl - r.stop), abs(r.target - cl))
            if not m2: dropped["read"] += 1; continue
            a, b = m2; me[0].append(a); me[1].append(b); me[2].append(r.pool)
            if n2: both.append(((a - b) / 2) - ((n2[0] - n2[1]) / 2))
    out = ["pairs dropped (entry already beyond the target or stop, Amendment 1): read %d, naive %d" % (dropped["read"], dropped["naive"])]
    for name, (a, b, p) in (("read", me), ("naive_trend30", nv)):
        obs, mir, exc, pv = B.signflip(a, b)
        out.append("%-14s n %3d  mean R %+.3f  mirror %+.3f  excess %+.3f  wins %d / %d  P %.4f" % (name, len(a), obs, mir, exc, sum(x > 0 for x in a), len(a), pv))
        for pool in ("A", "B"):
            aa = [x for x, q in zip(a, p) if q == pool]; bb = [x for x, q in zip(b, p) if q == pool]
            if aa:
                o2, m2, e2, p2 = B.signflip(aa, bb); out.append("    pool %s     n %3d  mean R %+.3f  excess %+.3f  P %.4f" % (pool, len(aa), o2, e2, p2))
    out.append("read excess minus naive excess on the days the read trades: %+.3f (n %d)" % (np.mean(both), len(both)))
    obs, mir, exc, pv = B.signflip(*me[:2]); verdict = "SUPPORTED" if (exc >= 0.10 and pv <= 0.03 and obs > 0) else "NOT SHOWN"
    out.append("PRIMARY: excess %+.3f, P %.4f, mean R %+.3f -> %s (bar: excess >= +0.10, P <= 0.03 and mean R > 0)" % (exc, pv, obs, verdict))
    txt = "\n".join(out); print(txt)
    if len(t) >= 100: open(os.path.join(HERE, "READ_TEST2_OUTPUT.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"draw": cmd_draw, "new": cmd_new, "scan": lambda: K.cmd_scan(False), "show": cmd_show, "call": lambda: cmd_call(a[1:]),
     "status": cmd_status, "score": cmd_score}[a[0]]()
