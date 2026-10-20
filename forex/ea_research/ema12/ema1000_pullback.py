"""PREREG_EMA1000_PULLBACK.md: the 1,000 EMA1000 variants entered on a PULLBACK limit order (depth 0.25 / 0.5 / 1.0 ATR or a retest of the EMA behind the signal candle's close, live 15 minutes), zero spread (Z) and real bid / ask (Q), rule side (r) and inverted side (i). Nothing after 2025-12-31 is loaded.
python ema1000_pullback.py --dry-run     engine checks (fill invariants, truncation test, hand check, fill rates)
python ema1000_pullback.py --run [W]     the run on W worker processes (default 8) -> EMA1000_PULLBACK_TRIALS.csv, EMA1000_PULLBACK_MARKETS.csv, EMA1000_PULLBACK_OUTPUT.txt"""
import sys, time
import numpy as np, pandas as pd
from ema1000 import *
from ema1000 import om_of
from ema1000_nocost import zero_spread
WAIT = 15; BIG = 10 ** 9; TBAR = 4.19; DEPTHS = ("P25", "P50", "P100", "PEMA"); FR = {"P25": 0.25, "P50": 0.5, "P100": 1.0}; KEYS = [d + m + s for d in DEPTHS for m in ("Z", "Q") for s in ("r", "i")]
def pull_signals(M, B, ok, side, ses, win, tgt, depth, ema):
    rr, ii = [], []
    for dy in M["days"]:
        om = om_of(dy, ses); lo = np.searchsorted(B["key"], dy * 1440 + om, "left"); hi = np.searchsorted(B["key"], dy * 1440 + om + win - 1, "right")
        for t in np.flatnonzero(ok[lo:hi]) + lo:
            end = B["end"][t]
            if end + 1 >= M["n"] or M["dord"][end + 1] != dy or M["hm"][end + 1] - M["hm"][end] > 2: break
            s = int(side[t]); c0 = float(B["c"][t]); dep = abs(c0 - float(ema[t])) if depth == "PEMA" else FR[depth] * float(B["atrp"][t])
            if not dep > 0: continue
            Lr = c0 - s * dep; d = target(B, t, s, Lr, tgt)
            if d is None or not d > 0: continue
            rr.append((dy, int(end), s, Lr, d, t)); ii.append((dy, int(end), s, c0 + s * dep, d, t)); break
    return rr, ii
def limit_sim(M, sig, stop, inv, wait=WAIT, max_bars=60, info=None):
    n = M["n"]; al, ao, bh, bo, bl, ah, bc, ac, hm, dord = (M[k] for k in ("al", "ao", "bh", "bo", "bl", "ah", "bc", "ac", "hm", "dord")); R = np.full(len(sig), np.nan, dtype=np.float32)
    for i, (dy, end, s, c, d, t) in enumerate(sig):
        ss = -s if inv else s; js = np.arange(end + 1, min(end + 1 + wait, n)); js = js[(dord[js] == dy) & (hm[js] - hm[end] <= wait)]
        if len(js) == 0: continue
        hit = (al[js] <= c) if ss > 0 else (bh[js] >= c)
        if not hit.any(): continue
        j = int(js[int(np.argmax(hit))]); f = min(ao[j], c) if ss > 0 else max(bo[j], c)
        x = slice(j, min(j + max_bars, n)); tp = c + ss * d; sl = c - ss * stop * d
        if ss > 0: hs, ht = bl[x] <= sl, bh[x] >= tp
        else: hs, ht = ah[x] >= sl, al[x] <= tp
        ht = ht.copy(); ht[0] = False
        i_s = int(np.argmax(hs)) if hs.any() else BIG; i_t = int(np.argmax(ht)) if ht.any() else BIG
        if i_s <= i_t and i_s < BIG: ex = sl
        elif i_t < BIG: ex = tp
        else: jj = min(j + max_bars, n) - 1; ex = bc[jj] if ss > 0 else ac[jj]
        R[i] = ss * (ex - f) / (stop * d)
        if info is not None: info.append((i, j, f, c, ss, tp, sl, float(R[i])))
    return R
