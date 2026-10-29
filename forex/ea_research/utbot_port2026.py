"""UT Bot portfolio on 2026 (EXPLORATORY: opens the sealed 2026 data for UT Bot; recorded in UTBOT_PORT2026_RESULT.md).
Every trade risks 500 USD (position sized so that a move of Key x ATR from the signal close costs 500), account 100,000, no compounding.
A = the 71 cells profitable in both DEV and VAL (selected before 2026); B = default setting, H1, all 46 symbols. python -m forex.ea_research.utbot_port2026"""
import sys, glob, os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.argv = [sys.argv[0]]
from forex.ea_research import utbot as U

RISK, START = 500.0, 100000.0
T0, T1 = pd.Timestamp("2026-01-01").timestamp(), pd.Timestamp("2026-10-03").timestamp()
VAR = {"base": (1.0, False), "k2": (2.0, False), "k3": (3.0, False), "ha": (1.0, True)}
a = pd.read_csv("data/tmp/utbot_cells.csv"); a["var"] = "base"; b = pd.read_csv("data/tmp/utbot_variant_cells.csv")
R0 = pd.concat([a, b]); A = R0[(R0.mu_DEV > 0) & (R0.mu_VAL > 0)][["sym", "tf", "var"]].values.tolist()
syms = sorted(os.path.basename(f).replace("_M1_rates.parquet", "") for f in glob.glob(U.DATA + "*_M1_rates.parquet"))
B = [[s, "H1", "base"] for s in syms]
cache = {}


