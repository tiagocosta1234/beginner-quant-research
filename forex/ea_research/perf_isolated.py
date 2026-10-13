"""Each strategy ALONE, every trade risking 500 USD and then 1,000 USD (no guard, no news-flat, no other strategy).  the trader 2026-10-12.
"Risk per trade" = the loss if the trade's stop is hit: SDB stop = 1.9% of the entry (exact); ManualDip and US RSI(2) dips: stop at 3 sigma60 (exact, as built); XAU5 (closed source,
swing stop not recorded): the size is scaled so that its MEDIAN losing trade equals the risk (approximation, declared). ManualDip / RSI(2) P&L x0.75 (real-tick haircut used in all planning).
Pools: FT 2022-01 .. 2026-09 (1,225 days) and MT5 12 months (real ticks).   python -m forex.ea_research.perf_isolated"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from forex.ea_research import combo_grid as G, clean_boot_lib as L, dip_addon as DA, fincept_mt5_verify as V
from forex.ea_batch.mt5_mc_config import CH

KSTOP = 3.0; HERE = os.path.dirname(os.path.abspath(__file__))


def scaled_gold(pool, which, R):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); t = L.ea_trades(src, which, CH[which], lo)
    if which == "sdb": k = R / (0.019 * t["entry"] * t["q"])
    else:
        loss = np.abs(t["pl"][t["pl"] < 0]); k = np.full(len(t["pl"]), R / np.median(loss))
    t = dict(t); t["q"] = t["q"] * k; t["pl"] = t["pl"] * k
    r = L.C.simulate(G.bars, t, lo, hi, None, 1e12); return t["pl"], dict(V=r["V"], B=r["B"], days=r["days"], times=t["out_s"])


def dip_like(trades_df, bars, R, pool_days):
    T = trades_df.copy(); T["n"] = 1; T["q"] = np.minimum(R / (KSTOP * T.sd), DA.CAP) / T.e; T["stop"] = T.e * (1 - KSTOP * T.sd); T, D = DA.day_arrays(T, bars)
    D = D * 0.75; pl = T.pl.values * 0.75; X = D.reindex(pool_days).fillna(0.0); return pl, dict(V=X.V.values, B=X.B.values, days=pool_days, times=None)


def rsi2_table():
    rows, bars = [], {}
    for m in ("SP", "NSDQ", "DOW"):
        d = DA.load(m); bars[m] = d; s = d[d.hm == 1559].drop_duplicates("date").set_index("date"); b, a, t = s.bo, s.ao, s.t
        r2 = V.rsi(b); s200, s5 = b.rolling(200).mean(), b.rolling(5).mean(); sd = b.pct_change().rolling(60, min_periods=40).std(); i = 200
        while i < len(b) - 1:
            if r2.iat[i] < 10 and b.iat[i] > s200.iat[i] and np.isfinite(sd.iat[i]):
                e = i; j = i + 1
                while j < len(b) - 1 and not (b.iat[j] > s5.iat[j] or r2.iat[j] > 70 or j - e >= 5): j += 1
                rows.append(dict(mkt=m, date=b.index[e], t_in=int(t.iat[e]), t_out=int(t.iat[j]), e=float(a.iat[e]) * (1 + DA.SLIP), sd=float(sd.iat[i]))); i = j + 1
            else: i += 1
    return pd.DataFrame(rows), bars


def stats(pl, S, label):
    V_ = pd.Series(S["V"], index=pd.to_datetime(np.asarray(S["days"]) * 86400, unit="s")); B_ = np.asarray(S["B"]); eq = V_.cumsum(); mo = V_.groupby(V_.index.to_period("M")).sum()
    w, l = pl[pl > 0].sum(), -pl[pl < 0].sum()
    return dict(strategy=label, trades=len(pl), per_year=round(len(pl) / (len(V_) / 252), 0), win=round(100 * (pl > 0).mean()), avg_trade=round(pl.mean()), pf=round(w / l, 2) if l else np.inf, net=round(V_.sum()),
                per_month=round(V_.sum() / max(len(mo), 1)), months_pos=round(100 * (mo > 0).mean()), max_dd=round((eq.cummax() - eq).max()), worst_day=round(B_.min()), days_le_1500=int((B_ <= -1500).sum()), days_le_2500=int((B_ <= -2500).sum())), eq


if __name__ == "__main__":
    DA.RISK = 500.0; T0, bb = DA.trades(); R2T, R2B = rsi2_table(); out = {}
    for pool in ("FT", "MT5"):
        src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); days = G.pair_series(pool, 0, 0, 1500.0)["days"]
        for R in (500, 1000):
            rows, curves = [], {}
            for label, fn in (("ManualSDB", lambda: scaled_gold(pool, "sdb", R)), ("XAU5 (5 min)", lambda: scaled_gold(pool, "xau5", R)), ("ManualDip", lambda: dip_like(T0[(T0.date >= a) & (T0.date <= b)], bb, R, days)), ("US RSI(2) dips", lambda: dip_like(R2T[(R2T.date >= a) & (R2T.date <= b)], R2B, R, days))):
                pl, S = fn(); s, eq = stats(pl, S, label); rows.append(s); curves[label] = eq
            out[(pool, R)] = (pd.DataFrame(rows), curves)
    txt = []
    for (pool, R), (df, _) in out.items():
        txt.append(f"\n=== {pool} pool ({'FT 2022-01..2026-09, modelled on MT5 broker real ticks' if pool == 'FT' else 'MT5 broker last 12 months, real ticks'}), every trade risks {R} USD at its stop ===")
        txt.append(df.drop(columns=[]).to_string(index=False))
    s = "\n".join(txt); print(s); open(os.path.join(HERE, "PERF_ISOLATED_OUTPUT.txt"), "w").write(s)
    BLUE, ORANGE, GREEN, PURPLE, INK, MUTED, SURF = "#2a78d6", "#eb6834", "#2a9d8f", "#8e6bbf", "#1f1f1c", "#6b6b66", "#fcfcfb"; col = {"ManualSDB": BLUE, "XAU5 (5 min)": ORANGE, "ManualDip": GREEN, "US RSI(2) dips": PURPLE}
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.9), facecolor=SURF, sharey=False)
    for ax, R in zip(axs, (500, 1000)):
        ax.set_facecolor(SURF); [ax.spines[s_].set_visible(False) for s_ in ("top", "right")]; ax.tick_params(colors=MUTED); ax.axhline(0, color="#d8d8d3", lw=.8)
        for label, eq in out[("FT", R)][1].items(): ax.plot(eq.index, eq.values, lw=1.8, color=col[label], label=f"{label}: {eq.iloc[-1]:+,.0f}")
        ax.set_title(f"Cada trade arrisca {R} USD", loc="left", color=INK, fontsize=11); ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_ylabel("Lucro acumulado (USD)", color=MUTED)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:+,.0f}".replace(",", ".")))
    fig.suptitle("Cada estratégia isolada, 2022-2026 (sem stop diário, sem outras estratégias)", x=0.01, ha="left", fontsize=13, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(os.path.join(HERE, "PERF_ISOLATED.png"), dpi=140, facecolor=SURF)
