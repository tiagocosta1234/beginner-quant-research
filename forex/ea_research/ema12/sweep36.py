"""PREREG_SWEEP36.md: a sweep reversal with the trader's confirmation (a gap in the reversal direction or a displacement candle that breaks structure) on all 46 MT5, DEV 2022-24 / VAL 2025 only (nothing after 2025-12-31 is ever loaded).
python sweep36.py --dry-run     engine checks (truncation test, hand check incl. 30 Apr 2025 London, trades per year, 36 variants)
python sweep36.py --run [W]     the run on W worker processes (default 8) -> SWEEP36_TRIALS.csv, SWEEP36_MARKETS.csv, SWEEP36_OUTPUT.txt
Kinds per variant: r = rule, real bid / ask (the bars); i = inverted side, real; c = control without the sweep requirement, real; z = rule at mid prices (ceiling); zc = control at mid prices."""
import sys, time, itertools
import numpy as np, pandas as pd
from ema1000 import load_market, MARKETS, D0, DEV_END, VAL_END, YB, cstats, om_of
from ema1000_nocost import zero_spread
W = 30; HOLD = 60; TBAR = 2.77
AXES = (("L", (30, 60)), ("conf", ("gap", "disp", "either")), ("m", (0.5, 1.0, 2.0)), ("ses", ("London", "NY")))
VARIANTS = [dict(id=i, **dict(zip([k for k, _ in AXES], v))) for i, v in enumerate(itertools.product(*[v for _, v in AXES]))]; assert len(VARIANTS) == 36
KINDS = ("r", "i", "c", "z", "zc")
def feats(M):
    mh, ml, mo, mc = M["mh"], M["ml"], M["mo"], M["mid"]; atr = pd.Series(mh - ml).rolling(14).mean().shift(1).to_numpy()
    F = dict(atr=atr, minlow10=pd.Series(ml).rolling(10).min().to_numpy(), maxhigh10=pd.Series(mh).rolling(10).max().to_numpy(), gap_b=np.r_[[False, False], ml[2:] > mh[:-2]], gap_s=np.r_[[False, False], mh[2:] < ml[:-2]])
    ph5 = pd.Series(mh).rolling(5).max().shift(1).to_numpy(); pl5 = pd.Series(ml).rolling(5).min().shift(1).to_numpy()
    with np.errstate(invalid="ignore"):
        F["disp_b"] = ((mc - mo) >= atr) & (mc > ph5); F["disp_s"] = ((mo - mc) >= atr) & (mc < pl5)
        for L in (30, 60): F[("sw_b", L)] = F["minlow10"] < pd.Series(ml).rolling(L).min().shift(10).to_numpy(); F[("sw_s", L)] = F["maxhigh10"] > pd.Series(mh).rolling(L).max().shift(10).to_numpy()
    return F
def signals(M, F, L, conf, ses, ctrl):
    key = M["dord"] * 1440 + M["hm"]; out = []
    cb = {"gap": F["gap_b"], "disp": F["disp_b"], "either": F["gap_b"] | F["disp_b"]}[conf]; cs = {"gap": F["gap_s"], "disp": F["disp_s"], "either": F["gap_s"] | F["disp_s"]}[conf]
    sb = cb if ctrl else cb & F[("sw_b", L)]; ss = cs if ctrl else cs & F[("sw_s", L)]
    for dy in M["days"]:
        om = om_of(dy, ses); lo = np.searchsorted(key, dy * 1440 + om, "left"); hi = np.searchsorted(key, dy * 1440 + om + W - 1, "right")
        if hi <= lo: continue
        idx = np.flatnonzero(sb[lo:hi] | ss[lo:hi]) + lo
        if len(idx) == 0: continue
        k = int(idx[0])
        if sb[k] and ss[k]: continue
        e = k + 1
        if e >= M["n"] or M["dord"][e] != dy or M["hm"][e] - M["hm"][k] > 2: continue
        s = 1 if sb[k] else -1; out.append((dy, k, s, float(F["minlow10"][k] if s > 0 else F["maxhigh10"][k]), float(F["atr"][k])))
    return out
