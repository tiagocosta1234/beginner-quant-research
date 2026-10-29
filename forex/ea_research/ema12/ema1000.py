"""PREREG_EMA1000.md: 1,000 variations of the 12 EMA rule on all 46 MT5, DEV 2022-24 / VAL 2025 only (nothing after 2025-12-31 is ever loaded).
python ema1000.py --dry-run     engine checks (reproduces MANUALRULE_TRIALS.csv, truncation test, hand check, trades per year)
python ema1000.py --run [W]     the 46,000 trial series on W worker processes (default 8) -> EMA1000_TRIALS.csv, EMA1000_MARKETS.csv, EMA1000_OUTPUT.txt"""
import sys, os, glob, itertools, datetime as dt, time
import numpy as np, pandas as pd
from ema12_test import open_min
DATA = "forex/data_mt5"; MARKETS = sorted(os.path.basename(f).replace("_M1_rates.parquet", "") for f in glob.glob(DATA + "/*_M1_rates.parquet"))
AXES = (("ema", (8, 12, 20)), ("tf", (1, 3, 5)), ("body", ("none", "wick", "wick_atr")), ("win", (15, 30, 60)), ("tgt", ("K1", "K2", "K3", "SW", "ATR1")), ("stop", (1.5, 2.0, 3.0)), ("ses", ("London", "NY")), ("trend", ("none", "m30")))
GRID = list(itertools.product(*[v for _, v in AXES])); assert len(GRID) == 4860
PICK = np.sort(np.random.default_rng(20261020).choice(len(GRID), 1000, replace=False)); VARIANTS = [dict(id=i, **dict(zip([k for k, _ in AXES], GRID[g]))) for i, g in enumerate(PICK)]
EPOCH = dt.date(1970, 1, 1).toordinal(); D0 = dt.date(2022, 1, 1).toordinal(); DEV_END = dt.date(2024, 12, 31).toordinal(); VAL_END = dt.date(2025, 12, 31).toordinal(); LIMIT_T = int(pd.Timestamp("2026-01-01").timestamp())
YB = [dt.date(y, 1, 1).toordinal() for y in (2022, 2023, 2024, 2025, 2026)]
def load_market(m, upto=None, med=None):
    d = pd.read_parquet(f"{DATA}/{m}_M1_rates.parquet").sort_values("t"); d = d[d.t < LIMIT_T].reset_index(drop=True); yr = pd.to_datetime(d.t, unit="s").dt.year
    if med is None: med = d[d.sp > 0].groupby(yr[d.sp > 0]).sp.median()
    z = (d.sp <= 0).to_numpy()
    for b, a in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): d.loc[z, a] = d.loc[z, b] + yr[z].map(med).to_numpy()
    if upto is not None: d = d.iloc[:upto + 1]
    M = {k: d[k].to_numpy() for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")}; M["mid"] = (M["bc"] + M["ac"]) / 2; M["mo"] = (M["bo"] + M["ao"]) / 2; M["mh"] = (M["bh"] + M["ah"]) / 2; M["ml"] = (M["bl"] + M["al"]) / 2
    t = d.t.to_numpy(); M["dord"] = t // 86400 + EPOCH; M["hm"] = (t % 86400) // 60; M["med"] = med; M["n"] = len(d); dd = np.unique(M["dord"]); M["days"] = dd[(dd >= D0) & ((dd - 1) % 7 < 5)]; return M
def make_bars(M, tf):
    n, key = M["n"], M["dord"] * 1440 + M["hm"] // tf
    if tf == 1: st = np.arange(n); en = st; keep = np.ones(n, bool)
    else: ch = np.flatnonzero(np.diff(key)) + 1; st = np.r_[0, ch]; en = np.r_[ch - 1, n - 1]; keep = (en - st + 1) == tf
    h = (M["mh"] if tf == 1 else np.maximum.reduceat(M["mh"], st))[keep] if tf > 1 else M["mh"]; l = (M["ml"] if tf == 1 else np.minimum.reduceat(M["ml"], st))[keep] if tf > 1 else M["ml"]
    st, en = st[keep], en[keep]; B = dict(o=M["mo"][st], c=M["mid"][en], h=h, l=l, end=en, dord=M["dord"][st], shm=M["hm"][st]); B["key"] = B["dord"] * 1440 + B["shm"]
    B["m30"] = np.sign(M["mid"][en] - M["mid"][np.maximum(en - 30, 0)]) * (en >= 30); rng = B["h"] - B["l"]; B["atr"] = pd.Series(rng).rolling(14).mean().to_numpy(); B["atrp"] = np.r_[np.nan, B["atr"][:-1]]
    w = np.lib.stride_tricks.sliding_window_view; k = len(B["h"]); sh = np.zeros(k, bool); sl = np.zeros(k, bool)
    if k >= 5: sh[2:k - 2] = B["h"][2:k - 2] >= w(B["h"], 5).max(axis=1); sl[2:k - 2] = B["l"][2:k - 2] <= w(B["l"], 5).min(axis=1)
    B["sh"], B["sl"] = sh, sl; return B
def cond(B, ema_len, body_f, trend):
    c, o, h, l = B["c"], B["o"], B["h"], B["l"]; ema = pd.Series(c).ewm(span=ema_len, adjust=False).mean().to_numpy(); side = np.where(c > ema, 1, -1)
    ok = ((o - ema) * (c - ema) < 0) & (np.arange(len(c)) >= 100) & ~np.isnan(B["atrp"]); body = np.abs(c - o); wick = np.maximum(h - np.maximum(o, c), np.minimum(o, c) - l)
    if body_f in ("wick", "wick_atr"): ok &= body > wick
    if body_f == "wick_atr": ok &= body >= 0.5 * np.nan_to_num(B["atrp"], nan=np.inf)
    if trend == "m30": ok &= side == B["m30"]
    return ok, side
def target(B, t, side, entry, tgt):
    a_t = B["atrp"][t]
    if tgt == "ATR1": return 1.0 * a_t
    H, L = B["h"], B["l"]
    if tgt == "SW":
        k0 = max(t - 89, 2); ks = np.arange(k0, t - 1)
        if len(ks) == 0: return None
        if side > 0: lv = H[ks][B["sh"][ks]]; lv = lv[lv - entry >= 0.5 * a_t]; return None if len(lv) == 0 else lv.min() - entry
        lv = L[ks][B["sl"][ks]]; lv = lv[entry - lv >= 0.5 * a_t]; return None if len(lv) == 0 else entry - lv.max()
    c0 = max(t - 90, 2); cs = np.arange(c0, t + 1); a = cs - 2
    if side > 0:
        gap = L[a] > H[cs]; near, far = H[cs], L[a]; rev = np.maximum.accumulate(H[c0 + 1:t + 1][::-1])[::-1] if t > c0 else np.array([]); later = np.r_[rev, -np.inf]; unf = later < far
    else:
        gap = H[a] < L[cs]; near, far = L[cs], H[a]; rev = np.minimum.accumulate(L[c0 + 1:t + 1][::-1])[::-1] if t > c0 else np.array([]); later = np.r_[rev, np.inf]; unf = later > far
    dn = (near - entry) * side; valid = gap & unf & (dn >= 0.5 * a_t)
    if not valid.any(): return None
    j = int(np.argmin(np.where(valid, dn, np.inf))); size = abs(far[j] - near[j]); lvl = near[j] if tgt == "K2" else far[j] if tgt == "K3" else (far[j] if size <= 1.5 * a_t else (near[j] + far[j]) / 2)
    return abs(lvl - entry)
_om = {}
def om_of(dord, ses):
    k = (dord, ses)
    if k not in _om: _om[k] = open_min(dt.date.fromordinal(int(dord)), ses)
    return _om[k]
def signals(M, B, ok, side, ses, win, tgt):
    out = []
    for dy in M["days"]:
        om = om_of(dy, ses); lo = np.searchsorted(B["key"], dy * 1440 + om, "left"); hi = np.searchsorted(B["key"], dy * 1440 + om + win - 1, "right")
        for t in np.flatnonzero(ok[lo:hi]) + lo:
            e = B["end"][t] + 1
            if e >= M["n"] or M["dord"][e] != dy or M["hm"][e] - M["hm"][B["end"][t]] > 2: break
            s = int(side[t]); entry = M["ao"][e] if s > 0 else M["bo"][e]; d = target(B, t, s, entry, tgt)
            if d is None or not d > 0: continue
            out.append((dy, e, s, entry, d, t)); break
    return out
def simulate(M, sig, stop, max_bars=60):
    R = np.empty(len(sig)); bh, bl, bc, ah, al, ac = (M[k] for k in ("bh", "bl", "bc", "ah", "al", "ac")); n = M["n"]
    for i, (dy, e, s, entry, d, t) in enumerate(sig):
        x = slice(e, min(e + max_bars, n)); tp = entry + s * d; sl = entry - s * stop * d
        if s > 0: hs, ht = bl[x] <= sl, bh[x] >= tp
        else: hs, ht = ah[x] >= sl, al[x] <= tp
        i_s = int(np.argmax(hs)) if hs.any() else 10 ** 9; i_t = int(np.argmax(ht)) if ht.any() else 10 ** 9
        if i_s <= i_t and i_s < 10 ** 9: R[i] = -1.0
        elif i_t < 10 ** 9: R[i] = 1.0 / stop
        else: j = min(e + max_bars, n) - 1; R[i] = ((bc[j] - entry) if s > 0 else (entry - ac[j])) / (stop * d)
    return R
def run_market(m, variants=None, M=None):
    M = M or load_market(m); variants = variants or VARIANTS; bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}; cc = {}; sg = {}; out = {}
    for v in variants:
        ck = (v["tf"], v["ema"], v["body"], v["trend"])
        if ck not in cc: cc[ck] = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"])
        sk = (v["ses"], v["win"], v["tgt"]) + ck
        if sk not in sg: sg[sk] = signals(M, bars[v["tf"]], cc[ck][0], cc[ck][1], v["ses"], v["win"], v["tgt"])
        s = sg[sk]; out[v["id"]] = (np.array([x[0] for x in s], dtype=np.int32), simulate(M, s, v["stop"]).astype(np.float32))
    return out
