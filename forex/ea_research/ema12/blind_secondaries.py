"""PREREG_BLIND2026 Amendment 6 (logging only): the two secondary bracket readings, computed from the same logged entries as blind_score.py.
S1 = his logged stop, target = 1.0 x |entry - stop|; S2 = fixed 10.0 / 10.0 points at 2 lots (USD 200 a point). Primary = his logged stop and target (unchanged). Same entry minute and side as blind_score (lag 1),
MT5 broker bid / ask, same-minute stop and target = loss, open at the session close marked on the exit side. Reported at the feed's own spread and re-priced at a flat 0.48. Descriptive: no bar, gate or futility rule depends on it.
Do not show the per-trade output to the trader before he has finished the batch (blind rule).
python blind_secondaries.py NEW_LOG.csv [--pool BLIND_LOG_JAN2026_FXR.csv]     LOG.csv columns as in blind_score.py (date, ses, side, hhmm, entry, stop, target, flag, pre)
python blind_secondaries.py --selftest                                          January 2026 through the whole path (must give the numbers of MANUAL_FIXED_BRACKET_OUTPUT.txt)"""
import sys, numpy as np, pandas as pd
from blind_score import load_days, score
LOTS, START, FLOOR, M1, S_FLAT = 2.0, 95472.14, 92000.0, 27580.0, 0.48
PT = LOTS * 100                                                    # USD per gold point at 2 lots
def prep(path):
    L = pd.read_csv(path, dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"]) & (L.ses == "London")].copy()    # primary = London, as in blind_score
    if "flag" in L: L = L[L.flag.fillna(0) == 0]
    if "pre" in L: L = L[L.pre.fillna(1) == 1]
    return L.drop(columns=[c for c in ("risk", "rew") if c in L]).reset_index(drop=True)
def reprice(days):
    out = {}
    for k, g in days.items():
        g = g.copy()
        for b, a in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): g[a] = g[b] + S_FLAT
        g["mo"] = g.bo + S_FLAT / 2; out[k] = g
    return out
def variants(L, days):
    z = {}
    p = L.copy(); z["primary"] = score(p, days, lag=1)
    s1 = L.copy(); s1["risk"] = (s1.entry - s1.stop).abs(); s1["rew"] = 1.0 * s1.risk; z["S1 own stop / 1.0 R"] = score(s1, days, lag=1)
    s2 = L.copy(); s2["risk"] = 10.0; s2["rew"] = 10.0; z["S2 fixed 10 / 10"] = score(s2, days, lag=1)
    return z
def report(Z, label):
    rng = np.random.default_rng(5); P = Z["primary"]; res = {}
    print("  %s (n %d)" % (label, len(P)))
    for name, V in Z.items():
        n = len(V); R = V.R_mine.to_numpy(); L, S = V.R_L.to_numpy(), V.R_S.to_numpy()
        null = np.where(rng.random((60000, n)) < 0.5, L, S).mean(axis=1) if n else np.array([np.nan])
        usd = (V.R_mine * V.risk).to_numpy() * PT; dif = R - P.R_mine.to_numpy(); se = dif.std(ddof=1) / np.sqrt(n) if n > 1 else float("nan")
        res[name] = dict(R=R, mean=R.mean() if n else float("nan"), usd=usd, V=V)
        print("    %-22s wins %2d/%2d | mean R %+.3f sum R %+6.2f | USD a trade at 2 lots %+7.0f | his side minus random side %+.3f (P %.3f)%s" % (
            name, (R > 0).sum(), n, res[name]["mean"], R.sum(), usd.mean() if n else float("nan"), (R.mean() - null.mean()) if n else float("nan"), (null >= R.mean()).mean() if n else float("nan"),
            "" if name == "primary" else " | minus primary %+.3f (se %.3f)" % (dif.mean(), se)))
    V = Z["S2 fixed 10 / 10"]; usd = pd.Series(V.R_mine.to_numpy() * 10.0 * PT).groupby(V.date.astype(str).to_numpy(), sort=True).sum().clip(upper=2000.0)   # counted profit capped at +2,000 a day
    eq = START + usd.cumsum(); print("    S2 dollar path from %.2f: final %.0f | lowest %.0f (%s the %.0f floor) | worst day %+.0f | days <= -2,500: %d | margin level at 2 lots %.0f%% (margin %.0f)" % (
        START, eq.iloc[-1], eq.min(), "BELOW" if eq.min() < FLOOR else "above", FLOOR, usd.min(), (usd <= -2500).sum(), 100 * START / (LOTS * M1), LOTS * M1))
    return res
def readings(new):
    p, s1, s2 = new["primary"], new["S1 own stop / 1.0 R"], new["S2 fixed 10 / 10"]
    V = s2["V"]; day = pd.Series(V.R_mine.to_numpy() * 10.0 * PT).groupby(V.date.astype(str).to_numpy()).sum().clip(upper=2000.0); eq = START + day.cumsum()
    print("\nPre-declared readings on the new block at the feed's spread (Amendment 6 of the blind prereg, Amendment 2 of the forward prereg; a proposal to the trader only, the gate is unchanged):")
    print("  S1 worth carrying forward (mean R >= +0.10 and >= primary %+.3f): mean %+.3f -> %s" % (p["mean"], s1["mean"], "YES" if s1["mean"] >= 0.10 and s1["mean"] >= p["mean"] else "no"))
    print("  S2 workable for sizing (mean R > 0, no day <= -2,500, path above %.0f): mean %+.3f, worst day %+.0f, lowest %.0f -> %s" % (FLOOR, s2["mean"], day.min(), eq.min(), "YES" if s2["mean"] > 0 and day.min() > -2500 and eq.min() > FLOOR else "no"))
def run(new_path, pool_path=None, quiet=False):
    blocks = [("new block", prep(new_path))] + ([("pooled with " + pool_path, pd.concat([prep(new_path), prep(pool_path)], ignore_index=True))] if pool_path else [])
    d = load_days(min(b[1].date.min() for b in blocks), max(b[1].date.max() for b in blocks)) if not pool_path else {**load_days(prep(new_path).date.min(), prep(new_path).date.max()), **load_days(prep(pool_path).date.min(), prep(pool_path).date.max())}
    out = {}
    for sp, dd in (("feed spread", d), ("flat 0.48", reprice(d))):
        print("=== %s ===" % sp)
        for lab, L in blocks: out[(sp, lab)] = report(variants(L, dd), lab)
    readings(out[("feed spread", "new block")])
    return out
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        out = run("BLIND_LOG_JAN2026_FXR.csv")
        f, fl = out[("feed spread", "new block")], out[("flat 0.48", "new block")]
        chk = [("primary feed", f["primary"]["mean"], 0.007, 0.01), ("primary flat", fl["primary"]["mean"], 0.007, 0.002), ("S1 flat", fl["S1 own stop / 1.0 R"]["mean"], 0.277, 0.002), ("S2 flat", fl["S2 fixed 10 / 10"]["mean"], 0.176, 0.002)]
        for nm, got, want, tol in chk: print("selftest %-13s got %+.4f want %+.3f +/- %.3f -> %s" % (nm, got, want, tol, "ok" if abs(got - want) <= tol else "FAIL"))
        assert all(abs(g - w) <= t for _, g, w, t in chk), "selftest failed"; print("selftest passed")
    else:
        a = [x for x in sys.argv[1:] if not x.startswith("--")]; pool = sys.argv[sys.argv.index("--pool") + 1] if "--pool" in sys.argv else None
        run(a[0], pool if pool != a[0] else None)