def sim(P, sigs, m, mirror=False, info=None):
    n = len(P["bc"]); bl, bh, ah, al, bc, ac, ao, bo = (P[k] for k in ("bl", "bh", "ah", "al", "bc", "ac", "ao", "bo")); dd = []; RR = []
    for (dy, k, s, stop, atrk) in sigs:
        e = k + 1; er = ao[e] if s > 0 else bo[e]; sd = abs(er - stop)
        if sd < 0.2 * atrk or (s > 0 and stop >= er) or (s < 0 and stop <= er): continue
        ss = -s if mirror else s; ent = ao[e] if ss > 0 else bo[e]; st = ent - ss * sd; tg = ent + ss * m * sd; x = slice(e, min(e + HOLD, n))
        if ss > 0: hs, ht = bl[x] <= st, bh[x] >= tg
        else: hs, ht = ah[x] >= st, al[x] <= tg
        i_s = int(np.argmax(hs)) if hs.any() else 10 ** 9; i_t = int(np.argmax(ht)) if ht.any() else 10 ** 9
        if i_s <= i_t and i_s < 10 ** 9: R = -1.0
        elif i_t < 10 ** 9: R = m
        else: j = min(e + HOLD, n) - 1; R = ((bc[j] - ent) if ss > 0 else (ent - ac[j])) / sd
        dd.append(dy); RR.append(R)
        if info is not None: info.append((dy, k, e, ss, ent, st, tg, R))
    return np.array(dd, dtype=np.int16) - D0 if False else np.array(dd, dtype=np.int32), np.array(RR, dtype=np.float32)
def run_market(m_name):
    t0 = time.time(); M = load_market(m_name); Z = zero_spread(M); F = feats(M); out = {}; cache = {}
    for v in VARIANTS:
        for ctrl in (False, True):
            ck = (v["ses"], v["L"], v["conf"], ctrl)
            if ck not in cache: cache[ck] = signals(M, F, v["L"], v["conf"], v["ses"], ctrl)
        r = cache[(v["ses"], v["L"], v["conf"], False)]; c = cache[(v["ses"], v["L"], v["conf"], True)]
        out[(v["id"], "r")] = sim(M, r, v["m"]); out[(v["id"], "i")] = sim(M, r, v["m"], True); out[(v["id"], "c")] = sim(M, c, v["m"]); out[(v["id"], "z")] = sim(Z, r, v["m"]); out[(v["id"], "zc")] = sim(Z, c, v["m"])
    return m_name, out, time.time() - t0
def stats(d, R, mk, nm):
    dev = (d >= D0) & (d <= DEV_END); val = (d > DEV_END) & (d <= VAL_END); a, b = cstats(d[dev], R[dev]), cstats(d[val], R[val]); yrs = np.digitize(d, YB)
    ym = [R[dev & (yrs == y)].mean() if (dev & (yrs == y)).any() else np.nan for y in (1, 2, 3)]
    if dev.any():
        tot = np.bincount(mk[dev], weights=R[dev], minlength=nm); best = int(np.argmax(tot)); nb = dev & (mk != best); wo = cstats(d[nb], R[nb])
    else: wo = dict(n=0, mean=np.nan, t=np.nan)
    cand = bool(a["n"] >= 3000 and a["mean"] >= 0.03 and a["t"] >= TBAR and b["mean"] > 0 and b["t"] >= 1.65 and all(y > 0 for y in ym) and wo["mean"] > 0 and wo["t"] >= 2.5)
    return dict(dev_n=a["n"], dev_R=a["mean"], dev_t=a["t"], val_n=b["n"], val_R=b["mean"], val_t=b["t"], y22=ym[0], y23=ym[1], y24=ym[2], nb_R=wo["mean"], nb_t=wo["t"], cand=cand)