def run_market_pb(m):
    t0 = time.time(); M = load_market(m); Z = zero_spread(M); bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}; cc = {}; emas = {}; sgs = {}; sims = {}; out = {}
    for v in VARIANTS:
        ck = (v["tf"], v["ema"], v["body"], v["trend"])
        if ck not in cc: cc[ck] = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"])
        ek = (v["tf"], v["ema"])
        if ek not in emas: emas[ek] = pd.Series(bars[v["tf"]]["c"]).ewm(span=v["ema"], adjust=False).mean().to_numpy()
        sk = (v["ses"], v["win"], v["tgt"]) + ck; r = {}
        for dp in DEPTHS:
            k1 = (sk, dp)
            if k1 not in sgs: sgs[k1] = pull_signals(M, bars[v["tf"]], cc[ck][0], cc[ck][1], v["ses"], v["win"], v["tgt"], dp, emas[ek])
            sr, si = sgs[k1]; k2 = (k1, v["stop"])
            if k2 not in sims: sims[k2] = {dp + "Z" + "r": limit_sim(Z, sr, v["stop"], False), dp + "Z" + "i": limit_sim(Z, si, v["stop"], True), dp + "Q" + "r": limit_sim(M, sr, v["stop"], False), dp + "Q" + "i": limit_sim(M, si, v["stop"], True)}
            dl = (np.array([x[0] for x in sr], dtype=np.int64) - D0).astype(np.int16)
            for k, R in sims[k2].items(): r[k] = (dl, R.astype(np.float32))
        out[v["id"]] = r
    return m, out, time.time() - t0
def cand_flag(a, b, ym, nb):
    return bool(a["n"] >= 3000 and a["mean"] >= 0.03 and a["t"] >= TBAR and b["mean"] > 0 and b["t"] >= 1.65 and all(y > 0 for y in ym) and nb["mean"] > 0 and nb["t"] >= 2.5)
def pooled_stats(d, R, mk, nm):
    f = ~np.isnan(R); dev = (d >= D0) & (d <= DEV_END); val = (d > DEV_END) & (d <= VAL_END); a, b = cstats(d[dev & f], R[dev & f]), cstats(d[val & f], R[val & f]); yrs = np.digitize(d, YB)
    ym = [R[dev & f & (yrs == y)].mean() if (dev & f & (yrs == y)).any() else np.nan for y in (1, 2, 3)]; x = dev & f
    tot = np.bincount(mk[x], weights=R[x], minlength=nm); best = int(np.argmax(tot)); nb = x & (mk != best); wo = cstats(d[nb], R[nb])
    cnt = np.bincount(mk[x], minlength=nm); mean_m = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    return dict(dev_n=a["n"], dev_sig=int(dev.sum()), dev_R=a["mean"], dev_t=a["t"], dev_Rsig=float(np.nansum(R[dev]) / max(dev.sum(), 1)), val_R=b["mean"], val_t=b["t"], y22=ym[0], y23=ym[1], y24=ym[2], nb_R=wo["mean"], nb_t=wo["t"], cand=cand_flag(a, b, ym, wo)), mean_m
