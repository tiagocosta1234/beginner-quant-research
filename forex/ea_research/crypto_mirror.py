"""CM1: the Bollinger + RSI(2) 4 h rule inverted on crypto (PREREG_CRYPTO_MIRROR.md).   env CM=dry|run"""
from __future__ import annotations
import os, time
import numpy as np, pandas as pd, requests
from pathlib import Path
from forex.ea_research import intraday_dip as ID, core4_bb as CB

COINS = {"BTCUSD": "BTCUSDT", "ETHUSD": "ETHUSDT", "LTCUSD": "LTCUSDT", "SOLUSD": "SOLUSDT", "XRPUSD": "XRPUSDT", "ADAUSD": "ADAUSDT", "BNBUSD": "BNBUSDT", "BCHUSD": "BCHUSDT"}
ALT = Path("D:/finance/data_macro/alt"); PROOF = ("2020-01-01", "2021-11-30"); SEC = 14400


def klines(sym):
    f = ALT / f"binance_4h_{sym}.csv"
    if f.exists(): return pd.read_csv(f)
    rows, start, end = [], int(pd.Timestamp("2019-09-01").timestamp() * 1000), int(pd.Timestamp("2021-12-01").timestamp() * 1000)
    while start < end:
        r = requests.get("https://api.binance.com/api/v3/klines", params=dict(symbol=sym, interval="4h", startTime=start, limit=1000), timeout=30).json()
        if not r or isinstance(r, dict): break
        rows += r; start = r[-1][0] + 4 * 3600 * 1000; time.sleep(0.2)
        if len(r) < 1000: break
    d = pd.DataFrame(rows).iloc[:, :6]; d.columns = ["ms", "open", "high", "low", "close", "vol"]; d = d[d.ms < end].astype({"open": float, "close": float}); d.to_csv(f, index=False); return d


def spread_rel(m):
    d = pd.read_parquet(ID.DATA / f"{m}_M1_rates.parquet", columns=["bo", "ao"]); d = d[(d.bo > 0) & (d.ao >= d.bo)]; return float(((d.ao - d.bo) / d.bo).median())


def signals(c):
    r = CB.rsi_simple(c); s200, s5, s20 = c.rolling(200).mean(), c.rolling(5).mean(), c.rolling(20).mean(); lo = s20 - 2 * c.rolling(20).std(); n = len(c); out = []; i = 200
    while i < n - 2:
        if r.iat[i] < 10 and c.iat[i] > s200.iat[i] and c.iat[i] < lo.iat[i]:
            j = i + 1
            while j < n - 2 and not (c.iat[j] > s5.iat[j] or r.iat[j] > 70): j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out


def binance_trades(m, sym, sp):
    d = klines(sym).reset_index(drop=True); c = d.close; ms = d.ms.values; out = []
    for i, j in signals(c):
        if ms[i + 1] - ms[i] > 2 * SEC * 1000: continue
        gross = d.open.iat[i + 1] / d.open.iat[j + 1] - 1                           # short: sell at the entry bar open, buy back at the exit bar open
        out.append(dict(mkt=m, entry=pd.Timestamp(ms[i + 1], unit="ms"), exit=pd.Timestamp(ms[j + 1], unit="ms"), ret=gross - sp))
    return out


def mt5_trades(m):
    g = ID.bars(m, SEC, 120); c = g.cb; t0 = g.t0.values; out = []
    for i, j in signals(c):
        if t0[i + 1] - t0[i] > 2 * SEC: continue
        out.append(dict(mkt=m, entry=pd.Timestamp(t0[i + 1], unit="s"), exit=pd.Timestamp(t0[j + 1], unit="s"), ret=g.ob.iat[i + 1] / g.oa.iat[j + 1] - 1))
    return out


if __name__ == "__main__":
    mode = os.environ.get("CM"); sp = {m: spread_rel(m) for m in COINS}
    B = pd.DataFrame(sum((binance_trades(m, s, sp[m]) for m, s in COINS.items()), [])); E = pd.DataFrame(sum((mt5_trades(m) for m in COINS), []))
    if mode == "dry": print("spread bp:", {m: round(1e4 * v, 1) for m, v in sp.items()}); print("Binance proof trades:", len(ID.win(B, PROOF)), "| MT5 OOS", len(ID.win(E, CB.OOS)), "INS", len(ID.win(E, CB.INS)))
    if mode == "run":
        p, o, i_ = CB.summ(B, PROOF, 1.92), CB.summ(E, CB.OOS, 2.75), CB.summ(E, CB.INS, 2.0)
        acc = bool(p["days"] >= 40 and p["mean"] >= 15 and p["pf"] >= 1.3 and p["t"] >= 1.65 and o["mean"] > 0 and i_["mean"] > 0)
        lines = ["CM1 inverted rule (short) on crypto", f"  PROOF Binance 2020-01..2021-11 (unseen): {ID.f(p)}", f"  consistency MT5 OOS 2022-01..2024-09     : {ID.f(o)}", f"  consistency MT5 broker in-sample 2024-10..2026-09: {ID.f(i_)}",
                 f"  indicative Sharpe (25k/trade): proof {ID.sharpe(B, PROOF):.2f} | MT5 OOS {ID.sharpe(E, CB.OOS):.2f} | MT5 broker in-sample {ID.sharpe(E, CB.INS):.2f}", f"  accepted: {acc}",
                 "  per coin, proof window (trades, mean bp net): " + str({m: (len(g), round(1e4 * g.ret.mean())) for m, g in ID.win(B, PROOF).groupby("mkt")}),
                 "  per coin, MT5 2022-26 (trades, mean bp): " + str({m: (len(g), round(1e4 * g.ret.mean())) for m, g in ID.win(E, ("2022-01-01", "2026-09-30")).groupby("mkt")})]
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "CRYPTO_MIRROR_RESULT.txt"), "w").write(txt)