nm = 46
def full(workers):
    global nm
    from multiprocessing import Pool
    t0 = time.time(); res = {}; print("start", time.strftime("%H:%M:%S"), "workers", workers, flush=True)
    with Pool(workers) as p:
        for m_, r, sec in p.imap_unordered(run_market, MARKETS): res[m_] = r; print("  %-7s done in %5.0fs (%d/%d)" % (m_, sec, len(res), len(MARKETS)), flush=True)
    ms = sorted(res); nm = len(ms); rows = []; permk = {k: [] for k in KINDS}; gold = {}
    for v in VARIANTS:
        row = dict(**v)
        for kd in KINDS:
            d = np.concatenate([res[m_][(v["id"], kd)][0] for m_ in ms]).astype(np.int64) + (0); R = np.concatenate([res[m_][(v["id"], kd)][1] for m_ in ms]).astype(float); mk = np.concatenate([np.full(len(res[m_][(v["id"], kd)][0]), i) for i, m_ in enumerate(ms)])
            st = stats(d, R, mk, nm)
            for a, b in st.items(): row["%s_%s" % (kd, a)] = b
            if kd in ("r", "z"):
                dev = (d >= D0) & (d <= DEV_END); pm = [R[dev & (mk == i)].mean() if (dev & (mk == i)).sum() >= 30 else np.nan for i in range(nm)]; permk[kd].append(pm)
                for nmq, sel in (("XAU", ["XAUUSD"]), ("XAU+NSDQ", ["XAUUSD", "NSDQ"])):
                    msk = dev & np.isin(mk, [ms.index(x) for x in sel]); s2 = cstats(d[msk], R[msk]); row["%s_%s_dev_n" % (kd, nmq)] = s2["n"]; row["%s_%s_dev_R" % (kd, nmq)] = s2["mean"]; row["%s_%s_dev_t" % (kd, nmq)] = s2["t"]
        rows.append(row)
    T = pd.DataFrame(rows); T.to_csv("SWEEP36_TRIALS.csv", index=False); mrows = []
    for kd in ("r", "z"):
        A = np.array(permk[kd])
        for i, m_ in enumerate(ms): mrows.append(dict(kind=kd, market=m_, med_dev_R=np.nanmedian(A[:, i]), best_dev_R=np.nanmax(A[:, i]), n_pos=int((A[:, i] > 0).sum())))
    MK = pd.DataFrame(mrows); MK.to_csv("SWEEP36_MARKETS.csv", index=False); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print("\nfinished %s in %.1f min | variants %d | CANDIDATES (all bars, real bid / ask, DEV t >= %.2f): %d" % (time.strftime("%H:%M:%S"), (time.time() - t0) / 60, len(T), TBAR, int(T.r_cand.sum())))
    print("\nRULE, real bid / ask, DEV 2022-24 pooled over 46 markets (36 variants): trades per variant median %d | mean R median %+.4f best %+.4f | share > 0: %.0f%% | t: min %.2f median %.2f max %.2f | VAL 2025 mean R median %+.4f, share > 0 %.0f%%" % (T.r_dev_n.median(), T.r_dev_R.median(), T.r_dev_R.max(), 100 * (T.r_dev_R > 0).mean(), T.r_dev_t.min(), T.r_dev_t.median(), T.r_dev_t.max(), T.r_val_R.median(), 100 * (T.r_val_R > 0).mean()))
    print("INVERTED side, real: DEV mean R median %+.4f best %+.4f | direction skill (rule - inverted) / 2: median %+.4f, share of variants > 0: %.0f%%" % (T.i_dev_R.median(), T.i_dev_R.max(), ((T.r_dev_R - T.i_dev_R) / 2).median(), 100 * ((T.r_dev_R - T.i_dev_R) > 0).mean()))
    print("CONTROL without the sweep (confirmation only), real: DEV mean R median %+.4f best %+.4f | rule minus control (the sweep's contribution): median %+.4f, share of variants where the sweep helps: %.0f%%" % (T.c_dev_R.median(), T.c_dev_R.max(), (T.r_dev_R - T.c_dev_R).median(), 100 * ((T.r_dev_R - T.c_dev_R) > 0).mean()))
    print("CEILING, no spread: rule DEV mean R median %+.4f best %+.4f (t max %+.2f), share > 0 %.0f%% | control %+.4f -> the spread costs %+.4f R a trade at the median" % (T.z_dev_R.median(), T.z_dev_R.max(), T.z_dev_t.max(), 100 * (T.z_dev_R > 0).mean(), T.zc_dev_R.median(), (T.z_dev_R - T.r_dev_R).median()))
    for ax in ("conf", "m", "L", "ses"): print("median DEV mean R (rule, real) by %s:" % ax, T.groupby(ax).r_dev_R.median().round(4).to_dict())
    print("\ntop 8 variants by DEV t (rule, real):"); print(T.sort_values("r_dev_t", ascending=False).head(8)[["id", "L", "conf", "m", "ses", "r_dev_n", "r_dev_R", "r_dev_t", "r_val_R", "r_val_t", "r_y22", "r_y23", "r_y24", "r_nb_t", "i_dev_R", "c_dev_R", "z_dev_R"]].round(3).to_string(index=False))
    for nmq in ("XAU", "XAU+NSDQ"): print("\n%s alone (rule, real) DEV: trades median %d, mean R median %+.4f best %+.4f, t max %+.2f, share > 0 %.0f%% | ceiling no spread: median %+.4f" % (nmq, T["r_%s_dev_n" % nmq].median(), T["r_%s_dev_R" % nmq].median(), T["r_%s_dev_R" % nmq].max(), T["r_%s_dev_t" % nmq].max(), 100 * (T["r_%s_dev_R" % nmq] > 0).mean(), T["z_%s_dev_R" % nmq].median()))
    for kd in ("r", "z"):
        g = MK[MK.kind == kd].sort_values("med_dev_R", ascending=False); print("\nper market, %s: median DEV mean R over the 36 variants, 6 best and 4 worst" % ("rule real" if kd == "r" else "rule at mid (ceiling)")); print(pd.concat([g.head(6), g.tail(4)]).round(4).to_string(index=False)); print("  markets with a positive median:", list(g.market[g.med_dev_R > 0]) or "none")
