"""PREREG_TRAP12.md: the trader's 22 Oct "failed break at the 12 EMA" setup (down-trend, pullback coil on the EMA, a weak white candle breaking above it, a displacement candle back below it,
his close rule on untouched gap remainders, entry after the displacement or its continuation candle, target the nearest whole untouched gap), on all 46 MT5, DEV 2022-24 / VAL 2025 only.
python trap12.py --dry-run     engine checks (truncation test, hand check on the 22 Oct OANDA bars, setups per year, coverage of his April-May 2025 trades), no P&L
python trap12.py --run [W]     the run on W worker processes (default 8) -> TRAP12_TRIALS.csv, TRAP12_MARKETS.csv (output to stdout, saved as TRAP12_OUTPUT.txt)
Shorts are found on the prices as they are; longs on the mirrored prices (every price negated, high and low swapped), so one function serves both sides.
Kinds per variant: r = rule, real bid / ask; i = inverted side; c = control (the displacement candle alone); z / zc = rule / control at mid prices (no spread)."""
import sys, time, itertools, datetime as dt
import numpy as np, pandas as pd
from ema1000 import load_market, MARKETS, D0, DEV_END, VAL_END, YB, cstats, om_of
from ema1000_nocost import zero_spread
HOLD = 240; LB = 240; TBAR = 2.77   # Amendment 1: 36 tests, one-sided Bonferroni 0.1 / 36
AXES = (("ses", ("London", "NY")), ("win", (15, 60, 240)), ("x", ("drawn", "card", "S1")))
VARIANTS = [dict(id=i, **dict(zip([k for k, _ in AXES], v))) for i, v in enumerate(itertools.product(*[v for _, v in AXES]))]; assert len(VARIANTS) == 18
KINDS = ("r", "i", "c", "z", "zc")
EXIT = {"drawn": (1.0, 1.0), "card": (2.0, 1.0), "S1": (2.0, 2.0)}   # (stop, target) as multiples of D, the distance from the entry to the gap's near edge


def space(M, sg):
    """price arrays of one side's search space: sg = -1 shorts on the prices as they are, sg = +1 longs on the mirrored prices."""
    if sg < 0: o, h, l, c = M["mo"], M["mh"], M["ml"], M["mid"]
    else: o, h, l, c = -M["mo"], -M["ml"], -M["mh"], -M["mid"]
    a = pd.Series(h - l).rolling(14).mean().shift(1).to_numpy(); e = pd.Series(c).ewm(span=12, adjust=False).mean().to_numpy()
    key = M["dord"] * 1440 + M["hm"]; cons = np.r_[False, False, (key[2:] - key[:-2]) == 2]   # three consecutive minutes ending at k
    up = cons & np.r_[False, False, l[2:] > h[:-2]]; dn = cons & np.r_[False, False, h[2:] < l[:-2]]   # 'up' gaps lie below price after an up move (the targets of a short in this space)
    bd = o - c
    with np.errstate(invalid="ignore"):
        disp = (bd >= a) & ((c - l) <= 0.3 * bd) & (bd > (h - o) + (c - l)) & (o >= np.r_[np.nan, e[:-1]]) & (c < e)
    return dict(o=o, h=h, l=l, c=c, a=a, e=e, up=up, dn=dn, disp=np.nan_to_num(disp, nan=0).astype(bool), key=key)


def close_ok(S, j):
    """the trader's rule: the close of candle j may not lie in the untouched remainder of a 1-minute gap of the last LB candles (touches = candles after the gap's third candle and before j)."""
    h, l, cj = S["h"], S["l"], S["c"][j]; k0 = max(2, j - LB)
    ks = np.flatnonzero(S["up"][k0:j + 1] | S["dn"][k0:j + 1]) + k0
    for k in ks:
        lo, hi = (h[k - 2], l[k]) if S["up"][k] else (h[k], l[k - 2])
        if lo <= cj <= hi and not np.any((l[k + 1:j] <= cj) & (h[k + 1:j] >= cj)): return False
    return True


def target_edge(S, s, ent):
    """nearest WHOLE untouched 'up' gap below the entry (in this space) from the last LB candles, near edge >= 1 ATR(s) below the entry; returns (D, edge) or None."""
    h, l = S["h"], S["l"]; k0 = max(2, s - LB); best = None
    for k in np.flatnonzero(S["up"][k0:s + 1]) + k0:
        top = l[k]
        if k < s and l[k + 1:s + 1].min() <= top: continue      # some candle reached it: not whole
        if ent - top >= S["a"][s] and (best is None or top > best): best = top
    return None if best is None else (ent - best, best)


