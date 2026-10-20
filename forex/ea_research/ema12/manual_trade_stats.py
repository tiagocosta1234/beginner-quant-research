"""DESCRIPTIVE ONLY (21 Oct, the trader: 'sum of R return on our 12 ema taken trades, then show stats'): the 50 replay trades he took, 30 of 14 Apr-12 May 2025 (in-sample, rule built on them)
and 20 blind of Jan 2026, on MT5 broker bid / ask (R_mine of direction_skill.csv and blind_score.score) and as FX Replay logged them (chart prices, no spread). No live or paper trade is in it.
python manual_trade_stats.py"""
import math, numpy as np, pandas as pd
from blind_score import load_days, score
START, FLOOR, CAP_LOTS, SPREAD_NOW = 95472.14, 92000.0, 3.1, 0.48

o = pd.read_csv("replay_mt5.csv"); q = pd.read_csv("direction_skill.csv")
a = pd.DataFrame(dict(period="Apr-May 2025", date=o.day, ses=o.ses, side=o.side, risk=o.risk, spr=o.spr, R=q.R_mine, hm=o.hm))
log = pd.read_csv("BLIND_LOG_JAN2026_FXR.csv", dtype={"hhmm": str}); log = log[log.side.isin(["L", "S"])]
days = load_days(log.date.min(), log.date.max()); Z = score(log, days, lag=1)
sp = np.median([(g.ao - g.bo)[(g.hm >= 600) & (g.hm <= 615)].median() for g in days.values()])
b = pd.DataFrame(dict(period="Jan 2026 (blind)", date=Z.date, ses=Z.ses, side=Z.side, risk=Z.risk, spr=sp, R=Z.R_mine, hm=0))
T = pd.concat([a, b], ignore_index=True); T["date"] = pd.to_datetime(T.date).dt.date
T = T.sort_values(["date", "hm"]).reset_index(drop=True)
T["R_now"] = T.R - (SPREAD_NOW - T.spr).clip(lower=0) / T.risk       # same trades re-priced at today's 0.48 spread (approximation: one extra cost per trade)

def streak(x, sign):
    best = cur = 0
    for v in x:
        cur = cur + 1 if (v > 0) == sign else 0; best = max(best, cur)
    return best
def stats(R, label, ses=None):
    R = np.asarray(R, float); n = len(R); w = R[R > 0]; l = R[R <= 0]
    aw, al = (w.mean() if len(w) else 0.0), (-l.mean() if len(l) else 0.0)
    be = al / (aw + al) if aw + al else float("nan")
    rng = np.random.default_rng(7); bs = np.sort([rng.choice(R, n).mean() for _ in range(5000)])
    cum = np.cumsum(R); dd = (np.maximum.accumulate(np.r_[0, cum])[1:] - cum).max()
    # exact one-sided binomial P(wins >= observed | win prob = break-even)
    k = len(w); pb = sum(math.comb(n, i) * be ** i * (1 - be) ** (n - i) for i in range(k, n + 1)) if 0 < be < 1 else float("nan")
    t = R.mean() / (R.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    print("%-26s n %2d | wins %2d (%.0f%%) | SUM R %+7.2f | mean %+.3f | median %+.3f | sd %.2f | t %+.2f | 95%% CI %+.2f..%+.2f" % (label, n, k, 100 * k / n, R.sum(), R.mean(), np.median(R), R.std(ddof=1), t, bs[125], bs[4875]))
    print("%-26s avg win %+.3f | avg loss %.3f | payoff %.2f | break-even win rate %.0f%% (P wins>=obs at b/e %.2f) | profit factor %.2f | best %+.2f worst %+.2f | max DD %.2f R | streaks W%d L%d" % (
        "", aw, al, aw / al if al else float("inf"), 100 * be, pb, w.sum() / -l.sum() if len(l) and l.sum() else float("inf"), R.max(), R.min(), dd, streak(R, True), streak(R, False)))

print("=== MT5 broker bid/ask R (spread of the day: Apr-May 2025 median %.2f, Jan 2026 %.2f), %d trades ===" % (T[T.period == "Apr-May 2025"].spr.median(), sp, len(T)))
stats(T.R, "ALL 50"); stats(T[T.period == "Apr-May 2025"].R, "Apr-May 2025 (in-sample)"); stats(T[T.period != "Apr-May 2025"].R, "Jan 2026 (blind)")
print("\n--- split (all 50) ---")
for s in ("London", "NY"): stats(T[T.ses == s].R, s)
for s, nm in (("L", "Long"), ("S", "Short")): stats(T[T.side == s].R, nm)
T["month"] = pd.to_datetime(T.date).dt.strftime("%Y-%m")
print("\n--- by month ---")
for m, g in T.groupby("month"): print("%s n %2d wins %2d sum R %+6.2f mean %+.3f" % (m, len(g), (g.R > 0).sum(), g.R.sum(), g.R.mean()))
print("\n--- stop size (points) ---  mean %.2f median %.2f min %.2f max %.2f" % (T.risk.mean(), T.risk.median(), T.risk.min(), T.risk.max()))
print("\n=== same trades re-priced at today's 0.48 spread (approx.) ===")
stats(T.R_now, "ALL 50 at 0.48"); stats(T[T.period == "Apr-May 2025"].R_now, "Apr-May at 0.48"); stats(T[T.period != "Apr-May 2025"].R_now, "Jan 2026 at 0.48")

f = pd.read_csv("FXREPLAY_TRADES_2026-10-20.csv"); f = f[f.stop.notna() & (f.stop > 0)]
print("\n=== as FX Replay logged them (chart prices, no spread; 29 + 20 = %d trades with a stop; the 6 May 2025 NY short is not in FX Replay) ===" % len(f))
stats(f.R_fxr, "ALL FX Replay")
for g, nm in (("aprmay2025", "Apr-May 2025"), ("jan2026", "Jan 2026")): stats(f[f.group == g].R_fxr, nm)

print("\n=== dollars at a fixed risk per trade (MT5 broker bid/ask R, chronological, start %.2f, floor %.0f, lot cap %.1f) ===" % (START, FLOOR, CAP_LOTS))
for risk in (2000, 1000, 500, 100):
    for capped in (False, True):
        usd = T.R * (np.minimum(risk, CAP_LOTS * 100 * T.risk) if capped else risk)
        eq = START + usd.cumsum(); day = usd.groupby(T.date).sum()
        print("risk %4d %-9s | sum %+9.0f | final %9.0f | lowest equity %9.0f (%s the 92,000 floor) | worst day %+7.0f | days <= -2,500: %d | max DD %.0f" % (
            risk, "capped" if capped else "uncapped", usd.sum(), eq.iloc[-1], eq.min(), "BELOW" if eq.min() < FLOOR else "above", day.min(), (day <= -2500).sum(),
            (np.maximum.accumulate(np.r_[0, usd.cumsum()])[1:] - usd.cumsum()).max()))
print("\ntrades over the %.1f-lot cap at USD 2,000 risk: %d of %d" % (CAP_LOTS, (T.risk < 2000 / (CAP_LOTS * 100)).sum(), len(T)))
