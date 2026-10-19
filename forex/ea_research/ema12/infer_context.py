"""Which ICT-style context (PO3 / daily open / Asian range / previous-day levels) explains the trader's direction on the 30 dated gold trades? Descriptive, no P&L."""
import numpy as np, pandas as pd
from ema12_test import load
O = pd.read_csv("replay_mt5.csv"); g = load("XAUUSD", last_day="2025-12-31")
g["date"] = pd.to_datetime(g.day)
by_day = {d: x for d, x in g.groupby("day")}
days_sorted = sorted(by_day)
def dopen(d):                      # MT5/OANDA daily candle opens 22:00 local = 00:00 server
    x = by_day[d]; y = x[x.hm >= 0]; return y.mid.iloc[0]
rows = []
for _, r in O.iterrows():
    d = pd.Timestamp(r.day).date(); x = by_day[d]; i_loc = x.index[x.hm == int(r.hm)][0]
    side = 1 if r.side == "L" else -1; px = g.mid[i_loc - 1]
    do = dopen(d)
    asia = x[(x.hm >= 120) & (x.hm < 600)]; ah, al = asia.mh.max(), asia.ml.min()
    since = x[(x.hm >= 600) & (x.index < i_loc)]                     # from the London open up to the entry bar
    sw_hi = since.mh.max() > ah; sw_lo = since.ml.min() < al
    k = days_sorted.index(d); pdx = by_day[days_sorted[k - 1]]; pdh, pdl = pdx.mh.max(), pdx.ml.min()
    sw_pdh = x[(x.index < i_loc)].mh.max() > pdh; sw_pdl = x[(x.index < i_loc)].ml.min() < pdl
    rows.append(dict(k=r.k, ses=r.ses, side=side, above_dopen=int(np.sign(px - do)), dopen_dist=px - do, sw_asia_hi=sw_hi, sw_asia_lo=sw_lo, sw_pdh=sw_pdh, sw_pdl=sw_pdl))
F = pd.DataFrame(rows); pd.set_option("display.width", 200)
print(F.round(1).to_string(index=False))
n = len(F)
def agree(mask, pred): 
    m = mask & (pred != 0); return int(((F.side == pred) & m).sum()), int(m.sum())
print("\nrule -> agrees / applicable (of 30; chance = half of applicable)")
print("short above the daily open, long below (mean-reversion to the open):", agree(pd.Series(True, index=F.index), -F.above_dopen))
print("long above the daily open, short below (follow the daily bias)      :", agree(pd.Series(True, index=F.index), F.above_dopen))
pa = np.where(F.sw_asia_hi & ~F.sw_asia_lo, -1, np.where(F.sw_asia_lo & ~F.sw_asia_hi, 1, 0)); print("fade the Asian-range sweep (short after high sweep, long after low sweep):", agree(pd.Series(True, index=F.index), pd.Series(pa)))
print("   follow the Asian-range break instead:", agree(pd.Series(True, index=F.index), pd.Series(-pa)))
pp = np.where(F.sw_pdh & ~F.sw_pdl, -1, np.where(F.sw_pdl & ~F.sw_pdh, 1, 0)); print("fade the previous-day high/low sweep:", agree(pd.Series(True, index=F.index), pd.Series(pp)), "| follow:", agree(pd.Series(True, index=F.index), pd.Series(-pp)))
print("share of trades short with price above the daily open: %.0f%% | long with price below: %.0f%%" % (100 * ((F.side < 0) & (F.above_dopen > 0)).sum() / (F.side < 0).sum(), 100 * ((F.side > 0) & (F.above_dopen < 0)).sum() / (F.side > 0).sum()))
