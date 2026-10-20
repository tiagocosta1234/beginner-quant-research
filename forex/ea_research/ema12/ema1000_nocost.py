"""PREREG_EMA1000_NOCOST.md: the 1,000 EMA1000 variants with NO SPREAD (Z: market entry at the mid), ZERO-SPREAD LIMIT entries (L) and real-quote LIMIT entries (Q), each for the rule side (r) and the inverted side (i). Same data limits as EMA1000 (nothing after 2025-12-31 is loaded).
python ema1000_nocost.py --dry-run     engine checks (market path reproduces EMA1000_MARKETS.csv, fill invariants, truncation test, hand check, fill rates)
python ema1000_nocost.py --run [W]     the run on W worker processes (default 8) -> EMA1000_NOCOST_TRIALS.csv, EMA1000_NOCOST_MARKETS.csv, EMA1000_NOCOST_OUTPUT.txt"""
import sys, time
import numpy as np, pandas as pd
from ema1000 import *
from ema1000 import om_of
WAIT = 5; BIG = 10 ** 9; MODELS = ("Zr", "Zi", "Lr", "Li", "Qr", "Qi"); TBAR = 3.99
def zero_spread(M):
    Z = dict(M); Z["bo"] = Z["ao"] = M["mo"]; Z["bh"] = Z["ah"] = M["mh"]; Z["bl"] = Z["al"] = M["ml"]; Z["bc"] = Z["ac"] = M["mid"]; return Z
def market_sims(M, sig, stop):
    inv = [(dy, e, -sd, (M["bo"][e] if sd > 0 else M["ao"][e]), d, t) for (dy, e, sd, entry, d, t) in sig]
    return simulate(M, sig, stop), simulate(M, inv, stop)
def limit_signals(M, B, ok, side, ses, win, tgt):
    out = []
    for dy in M["days"]:
        om = om_of(dy, ses); lo = np.searchsorted(B["key"], dy * 1440 + om, "left"); hi = np.searchsorted(B["key"], dy * 1440 + om + win - 1, "right")
        for t in np.flatnonzero(ok[lo:hi]) + lo:
            end = B["end"][t]
            if end + 1 >= M["n"] or M["dord"][end + 1] != dy or M["hm"][end + 1] - M["hm"][end] > 2: break
            s = int(side[t]); c = B["c"][t]; d = target(B, t, s, c, tgt)
            if d is None or not d > 0: continue
            out.append((dy, int(end), s, float(c), d, t)); break
    return out
def limit_sim(M, sig, stop, inv, max_bars=60, info=None):
    n = M["n"]; al, ao, bh, bo, bl, ah, bc, ac, hm, dord = (M[k] for k in ("al", "ao", "bh", "bo", "bl", "ah", "bc", "ac", "hm", "dord")); R = np.full(len(sig), np.nan, dtype=np.float32)
    for i, (dy, end, s, c, d, t) in enumerate(sig):
        ss = -s if inv else s; js = np.arange(end + 1, min(end + 1 + WAIT, n)); js = js[(dord[js] == dy) & (hm[js] - hm[end] <= WAIT)]
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
def run_market_nc(m):
    t0 = time.time(); M = load_market(m); Z = zero_spread(M); bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}; cc = {}; sgm = {}; sgl = {}; sims = {}; out = {}
    for v in VARIANTS:
        ck = (v["tf"], v["ema"], v["body"], v["trend"])
        if ck not in cc: cc[ck] = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"])
        sk = (v["ses"], v["win"], v["tgt"]) + ck
        if sk not in sgm: sgm[sk] = signals(Z, bars[v["tf"]], cc[ck][0], cc[ck][1], v["ses"], v["win"], v["tgt"]); sgl[sk] = limit_signals(M, bars[v["tf"]], cc[ck][0], cc[ck][1], v["ses"], v["win"], v["tgt"])
        k2 = (sk, v["stop"])
        if k2 not in sims:
            zr, zi = market_sims(Z, sgm[sk], v["stop"]); sims[k2] = dict(Zr=zr, Zi=zi, Lr=limit_sim(Z, sgl[sk], v["stop"], False), Li=limit_sim(Z, sgl[sk], v["stop"], True), Qr=limit_sim(M, sgl[sk], v["stop"], False), Qi=limit_sim(M, sgl[sk], v["stop"], True))
        S = sims[k2]; dz = (np.array([x[0] for x in sgm[sk]], dtype=np.int64) - D0).astype(np.int16); dl = (np.array([x[0] for x in sgl[sk]], dtype=np.int64) - D0).astype(np.int16)
        out[v["id"]] = {k: (dz if k[0] == "Z" else dl, S[k].astype(np.float32)) for k in MODELS}
    return m, out, time.time() - t0