def cstats(day, R):
    n = len(R)
    if n < 30: return dict(n=n, mean=np.nan, t=np.nan)
    mu = R.mean(); u, inv = np.unique(day, return_inverse=True); se = np.sqrt((np.bincount(inv, weights=R - mu) ** 2).sum()) / n
    return dict(n=n, mean=mu, t=mu / se if se > 0 else np.nan)
def _work(m): t0 = time.time(); r = run_market(m); return m, r, time.time() - t0
def dry():
    print("variants %d, markets %d, grid %d; first variants:" % (len(VARIANTS), len(MARKETS), len(GRID)))
    for v in VARIANTS[:3]: print("  ", v)
    K = pd.read_csv("MANUALRULE_TRIALS.csv"); base = dict(ema=12, tf=1, body="wick_atr", win=15, tgt="K1", stop=2.0, trend="none"); print("\n(1) reproduction of MANUALRULE_TRIALS.csv (K1, DEV 2022-24):")
    worst = 0.0
    for m in ("XAUUSD", "NSDQ"):
        M = load_market(m)
        for ses in ("London", "NY"):
            r = run_market(m, [dict(id=0, ses=ses, **base)], M)[0]; dev = r[0] <= DEV_END; keep = r[0] >= D0; x = r[1][keep & dev]; n = len(x); mean = x.mean(); t = mean / (x.std(ddof=1) / np.sqrt(n))
            k = K[(K.market == m) & (K.sess == ses) & (K["var"] == "K1")].iloc[0]; print("  %-7s %-6s new: n %4d meanR %+.4f t %+.2f | MANUALRULE: n %4d meanR %+.4f t %+.2f" % (m, ses, n, mean, t, k.dev_n, k.dev_R, k.dev_t)); worst = max(worst, abs(n - k.dev_n), abs(mean - k.dev_R) * 100)
    print("  largest difference (trades or 100 x mean R): %.3f" % worst)
    print("\n(4) trades per year, baseline variant, first 8 markets:")
    for m in MARKETS[:8]:
        r = run_market(m, [dict(id=0, ses="London", **base)])[0]; yrs = np.digitize(r[0], YB) ; print("  %-7s London trades per year %s" % (m, {2021 + int(y): int((yrs == y).sum()) for y in np.unique(yrs)}))
    print("\n(2) truncation test: signal recomputed with everything after the entry minute cut:"); rng = np.random.default_rng(5); bad = tested = 0
    for m in ("XAUUSD", "EURUSD", "BTCUSD", "NIKKEI"):
        M = load_market(m)
        for v in [VARIANTS[i] for i in rng.choice(len(VARIANTS), 6, replace=False)]:
            s = None; bars = make_bars(M, v["tf"]); ok, side = cond(bars, v["ema"], v["body"], v["trend"]); s = signals(M, bars, ok, side, v["ses"], v["win"], v["tgt"])
            for k in (rng.choice(len(s), min(3, len(s)), replace=False) if len(s) else []):
                x = s[k]; M2 = load_market(m, upto=x[1], med=M["med"]); b2 = make_bars(M2, v["tf"]); ok2, side2 = cond(b2, v["ema"], v["body"], v["trend"]); y = [z for z in signals(M2, b2, ok2, side2, v["ses"], v["win"], v["tgt"]) if z[0] == x[0]]
                tested += 1; bad += not (y and y[0][1] == x[1] and y[0][2] == x[2] and abs(y[0][4] - x[4]) < 1e-9)
    print("  %d trades recomputed with the future cut, %d mismatches" % (tested, bad))
    print("\n(3) hand check, XAUUSD London baseline:"); M = load_market("XAUUSD"); B = make_bars(M, 1); ok, side = cond(B, 12, "wick_atr", "none"); s = signals(M, B, ok, side, "London", 15, "K1")[60:63]
    for (dy, e, sd, entry, d, t) in s: print("  %s signal minute %02d:%02d open %.2f close %.2f ema(12) -> side %d, entry %.2f target dist %.2f stop dist %.2f" % (dt.date.fromordinal(int(dy)), M["hm"][B["end"][t]] // 60, M["hm"][B["end"][t]] % 60, B["o"][t], B["c"][t], sd, entry, d, 2 * d))
def full(workers):
    from multiprocessing import Pool
    t0 = time.time(); res = {}; print("start", time.strftime("%H:%M:%S"), "workers", workers, flush=True)
    with Pool(workers) as p:
        for m, r, sec in p.imap_unordered(_work, MARKETS): res[m] = r; print("  %-7s done in %5.0fs (%d/%d)" % (m, sec, len(res), len(MARKETS)), flush=True)
    rows, mrows = [], []; ms = list(res)
    for v in VARIANTS:
        d = np.concatenate([res[m][v["id"]][0] for m in ms]); R = np.concatenate([res[m][v["id"]][1] for m in ms]).astype(float); mk = np.concatenate([np.full(len(res[m][v["id"]][0]), i) for i, m in enumerate(ms)])
        dev = (d >= D0) & (d <= DEV_END); val = (d > DEV_END) & (d <= VAL_END); a, b = cstats(d[dev], R[dev]), cstats(d[val], R[val]); yrs = np.digitize(d, YB); ym = [R[dev & (yrs == y)].mean() if (dev & (yrs == y)).any() else np.nan for y in (1, 2, 3)]
        tot = np.bincount(mk[dev], weights=R[dev], minlength=len(ms)); best = int(np.argmax(tot)); nb = dev & (mk != best); wo = cstats(d[nb], R[nb])
        pos = np.mean([R[dev & (mk == i)].mean() > 0 for i in range(len(ms)) if (dev & (mk == i)).sum() >= 30] or [np.nan])
        for i, m in enumerate(ms):
            x, y = dev & (mk == i), val & (mk == i); mrows.append(dict(id=v["id"], market=m, dev_n=int(x.sum()), dev_R=R[x].mean() if x.any() else np.nan, val_n=int(y.sum()), val_R=R[y].mean() if y.any() else np.nan))
        rows.append(dict(**v, dev_n=a["n"], dev_R=a["mean"], dev_t=a["t"], val_n=b["n"], val_R=b["mean"], val_t=b["t"], y22=ym[0], y23=ym[1], y24=ym[2], noBest_R=wo["mean"], noBest_t=wo["t"], best_market=ms[best], share_pos=pos))
    T = pd.DataFrame(rows); T["cand"] = (T.dev_n >= 3000) & (T.dev_R >= 0.03) & (T.dev_t >= 3.72) & (T.val_R > 0) & (T.val_t >= 1.65) & (T.y22 > 0) & (T.y23 > 0) & (T.y24 > 0) & (T.noBest_R > 0) & (T.noBest_t >= 2.5)
    T.to_csv("EMA1000_TRIALS.csv", index=False); pd.DataFrame(mrows).to_csv("EMA1000_MARKETS.csv", index=False); pd.set_option("display.width", 260); pd.set_option("display.max_columns", 30)
    print("\nfinished %s in %.0f min | variants %d | CANDIDATES (all bars): %d" % (time.strftime("%H:%M:%S"), (time.time() - t0) / 60, len(T), int(T.cand.sum())))
    print("DEV clustered t over the 1,000 variants: min %.2f, 5%% %.2f, 25%% %.2f, median %.2f, 75%% %.2f, 95%% %.2f, max %.2f | share with DEV mean R > 0: %.0f%% | DEV t >= 3.72: %d | DEV t >= 2.58: %d" % (T.dev_t.min(), *T.dev_t.quantile([.05, .25, .5, .75, .95]), T.dev_t.max(), 100 * (T.dev_R > 0).mean(), (T.dev_t >= 3.72).sum(), (T.dev_t >= 2.58).sum()))
    print("trades per variant (DEV): median %d | median DEV mean R %+.4f | median VAL mean R %+.4f" % (T.dev_n.median(), T.dev_R.median(), T.val_R.median()))
    print("\nbest 20 by DEV t:"); print(T.sort_values("dev_t", ascending=False).head(20)[["id", "ema", "tf", "body", "win", "tgt", "stop", "ses", "trend", "dev_n", "dev_R", "dev_t", "val_R", "val_t", "y22", "y23", "y24", "noBest_t", "best_market", "share_pos", "cand"]].round(3).to_string(index=False))
    for ax in ("ses", "tf", "tgt", "stop", "body", "trend", "ema", "win"): print("\nmedian DEV mean R by %s:" % ax, T.groupby(ax).dev_R.median().round(4).to_dict())
if __name__ == "__main__":
    if "--dry-run" in sys.argv: dry()
    elif "--run" in sys.argv: full(int(sys.argv[sys.argv.index("--run") + 1]) if len(sys.argv) > sys.argv.index("--run") + 1 else 8)
    else: print(__doc__)
