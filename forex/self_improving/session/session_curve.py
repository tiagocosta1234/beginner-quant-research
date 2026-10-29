"""Equity curve of session config D (L1500, m0 3, k1, r0, H_stop 3) on the MT5 12 months and FT 2025-26. python -m forex.self_improving.session.session_curve"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from forex.self_improving.session import session_lab as S


def curve(df):
    p = df.pnl.values; c = np.cumsum(np.where(p > 0, np.minimum(p, S.UP), p)); return pd.to_datetime(df.day.values * 86400, unit="s"), c, np.cumsum(p)


fig, axes = plt.subplots(2, 2, figsize=(14, 8), gridspec_kw=dict(height_ratios=[3, 1.4]), sharex="col")
for col, (nm, T) in enumerate((("MT5 broker pool, Oct 2025 - Sep 2026", S.load("MT5")), ("FT pool, 2025-26 (out of training)", S.load("FT", "2025-01-01", "2026-09-30")))):
    df = S.run(*T, 1500.0, 3.0, 1.0, 0.0, 3.0); d, c, raw = curve(df); ax, bx = axes[0, col], axes[1, col]
    ax.plot(d, c, color="#1f6feb", lw=1.6, label="counted equity (2,000-a-day profit cap)"); ax.plot(d, raw, color="#9aa5b1", lw=1, ls="--", label="uncapped")
    ax.axhline(8000, color="#2da44e", lw=1, ls=":"); ax.text(d[0], 8100, "+8,000 pass", color="#2da44e", fontsize=8); ax.axhline(-8000, color="#cf222e", lw=1, ls=":")
    ax.set_title(f"System D - {nm}\n{len(df)} sessions: +2,000 on {100 * (df.res == 1).mean():.0f}%, -1,500 on {100 * (df.res == -1).mean():.0f}%, unresolved {100 * (df.res == 0).mean():.0f}%", fontsize=10); ax.legend(fontsize=8, loc="upper left"); ax.set_ylabel("USD since start"); ax.grid(alpha=.25)
    colors = np.where(df.res == 1, "#2da44e", np.where(df.res == -1, "#cf222e", "#c9d1d9")); bx.bar(d, df.pnl.values, color=colors, width=1.0); bx.set_ylabel("session P&L"); bx.axhline(0, color="k", lw=.5); bx.grid(alpha=.25)
fig.suptitle("Session system D: equity curve (green = day ended +2,000, red = -1,500, grey = unresolved)", fontsize=11); fig.tight_layout()
fig.savefig("forex/self_improving/session/session_D_equity.png", dpi=110)
