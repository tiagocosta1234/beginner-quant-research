"""
Round 341 (2026-10-04, DESCRIPTIVE, no ledger row, k stays 2042): what would an average of +4% a month take, using the best lead we have, under MT5 broker's loss limits?
the trader: "what about avg 4% a month?". The lead: follow the 09:30 -> 10:30 move at 10:30 inside the Round 324 table geometry (stop 0.25 x mean RTH range of 20 sessions, target k x stop, exit 15:59), MT5 broker real fills, k = 2.5 (the middle table target; not selected), net R per trade;
US100 alone and the four US indices together (risk split equally; US2000 from 2022). One day = one trade per index at 10:30; the account risks r of the balance per index-trade (the R multiple is the loss at the stop = r).
Reported: mean month, share of months >= +4%, worst month, worst day, max end-of-day drawdown, days below -3% (MT5 broker daily loss), and the share of rolling 12-month windows that touch MT5 broker's 3% daily loss or 10% end-of-day trailing limit. Descriptive: the lead itself is unconfirmed and negative in 2026.
"""
import os, sys
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import round324_post_open_drive_entry as Q

K = 2.5
def follow_R(sym):
    df = Q.day_table_T(sym, Q.TS["1030"]); df = df[df.move != 0]
    s = np.sign(df.move.values)
    return pd.Series(np.where(s > 0, df[f"R_1_{K}"].values, df[f"R_-1_{K}"].values), index=df.index)

R = {s: follow_R(s) for s in ("NQ", "ES", "YM", "RTY")}
print("mean net R per trade (k=2.5): " + ", ".join(f"{s} {r.mean():+.3f} (sd {r.std():.2f}, n {len(r)})" for s, r in R.items()))

def run(series_list, risk):
    X = pd.concat(series_list, axis=1)                 # days x instruments
    daily = (X.fillna(0.0) * risk / len(series_list)).sum(axis=1) if len(series_list) > 1 else X.iloc[:, 0] * risk
    bal = (1 + daily).cumprod()
    eod_dd = (bal.cummax() - bal) / bal.cummax()
    mo = (1 + daily).groupby(daily.index.to_period("M")).prod() - 1
    # rolling 12-month windows: breach if daily loss <= -3% or EOD trailing drawdown >= 10% inside the window
    wins = 0; breach = 0
    months = sorted(mo.index)
    for i in range(0, len(months) - 11):
        a, b = months[i].start_time, months[i + 11].end_time
        d = daily[(daily.index >= a) & (daily.index <= b)]
        bl = (1 + d).cumprod(); dd = ((bl.cummax().clip(lower=1.0) - bl) / bl.cummax().clip(lower=1.0))
        wins += 1; breach += int((d <= -0.03).any() or (dd >= 0.10).any())
    return dict(mean_month=mo.mean(), share_ge4=(mo >= 0.04).mean(), worst_month=mo.min(), worst_day=daily.min(), max_dd=eod_dd.max(), days_below_3=int((daily <= -0.03).sum()), breach12=breach / wins, n_months=len(mo))

print(f"\n{'sleeve':<22}{'risk':>6}{'mean mo':>9}{'>=4% mo':>9}{'worst mo':>10}{'worst day':>10}{'max DD':>8}{'days<-3%':>9}{'12m breach':>11}")
for name, lst in (("US100 only", [R["NQ"]]), ("4 indices", [R["NQ"], R["ES"], R["YM"], R["RTY"]])):
    for risk in (0.005, 0.01, 0.02, 0.04, 0.08):
        r = run(lst, risk)
        print(f"{name:<22}{risk*100:>5.1f}%{r['mean_month']*100:>8.2f}%{r['share_ge4']*100:>8.0f}%{r['worst_month']*100:>9.1f}%{r['worst_day']*100:>9.1f}%{r['max_dd']*100:>7.1f}%{r['days_below_3']:>9}{r['breach12']*100:>10.0f}%")
# by year at 1% risk, 4 indices
X = pd.concat([R["NQ"], R["ES"], R["YM"], R["RTY"]], axis=1).fillna(0.0); d = (X * 0.01 / 4).sum(axis=1)
mo = (1 + d).groupby(d.index.to_period("M")).prod() - 1
print("\n4 indices at 1% risk, mean month by year:", {int(y): round(float(v) * 100, 2) for y, v in mo.groupby(mo.index.year).mean().items()})