def cand_flag(a, b, ym, nb):
    return bool(a["n"] >= 3000 and a["mean"] >= 0.03 and a["t"] >= TBAR and b["mean"] > 0 and b["t"] >= 1.65 and all(y > 0 for y in ym) and nb["mean"] > 0 and nb["t"] >= 2.5)
def pooled_stats(d, R, mk, nm):
    f = ~np.isnan(R); dev = (d >= D0) & (d <= DEV_END); val = (d > DEV_END) & (d <= VAL_END); a, b = cstats(d[dev & f], R[dev & f]), cstats(d[val & f], R[val & f]); yrs = np.digitize(d, YB)
    ym = [R[dev & f & (yrs == y)].mean() if (dev & f & (yrs == y)).any() else np.nan for y in (1, 2, 3)]; x = dev & f
    tot = np.bincount(mk[x], weights=R[x], minlength=nm); best = int(np.argmax(tot)); nb = x & (mk != best); wo = cstats(d[nb], R[nb])
    cnt = np.bincount(mk[x], minlength=nm); mean_m = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    return dict(dev_n=a["n"], dev_sig=int(dev.sum()), dev_R=a["mean"], dev_t=a["t"], dev_Rsig=float(np.nansum(R[dev]) / max(dev.sum(), 1)), val_R=b["mean"], val_t=b["t"], y22=ym[0], y23=ym[1], y24=ym[2], nb_R=wo["mean"], nb_t=wo["t"], cand=cand_flag(a, b, ym, wo)), mean_m
def full(workers):
    from multiprocessing import Pool
    t0 = time.time(); res = {}; print("start", time.strftime("%H:%M:%S"), "workers", workers, flush=True)
    with Pool(workers) as p:
        for m, r, sec in p.imap_unordered(run_market_nc, MARKETS): res[m] = r; print("  %-7s done in %5.0fs (%d/%d)" % (m, sec, len(res), len(MARKETS)), flush=True)
    ms = sorted(res); nm = len(ms); rows = []; per_market = {k: [] for k in MODELS}
    for v in VARIANTS:
        row = dict(**v)
        for k in MODELS:
            d = np.concatenate([res[m][v["id"]][k][0] for m in ms]).astype(np.int64) + D0; R = np.concatenate([res[m][v["id"]][k][1] for m in ms]).astype(float); mk = np.concatenate([np.full(len(res[m][v["id"]][k][0]), i) for i, m in enumerate(ms)])
            st, mean_m = pooled_stats(d, R, mk, nm); per_market[k].append(mean_m)
            for a, b in st.items(): row["%s_%s" % (k, a)] = b
        rows.append(row)
    T = pd.DataFrame(rows); T.to_csv("EMA1000_NOCOST_TRIALS.csv", index=False)
    mrows = []
    for k in MODELS:
        A = np.array(per_market[k])
        for i, m in enumerate(ms): mrows.append(dict(model=k, market=m, med_dev_R=np.nanmedian(A[:, i]), best_dev_R=np.nanmax(A[:, i]), n_pos=int((A[:, i] > 0).sum())))
    MK = pd.DataFrame(mrows); MK.to_csv("EMA1000_NOCOST_MARKETS.csv", index=False)
    O = pd.read_csv("EMA1000_TRIALS.csv"); F = pd.read_csv("EMA1000_FOLLOWUP.csv"); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("\nfinished %s in %.0f min | variants %d | bar t >= %.2f (Q is the only realistic model; Z and L are a ceiling that produces no candidate)" % (time.strftime("%H:%M:%S"), (time.time() - t0) / 60, len(T), TBAR))
    names = dict(Zr="Z rule  (no spread, market entry)", Zi="Z inverted", Lr="L rule  (no spread, limit at signal close)", Li="L inverted", Qr="Q rule  (real quotes, limit at signal close)", Qi="Q inverted")
    print("\nDEV 2022-24 / VAL 2025, pooled over 46 markets, median over the 1,000 variants (R per FILLED trade; 'per signal' counts an unfilled order as 0)")
    for k in MODELS:
        print("\n%s" % names[k])
        print("  fill rate (DEV) median %.0f%% | DEV mean R median %+.4f best %+.4f | per signal median %+.4f | share of variants > 0: %.0f%% | max clustered t %+.2f | VAL mean R median %+.4f best %+.4f | share > 0 %.0f%% | candidates (all bars, t >= %.2f): %d" % (100 * (T[k + "_dev_n"] / T[k + "_dev_sig"]).median(), T[k + "_dev_R"].median(), T[k + "_dev_R"].max(), T[k + "_dev_Rsig"].median(), 100 * (T[k + "_dev_R"] > 0).mean(), T[k + "_dev_t"].max(), T[k + "_val_R"].median(), T[k + "_val_R"].max(), 100 * (T[k + "_val_R"] > 0).mean(), TBAR, int(T[k + "_cand"].sum())))
    X = T.merge(O[["id", "dev_R"]].rename(columns={"dev_R": "orig_R"}), on="id").merge(F[["id", "dev_random_side"]], on="id")
    print("\nWHERE THE LOSS COMES FROM (DEV, median over variants, R per trade)")
    print("  EMA1000 original (real spread, market entry): rule %+.4f | random side %+.4f" % (X.orig_R.median(), X.dev_random_side.median()))
    print("  Z (spread removed, market entry)            : rule %+.4f | inverted %+.4f | random side %+.4f   -> the structure drag that is left: %+.4f" % (X.Zr_dev_R.median(), X.Zi_dev_R.median(), ((X.Zr_dev_R + X.Zi_dev_R) / 2).median(), ((X.Zr_dev_R + X.Zi_dev_R) / 2).median()))
    print("  spread cost per trade (Z rule minus original rule): median %+.4f" % (X.Zr_dev_R - X.orig_R).median())
    print("  direction skill without spread (Z rule minus Z inverted)/2: median %+.4f R, share of variants > 0: %.0f%%" % (((X.Zr_dev_R - X.Zi_dev_R) / 2).median(), 100 * ((X.Zr_dev_R - X.Zi_dev_R) > 0).mean()))
    for k in ("Zr", "Lr", "Qr", "Li", "Qi"):
        print("\ntop 8 variants by DEV t, %s:" % names[k]); print(T.sort_values(k + "_dev_t", ascending=False).head(8)[["id", "ema", "tf", "body", "win", "tgt", "stop", "ses", "trend", k + "_dev_n", k + "_dev_R", k + "_dev_t", k + "_val_R", k + "_val_t", k + "_y22", k + "_y23", k + "_y24", k + "_nb_t"]].round(3).to_string(index=False))
    for k in ("Zr", "Lr", "Qr"):
        g = MK[MK.model == k].sort_values("med_dev_R", ascending=False); print("\nper market, %s, median DEV mean R over the variants: 6 best and 4 worst" % names[k]); print(pd.concat([g.head(6), g.tail(4)]).round(4).to_string(index=False)); print("  markets with a positive median:", list(g.market[g.med_dev_R > 0]) or "none")
