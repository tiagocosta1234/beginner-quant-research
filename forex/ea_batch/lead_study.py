"""Diagnostic study of the GBPUSD realised-exit lead (Exp_JFatl_Digit_System mirrored, TP 40 / SL 160) alone and next to the pair: why it adds only ~USD 190 a month at MT5 broker limits.   python -m forex.ea_batch.lead_study   Written 2026-10-08 at the trader's request; output in lead_study.out; not committed."""
import numpy as np, pandas as pd
from forex.ea_batch import inv_realize as IR, mt5_trio_exact as TE
from forex.intraday_lab import sdb
TP, SL = 40, 160
m = sdb.load_m1("GBPUSD"); frames = []
for y in IR.YEARS:
    tr = IR.simulate(m, IR.entries("15888", "GBPUSD", y), TP, SL); tr["y"] = y; frames.append(tr)
T = pd.concat(frames, ignore_index=True)
T["kind"] = np.where(T.pnl > 30, "TP", np.where(T.pnl < -140, "SL", "TIME")); T["d_in"] = pd.to_datetime(T.t0, unit="s"); T["d_out"] = pd.to_datetime(T.t1, unit="s"); T["hold_h"] = (T.t1 - T.t0) / 3600
print(f"##### A. THE LEAD ALONE: Exp_JFatl_Digit_System entries on GBPUSD, mirrored, TP {TP} / SL {SL} pips, 0.10 lot (USD 1 a pip), MT5 M1 bid/ask, 2023-2025")
for y, g in T.groupby("y"):
    w = g[g.pnl > 0]; l = g[g.pnl < 0]
    print(f"{y}: trades {len(g):3d} | net {g.pnl.sum():7,.0f} | win {100*(g.pnl>0).mean():4.1f}% | TP {int((g.kind=='TP').sum())}  SL {int((g.kind=='SL').sum())}  time-stop {int((g.kind=='TIME').sum())} | months with entries {g.d_in.dt.month.nunique()} of 12 | avg win {w.pnl.mean():5.1f} avg loss {l.pnl.mean():7.1f} | median hold {g.hold_h.median():5.1f} h")
w = T[T.pnl > 0]; l = T[T.pnl < 0]
print(f"ALL: {len(T)} trades, net {T.pnl.sum():,.0f}, win {100*(T.pnl>0).mean():.1f}%, avg win {w.pnl.mean():.1f}, avg loss {l.pnl.mean():.1f}, payoff {w.pnl.mean()/abs(l.pnl.mean()):.2f}, expectancy/trade {T.pnl.mean():.1f}, break-even win rate for this payoff {100*abs(l.pnl.mean())/(w.pnl.mean()+abs(l.pnl.mean())):.1f}%, net per year {T.pnl.sum()/3:,.0f} = {T.pnl.sum()/36:,.0f} a month on average (but entries only in some months)")
print(f"profit that comes from SL-free stretches: SL losses total {T[T.kind=='SL'].pnl.sum():,.0f} vs TP gains {T[T.kind=='TP'].pnl.sum():,.0f}; one SL loss erases {abs(l.pnl.mean())/w.pnl.mean():.1f} TP wins")
# loss clusters: SL exits by day
sl = T[T.kind == "SL"]; byday = sl.groupby(sl.d_out.dt.date).pnl.agg(["count", "sum"]).sort_values("sum").head(8)
print("worst SL days (number of stops hit on the same day, USD):", [(str(d), int(r["count"]), int(r["sum"])) for d, r in byday.iterrows()])
print(f"SL exits {len(sl)}; share of SL exits that happen on a day with >= 2 SL exits: {100*(sl.groupby(sl.d_out.dt.date).pnl.transform('count')>=2).mean():.0f}%")
ev = np.r_[np.ones(len(T)), -np.ones(len(T))]; ts = np.r_[T.t0.values, T.t1.values]; o = np.argsort(ts, kind="stable"); conc = np.cumsum(ev[o]); print(f"concurrent open positions: max {int(conc.max())}, 90th percentile while any is open {np.percentile(conc[conc>0],90):.0f}, share of time with >= 6 open {100*(conc>=6).mean():.0f}% of event times")
# worst floating (lead alone) from the exact minute series
li, le, lr = TE.lead_minute(TP, SL); fl = pd.Series(le - lr, index=li); print(f"lead alone: worst floating loss at any minute {fl.min():,.0f} (0.10 lot), at 0.05 {fl.min()/2:,.0f}, at 0.20 {fl.min()*2:,.0f}")
dd = fl.groupby(fl.index.date).min().sort_values().head(5); print("five worst floating days (0.10 lot):", [(str(d), int(v)) for d, v in dd.items()])
print("\n##### B. THE LEAD NEXT TO THE PAIR (pair 0.5/0.5 = SDB 0.103 + XAU5 0.035 lot, swap-free, exact minute combination, MT5 broker rules)")
lead = (li, le, lr); res = {}
for L in (0.0, 0.05, 0.10):
    bd, V, MB = TE.run_pair_plus_lead(0.5, lead, L); res[L] = (bd, V, MB)
bd, V0, M0 = res[0.0]; win = np.asarray((bd >= pd.Timestamp("2023-01-01")) & (bd <= pd.Timestamp("2025-12-31"))); nm = win.sum() / 21
for L in (0.0, 0.05, 0.10):
    _, V, MB = res[L]; print(f"L {L:4.2f}: {V[win].sum()/nm:7,.0f} a month | worst day {V[win].min():7,.0f} | worst floating day {MB[win].min():7,.0f} | days with floating loss >= 1.5% {int((MB[win]<=-1500).sum())} | >= 2.0% {int((MB[win]<=-2000).sum())} | >= 2.5% {int((MB[win]<=-2500).sum())}")
V1 = res[0.10][1] - V0; ok = win & (V1 != 0)
print(f"daily correlation lead vs pair (days the lead moved): {np.corrcoef(V1[ok], V0[ok])[0,1]:+.2f}; lead moved on {int(ok.sum())} of {int(win.sum())} days")
bad = win & (V0 <= np.percentile(V0[win], 5)); print(f"on the pair's worst 5% days (n={int(bad.sum())}, mean {V0[bad].mean():,.0f}) the lead (0.10) made on average {V1[bad].mean():+,.0f}; on the lead's worst 5% days (n={int((win&(V1<=np.percentile(V1[win],5))).sum())}) the pair made {V0[win&(V1<=np.percentile(V1[win],5))].mean():+,.0f}")
M10, M05 = res[0.10][2], res[0.05][2]
new = win & (M10 <= -2500) & (M0 > -2500)
print(f"days that breach the 2.5% daily line ONLY because of the lead at 0.10: {int(new.sum())}")
for i in np.flatnonzero(new)[:8]: print(f"   {bd[i].date()}: pair alone floating {M0[i]:,.0f}, with lead 0.05 {M05[i]:,.0f}, with lead 0.10 {M10[i]:,.0f}, closed P&L pair {V0[i]:,.0f} lead {V1[i]:+,.0f}")
print(f"\nmarginal economics: +0.05 lot of lead = +{(res[0.05][1][win].sum()-V0[win].sum())/nm:,.0f} a month for {M0[win].min()-M05[win].min():,.0f} more worst floating day ({(M0[win].min()-M05[win].min())/((res[0.05][1][win].sum()-V0[win].sum())/nm):.1f} USD of worst-day exposure per USD of monthly profit); the pair itself: {V0[win].sum()/nm:,.0f} a month for {-M0[win].min():,.0f} ({-M0[win].min()/(V0[win].sum()/nm):.1f})")
