"""DESCRIPTIVE ONLY (20 Oct, the trader: put limit orders on the prices so spreads do not cost): his 49 FX Replay trades with a stop on MT5 broker bid / ask, market entry against a buy limit at the chart (bid) price cancelled after 5 minutes; sells fill at once. python manual_limit_entries.py > MANUAL_LIMIT_ENTRIES_OUTPUT.txt. Not a test: n 24 buys, in-sample, fill-minute handled two ways."""
import pandas as pd, numpy as np
d = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet").sort_values("t").reset_index(drop=True)
d["lis"] = pd.to_datetime(d.t, unit="s") - pd.Timedelta(hours=2)
pos = {t: i for i, t in enumerate(d.lis)}
bl, bh, al, ah, bc, ac = (d[c].to_numpy() for c in ("bl", "bh", "al", "ah", "bc", "ac"))
f = pd.read_csv("FXREPLAY_TRADES_2026-10-20.csv"); f = f[f.stop.notna() & (f.stop > 0)].copy()
f["t"] = pd.to_datetime(f.chart_entry).dt.floor("min")
def run(i0, side, E, S, T, mode, valid=5, fill_min_target=False):
    sd = abs(E - S)
    if side == "Buy":
        if mode == "market": fill = ac[i0]; start = i0 + 1
        else:
            k = next((k for k in range(i0 + 1, i0 + 1 + valid) if al[k] <= E), None)
            if k is None: return None
            fill = E; start = k + 1 if not fill_min_target else k
            if bl[k] <= S: return -1.0, True  # stopped in the fill minute (conservative)
        for k in range(start, start + 60):
            if bl[k] <= S: return (S - fill) / sd, True
            if bh[k] >= T: return (T - fill) / sd, True
        return (bc[start + 59] - fill) / sd, True
    else:
        fill = bc[i0]; start = i0 + 1   # a sell limit at the current bid fills at once: same as market
        for k in range(start, start + 60):
            if ah[k] >= S: return (fill - S) / sd, True
            if al[k] <= T: return (fill - T) / sd, True
        return (fill - ac[start + 59]) / sd, True
rows = []
for _, r in f.iterrows():
    i0 = pos[r.t]; off = r.entry - bc[i0]; E, S, T = bc[i0], r.stop - off, r.target - off
    m = run(i0, r.side, E, S, T, "market"); lc = run(i0, r.side, E, S, T, "limit"); lo = run(i0, r.side, E, S, T, "limit", fill_min_target=True)
    rows.append(dict(side=r.side, R_chart=r.R_fxr, R_mkt=m[0], filled=lc is not None, R_lim_cons=lc[0] if lc else np.nan, R_lim_opt=lo[0] if lo else np.nan, spread=ac[i0]-bc[i0]))
x = pd.DataFrame(rows)
print("his %d trades with a stop, XAUUSD MT5 broker bid / ask, level = the bid close of his signal candle (chart price), exits on the real bid / ask, stop / target levels shifted from his FX Replay prices" % len(x))
print("chart-price R (FX Replay, no spread): mean %+.3f | MT5 broker bid/ask market entry: mean %+.3f" % (x.R_chart.mean(), x.R_mkt.mean()))
for s in ("Buy", "Sell"):
    g = x[x.side == s]
    print("  %-4s n %2d | chart R %+.3f | market R %+.3f | buy-limit at the chart price: filled %d (%.0f%%)" % (s, len(g), g.R_chart.mean(), g.R_mkt.mean(), g.filled.sum(), 100*g.filled.mean()) if s == "Buy" else "  %-4s n %2d | chart R %+.3f | market R %+.3f | a sell limit at the bid fills at once, same as market" % (s, len(g), g.R_chart.mean(), g.R_mkt.mean()))
b = x[x.side == "Buy"]
print("\nBUYS (n %d): market R %+.3f (wins %d)" % (len(b), b.R_mkt.mean(), (b.R_mkt > 0).sum()))
fl = b[b.filled]
print("  limit at the chart price, cancelled after 5 min: filled %d | their market R %+.3f -> limit R %+.3f (conservative fill minute) / %+.3f (optimistic)" % (len(fl), fl.R_mkt.mean(), fl.R_lim_cons.mean(), fl.R_lim_opt.mean()))
nf = b[~b.filled]
print("  NOT filled %d: their market R %+.3f (wins %d of %d) -> a limit order skips these" % (len(nf), nf.R_mkt.mean() if len(nf) else np.nan, (nf.R_mkt > 0).sum(), len(nf)))
tot_cons = np.concatenate([x[x.side == "Sell"].R_mkt.to_numpy(), fl.R_lim_cons.to_numpy()]); tot_opt = np.concatenate([x[x.side == "Sell"].R_mkt.to_numpy(), fl.R_lim_opt.to_numpy()])
print("\nALL trades taken (sells at market + buys that fill): n %d | market-all mean R %+.3f | with buy limits: %+.3f (cons) / %+.3f (opt) | sum R market-all %+.2f vs limits %+.2f / %+.2f" % (len(tot_cons), x.R_mkt.mean(), tot_cons.mean(), tot_opt.mean(), x.R_mkt.sum(), tot_cons.sum(), tot_opt.sum()))