def dry():
    K = pd.read_csv("EMA1000_MARKETS.csv"); print("(1) the market path reproduces EMA1000_MARKETS.csv (XAUUSD, 20 variants, DEV mean R):")
    M = load_market("XAUUSD"); bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}; worst = 0.0
    for v in VARIANTS[:20]:
        ok, side = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"]); s = signals(M, bars[v["tf"]], ok, side, v["ses"], v["win"], v["tgt"]); r, _ = market_sims(M, s, v["stop"]); d = np.array([x[0] for x in s]); dev = (d >= D0) & (d <= DEV_END)
        k = K[(K.id == v["id"]) & (K.market == "XAUUSD")].iloc[0]; worst = max(worst, abs(r[dev].mean() - k.dev_R) if dev.any() else 0, abs(dev.sum() - k.dev_n))
    print("  largest difference (R or trade count): %.6f" % worst)
    print("\n(2) fill invariants (fill never worse than the limit; fill minute 1..%d after the signal candle; touch really happened), 30 random variants x 3 markets x L / Q x both sides:" % WAIT)
    rng = np.random.default_rng(7); bad = tot = 0; fills = []
    for m in ("XAUUSD", "EURUSD", "NSDQ"):
        M = load_market(m); Z = zero_spread(M); bars = {tf: make_bars(M, tf) for tf in (1, 3, 5)}
        for v in [VARIANTS[i] for i in rng.choice(len(VARIANTS), 30, replace=False)]:
            ok, side = cond(bars[v["tf"]], v["ema"], v["body"], v["trend"]); sg = limit_signals(M, bars[v["tf"]], ok, side, v["ses"], v["win"], v["tgt"])
            for MM in (Z, M):
                for inv in (False, True):
                    info = []; limit_sim(MM, sg, v["stop"], inv, info=info)
                    for (i, j, f, c, ss, tp, sl, Rv) in info:
                        end = sg[i][1]; tot += 1; touch = (MM["al"][j] <= c) if ss > 0 else (MM["bh"][j] >= c); bad += not ((f <= c + 1e-9 if ss > 0 else f >= c - 1e-9) and 1 <= j - end <= WAIT and touch)
    print("  %d fills checked, %d violations" % (tot, bad))
    print("\n(3) truncation test: data after the fill minute cut, the signal and the fill must be identical (L and Q, both sides):"); bad = tested = 0
    for m in ("XAUUSD", "EURUSD", "BTCUSD", "NIKKEI"):
        M = load_market(m); Z = zero_spread(M)
        for v in [VARIANTS[i] for i in rng.choice(len(VARIANTS), 5, replace=False)]:
            bars = make_bars(M, v["tf"]); ok, side = cond(bars, v["ema"], v["body"], v["trend"]); sg = limit_signals(M, bars, ok, side, v["ses"], v["win"], v["tgt"])
            for name, MM in (("L", Z), ("Q", M)):
                for inv in (False, True):
                    info = []; limit_sim(MM, sg, v["stop"], inv, info=info)
                    for q in (rng.choice(len(info), min(2, len(info)), replace=False) if info else []):
                        i, j, f, c, ss, tp, sl, Rv = info[q]; M2 = load_market(m, upto=j, med=M["med"]); MM2 = zero_spread(M2) if name == "L" else M2; b2 = make_bars(M2, v["tf"]); ok2, side2 = cond(b2, v["ema"], v["body"], v["trend"]); sg2 = [z for z in limit_signals(M2, b2, ok2, side2, v["ses"], v["win"], v["tgt"]) if z[0] == sg[i][0]]
                        info2 = []
                        if sg2: limit_sim(MM2, sg2, v["stop"], inv, info=info2)
                        tested += 1; bad += not (sg2 and sg2[0][1] == sg[i][1] and abs(sg2[0][3] - sg[i][3]) < 1e-9 and abs(sg2[0][4] - sg[i][4]) < 1e-9 and info2 and info2[0][1] == j and abs(info2[0][2] - f) < 1e-9)
    print("  %d fills recomputed with the future cut, %d mismatches" % (tested, bad))
    print("\n(4) hand check, XAUUSD London baseline (EMA 12, 1 min, wick_atr, 15 min, K1, stop 2), zero spread L, rule side:")
    M = load_market("XAUUSD"); Z = zero_spread(M); B = make_bars(M, 1); ok, side = cond(B, 12, "wick_atr", "none"); sg = limit_signals(M, B, ok, side, "London", 15, "K1"); info = []; limit_sim(Z, sg, 2.0, False, info=info)
    for (i, j, f, c, ss, tp, sl, Rv) in info[60:63]:
        dy, end, s, c0, d, t = sg[i]; print("  %s signal candle closes %02d:%02d mid close %.2f side %+d | fill minute %02d:%02d mid O %.2f H %.2f L %.2f C %.2f | fill %.2f target %.2f stop %.2f (d %.2f) -> R %+.3f" % (dt.date.fromordinal(int(dy)), M["hm"][end] // 60, M["hm"][end] % 60, c0, s, M["hm"][j] // 60, M["hm"][j] % 60, Z["bo"][j], Z["bh"][j], Z["bl"][j], Z["bc"][j], f, tp, sl, d, Rv))
    print("\n(5) fill rates and DEV mean R for the baseline variant (London, K1, stop 2):")
    base = dict(id=0, ema=12, tf=1, body="wick_atr", win=15, tgt="K1", stop=2.0, ses="London", trend="none")
    for m in ("XAUUSD", "EURUSD", "NSDQ", "GBPUSD"):
        M = load_market(m); Z = zero_spread(M); B = make_bars(M, 1); ok, side = cond(B, 12, "wick_atr", "none"); sg = limit_signals(M, B, ok, side, "London", 15, "K1"); dd = np.array([x[0] for x in sg]); dev = (dd >= D0) & (dd <= DEV_END); line = "  %-7s signals(DEV) %4d" % (m, dev.sum())
        for name, MM in (("L", Z), ("Q", M)):
            for inv in (False, True):
                R = limit_sim(MM, sg, 2.0, inv); f = ~np.isnan(R) & dev; line += " | %s%s fill %3.0f%% R %+.3f" % (name, "i" if inv else "r", 100 * f.sum() / max(dev.sum(), 1), R[f].mean() if f.any() else np.nan)
        print(line)
if __name__ == "__main__":
    if "--dry-run" in sys.argv: dry()
    elif "--run" in sys.argv: full(int(sys.argv[sys.argv.index("--run") + 1]) if len(sys.argv) > sys.argv.index("--run") + 1 else 8)
    else: print(__doc__)