FUN = None   # stage counter for the dry run funnel
def _f(stage):
    if FUN is not None: FUN[stage] = FUN.get(stage, 0) + 1


def setup(M, S, d, sg, dy, om, win, ctrl):
    """the setup whose displacement candle is d, in the space of side sg; returns (dy, s, en, sg, D, tag) or None. tag: 0 = entry after d, 1 = after the continuation candle, 2 = idem with the EMA inside the fresh gap."""
    o, h, l, c, a, e, key = S["o"], S["h"], S["l"], S["c"], S["a"], S["e"], S["key"]; n = M["n"]; t = d - 1
    if t < 12 or d + 1 >= n or M["dord"][t - 11] != dy or key[d] - key[t - 11] != 12: return None   # d + 1 must exist (the entry after d); never more (the truncation test)
    bd = o[d] - c[d]; _f("displacement")
    if not ctrl:
        if not e[t - 1] < e[t - 11]: return None
        _f("trend"); at = a[t]
        for k in (t - 3, t - 2, t - 1):
            if not (c[k] <= e[k] and e[k] - c[k] <= at and abs(c[k] - o[k]) <= 0.5 * at): return None
        _f("coil"); bt = c[t] - o[t]
        if not (bt > 0 and o[t] <= e[t - 1] and c[t] > e[t] and h[t] - c[t] >= 0.5 * bt): return None
        _f("trap candle")
        if not (o[d] >= e[t] and c[d] < l[t]): return None
        _f("closes below the trap low"); s, tag = None, 0
        if close_ok(S, d): s = d
        else:
            q = d + 1
            if q + 1 < n and key[q] - key[d] == 1 and h[q] < e[q] and c[q] < c[d] and h[q] - c[d] <= 0.5 * bd and close_ok(S, q): s, tag = q, (2 if (h[q] < l[t] and h[q] <= e[q] <= l[t]) else 1)
        if s is None: return None
        _f("close rule (after d or c)")
    else: s, tag = d, 0
    en = s + 1
    if en >= n or key[en] - key[s] != 1 or M["dord"][en] != dy or not (om <= M["hm"][en] <= om + win): return None
    _f("entry in the window"); ent = M["bo"][en] if sg < 0 else -M["ao"][en]
    tg = target_edge(S, s, ent)
    if tg is not None: _f("whole untouched gap target")
    return None if tg is None else (int(dy), int(s), int(en), int(sg), float(tg[0]), tag)


def signals(M, SS, ses, win, ctrl):
    out = []; key = SS[-1]["key"]
    for dy in M["days"]:
        om = om_of(dy, ses); lo = np.searchsorted(key, dy * 1440 + om - 2, "left"); hi = np.searchsorted(key, dy * 1440 + om + win - 1, "right")
        if hi <= lo: continue
        cand = sorted(set((np.flatnonzero(SS[-1]["disp"][lo:hi]) + lo).tolist()) | set((np.flatnonzero(SS[1]["disp"][lo:hi]) + lo).tolist()))
        for d in cand:
            got = None
            for sg in (-1, 1):
                if SS[sg]["disp"][d]: got = got or setup(M, SS[sg], d, sg, dy, om, win, ctrl)
            if got: out.append(got); break
    return out


def sim(P, sigs, x, mirror=False, info=None):
    n = len(P["bc"]); bl, bh, ah, al, bc, ac, ao, bo = (P[k] for k in ("bl", "bh", "ah", "al", "bc", "ac", "ao", "bo")); fs, ft = EXIT[x]; dd, RR, TG = [], [], []
    for (dy, s, en, sg, D, tag) in sigs:
        ss = -sg if mirror else sg; ent = ao[en] if ss > 0 else bo[en]; sd, td = fs * D, ft * D; st = ent - ss * sd; tg = ent + ss * td; w = slice(en, min(en + HOLD, n))
        if ss > 0: hs, ht = bl[w] <= st, bh[w] >= tg
        else: hs, ht = ah[w] >= st, al[w] <= tg
        i_s = int(np.argmax(hs)) if hs.any() else 10 ** 9; i_t = int(np.argmax(ht)) if ht.any() else 10 ** 9
        if i_s <= i_t and i_s < 10 ** 9: R = -1.0
        elif i_t < 10 ** 9: R = td / sd
        else: j = min(en + HOLD, n) - 1; R = ((bc[j] - ent) if ss > 0 else (ent - ac[j])) / sd
        dd.append(dy); RR.append(R); TG.append(tag)
        if info is not None: info.append((dy, s, en, ss, ent, st, tg, D, tag, R))
    return np.array(dd, dtype=np.int32), np.array(RR, dtype=np.float32), np.array(TG, dtype=np.int8)