NAMES = {"Z": "no spread", "Q": "real bid/ask"}; DN = {"P25": "pullback 0.25 ATR", "P50": "pullback 0.5 ATR", "P100": "pullback 1.0 ATR", "PEMA": "retest of the EMA"}
def full(workers):
    from multiprocessing import Pool
    t0 = time.time(); res = {}; print("start", time.strftime("%H:%M:%S"), "workers", workers, flush=True)
    with Pool(workers) as p:
        for m, r, sec in p.imap_unordered(run_market_pb, MARKETS): res[m] = r; print("  %-7s done in %5.0fs (%d/%d)" % (m, sec, len(res), len(MARKETS)), flush=True)
    ms = sorted(res); nm = len(ms); rows = []; per_market = {k: [] for k in KEYS}
    for v in VARIANTS:
        row = dict(**v)
        for k in KEYS:
            d = np.concatenate([res[m][v["id"]][k][0] for m in ms]).astype(np.int64) + D0; R = np.concatenate([res[m][v["id"]][k][1] for m in ms]).astype(float); mk = np.concatenate([np.full(len(res[m][v["id"]][k][0]), i) for i, m in enumerate(ms)])
            st, mean_m = pooled_stats(d, R, mk, nm); per_market[k].append(mean_m)
            for a, b in st.items(): row["%s_%s" % (k, a)] = b
        rows.append(row)
    T = pd.DataFrame(rows); T.to_csv("EMA1000_PULLBACK_TRIALS.csv", index=False); mrows = []
    for k in KEYS:
        A = np.array(per_market[k])
        for i, m in enumerate(ms): mrows.append(dict(model=k, market=m, med_dev_R=np.nanmedian(A[:, i]), best_dev_R=np.nanmax(A[:, i]), n_pos=int((A[:, i] > 0).sum())))
    MK = pd.DataFrame(mrows); MK.to_csv("EMA1000_PULLBACK_MARKETS.csv", index=False)
    O = pd.read_csv("EMA1000_TRIALS.csv"); N = pd.read_csv("EMA1000_NOCOST_TRIALS.csv"); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("\nfinished %s in %.0f min | variants %d | candidates need DEV t >= %.2f (Q only; Z is a ceiling that gives no candidate)" % (time.strftime("%H:%M:%S"), (time.time() - t0) / 60, len(T), TBAR))
    print("\nreference, median DEV mean R per trade: original (real spread, market entry) %+.4f | no spread market entry (NOCOST Z) rule %+.4f inverted %+.4f | real-quote limit at the signal close (NOCOST Q) rule %+.4f inverted %+.4f (fill %.0f%%)" % (O.dev_R.median(), N.Zr_dev_R.median(), N.Zi_dev_R.median(), N.Qr_dev_R.median(), N.Qi_dev_R.median(), 100 * (N.Qr_dev_n / N.Qr_dev_sig).median()))
    print("\nDEV 2022-24 / VAL 2025, pooled over 46 markets, median over the 1,000 variants; R per FILLED trade ('per signal' counts an unfilled order as 0)")
    for dp in DEPTHS:
        for mo in ("Z", "Q"):
            for sd in ("r", "i"):
                k = dp + mo + sd
                print("%-18s %-13s %-8s fill %3.0f%% | DEV R median %+.4f best %+.4f | per signal %+.4f | >0: %3.0f%% | max t %+.2f | VAL R median %+.4f best %+.4f >0: %3.0f%% | candidates %d" % (DN[dp], NAMES[mo], "rule" if sd == "r" else "inverted", 100 * (T[k + "_dev_n"] / T[k + "_dev_sig"]).median(), T[k + "_dev_R"].median(), T[k + "_dev_R"].max(), T[k + "_dev_Rsig"].median(), 100 * (T[k + "_dev_R"] > 0).mean(), T[k + "_dev_t"].max(), T[k + "_val_R"].median(), T[k + "_val_R"].max(), 100 * (T[k + "_val_R"] > 0).mean(), int(T[k + "_cand"].sum())))
    print("\ndirection skill (rule minus inverted)/2, DEV, median over variants, share of variants above 0:")
    for dp in DEPTHS:
        for mo in ("Z", "Q"): sk = (T[dp + mo + "r_dev_R"] - T[dp + mo + "i_dev_R"]) / 2; print("  %-18s %-13s %+.4f R  %3.0f%%" % (DN[dp], NAMES[mo], sk.median(), 100 * (sk > 0).mean()))
    for dp in DEPTHS:
        for mo, nr in (("Q", 5), ("Z", 3)):
            for sd in ("r", "i"):
                k = dp + mo + sd; print("\ntop %d variants by DEV t, %s, %s, %s:" % (nr, DN[dp], NAMES[mo], "rule" if sd == "r" else "inverted")); print(T.sort_values(k + "_dev_t", ascending=False).head(nr)[["id", "ema", "tf", "body", "win", "tgt", "stop", "ses", "trend", k + "_dev_n", k + "_dev_R", k + "_dev_t", k + "_val_R", k + "_val_t", k + "_y22", k + "_y23", k + "_y24", k + "_nb_t"]].round(3).to_string(index=False))
    for dp in DEPTHS:
        for mo in ("Q", "Z"):
            k = dp + mo + "r"; g = MK[MK.model == k].sort_values("med_dev_R", ascending=False); print("\nper market, %s, %s, rule: median DEV mean R over the variants, 4 best and 3 worst" % (DN[dp], NAMES[mo])); print(pd.concat([g.head(4), g.tail(3)]).round(4).to_string(index=False)); print("  markets with a positive median:", list(g.market[g.med_dev_R > 0]) or "none")
