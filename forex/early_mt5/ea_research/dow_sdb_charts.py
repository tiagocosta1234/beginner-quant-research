"""DOW+ with the frozen ManualSDB (SM1), 2025 and 2026 in separate charts (the trader 2026-10-12). 2026 is a DESCRIPTIVE look at a variant that
already failed DEV (PREREG_SDB_MARKETS.md); it is not evidence and does not change the verdict.   python -m mt5broker.ea_research.dow_sdb_charts"""
import os
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md

HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, "..", "ea_batch", "sdb_markets")
BLUE, ORANGE, INK, MUTED, SURF = "#2a78d6", "#eb6834", "#1f1f1c", "#6b6b66", "#fcfcfb"
K = lambda v, sign=True: (f"{v:+,.0f}" if sign else f"{v:,.0f}").replace(",", ".")
PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
for year, note in (("2025", "Validation year (2025). It passed the 2025 rule (PF >= 1.10), but 2022-24 failed (PF 1.09 < 1.20)."),
                   ("2026", "(original wording omitted)")):
    d = pd.read_csv(os.path.join(SRC, f"DOW_SM1_{year}.csv")); d["time"] = pd.to_datetime(d.time, format="%Y.%m.%d %H:%M:%S")
    o = d[d.direction == "out"].copy(); o["net"] = o.profit + o.commission + o.swap; o = o.sort_values("time"); eq = o.net.cumsum()
    w, l = o.net[o.net > 0].sum(), -o.net[o.net < 0].sum(); pf = w / l if l else float("inf"); dd = (eq.cummax() - eq).max()
    fig, ax = plt.subplots(figsize=(11, 4.6), facecolor=SURF); ax.set_facecolor(SURF)
    x = [pd.Timestamp(f"{year}-01-01")] + list(o.time); y = [0.0] + list(eq)
    col = BLUE if eq.iloc[-1] >= 0 else ORANGE
    ax.step(x, y, where="post", color=col, lw=2); ax.axhline(0, color="#d8d8d3", lw=.8)
    ax.scatter(o.time, eq, s=14, color=[BLUE if v > 0 else ORANGE for v in o.net], zorder=3)
    ax.annotate(K(eq.iloc[-1]), (x[-1], y[-1]), textcoords="offset points", xytext=(6, 0), va="center", fontsize=10, color=INK)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#bbb"); ax.spines["bottom"].set_color("#bbb"); ax.tick_params(colors=MUTED)
    ax.xaxis.set_major_locator(md.MonthLocator()); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: PT[md.num2date(v).month - 1]))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:+,.0f}".replace(",", ".")))
    ax.set_ylabel("Lucro acumulado (USD, 1% de risco por trade)", color=MUTED)
    fig.suptitle(f"ManualSDB no DOW (parâmetros do ouro), {year}: {len(o)} trades, {K(o.net.sum())} USD, PF {pf:.2f}".replace("PF 0.", "PF 0,").replace("PF 1.", "PF 1,"), x=0.01, ha="left", fontsize=13, color=INK)
    fig.text(0.01, 0.865, f"Tester MT5, H1, stop/alvo 1,9%, guard desligado. Ganhadores {100*(o.net > 0).mean():.0f}%, maior queda {K(dd, False)} USD.\n{note}", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.84)); out = os.path.join(HERE, f"DOW_SDB_{year}.png"); fig.savefig(out, dpi=150, facecolor=SURF); print(out, len(o), round(o.net.sum()), round(pf, 2))