def cell_trades(sym, tf, var):
    if sym not in cache:
        d = pd.read_parquet(U.DATA + f"{sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
        d = d[(d.t < T1) & (d.bo > 0) & (d.ao >= d.bo)]
        cache[sym] = pd.DataFrame({"t": d.t.to_numpy(), "bo": d.bo.to_numpy(), "ao": d.ao.to_numpy(), "mo": ((d.bo + d.ao) / 2).to_numpy(), "mh": ((d.bh + d.ah) / 2).to_numpy(), "ml": ((d.bl + d.al) / 2).to_numpy(), "mc": ((d.bc + d.ac) / 2).to_numpy()})
    bars = U.bars(cache[sym], U.TFS[tf]); key, ha = VAR[var]
    src = ((bars.mo + bars.mh + bars.ml + bars.mc) / 4).to_numpy() if ha else bars.mc.to_numpy()
    cl = bars.mc.to_numpy(); cp = np.r_[cl[0], cl[:-1]]
    tr = np.maximum.reduce([bars.mh.to_numpy() - bars.ml.to_numpy(), np.abs(bars.mh.to_numpy() - cp), np.abs(bars.ml.to_numpy() - cp)])
    atr = pd.Series(tr).ewm(alpha=1.0 / U.ATRP, adjust=False).mean().to_numpy()
    sg = U.signals(bars, key, ha)
    t, bo, ao = bars.t.to_numpy(), bars.bo.to_numpy(), bars.ao.to_numpy()
    nxt = U.allowed_next(t)
    idx = np.nonzero(sg)[0]
    ex = nxt[np.minimum(idx + 1, len(t))]; sd = sg[idx]; keep = ex < len(t); ex, sd, idx = ex[keep], sd[keep], idx[keep]
    last = np.r_[ex[1:] != ex[:-1], True]; e, s, si = ex[last], sd[last], idx[last]
    chg = np.r_[True, s[1:] != s[:-1]]; e, s, si = e[chg], s[chg], si[chg]
    if len(e) < 2:
        return []
    ent = np.where(s[:-1] > 0, ao[e[:-1]], bo[e[:-1]]); ext = np.where(s[:-1] > 0, bo[e[1:]], ao[e[1:]])
    ret = np.where(s[:-1] > 0, ext / ent - 1, ent / ext - 1)
    risk_frac = key * atr[si[:-1]] / cl[si[:-1]]
    te, tx = t[e[:-1]], t[e[1:]]
    m = (te >= T0) & (tx < T1) & (risk_frac > 0)
    notional = RISK / risk_frac[m]
    return list(zip([sym] * m.sum(), [tf] * m.sum(), [var] * m.sum(), te[m], tx[m], s[:-1][m], ret[m] * 1e4, ret[m] * notional, notional, ret[m] / risk_frac[m]))


def run(cells, name):
    rows = []
    for sym, tf, var in cells:
        rows += cell_trades(sym, tf, var)
    T = pd.DataFrame(rows, columns=["sym", "tf", "var", "te", "tx", "side", "bp", "pnl", "notional", "R"]).sort_values("tx").reset_index(drop=True)
    T["exit"] = pd.to_datetime(T.tx, unit="s"); T["day"] = T.exit.dt.normalize()
    eq = START + T.pnl.cumsum()
    daily = T.groupby("day").pnl.sum()
    days = pd.date_range("2026-01-01", "2026-10-02", freq="D"); days = days[days.dayofweek < 5]
    dd = daily.reindex(days).fillna(0.0)
    ev = np.r_[T.te.to_numpy(), T.tx.to_numpy()]; dv = np.r_[T.notional.to_numpy(), -T.notional.to_numpy()]; o = np.argsort(ev, kind="stable")
    conc = np.cumsum(np.where(dv[o] > 0, 1, -1)); gross = np.cumsum(dv[o])
    peak = np.maximum.accumulate(eq.values); mdd = float((peak - eq.values).max())
    w = T[T.pnl > 0].pnl.sum(); l = -T[T.pnl < 0].pnl.sum()
    s = dict(name=name, cells=len(cells), trades=len(T), win=(T.pnl > 0).mean() * 100, total=T.pnl.sum(), R_total=T.R.sum(), avgR=T.R.mean(), pf=w / l if l else np.nan,
             maxdd=mdd, best_day=dd.max(), worst_day=dd.min(), days_le_2000=int((dd <= -2000).sum()), days_le_2500=int((dd <= -2500).sum()),
             sharpe=dd.mean() / dd.std() * np.sqrt(252) if dd.std() > 0 else np.nan, max_open=int(conc.max()), max_gross_notional=float(gross.max()), eq_end=float(eq.iloc[-1]))
    mo = T.groupby(T.exit.dt.to_period("M")).pnl.sum()
    return T, eq, s, mo


outs = {}
for name, cells in (("A: 71 selected cells", A), ("B: default H1, all 46 symbols", B)):
    outs[name] = run(cells, name)
    s = outs[name][2]
    print(f"\n== {name} ({s['cells']} cells), 2026-01-01..2026-10-02, 500 USD risk per trade, account 100,000")
    print(f"trades {s['trades']} | win {s['win']:.1f}% | total {s['total']:+,.0f} USD ({s['R_total']:+.0f} R, avg {s['avgR']:+.3f} R) | PF {s['pf']:.2f} | end equity {s['eq_end']:,.0f}")
    print(f"max drawdown (closed trades) {s['maxdd']:,.0f} | best day {s['best_day']:+,.0f} | worst day {s['worst_day']:+,.0f} | days <= -2,000: {s['days_le_2000']} | days <= -2,500 (MT5 broker hard line): {s['days_le_2500']} | daily Sharpe {s['sharpe']:.2f}")
    print(f"peak simultaneous open trades {s['max_open']} | peak gross notional {s['max_gross_notional']:,.0f} USD ({s['max_gross_notional'] / START:.0f}x the account)")
    print("monthly P&L:", {str(k): round(v) for k, v in outs[name][3].items()})
    print("by symbol class, total USD:", outs[name][0].assign(cls=np.where(outs[name][0].sym.isin(['SP', 'NSDQ', 'DOW', 'DAX', 'NIKKEI', 'ASX']), 'index', np.where(outs[name][0].sym.isin(['XAUUSD', 'XAGUSD', 'BRENT', 'WTI']), 'metal/oil', np.where(outs[name][0].sym.str.contains('BTC|ETH|SOL|XRP|BNB|ADA|LTC|BCH|DOGE'), 'crypto', 'FX')))).groupby('cls').pnl.sum().round(0).to_dict())
fig, axs = plt.subplots(1, 2, figsize=(16, 5.6), sharey=False)
for ax, (name, (T, eq, s, mo)) in zip(axs, outs.items()):
    ax.step(T.exit, eq.values, where="post", color="#0969da", lw=1.4)
    ax.axhline(START, color="gray", lw=.8); ax.axhline(START * 0.92, color="#cf222e", ls="--", lw=.8)
    ax.set_title(f"{name}: {s['trades']} trades, {s['total']:+,.0f} USD, max DD {s['maxdd']:,.0f}", fontsize=10); ax.grid(alpha=.25); ax.set_ylabel("closed-trade equity, USD")
fig.suptitle("UT Bot, each trade risks 500 USD (Key x ATR), account 100,000, 2026-01-01..2026-10-02, real bid/ask (EXPLORATORY: 2026 opened)", fontsize=11)
fig.tight_layout(); fig.savefig("forex/ea_research/UTBOT_PORT2026_EQUITY.png", dpi=100)
for name, (T, eq, s, mo) in outs.items():
    T.to_csv(f"data/tmp/utbot_port2026_{name[0]}.csv", index=False)