def run_market(m_name):
    t0 = time.time(); M = load_market(m_name); Z = zero_spread(M); SS = {-1: space(M, -1), 1: space(M, 1)}; out = {}; cache = {}
    for v in VARIANTS:
        for ck in ((v["ses"], v["win"], False), (v["ses"], v["win"], True)):
            if ck not in cache: cache[ck] = signals(M, SS, *ck)
        r = cache[(v["ses"], v["win"], False)]; c = cache[(v["ses"], v["win"], True)]
        out[(v["id"], "r")] = sim(M, r, v["x"]); out[(v["id"], "i")] = sim(M, r, v["x"], True); out[(v["id"], "c")] = sim(M, c, v["x"]); out[(v["id"], "z")] = sim(Z, r, v["x"]); out[(v["id"], "zc")] = sim(Z, c, v["x"])
    return m_name, out, time.time() - t0


def stats(d, R, mk, nm):
    dev = (d >= D0) & (d <= DEV_END); val = (d > DEV_END) & (d <= VAL_END); a, b = cstats(d[dev], R[dev]), cstats(d[val], R[val]); yrs = np.digitize(d, YB)
    ym = [R[dev & (yrs == y)].mean() if (dev & (yrs == y)).any() else np.nan for y in (1, 2, 3)]
    if dev.any() and nm > 1:
        tot = np.bincount(mk[dev], weights=R[dev], minlength=nm); best = int(np.argmax(tot)); nb = dev & (mk != best); wo = cstats(d[nb], R[nb])
    else: wo = dict(n=0, mean=np.nan, t=np.nan)
    cand = bool(a["n"] >= 300 and a["mean"] >= 0.03 and a["t"] >= TBAR and b["mean"] > 0 and b["t"] >= 1.65 and all(y > 0 for y in ym) and wo["mean"] > 0 and wo["t"] >= 2.0)
    return dict(dev_n=a["n"], dev_R=a["mean"], dev_t=a["t"], val_n=b["n"], val_R=b["mean"], val_t=b["t"], y22=ym[0], y23=ym[1], y24=ym[2], nb_R=wo["mean"], nb_t=wo["t"], cand=cand)


