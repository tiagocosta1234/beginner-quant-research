"""the trader 26 Oct 2026: "maybe you could help me upgrade my trading to increase the win rate". Post-hoc forensics of his 88 blind trades
(January, batch 2, extension / recent-2026; BLIND_LOOK2_FOR_SCORE.csv, all in MT5 broker spot prices) on MT5 broker bid/ask with the fixed clock.
For each trade: the outcome (blind_score convention: fill at the next minute's open on the ask / bid, his stop and target DISTANCES, stop
first on a tie, 17:00 close), the stop size against the pre-entry noise (median 1-minute range 07:00-07:59) and the prior daily ATR, the side
against the 15m / 1h EMA12, chasing (the move in the trade's direction over the 5 minutes before entry, in noise units), the entry minute,
how close winners came to the stop (MAE), and for losers whether price reached the target later that day (direction right, stop too tight).
POST-HOC: every pattern here is a hypothesis to pre-register and test on fresh days, not a rule. Usage (from ema12): python trade_forensics.py"""
import numpy as np, pandas as pd
import spot_vs_futures as V

L = pd.read_csv("BLIND_LOOK2_FOR_SCORE.csv", dtype={"hhmm": str})
L = L[L.side.isin(["L", "S"])].copy()
L["block"] = np.where(L.date < "2026-02-01", "Jan 2026", np.where(L.date >= "2026-07-27", "recent 2026", np.where(L.date < "2024-01-01", "2023", "batch 2")))
rows = []
for r in L.itertuples():
    s = V.spot_day(r.date)
    if s.empty: continue
    mid = (s[["bo", "bh", "bl", "bc"]].to_numpy() + s[["ao", "ah", "al", "ac"]].to_numpy()) / 2
    m = pd.DataFrame(mid, index=s.index, columns=["open", "high", "low", "close"])
    t = pd.Timestamp(f"{r.date} {r.hhmm}"); start = t + pd.Timedelta(minutes=1); end = pd.Timestamp(f"{r.date} 17:00")
    sd = 1 if r.side == "L" else -1; sdist, tdist = abs(r.entry - r.stop), abs(r.target - r.entry)
    after = s[(s.index >= start) & (s.index <= end)]
    if after.empty or sdist <= 0: continue
    fill = after.ao.iloc[0] if sd > 0 else after.bo.iloc[0]
    R, kind, tx = V.play(after, sd, sdist, tdist, "bh" if sd > 0 else "ah", "bl" if sd > 0 else "al", fill, 0.0)
    pre = m[(m.index >= pd.Timestamp(f"{r.date} 07:00")) & (m.index < pd.Timestamp(f"{r.date} 08:00"))]
    noise = float((pre.high - pre.low).median()) if len(pre) > 20 else np.nan
    hist = m[m.index <= t]
    c15 = hist.close.resample("15min", label="left", closed="left").last().dropna(); e15 = c15.ewm(span=12, adjust=False).mean()
    c1h = hist.close.resample("60min", label="left", closed="left").last().dropna(); e1h = c1h.ewm(span=12, adjust=False).mean()
    daily = s.bc.resample("1D").agg(["max", "min", "last"]).dropna()
    path = after.loc[:tx] if kind != "EOD" else after
    adverse = (fill - path.bl.min()) if sd > 0 else (path.ah.max() - fill)                 # max adverse excursion before the exit
    later = after[after.index > tx]
    tgt_px = fill + sd * tdist
    hit_later = bool(((later.bh >= tgt_px).any() if sd > 0 else (later.al <= tgt_px).any())) if kind == "SL" and len(later) else np.nan
    five = hist.close.iloc[-6:] if len(hist) >= 6 else hist.close
    rows.append(dict(date=r.date, block=r.block, side=r.side, hhmm=r.hhmm, R=R, win=R > 0, kind=kind, stop=sdist, rr=tdist / sdist,
                     noise=noise, stop_noise=sdist / noise if noise else np.nan, mins=(tx - start).total_seconds() / 60 + 1,
                     with15=bool(sd * (c15.iloc[-1] - e15.iloc[-1]) > 0), with1h=bool(sd * (c1h.iloc[-1] - e1h.iloc[-1]) > 0),
                     chase=sd * (five.iloc[-1] - five.iloc[0]) / noise if noise else np.nan, mae_R=adverse / sdist, hit_later=hit_later,
                     flagged=int(r.flag) == 1 or int(r.pre) == 0))
D = pd.DataFrame(rows); D.to_csv("TRADE_FORENSICS.csv", index=False)
pd.set_option("display.width", 200)


def table(title, key):
    print("\n" + title)
    for k, g in D.groupby(key, observed=True):
        print("  %-22s n %3d  wins %3.0f%%  mean R %+.3f" % (k, len(g), 100 * g.win.mean(), g.R.mean()))


print("ALL %d trades: wins %.0f%%, mean R %+.3f (MT5 broker spot, his levels)" % (len(D), 100 * D.win.mean(), D.R.mean()))
table("by block", "block")
loss = D[D.kind == "SL"]
print("\nLOSSES stopped out: %d. Price reached his TARGET later the same day on %d of them (%.0f%%): direction right, stop wrong." % (
    len(loss), loss.hit_later.sum(), 100 * loss.hit_later.mean()))
print("  losses stopped within 10 minutes: %d of %d" % ((loss.mins <= 10).sum(), len(loss)))
D["stop_bucket"] = pd.cut(D.stop_noise, [0, 3, 5, 8, 12, 99], labels=["< 3x noise", "3-5x", "5-8x", "8-12x", "> 12x noise"])
table("by stop size vs the pre-entry 1-minute noise (median 07:00-07:59 candle range)", "stop_bucket")
table("side vs the 15m EMA12 at entry", D.with15.map({True: "with 15m trend", False: "against 15m trend"}))
table("side vs the 1h EMA12 at entry", D.with1h.map({True: "with 1h trend", False: "against 1h trend"}))
D["both"] = np.where(D.with15 & D.with1h, "with 15m AND 1h", np.where(~D.with15 & ~D.with1h, "against both", "mixed"))
table("trend alignment", "both")
D["chase_b"] = pd.cut(D.chase, [-99, -1, 1, 3, 99], labels=["entered on a pullback", "flat", "after a move (1-3x noise)", "chasing (> 3x noise)"])
table("the 5 minutes before entry, in the trade's direction", "chase_b")
D["minute"] = np.where(D.hhmm <= "08:01", "07:59-08:01 (first candle)", np.where(D.hhmm <= "08:09", "08:02-08:09", "08:10-08:14 (late)"))
table("entry timing (last visible candle)", "minute")
D["rr_b"] = pd.cut(D.rr, [0, 0.8, 1.2, 1.7, 99], labels=["< 0.8R target", "~1:1", "1.2-1.7R", "> 1.7R"])
table("target size", "rr_b")
w = D[D.win]
print("\nWINNERS: %d. How far against them before the target (MAE in R): median %.2f, 75%% within %.2f, %d of %d came within 0.2R of the stop" % (
    len(w), w.mae_R.median(), w.mae_R.quantile(0.75), (w.mae_R >= 0.8).sum(), len(w)))