def dry():
    print("(1) fill invariants (fill never worse than the limit; fill minute 1..%d after the signal candle; the touch happened; rule limit behind and inverted limit ahead of the close), 25 random variants x 3 markets x 4 depths x Z / Q x both sides:" % WAIT)
    rng = np.random.default_rng(11); bad = tot = 0; fr = {}
    for m in ("XAUUSD", "EURUSD", "NSDQ"):
        M = load_market(m); Z = zero_spread(M); bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}
        for v in [VARIANTS[i] for i in rng.choice(len(VARIANTS), 25, replace=False)]:
            ok, side = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"]); ema = pd.Series(bars[v["tf"]]["c"]).ewm(span=v["ema"], adjust=False).mean().to_numpy()
            for dp in DEPTHS:
                sr, si = pull_signals(M, bars[v["tf"]], ok, side, v["ses"], v["win"], v["tgt"], dp, ema)
                bad += sum(not (x[2] * (y[3] - x[3]) > 0 and x[:3] == y[:3] and x[4] == y[4]) for x, y in zip(sr, si)); tot += len(sr)
                for MM in (Z, M):
                    for inv, sg in ((False, sr), (True, si)):
                        info = []; limit_sim(MM, sg, v["stop"], inv, info=info)
                        for (i, j, f, c, ss, tp, sl, Rv) in info:
                            end = sg[i][1]; touch = (MM["al"][j] <= c) if ss > 0 else (MM["bh"][j] >= c); bad += not ((f <= c + 1e-9 if ss > 0 else f >= c - 1e-9) and 1 <= j - end <= WAIT and touch); tot += 1
    print("  %d checks (signal pairs + fills), %d violations" % (tot, bad))
    print("\n(2) truncation test: data after the fill minute cut, signal and fill identical (all depths, Z and Q, both sides):"); bad = tested = 0
    for m in ("XAUUSD", "EURUSD", "BTCUSD", "NIKKEI"):
        M = load_market(m); Z = zero_spread(M)
        for v in [VARIANTS[i] for i in rng.choice(len(VARIANTS), 4, replace=False)]:
            bars = make_bars(M, v["tf"]); ok, side = cond(bars, v["ema"], v["body"], v["trend"]); ema = pd.Series(bars["c"]).ewm(span=v["ema"], adjust=False).mean().to_numpy()
            for dp in DEPTHS:
                sr, si = pull_signals(M, bars, ok, side, v["ses"], v["win"], v["tgt"], dp, ema)
                for name, MM in (("Z", Z), ("Q", M)):
                    for inv, sg in ((False, sr), (True, si)):
                        info = []; limit_sim(MM, sg, v["stop"], inv, info=info)
                        for q in (rng.choice(len(info), min(1, len(info)), replace=False) if info else []):
                            i, j, f, c, ss, tp, sl, Rv = info[q]; M2 = load_market(m, upto=j, med=M["med"]); MM2 = zero_spread(M2) if name == "Z" else M2; b2 = make_bars(M2, v["tf"]); ok2, side2 = cond(b2, v["ema"], v["body"], v["trend"]); ema2 = pd.Series(b2["c"]).ewm(span=v["ema"], adjust=False).mean().to_numpy()
                            r2, i2 = pull_signals(M2, b2, ok2, side2, v["ses"], v["win"], v["tgt"], dp, ema2); s2 = [z for z in (i2 if inv else r2) if z[0] == sg[i][0]]; info2 = []
                            if s2: limit_sim(MM2, s2, v["stop"], inv, info=info2)
                            tested += 1; bad += not (s2 and s2[0][1] == sg[i][1] and abs(s2[0][3] - sg[i][3]) < 1e-9 and abs(s2[0][4] - sg[i][4]) < 1e-9 and info2 and info2[0][1] == j and abs(info2[0][2] - f) < 1e-9)
    print("  %d fills recomputed with the future cut, %d mismatches" % (tested, bad))
    print("\n(3) hand check, XAUUSD London baseline (EMA 12, 1 min, wick_atr, 15 min, K1, stop 2), pullback 0.5 ATR, no spread, rule side:")
    M = load_market("XAUUSD"); Z = zero_spread(M); B = make_bars(M, 1); ok, side = cond(B, 12, "wick_atr", "none"); ema = pd.Series(B["c"]).ewm(span=12, adjust=False).mean().to_numpy(); sr, si = pull_signals(M, B, ok, side, "London", 15, "K1", "P50", ema); info = []; limit_sim(Z, sr, 2.0, False, info=info)
    for (i, j, f, c, ss, tp, sl, Rv) in info[60:63]:
        dy, end, s, L0, d, t = sr[i]; print("  %s signal candle closes %02d:%02d mid close %.2f ATR %.2f side %+d | limit %.2f | fill minute %02d:%02d mid O %.2f H %.2f L %.2f C %.2f | fill %.2f target %.2f stop %.2f (d %.2f) -> R %+.3f" % (dt.date.fromordinal(int(dy)), M["hm"][end] // 60, M["hm"][end] % 60, B["c"][t], B["atrp"][t], s, L0, M["hm"][j] // 60, M["hm"][j] % 60, Z["bo"][j], Z["bh"][j], Z["bl"][j], Z["bc"][j], f, tp, sl, d, Rv))
    print("\n(4) fill rates and DEV mean R, baseline variant (London, K1, stop 2), rule / inverted:")
    for m in ("XAUUSD", "EURUSD", "NSDQ", "GBPUSD"):
        M = load_market(m); Z = zero_spread(M); B = make_bars(M, 1); ok, side = cond(B, 12, "wick_atr", "none"); ema = pd.Series(B["c"]).ewm(span=12, adjust=False).mean().to_numpy()
        for dp in DEPTHS:
            sr, si = pull_signals(M, B, ok, side, "London", 15, "K1", dp, ema); dd = np.array([x[0] for x in sr]); dev = (dd >= D0) & (dd <= DEV_END); line = "  %-7s %-5s signals(DEV) %4d" % (m, dp, dev.sum())
            for name, MM in (("Z", Z), ("Q", M)):
                for inv, sg in ((False, sr), (True, si)):
                    R = limit_sim(MM, sg, 2.0, inv); f = ~np.isnan(R) & dev; line += " | %s%s fill %3.0f%% R %+.3f" % (name, "i" if inv else "r", 100 * f.sum() / max(dev.sum(), 1), R[f].mean() if f.any() else np.nan)
            print(line)
if __name__ == "__main__":
    if "--dry-run" in sys.argv: dry()
    elif "--run" in sys.argv: full(int(sys.argv[sys.argv.index("--run") + 1]) if len(sys.argv) > sys.argv.index("--run") + 1 else 8)
    else: print(__doc__)
