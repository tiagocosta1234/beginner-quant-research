"""DESCRIPTIVE ONLY (21 Oct, the trader: 'explore if our backtesting in notion would be better if we had the 10.0 points fixed brackets and 2 fixed lots'): his 50 replay entries (30 Apr-May 2025 in-sample + 20 blind Jan 2026),
same entry minutes and sides, MT5 broker bid / ask with the spread forced to 0.48, stop and target replaced by a fixed bracket in points and 2 fixed lots (USD 200 a point), against the brackets as he logged them.
Post-hoc on the same 50 trades, so every extra bracket looked at is another look; not a rule. python manual_fixed_bracket.py > MANUAL_FIXED_BRACKET_OUTPUT.txt"""
import numpy as np, pandas as pd
from blind_score import load_days, score
S, LOTS, START, FLOOR = 0.48, 2.0, 95472.14, 92000.0
PT = LOTS * 100                                                 # USD per point at 2 lots
O = pd.read_csv("replay_mt5.csv"); h = O.hm - 120
A = pd.DataFrame(dict(date=O.day, ses=O.ses, side=O.side, hhmm=["%02d:%02d" % (x // 60, x % 60) for x in h], entry=np.nan, risk=O.risk, rew=O.rew, flag=0))
J = pd.read_csv("BLIND_LOG_JAN2026_FXR.csv", dtype={"hhmm": str}); J = J[J.side.isin(["L", "S"]) & (J.get("flag", 0) == 0) & (J.get("pre", 1) == 1)].copy()
J["risk"] = (J.entry - J.stop).abs(); J["rew"] = (J.target - J.entry).abs()
def reprice(days):
    out = {}
    for k, g in days.items():
        g = g.copy()
        for b, a in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): g[a] = g[b] + S
        g["mo"] = g.bo + S / 2; out[k] = g
    return out
dA, dJ = reprice(load_days("2025-04-14", "2025-05-12")), reprice(load_days("2026-01-02", "2026-01-30"))
def trades(rk=None, rw=None):
    a, j = A.copy(), J.copy()
    if rk is not None:
        for d in (a, j): d["risk"] = float(rk); d["rew"] = float(rw)
    za, zj = score(a, dA, lag=0), score(j, dJ, lag=1)
    return pd.concat([za.assign(per="Apr-May 2025"), zj.assign(per="Jan 2026 (blind)")], ignore_index=True)
rng = np.random.default_rng(3)
def st(G):
    n = len(G); R = G.R_mine.to_numpy(); L, Sh = G.R_L.to_numpy(), G.R_S.to_numpy(); mine = np.where(G.side == "L", L, Sh)
    null = np.where(rng.random((60000, n)) < 0.5, L, Sh).mean(axis=1)
    usd = (G.R_mine * G.risk).to_numpy() * PT
    return n, (R > 0).sum(), R.mean(), R.sum(), usd.mean(), usd.sum(), R.mean() / (R.std(ddof=1) / np.sqrt(n)), R.mean() - null.mean(), (null >= R.mean()).mean()
def line(lab, Z):
    out = []
    for nm, G in (("all 50", Z), ("Apr-May 25", Z[Z.per == "Apr-May 2025"]), ("Jan 26 blind", Z[Z.per != "Apr-May 2025"])):
        n, w, m, sR, um, ut, t, ex, p = st(G); out.append("%s: wins %2d/%2d meanR %+.3f sumR %+6.2f USD/trade %+7.0f total %+8.0f excess %+.3f P %.3f" % (nm, w, n, m, sR, um, ut, ex, p))
    print("%-24s" % lab); [print("      " + o) for o in out]
def path(lab, usd_trade, dates, cap=True):
    d = pd.Series(usd_trade).groupby(pd.Series(dates).astype(str).to_numpy(), sort=True).sum()
    if cap: d = d.clip(upper=2000.0)                             # counted profit above +2,000 a day is removed
    eq = START + d.cumsum(); dd = (np.maximum.accumulate(np.r_[0, d.cumsum()])[1:] - d.cumsum()).max()
    print("   %-30s final %9.0f | lowest %9.0f (%s the floor) | worst day %+7.0f | days <= -2,500: %d | max drawdown %6.0f" % (lab, eq.iloc[-1], eq.min(), "BELOW" if eq.min() < FLOOR else "above", d.min(), (d <= -2500).sum(), dd))

base = trades()
print("=== baseline: brackets as he logged them, stop median %.2f (range %.2f-%.2f), spread forced to %.2f ===" % (base.risk.median(), base.risk.min(), base.risk.max(), S))
line("as logged (R above)", base)
print("      with 2 fixed lots the dollars vary with his stop: risk per trade %.0f..%.0f (median %.0f); trades over USD 2,500 = %d, over USD 2,000 = %d of %d" % (
    (base.risk * PT).min(), (base.risk * PT).max(), (base.risk * PT).median(), (base.risk * PT > 2500).sum(), (base.risk * PT > 2000).sum(), len(base)))
Z10 = trades(10, 10); Z105 = trades(10, 5.3)
print("\n=== fixed 10 point bracket, 2 lots (USD 200 a point: stop USD 2,000, target USD 2,000 for 10/10) ===")
line("10 / 10 (1:1)", Z10); line("10 / 5.3 (his 0.53 ratio)", Z105)
def trades_own(ratio):                                          # his own stop as logged, target = ratio x that stop
    a, j = A.copy(), J.copy()
    for d in (a, j): d["rew"] = ratio * d.risk
    return pd.concat([score(a, dA, lag=0).assign(per="Apr-May 2025"), score(j, dJ, lag=1).assign(per="Jan 2026 (blind)")], ignore_index=True)
Zown = trades_own(1.0)
print("\n=== his own stop as logged, target 1.0 x that stop (the earlier lever, for comparison; USD at 2 fixed lots varies with his stop) ===")
line("own stop / 1.0 R", Zown)
print("\n=== paired difference in R per trade (same trades, second minus first; se = sd of the differences / sqrt(n)) ===")
for lab, X, Y in (("10/10 minus as logged", Z10, base), ("10/5.3 minus as logged", Z105, base), ("own stop 1.0 R minus as logged", Zown, base), ("10/10 minus own stop 1.0 R", Z10, Zown)):
    for nm, msk in (("all 50", np.ones(len(base), bool)), ("Jan blind", (base.per != "Apr-May 2025").to_numpy())):
        dlt = (X.R_mine - Y.R_mine).to_numpy()[msk]; n = len(dlt); se = dlt.std(ddof=1) / np.sqrt(n)
        print("  %-32s %-9s n %2d mean diff %+.3f se %.3f t %+.2f" % (lab, nm, n, dlt.mean(), se, dlt.mean() / se))
dd = pd.Series(base.date.astype(str)).value_counts(); print("\ndays with two of the 50 trades: %d (a USD 2,000 stop twice on the same day = -4,000, past the -2,500 daily hard breach)" % (dd >= 2).sum())
print("\n=== is 10 special? same entries, 1:1 and 0.53 ratio, fixed 2 lots (mean R, USD per trade at 2 lots, Jan blind in brackets) ===")
for sz in (5, 7.5, 10, 12.5, 15, 20):
    r = []
    for nm, rw in (("1:1", sz), ("0.53", round(0.53 * sz, 3))):
        Z = trades(sz, rw); Zj = Z[Z.per != "Apr-May 2025"]
        r.append("%s all %+.3f R %+6.0f USD (Jan %+.3f R %+6.0f USD) wins %d/50" % (nm, Z.R_mine.mean(), (Z.R_mine * Z.risk).mean() * PT, Zj.R_mine.mean(), (Zj.R_mine * Zj.risk).mean() * PT, (Z.R_mine > 0).sum()))
    print("  size %4.1f pts (stop USD %5.0f): %s | %s" % (sz, sz * PT, r[0], r[1]))
print("\n=== account path at 2 fixed lots from %.2f, floor %.0f, counted profit capped at +2,000 a day ===" % (START, FLOOR))
for lab, Z in (("as logged brackets", base), ("fixed 10 / 10", Z10), ("fixed 10 / 5.3", Z105)):
    print(lab)
    for nm, G in (("Jan 2026 blind (20)", Z[Z.per != "Apr-May 2025"]), ("all 50 in order", Z)):
        path(nm, (G.R_mine * G.risk).to_numpy() * PT, G.date.to_numpy())
print("\nper-trade R of the Jan blind trades at fixed 10 / 10 and 10 / 5.3 (his side; stop-or-target, still-open trades marked at 17:00):")
for (_, a), (_, b), (_, c) in zip(Z10[Z10.per != "Apr-May 2025"].iterrows(), Z105[Z105.per != "Apr-May 2025"].iterrows(), base[base.per != "Apr-May 2025"].iterrows()):
    print("  %s %s  as logged %+.2f (stop %5.2f) | 10/10 %+.2f | 10/5.3 %+.2f" % (str(a.date)[5:], a.side, c.R_mine, c.risk, a.R_mine, b.R_mine))
