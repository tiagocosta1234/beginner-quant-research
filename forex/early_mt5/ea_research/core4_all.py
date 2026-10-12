"""CA: the trader's Bollinger + RSI(2) 4 h rule on every MT5 broker symbol (PREREG_CORE4_ALL.md).   env CA=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path
from mt5broker.ea_research import intraday_dip as ID, core4_bb as CB

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
ALL = sorted(p.name.split("_M1_rates")[0] for p in DATA.glob("*_M1_rates.parquet"))
GROUPS = {"indices": ["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX"], "metals": ["XAUUSD", "XAGUSD"], "energy": ["WTI", "BRENT"],
          "crypto": ["BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD", "XRPUSD", "ADAUSD", "BNBUSD", "BCHUSD"]}
GROUPS["fx"] = [s for s in ALL if s not in sum(GROUPS.values(), [])]
OOS, INS = CB.OOS, CB.INS


def run_symbol(m):
    try: return pd.DataFrame(CB.trades(m))
    except Exception as ex: print("skip", m, ex); return pd.DataFrame()


if __name__ == "__main__":
    mode = os.environ.get("CA"); T = {m: run_symbol(m) for m in ALL}
    if mode == "dry":
        print("symbols", len(ALL), {g: len(v) for g, v in GROUPS.items()}); print("trades per group:", {g: int(sum(len(T[m]) for m in v)) for g, v in GROUPS.items()})
    if mode == "run":
        lines, passed = [], {}
        for g, ms in list(GROUPS.items()) + [("all", ALL)]:
            df = pd.concat([T[m] for m in ms if len(T[m])], ignore_index=True); o, i_ = CB.summ(df, OOS, 2.75), CB.summ(df, INS, 2.0)
            acc = bool(o["days"] >= 40 and o["mean"] >= 15 and o["pf"] >= 1.3 and o["t"] >= 1.65 and i_["mean"] > 0); passed[g] = acc
            lines.append(f"{g:8s} ({len(ms)} symbols)\n  OUT-OF-SAMPLE: {ID.f(o)}\n  in-sample    : {ID.f(i_)}\n  Sharpe (25k/trade): OOS {ID.sharpe(df, OOS):.2f} | in-sample {ID.sharpe(df, INS):.2f} | accepted: {acc}")
        lines.append("\nper symbol (OOS trades, OOS mean bp | in-sample trades, mean bp):")
        pos_o = pos_i = n = 0
        for m in ALL:
            df = T[m]
            if df.empty: continue
            a, b = ID.win(df, OOS), ID.win(df, INS); ao = 1e4 * a.ret.mean() if len(a) else np.nan; bi = 1e4 * b.ret.mean() if len(b) else np.nan; n += 1; pos_o += ao > 0; pos_i += bi > 0
            lines.append(f"  {m:8s} {len(a):4d} {ao:+7.1f} | {len(b):4d} {bi:+7.1f}")
        lines.append(f"\nsymbols with a positive mean: out-of-sample {pos_o}/{n}, in-sample {pos_i}/{n} (pure luck would give about {n // 2}/{n} each)")
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "CORE4_ALL_RESULT.txt"), "w").write(txt)
