import numpy as np, pandas as pd
parts = []
for y in ("2022", "2023", "2024", "2025", "2026"):
    d = pd.read_csv(f"forex/early_mt5/ea_batch/results_{y}/mkt_xau5min.csv"); d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S"); o = d[d.direction == "out"].reset_index(drop=True); i = d[d.direction == "in"].reset_index(drop=True); n = min(len(i), len(o))
    parts.append(pd.DataFrame({"t_in": i.time[:n], "t_out": o.time[:n], "entry": i.price[:n], "exit": o.price[:n], "profit": o.profit[:n] + o.commission[:n], "year": y}))
T = pd.concat(parts, ignore_index=True); move = T.exit - T.entry; T["side"] = np.where(T.profit * move >= 0, 1.0, -1.0); T.loc[move == 0, "side"] = 1.0
T["pnl_oz"] = T.side * move; T["hold_h"] = (T.t_out - T.t_in).dt.total_seconds() / 3600
print(f"XAU5 trades 2022-26 (MT5 broker real-tick runs, 0.01 lot): {len(T)} | net USD {T.profit.sum():,.0f} | win rate {100*(T.pnl_oz>0).mean():.1f}% | longs {100*(T.side>0).mean():.0f}%")
print("per year: ", T.groupby("year").agg(n=("pnl_oz", "size"), net=("profit", "sum"), win=("pnl_oz", lambda x: (x > 0).mean()), longs=("side", lambda x: (x > 0).mean())).round(2).to_dict("index"))
print("hold hours: median %.1f, p25 %.1f, p75 %.1f, p95 %.1f" % tuple(np.percentile(T.hold_h, [50, 25, 75, 95])))
h = T.t_in.dt.hour; print("entries by server hour:", h.value_counts().sort_index().to_dict())
print("win rate / mean USD per oz by entry server hour (n>=60):", {int(k): (round(100 * v.pnl_oz.gt(0).mean()), round(v.pnl_oz.mean(), 2), len(v)) for k, v in T.groupby(h) if len(v) >= 60})
M = pd.read_parquet("forex/early_mt5/data_mt5/XAUUSD_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc"]).sort_values("t").reset_index(drop=True); tm = M.t.to_numpy()
tin = ((T.t_in - pd.Timestamp("1970-01-01")).dt.total_seconds()).astype("int64").to_numpy(); idx = np.searchsorted(tm, tin) - 1; ok = idx > 1440
c = M.bc.to_numpy(); hi = pd.Series(M.bh).rolling(1440, min_periods=1440).max().to_numpy(); lo = pd.Series(M.bl).rolling(1440, min_periods=1440).min().to_numpy()
for nm, lag in (("15m", 15), ("1h", 60), ("4h", 240)):
    prev = (c[idx] - c[np.maximum(idx - lag, 0)]) / c[idx] * 1e4; sg = T.side.to_numpy() * prev        # >0: the trade goes WITH the preceding move
    m = ok & np.isfinite(sg); w = T.pnl_oz.to_numpy() > 0
    print(f"preceding {nm} move vs trade direction: with-trend share {100*(sg[m] > 0).mean():.0f}% | win rate with {100*w[m & (sg > 0)].mean():.0f}% vs against {100*w[m & (sg <= 0)].mean():.0f}% | mean USD/oz with {T.pnl_oz.to_numpy()[m & (sg > 0)].mean():+.2f} vs against {T.pnl_oz.to_numpy()[m & (sg <= 0)].mean():+.2f}")
pos = (c[idx] - lo[idx]) / (hi[idx] - lo[idx]); m = ok & np.isfinite(pos); L = T.side.to_numpy() > 0
print("position in the previous 24h range (0 = at the low, 1 = at the high): longs median %.2f, shorts median %.2f" % (np.median(pos[m & L]), np.median(pos[m & ~L])))
for nm, sel in (("longs", L), ("shorts", ~L)):
    q = pd.qcut(pd.Series(pos[m & sel]), 4, labels=False); print(f"  {nm}: win rate by range-position quartile", [round(100 * (T.pnl_oz.to_numpy()[m & sel][q == k] > 0).mean()) for k in range(4)], "mean USD/oz", [round(T.pnl_oz.to_numpy()[m & sel][q == k].mean(), 2) for k in range(4)])
T = T.sort_values("t_in").reset_index(drop=True); gap = T.t_in.diff().dt.total_seconds() / 60; same = T.side == T.side.shift(); print("gap to the previous entry (minutes): median %.0f, share of entries within 60 min of the previous one %.0f%%, same direction as previous %.0f%%" % (gap.median(), 100 * (gap < 60).mean(), 100 * same.mean()))
conc = pd.concat([pd.Series(1, index=T.t_in), pd.Series(-1, index=T.t_out)]).sort_index().cumsum(); print("concurrent positions: max %d, 95th pct %d, share of time with >= 3 open %.0f%%" % (conc.max(), np.percentile(conc, 95), 100 * (conc >= 3).mean()))
