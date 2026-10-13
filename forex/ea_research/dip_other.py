"""Family DD: the frozen ManualDip rule on metals, energy and FX majors (PREREG_DIP_OTHER.md).   env DD=dry|run"""
from __future__ import annotations
import os
os.environ.setdefault("DA_Z", "1.5")
import numpy as np, pandas as pd
from forex.ea_research import dip_addon as DA
from forex.ea_research.vol_regime import DEV, VAL, HOLD

GROUPS = {"DD0_indices": ["SP", "NSDQ", "DOW", "DAX"], "DD1_metals": ["XAUUSD", "XAGUSD"], "DD2_energy": ["WTI", "BRENT"],
          "DD3_fx": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]}
for g, ms in GROUPS.items():
    for m in ms: DA.MK.setdefault(m, ("America/New_York", 1549))


def group_obs(ms):
    rows = []
    for m in ms:
        d, S = DA.signals(m)
        if S.empty: continue
        S["n"] = 1; S["q"] = np.minimum(DA.RISK / (DA.KSTOP * S.sd), DA.CAP) / S.e; S["stop"] = S.e * (1 - DA.KSTOP * S.sd)
        T, _ = DA.day_arrays(S, {m: d}); T["bp"] = T.pl / (T.q * T.e) * 1e4; rows.append(T[["mkt", "date", "bp"]])
    T = pd.concat(rows) if rows else pd.DataFrame(columns=["mkt", "date", "bp"])
    return T.groupby("date").bp.mean()


def win(s, w): return s[(s.index >= w[0]) & (s.index <= w[1])]
def one(s): return dict(n=len(s), mean=s.mean() if len(s) else np.nan, t=s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan)


if __name__ == "__main__":
    O = {g: group_obs(ms) for g, ms in GROUPS.items()}
    if os.environ.get("DD") == "dry":                                    # signal-day counts only
        for g, s in O.items(): print(g, "signal-days DEV", len(win(s, DEV)), "VAL", len(win(s, VAL)), "HOLD", len(win(s, HOLD)))
    if os.environ.get("DD") == "run":
        rows = []
        for g, s in O.items():
            d, v = one(win(s, DEV)), one(win(s, VAL)); acc = bool(g != "DD0_indices" and d["n"] >= 25 and d["mean"] >= 10 and d["t"] >= 1.65 and v["mean"] > 0)
            row = dict(group=g, dev_n=d["n"], dev_bp=round(d["mean"], 1), dev_t=round(d["t"], 2), val_n=v["n"], val_bp=round(v["mean"], 1), val_t=round(v["t"], 2), accepted=acc)
            if acc: h = one(win(s, HOLD)); row.update(hold_n=h["n"], hold_bp=round(h["mean"], 1), PASS=bool(h["mean"] > 0))
            rows.append(row)
        txt = pd.DataFrame(rows).to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "DIP_OTHER_RESULT.txt"), "w").write(txt)
