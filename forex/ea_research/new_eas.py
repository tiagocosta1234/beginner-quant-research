"""Families IM (last-half-hour momentum) and GS (gold/silver ratio reversion), PREREG_NEW_EAS.md.   env NE=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from forex.ea_research import dip_addon as DA

DEV = ("2022-01-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31"); HOLD = ("2026-01-01", "2026-09-30")
for m in ("XAUUSD", "XAGUSD"): DA.MK.setdefault(m, ("America/New_York", 1549))


def at(d, hm, col): return d[d.hm == hm].drop_duplicates("date").set_index("date")[col]


def im():
    obs = []
    for m in ("SP", "NSDQ", "DOW"):
        d = DA.load(m); b1559, b1000, a1530, b1530, b1559o, a1559 = at(d, 1559, "bo"), at(d, 1000, "bo"), at(d, 1530, "ao"), at(d, 1530, "bo"), at(d, 1559, "bo"), at(d, 1559, "ao")
        days = b1559.index; prev = pd.Series(days[:-1], index=days[1:]); r = {}
        for D in days[1:]:
            P = prev[D]
            if (D - P).days > 4 or D not in b1000.index or D not in a1530.index or D not in a1559.index: continue
            s = np.sign(b1000[D] / b1559[P] - 1)
            if s == 0: continue
            r[D] = (b1559o[D] / a1530[D] - 1) * 1e4 if s > 0 else (b1530[D] / a1559[D] - 1) * 1e4
        obs.append(pd.Series(r))
    return pd.concat(obs, axis=1).dropna().mean(axis=1)


def gs():
    x, y = DA.load("XAUUSD"), DA.load("XAGUSD")
    xb, xa, yb, ya = at(x, 1559, "bo"), at(x, 1559, "ao"), at(y, 1559, "bo"), at(y, 1559, "ao")
    idx = xb.index.intersection(yb.index).intersection(xa.index).intersection(ya.index).sort_values()
    xb, xa, yb, ya = xb[idx], xa[idx], yb[idx], ya[idx]
    lr = np.log(xb / yb); z = (lr - lr.rolling(60).mean()) / lr.rolling(60).std(ddof=1)
    out, pos, i = {}, 0, 60
    while i < len(idx):
        if z.iloc[i] >= 2.0 or z.iloc[i] <= -2.0:
            side = -1 if z.iloc[i] >= 2.0 else 1                      # +1 = long gold short silver
            e = i; j = i + 1
            while j < len(idx) - 1 and abs(z.iloc[j]) > 0.5 and j - e < 20: j += 1
            if side == 1:   ret = ((xb.iloc[j] / xa.iloc[e] - 1) - (ya.iloc[j] / yb.iloc[e] - 1)) * 1e4
            else:           ret = ((yb.iloc[j] / ya.iloc[e] - 1) - (xa.iloc[j] / xb.iloc[e] - 1)) * 1e4
            out[idx[e]] = ret; i = j + 1
        else: i += 1
    return pd.Series(out)


def win(s, w): return s[(s.index >= w[0]) & (s.index <= w[1])]
def one(s): return dict(n=len(s), mean=s.mean() if len(s) else np.nan, t=s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan)


if __name__ == "__main__":
    S = {"IM": im(), "GS": gs()}
    if os.environ.get("NE") == "dry":                                    # counts only
        for k, s in S.items(): print(k, "obs", len(s), "DEV", len(win(s, DEV)), "VAL", len(win(s, VAL)), "HOLD", len(win(s, HOLD)))
    if os.environ.get("NE") == "run":
        FL = {"IM": (1.5, 2.0, 0), "GS": (30.0, 1.65, 20)}; rows = []
        for k, s in S.items():
            fl, bar, mn = FL[k]; d, v = one(win(s, DEV)), one(win(s, VAL)); acc = bool(d["n"] >= mn and d["mean"] >= fl and d["t"] >= bar and v["mean"] > 0)
            row = dict(trial=k, dev_n=d["n"], dev_bp=round(d["mean"], 2), dev_t=round(d["t"], 2), val_n=v["n"], val_bp=round(v["mean"], 2), val_t=round(v["t"], 2), accepted=acc)
            if acc: h = one(win(s, HOLD)); row.update(hold_n=h["n"], hold_bp=round(h["mean"], 2), PASS=bool(h["mean"] > 0))
            rows.append(row)
        txt = pd.DataFrame(rows).to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "NEW_EAS_RESULT.txt"), "w").write(txt)
