"""The gold pair in the bad regime (2022-23, no gold trend) at different risk multipliers, FT pool, news-flat on, guard 1,500, no ManualDip.
the trader 2026-10-12 (point 3 of the follow-ups). Descriptive: shows what scaling the live size does when the pair has no tailwind. Live config unchanged.
python -m mt5broker.ea_research.risk_regime"""
import os
import numpy as np, pandas as pd
from mt5broker.ea_research import combo_grid as G

MULTS = (1.0, 1.2, 1.5, 1.8, 2.0)
rows = []
for m in MULTS:
    S = G.pair_series("FT", m, m, 1500.0); d = pd.to_datetime(S["days"] * 86400, unit="s"); V = pd.Series(S["V"], index=d); B = pd.Series(S["B"], index=d)
    for lab, (a, b) in (("2022-23", ("2022-01-01", "2023-12-31")), ("2024-26", ("2024-01-01", "2026-09-30")), ("all", ("2022-01-01", "2026-09-30"))):
        v, bb = V[(V.index >= a) & (V.index <= b)], B[(B.index >= a) & (B.index <= b)]; eq = v.cumsum(); mo = v.groupby(v.index.to_period("M")).sum()
        rows.append(dict(mult=m, period=lab, net=round(v.sum()), per_month=round(v.sum() / max(len(mo), 1)), months_pos_pct=round(100 * (mo > 0).mean()), max_dd=round((eq.cummax() - eq).max()),
                         worst_day=round(bb.min()), days_le_1500=int((bb <= -1500).sum())))
R = pd.DataFrame(rows); txt = R.to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "RISK_REGIME_OUTPUT.txt"), "w").write(txt)
