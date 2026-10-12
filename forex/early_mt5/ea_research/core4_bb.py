"""CB1: the trader's Core 4 + Bollinger 4-hour RSI(2) variant on MT5 broker data, out-of-sample 2022-01 .. 2024-09 (PREREG_CORE4_BB.md).   env CB=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from mt5broker.ea_research import intraday_dip as ID

MK = ("SP", "NSDQ", "DOW", "NIKKEI"); SEC, MINMIN = 14400, 120
OOS = ("2022-01-01", "2024-09-30"); INS = ("2024-10-01", "2026-09-30")


def rsi_simple(c):
    d = c.diff(); g = d.where(d > 0, 0.0).rolling(2).mean(); l = (-d.where(d < 0, 0.0)).rolling(2).mean(); return 100 - 100 / (1 + g / l)


def trades(m):
    g = ID.bars(m, SEC, MINMIN); c = g.cb; r = rsi_simple(c); s200, s5, s20 = c.rolling(200).mean(), c.rolling(5).mean(), c.rolling(20).mean(); lower = s20 - 2 * c.rolling(20).std(); t0 = g.t0.values; n = len(g); out = []; i = 200
    while i < n - 2:
        if r.iat[i] < 10 and c.iat[i] > s200.iat[i] and c.iat[i] < lower.iat[i] and t0[i + 1] - t0[i] <= 2 * SEC:
            j = i + 1
            while j < n - 2 and not (c.iat[j] > s5.iat[j] or r.iat[j] > 70): j += 1
            out.append(dict(mkt=m, entry=pd.Timestamp(t0[i + 1], unit="s"), exit=pd.Timestamp(t0[j + 1], unit="s"), ret=g.ob.iat[j + 1] / g.oa.iat[i + 1] - 1, bars=j + 1 - i)); i = j + 1
        else: i += 1
    return out


def summ(df, w, years):
    d = ID.win(df, w)
    if d.empty: return dict(trades=0, days=0, per_year=0.0, mean=np.nan, pf=np.nan, t=np.nan)
    g = ID.by_day(d); t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    return dict(trades=len(d), days=len(g), per_year=len(d) / years, mean=1e4 * g.mean(), pf=ID.pf(g), t=t)


if __name__ == "__main__":
    rows = []
    for m in MK: rows += trades(m)
    df = pd.DataFrame(rows)
    if os.environ.get("CB") == "dry": print("trades", len(df), "OOS", len(ID.win(df, OOS)), "INS", len(ID.win(df, INS)), df.mkt.value_counts().to_dict())
    if os.environ.get("CB") == "run":
        o, i_ = summ(df, OOS, 2.75), summ(df, INS, 2.0); acc = bool(o["days"] >= 40 and o["mean"] >= 15 and o["pf"] >= 1.3 and o["t"] >= 1.65)
        lines = [f"CB1 Core4 + Bollinger, 4 h, MT5 broker bid/ask", f"  OUT-OF-SAMPLE 2022-01..2024-09: {ID.f(o)}", f"  in-sample 2024-10..2026-09   : {ID.f(i_)}",
                 f"  indicative Sharpe (25k per trade): OOS {ID.sharpe(df, OOS):.2f} | in-sample {ID.sharpe(df, INS):.2f}", f"  accepted (out-of-sample): {acc}",
                 "  by market OOS (trades, mean bp): " + str({m: (len(g), round(1e4 * g.ret.mean(), 1)) for m, g in ID.win(df, OOS).groupby("mkt")}),
                 "  by market in-sample: " + str({m: (len(g), round(1e4 * g.ret.mean(), 1)) for m, g in ID.win(df, INS).groupby("mkt")})]
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "CORE4_BB_RESULT.txt"), "w").write(txt)