def full(workers):
    from multiprocessing import Pool
    t0 = time.time(); res = {}; print("start", time.strftime("%H:%M:%S"), "workers", workers, flush=True)
    with Pool(workers) as p:
        for m_, r, sec in p.imap_unordered(run_market, MARKETS): res[m_] = r; print("  %-7s done in %5.0fs (%d/%d)" % (m_, sec, len(res), len(MARKETS)), flush=True)
    ms = sorted(res); nm = len(ms); rows = []; permk = {k: [] for k in ("r", "z")}; tagrows = []
    for v in VARIANTS:
        row = dict(**v)
        for kd in KINDS:
            parts = [res[m_][(v["id"], kd)] for m_ in ms]
            d = np.concatenate([p_[0] for p_ in parts]).astype(np.int64); R = np.concatenate([p_[1] for p_ in parts]).astype(float); tg = np.concatenate([p_[2] for p_ in parts]); mk = np.concatenate([np.full(len(p_[0]), i) for i, p_ in enumerate(parts)])
            for a_, b_ in stats(d, R, mk, nm).items(): row["%s_%s" % (kd, a_)] = b_
            if kd in ("r", "z"):
                dev = (d >= D0) & (d <= DEV_END); permk[kd].append([R[dev & (mk == i)].mean() if (dev & (mk == i)).sum() >= 20 else np.nan for i in range(nm)])
                g = mk == ms.index("XAUUSD"); gs = stats(d[g], R[g], mk[g], 1); gdev = cstats(d[g & dev], R[g & dev])
                row["%s_XAU_dev_n" % kd], row["%s_XAU_dev_R" % kd], row["%s_XAU_dev_t" % kd], row["%s_XAU_val_n" % kd], row["%s_XAU_val_R" % kd] = gdev["n"], gdev["mean"], gdev["t"], gs["val_n"], gs["val_R"]
                if kd == "r":
                    row["XAU_cand"] = bool(gdev["n"] >= 60 and gdev["mean"] >= 0.10 and gdev["t"] >= TBAR and gs["val_R"] > 0)
                    for tgv, nmv in ((0, "after d"), (1, "after c"), (2, "after c, EMA in the fresh gap")):
                        sel = dev & (tg == tgv); tagrows.append(dict(id=v["id"], tag=nmv, n=int(sel.sum()), R=R[sel].mean() if sel.any() else np.nan, n_xau=int((sel & g).sum()), R_xau=R[sel & g].mean() if (sel & g).any() else np.nan))
        rows.append(row)
    T = pd.DataFrame(rows); T.to_csv("TRAP12_TRIALS.csv", index=False); mrows = []
    for kd in ("r", "z"):
        A = np.array(permk[kd], dtype=float)
        for i, m_ in enumerate(ms): mrows.append(dict(kind=kd, market=m_, med_dev_R=np.nanmedian(A[:, i]) if np.isfinite(A[:, i]).any() else np.nan, best_dev_R=np.nanmax(A[:, i]) if np.isfinite(A[:, i]).any() else np.nan, n_pos=int((A[:, i] > 0).sum())))
    MK = pd.DataFrame(mrows); MK.to_csv("TRAP12_MARKETS.csv", index=False); TG = pd.DataFrame(tagrows); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print("\nfinished %s in %.1f min | variants %d | POOLED CANDIDATES (all bars, real bid / ask, DEV t >= %.2f): %d | XAUUSD CANDIDATES: %d" % (time.strftime("%H:%M:%S"), (time.time() - t0) / 60, len(T), TBAR, int(T.r_cand.sum()), int(T.XAU_cand.sum())))
    print("\nRULE, real bid / ask, DEV 2022-24 pooled over 46 markets (%d variants): trades per variant median %d (min %d max %d) | mean R median %+.4f best %+.4f | share > 0: %.0f%% | t: min %.2f median %.2f max %.2f | VAL 2025 mean R median %+.4f, share > 0 %.0f%%" % (
        len(T), T.r_dev_n.median(), T.r_dev_n.min(), T.r_dev_n.max(), T.r_dev_R.median(), T.r_dev_R.max(), 100 * (T.r_dev_R > 0).mean(), T.r_dev_t.min(), T.r_dev_t.median(), T.r_dev_t.max(), T.r_val_R.median(), 100 * (T.r_val_R > 0).mean()))
    print("INVERTED side, real: DEV mean R median %+.4f best %+.4f | direction skill (rule - inverted) / 2: median %+.4f, share of variants > 0: %.0f%%" % (T.i_dev_R.median(), T.i_dev_R.max(), ((T.r_dev_R - T.i_dev_R) / 2).median(), 100 * ((T.r_dev_R - T.i_dev_R) > 0).mean()))
    print("CONTROL (displacement candle alone), real: DEV trades median %d, mean R median %+.4f best %+.4f | rule minus control (what trend + coil + trap + close rule add): median %+.4f, share > 0: %.0f%%" % (T.c_dev_n.median(), T.c_dev_R.median(), T.c_dev_R.max(), (T.r_dev_R - T.c_dev_R).median(), 100 * ((T.r_dev_R - T.c_dev_R) > 0).mean()))
    print("CEILING, no spread: rule DEV mean R median %+.4f best %+.4f (t max %+.2f) | control %+.4f -> the spread costs %+.4f R a trade at the median" % (T.z_dev_R.median(), T.z_dev_R.max(), T.z_dev_t.max(), T.zc_dev_R.median(), (T.z_dev_R - T.r_dev_R).median()))
    for ax in ("ses", "win", "x"): print("median DEV mean R (rule, real) by %s:" % ax, T.groupby(ax).r_dev_R.median().round(4).to_dict())
    print("\nall %d variants (rule, real; pooled and XAUUSD):" % len(T))
    print(T[["id", "ses", "win", "x", "r_dev_n", "r_dev_R", "r_dev_t", "r_val_n", "r_val_R", "r_val_t", "r_y22", "r_y23", "r_y24", "r_nb_R", "r_nb_t", "i_dev_R", "c_dev_R", "z_dev_R", "r_XAU_dev_n", "r_XAU_dev_R", "r_XAU_dev_t", "r_XAU_val_n", "r_XAU_val_R", "z_XAU_dev_R"]].round(3).to_string(index=False))
    print("\nby entry type (rule, real, DEV), per variant:"); print(TG.round(3).to_string(index=False))
    for kd in ("r", "z"):
        g = MK[MK.kind == kd].sort_values("med_dev_R", ascending=False); print("\nper market, %s: median DEV mean R over the variants (markets with >= 20 DEV trades), 6 best and 4 worst" % ("rule real" if kd == "r" else "rule at mid (ceiling)")); print(pd.concat([g.head(6), g.tail(4)]).round(4).to_string(index=False)); print("  markets with a positive median:", list(g.market[g.med_dev_R > 0]) or "none")


