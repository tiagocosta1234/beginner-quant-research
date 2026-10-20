"""What-if (the trader 20 Oct): same entries and targets as his logged setups, stop distance cut to HALF (target ~1:1), USD 2,000 risk a trade, on MT5 broker bid/ask. python halfstop_sim.py
DESCRIPTIVE, ONE variant (factor 0.5 as asked, no sweep): 30 trades 14 Apr-12 May 2025 (replay_mt5.csv, not blind, in-sample) and 20 London trades of Jan 2026 (BLIND_LOG_JAN2026.csv, blind log, lag 1).
Same-minute stop+target = loss. USD 2,000 risk is 'uncapped' (needs 2000 / (100 x stop) lots) and 'capped' (at most equity / (27,647 x 1.10) lots, the margin-call line read from the live terminal; lots floored to 0.01)."""
import numpy as np, pandas as pd
from blind_score import load_days, score, summarize
START, TARGET, FLOOR, CAPDAY, MARGIN, RISK = 95472.14, 108000.0, 92000.0, 2000.0, 27647.04, 2000.0
def logs(f):
    O = pd.read_csv("replay_mt5.csv"); h = O.hm - 120
    A = pd.DataFrame(dict(date=O.day, ses=O.ses, side=O.side, hhmm=["%02d:%02d" % (x // 60, x % 60) for x in h], entry=np.nan, risk=O.risk * f, rew=O.rew, flag=0))
    J = pd.read_csv("BLIND_LOG_JAN2026.csv", dtype={"hhmm": str}); J = J[J.side.isin(["L", "S"]) & (J.ses == "London") & (J.flag == 0) & (J.pre == 1)].copy()
    J["risk"] = (J.entry - J.stop).abs() * f; J["rew"] = (J.target - J.entry).abs()
    return A, J
def lots(stop, bal=START):
    unc = RISK / (100 * stop); cap = np.minimum(unc, bal / (MARGIN * 1.10)); return unc, np.floor(cap / 0.01 + 1e-9) * 0.01
def table(Z, label):
    stop = Z.risk.to_numpy(); unc, cap = lots(stop); R = Z.R_mine.to_numpy(); d_unc = R * RISK; d_cap = R * cap * 100 * stop
    print("  %-26s n %2d | wins %2d | mean R %+.3f | stop median %.2f | share of trades where USD 2,000 fits the margin cap %3.0f%% | uncapped %+8.0f USD (%+5.0f a trade) | capped %+8.0f USD (%+5.0f a trade, average risk %4.0f)" % (
        label, len(Z), (R > 0).sum(), R.mean(), np.median(stop), 100 * np.mean(np.floor(unc / 0.01 + 1e-9) * 0.01 <= cap + 1e-9), d_unc.sum(), d_unc.mean(), d_cap.sum(), d_cap.mean(), np.mean(cap * 100 * stop)))
    return R, stop, d_unc, d_cap
def path(pnl, label):
    bal, lo, peak, mdd, hit = START, START, START, 0.0, None
    for i, p in enumerate(pnl, 1):
        bal += min(p, CAPDAY) if p > 0 else p; lo = min(lo, bal); peak = max(peak, bal); mdd = max(mdd, peak - bal)
        if hit is None and (bal <= FLOOR): hit = "BREACH at trade %d" % i
        if hit is None and (bal >= TARGET): hit = "target at trade %d" % i
    print("  %-34s final %9.0f | lowest %9.0f | max drawdown %6.0f | %s" % (label, bal, lo, mdd, hit or "neither target nor floor"))
def mc(R, stop, label, N=20000, H=250, seed=3):
    rng = np.random.default_rng(seed); unc = RISK / (100 * stop); bal = np.full(N, START); st = np.zeros(N, int); de = np.zeros(N, int)
    for day in range(1, H + 1):
        use = st == 0
        if not use.any(): break
        i = rng.integers(len(R), size=N); cap = np.minimum(unc[i], bal / (MARGIN * 1.10)); risk = np.floor(cap / 0.01 + 1e-9) * 0.01 * 100 * stop[i]
        pnl = R[i] * risk; bal = np.where(use, bal + np.where(pnl > 0, np.minimum(pnl, CAPDAY), pnl), bal)
        b = use & (bal <= FLOOR); st[b] = 2; de[b] = day; p = use & ~b & (bal >= TARGET); st[p] = 1; de[p] = day
    print("  %-34s pass %3.0f%% (by 22 Dec, 47 days: %3.0f%%) | breach %3.0f%% (by 22 Dec: %3.0f%%) | still alive after 250 days %3.0f%%" % (label, 100 * np.mean(st == 1), 100 * np.mean((st == 1) & (de <= 47)), 100 * np.mean(st == 2), 100 * np.mean((st == 2) & (de <= 47)), 100 * np.mean(st == 0)))
dA = load_days("2025-04-14", "2025-05-12"); dJ = load_days("2026-01-02", "2026-01-30"); res = {}
for f, name in ((1.0, "ORIGINAL stops"), (0.5, "HALF stops")):
    A, J = logs(f); ZA = score(A, dA, lag=0); ZJ = score(J, dJ, lag=1); res[f] = (ZA, ZJ)
    print("\n=== %s (target distance unchanged) ===" % name)
    print("R-based result vs mirror and random side (his entries, MT5 broker bid/ask):"); summarize(ZA, "30 Apr-May 2025 (in-sample)"); summarize(ZJ, "20 Jan 2026 (blind)")
    print("USD at 2,000 risk a trade:")
    RA, sA, uA, cA = table(ZA, "Apr-May 2025"); RJ, sJ, uJ, cJ = table(ZJ, "Jan 2026")
    print("account path from 95,472.14 (+2,000 a day counted cap), trades in date order:")
    path(cA, "Apr-May 2025, capped"); path(cJ, "Jan 2026, capped"); path(np.r_[cA, cJ], "both in order, capped"); path(np.r_[uA, uJ], "both in order, uncapped (not placeable)")
    print("bootstrap of the account, 1 trade a day, trades drawn at random from the sets, margin cap with the equity:")
    mc(np.r_[RA, RJ], np.r_[sA, sJ], "all 50 trades"); mc(RJ, sJ, "Jan 2026 only (blind, 20)")
print("\nper-trade comparison, original vs half stop (R of his side, own stop units):")
a, b = res[1.0], res[0.5]
for nm, i in (("Apr-May 2025", 0), ("Jan 2026", 1)):
    o, h = a[i].R_mine.to_numpy(), b[i].R_mine.to_numpy(); print("  %-14s wins %d -> %d | trades that were winners and are now losers: %d | losers now winners: %d" % (nm, (o > 0).sum(), (h > 0).sum(), ((o > 0) & (h <= 0)).sum(), ((o <= 0) & (h > 0)).sum()))