def dry():
    print("variants: %d (L %s x conf %s x m %s x session %s)" % (len(VARIANTS), AXES[0][1], AXES[1][1], AXES[2][1], AXES[3][1]))
    rng = np.random.default_rng(3); print("\n(1) truncation test: data after the entry minute cut, same signal and same entry (4 markets x 4 variants x up to 5 trades):"); bad = tested = 0
    for mn in ("XAUUSD", "EURUSD", "BTCUSD", "NIKKEI"):
        M = load_market(mn); F = feats(M)
        for v in [VARIANTS[i] for i in rng.choice(36, 4, replace=False)]:
            sg = signals(M, F, v["L"], v["conf"], v["ses"], False)
            for q in (rng.choice(len(sg), min(5, len(sg)), replace=False) if sg else []):
                dy, k, s, stop, atrk = sg[q]; e = k + 1; M2 = load_market(mn, upto=e, med=M["med"]); F2 = feats(M2); s2 = [z for z in signals(M2, F2, v["L"], v["conf"], v["ses"], False) if z[0] == dy]
                tested += 1; bad += not (s2 and s2[0][1] == k and s2[0][2] == s and abs(s2[0][3] - stop) < 1e-9)
    print("  %d signals recomputed with the future cut, %d mismatches" % (tested, bad))
    print("\n(2) hand check, XAUUSD London, L 60, either, m 0.5, around 30 Apr 2025:"); M = load_market("XAUUSD"); F = feats(M); sg = signals(M, F, 60, "either", "London", False); info = []; sim(M, sg, 0.5, info=info)
    import datetime as dt
    for (dy, k, e, ss, ent, st, tg, R) in info:
        if dt.date.fromordinal(int(dy)) in (dt.date(2025, 4, 29), dt.date(2025, 4, 30), dt.date(2025, 5, 1)):
            hm = (int(M["hm"][k]) - 120); print("  %s side %+d: confirmation candle %02d:%02d local, entry %02d:%02d at %.2f, stop %.2f (%.2f away), target %.2f -> R %+.2f" % (dt.date.fromordinal(int(dy)), ss, hm // 60, hm % 60, (hm + 1) // 60, (hm + 1) % 60, ent, st, abs(ent - st), tg, R))
    print("\n(3) trades per year (XAUUSD, L 60, either, m 0.5):"); y = pd.Series([dt.date.fromordinal(int(x[0])).year for x in info]).value_counts().sort_index().to_dict(); print("  London", y)
    sg2 = signals(M, F, 60, "either", "NY", False); info2 = []; sim(M, sg2, 0.5, info=info2); print("  NY", pd.Series([dt.date.fromordinal(int(x[0])).year for x in info2]).value_counts().sort_index().to_dict())
    print("\n(4) buy / sell mix and mean R (XAUUSD London, DEV): ", end=""); dev = [x for x in info if D0 <= x[0] <= DEV_END]; print("%d trades, buys %d, sells %d, mean R %+.3f, wins %d" % (len(dev), sum(1 for x in dev if x[3] > 0), sum(1 for x in dev if x[3] < 0), np.mean([x[7] for x in dev]), sum(1 for x in dev if x[7] > 0)))
if __name__ == "__main__":
    if "--dry-run" in sys.argv: dry()
    elif "--run" in sys.argv: full(int(sys.argv[sys.argv.index("--run") + 1]) if len(sys.argv) > sys.argv.index("--run") + 1 else 8)
    else: print(__doc__)