def csv_market(path, spread=0.55, utc_to_server=3 * 3600):
    """the OANDA 1m bid bars of 22 Oct as a market dict (bid = the chart, ask = bid + spread), server clock = UTC + 3 h in October."""
    B = pd.read_csv(path); t = B.time_utc.to_numpy() + utc_to_server; M = {}
    for side, add in (("b", 0.0), ("a", spread)):
        for col, nm in (("open", "o"), ("high", "h"), ("low", "l"), ("close", "c")): M[side + nm] = B[col].to_numpy() + add
    M["mid"] = (M["bc"] + M["ac"]) / 2; M["mo"] = (M["bo"] + M["ao"]) / 2; M["mh"] = (M["bh"] + M["ah"]) / 2; M["ml"] = (M["bl"] + M["al"]) / 2
    M["dord"] = t // 86400 + dt.date(1970, 1, 1).toordinal(); M["hm"] = (t % 86400) // 60; M["n"] = len(B); M["days"] = np.unique(M["dord"]); return M


def dry():
    print("variants: %d (session %s x window %s x exit %s)" % (len(VARIANTS), AXES[0][1], AXES[1][1], AXES[2][1]))
    rng = np.random.default_rng(12); print("\n(1) truncation test: data after the entry minute cut, same signal (4 markets x 2 windows x 2 sessions, up to 5 setups each):"); bad = tested = 0
    for mn in ("XAUUSD", "EURUSD", "NSDQ", "BTCUSD"):
        M = load_market(mn); SS = {-1: space(M, -1), 1: space(M, 1)}
        for ses in ("London", "NY"):
            for win in (15, 60):
                sg = signals(M, SS, ses, win, False)
                for q in (rng.choice(len(sg), min(5, len(sg)), replace=False) if sg else []):
                    x = sg[q]; M2 = load_market(mn, upto=x[2], med=M["med"]); S2 = {-1: space(M2, -1), 1: space(M2, 1)}
                    M2["days"] = np.array([x[0]]); y = signals(M2, S2, ses, win, False)
                    tested += 1; bad += not (y and y[0][:4] == x[:4] and abs(y[0][4] - x[4]) < 1e-9)
    print("  %d setups recomputed with the future cut, %d mismatches" % (tested, bad))
    print("\n(2) hand check: the 22 Oct NY session on his OANDA bars (MANUAL_22OCT_NY_BARS.csv, ask = bid + 0.55):")
    M = csv_market("MANUAL_22OCT_NY_BARS.csv"); SS = {-1: space(M, -1), 1: space(M, 1)}
    for win in (15, 60):
        sg = signals(M, SS, "NY", win, False); info = []
        for x in ("drawn",): sim(M, sg, x, info=info)
        for (dy, s, en, ss, ent, st, tg, D, tag, R) in info:
            hs = int(M["hm"][s]) - 120; he = int(M["hm"][en]) - 120
            print("  W %d: side %+d, signal candle %02d:%02d local (%s), entry %02d:%02d at %.3f, D %.3f -> gap edge %.3f; drawn stop %.3f target %.3f" % (win, ss, hs // 60, hs % 60, ("after the displacement", "after the continuation", "after the continuation, EMA inside the fresh gap")[tag], he // 60, he % 60, ent, D, ent + ss * D, st, tg))
        if not sg: print("  W %d: no setup" % win)
    S_ = SS[-1]; j = [x for x in signals(M, SS, "NY", 15, False)][0]; ent = M["bo"][j[2]]; h_, l_ = S_["h"], S_["l"]
    print("  whole untouched bullish gaps below the entry at that moment (top edge, distance, size):", [(round(l_[k], 3), round(ent - l_[k], 3), round(l_[k] - h_[k - 2], 3), "%02d:%02d" % divmod(int(M["hm"][k]) - 120, 60)) for k in np.flatnonzero(S_["up"][max(2, j[1] - LB):j[1] + 1]) + max(2, j[1] - LB) if (k == j[1] or l_[k + 1:j[1] + 1].min() > l_[k]) and l_[k] < ent])
    c = signals(M, SS, "NY", 15, True); print("  control (displacement alone), W 15:", [("%02d:%02d" % divmod(int(M["hm"][x[1]]) - 120, 60), x[3], round(x[4], 3)) for x in c])
    print("\n(3) setups per year and entry type (rule; no results):")
    M = load_market("XAUUSD"); SS = {-1: space(M, -1), 1: space(M, 1)}
    for ses in ("London", "NY"):
        for win in (15, 60):
            sg = signals(M, SS, ses, win, False); yr = pd.Series([dt.date.fromordinal(x[0]).year for x in sg]).value_counts().sort_index().to_dict(); tg = pd.Series([x[5] for x in sg]).value_counts().sort_index().to_dict()
            cc = signals(M, SS, ses, win, True)
            print("  XAUUSD %-6s W %2d: %3d setups %s | entry type %s | shorts %d longs %d | control %d" % (ses, win, len(sg), yr, tg, sum(1 for x in sg if x[3] < 0), sum(1 for x in sg if x[3] > 0), len(cc)))
    global FUN
    for ses in ("London", "NY"):
        for win in (60, 240):
            FUN = {}; signals(M, SS, ses, win, False); print("  funnel XAUUSD %s W %d (candidate displacement candles, both sides, every day; each line = still alive after that condition):" % (ses, win), FUN)
    FUN = None
    tot = {}
    for mn in MARKETS[::6]:
        M2 = load_market(mn); S2 = {-1: space(M2, -1), 1: space(M2, 1)}
        for ses in ("London", "NY"):
            for win in (15, 60): tot[(ses, win)] = tot.get((ses, win), 0) + sum(1 for x in signals(M2, S2, ses, win, False) if x[0] <= DEV_END)
    print("  DEV setups on every 6th market (%d markets: %s): %s -> pooled 46 markets about x%.1f" % (len(MARKETS[::6]), ",".join(MARKETS[::6]), tot, 46 / len(MARKETS[::6])))
    f = pd.read_csv("FXREPLAY_TRADES_2026-10-20.csv"); f["t"] = pd.to_datetime(f.chart_entry); f = f[f.t < "2026-01-01"].copy(); f["day"] = f.t.dt.date; f["hm"] = f.t.dt.hour * 60 + f.t.dt.minute
    print("\n(4) coverage of his %d April-May 2025 recorded trades (W 60, the session he traded):" % len(f)); fires = same = 0
    for ses, g in (("London", f[f.hm < 12 * 60]), ("NY", f[f.hm >= 12 * 60])):
        sg = {x[0]: x for x in signals(M, SS, ses, 60, False)}
        for _, r in g.iterrows():
            x = sg.get(r.day.toordinal())
            if x is None: continue
            fires += 1; same += (x[3] > 0) == (r.side == "Buy"); hs = int(M["hm"][x[1]]) - 120
            print("   %s %s his %s at %02d:%02d, rule side %+d signal %02d:%02d" % (r.day, ses, r.side, r.hm // 60, r.hm % 60, x[3], hs // 60, hs % 60))
    print("  the rule fires on %d of his %d days, on his side on %d" % (fires, len(f), same))


if __name__ == "__main__":
    if "--dry-run" in sys.argv: dry()
    elif "--run" in sys.argv: full(int(sys.argv[sys.argv.index("--run") + 1]) if len(sys.argv) > sys.argv.index("--run") + 1 else 8)
    else: print(__doc__)
