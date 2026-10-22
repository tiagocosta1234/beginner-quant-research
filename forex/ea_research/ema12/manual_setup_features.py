"""DESCRIPTIVE + MULTIPLE-TESTING-AWARE (22 Oct, the trader: 'find a setup idea with the highest EV in R per trade'): which feature-defined subset of his own 50 replay trades has the highest mean R, and is that more than the best of
21 candidate subsets would show by chance? All features are known at the entry minute (bars before it only). Outcome = R as he logged the bracket on MT5 broker bid / ask at a 0.48 spread (the primary lever), and his stop with a 1.0 R target (S1) as a second column.
Max-statistic permutation test: R is shuffled across the 50 trades 20,000 times and the best subset (n >= 10) of each shuffle is recorded, so 'the highest of 21' is compared with the highest of 21 on pure noise.
Terciles are cut on the 30 Apr-May 2025 trades only, so the second check is clean: pick the best subset on Apr-May (n >= 8), look at the 20 blind Jan 2026 trades. Not a rule; a hypothesis generator. python -B manual_setup_features.py > MANUAL_SETUP_FEATURES_OUTPUT.txt"""
import sys, io, contextlib, numpy as np, pandas as pd
sys.dont_write_bytecode = True
with contextlib.redirect_stdout(io.StringIO()):
    import manual_fixed_bracket as K
base, own = K.trades(), K.Zown
A, J = K.A.reset_index(drop=True), K.J.reset_index(drop=True)
rows = [(r.date, int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + 120, dA) for r, dA in ((r, K.dA) for _, r in A.iterrows())] + [(r.date, int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + 121, K.dJ) for _, r in J.iterrows()]
assert len(rows) == len(base) == 50
F = []
for (date, hm, days), (_, t) in zip(rows, base.iterrows()):
    g = days[pd.Timestamp(date).date()]; i0 = g.index[g.hm >= hm][0]; P = g.iloc[:i0]; c = P.bc.to_numpy(); h = P.bh.to_numpy(); l = P.bl.to_numpy(); o = P.bo.to_numpy()
    sgn = 1 if t.side == "L" else -1
    ema = pd.Series(c).ewm(span=12, adjust=False).mean().to_numpy()
    trs = np.maximum(h[-14:] - l[-14:], np.maximum(np.abs(h[-14:] - c[-15:-1]), np.abs(l[-14:] - c[-15:-1]))); atr = trs.mean()
    rng60 = c[-60:].max() - c[-60:].min(); pos = (c[-1] - c[-60:].min()) / rng60 if rng60 > 0 else 0.5
    mom = (pos > 2 / 3 and sgn == 1) or (pos < 1 / 3 and sgn == -1); fad = (pos > 2 / 3 and sgn == -1) or (pos < 1 / 3 and sgn == 1)
    opn = 600 if t.ses == "London" else 990
    F.append(dict(side=t.side, ses=t.ses, risk=t.risk, early=(hm - opn) <= 2, slope_with=np.sign(ema[-1] - ema[-6]) == sgn, big_candle=abs(c[-1] - o[-1]) / atr >= 1.0, trend30_with=np.sign(c[-1] - c[-31]) == sgn,
                  pos=("momentum edge" if mom else "fade edge" if fad else "middle"), atr=atr))
F = pd.DataFrame(F); n = len(F); AM = (base.per == "Apr-May 2025").to_numpy()
q = lambda s, a: np.quantile(s[AM], a)
S = {}
for k, v in (("side = Long", F.side == "L"), ("side = Short", F.side == "S"), ("London", F.ses == "London"), ("NY", F.ses == "NY"),
             ("stop small third", F.risk <= q(F.risk, 1 / 3)), ("stop middle third", (F.risk > q(F.risk, 1 / 3)) & (F.risk <= q(F.risk, 2 / 3))), ("stop large third", F.risk > q(F.risk, 2 / 3)),
             ("entry within 2 min of the open", F.early), ("entry later than 2 min", ~F.early), ("EMA12 slope (5 min) with the side", F.slope_with), ("EMA12 slope against the side", ~F.slope_with),
             ("setup candle >= 1 ATR", F.big_candle), ("setup candle < 1 ATR", ~F.big_candle), ("30-min trend with the side", F.trend30_with), ("30-min trend against the side", ~F.trend30_with),
             ("entry at the 60-min extreme, with it (momentum)", F.pos == "momentum edge"), ("entry at the 60-min extreme, against it (fade)", F.pos == "fade edge"), ("entry mid-range", F.pos == "middle"),
             ("M1 ATR low third", F.atr <= q(F.atr, 1 / 3)), ("M1 ATR middle third", (F.atr > q(F.atr, 1 / 3)) & (F.atr <= q(F.atr, 2 / 3))), ("M1 ATR high third", F.atr > q(F.atr, 2 / 3))):
    S[k] = np.asarray(v, bool)
K_ = len(S); NMIN = 10; R = base.R_mine.to_numpy(); R1 = own.R_mine.to_numpy(); rng = np.random.default_rng(5)
print("his 50 trades, MT5 broker bid/ask at 0.48 spread: as-logged mean R %+.3f (S1 own stop / 1.0 R: %+.3f); %d candidate subsets, minimum n %d for ranking\n" % (R.mean(), R1.mean(), K_, NMIN))
print("%-48s %3s  %9s %9s | %9s %9s" % ("subset", "n", "meanR", "vs rest", "S1 meanR", "vs rest"))
res = sorted(((R[m].mean(), k, m) for k, m in S.items() if m.sum() >= NMIN), reverse=True)
for mR, k, m in res:
    print("%-48s %3d  %+9.3f %+9.3f | %+9.3f %+9.3f" % (k, m.sum(), mR, mR - R[~m].mean() if (~m).sum() else np.nan, R1[m].mean(), R1[m].mean() - R1[~m].mean() if (~m).sum() else np.nan))
def maxnull(Rv, masks, reps=20000):
    M = np.array([m / m.sum() for m in masks]); Rm = np.array([rng.permutation(Rv) for _ in range(reps)]); return (M @ Rm.T).max(axis=0)
elig = [m for _, _, m in res]
for lab, Rv in (("as logged", R), ("S1 own stop / 1.0 R", R1)):
    mx = maxnull(Rv, elig); best = max(Rv[m].mean() for m in elig)
    print("\nmax-statistic, %s: best subset mean %+.3f | on pure noise the best of %d subsets averages %+.3f (95th percentile %+.3f) | family-wise P(noise best >= observed) = %.3f" % (lab, best, len(elig), mx.mean(), np.quantile(mx, 0.95), (mx >= best).mean()))
print("\nclean check: best subset on the 30 Apr-May trades (n >= 8) against the 20 blind Jan 2026 trades")
cands = [(R[m & AM].mean(), k, m) for k, m in S.items() if (m & AM).sum() >= 8]; cands.sort(reverse=True)
for mR, k, m in cands[:3]:
    jm = m & ~AM
    print("  %-48s Apr-May n %2d mean %+.3f | Jan n %2d mean %+.3f (Jan all %+.3f) | S1 Jan %+.3f" % (k, (m & AM).sum(), mR, jm.sum(), R[jm].mean() if jm.sum() else np.nan, R[~AM].mean(), R1[jm].mean() if jm.sum() else np.nan))
