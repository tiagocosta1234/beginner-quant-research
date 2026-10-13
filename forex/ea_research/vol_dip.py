"""Family VD: implied-vol regime vs ManualDip trade returns (PREREG_VOL_DIP.md).   env VD=dry|run (clean_boot_lib-style argv rewriting avoided)"""
from __future__ import annotations
import os
os.environ.setdefault("DA_Z", "1.5")
import numpy as np, pandas as pd
from scipy import stats
from forex.ea_research import dip_addon as DA
from forex.ea_research.vol_regime import cboe, DEV, VAL, HOLD


def prior_close(s, days):
    s = s.dropna(); idx = s.index.searchsorted(days, side="left") - 1
    return pd.Series(np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan), index=days)


def build():
    T, bars = DA.trades(); T, _ = DA.day_arrays(T, bars); T["bp"] = T.pl / (T.q * T.e) * 1e4
    S = T.groupby("date").bp.mean().to_frame("bp"); d = S.index
    S["G1_VIX"] = prior_close(cboe("VIX", "close"), d).to_numpy()
    S["G2_term"] = prior_close(cboe("VIX9D", "close") / cboe("VIX3M", "close"), d).to_numpy()
    S["G3_SKEW"] = prior_close(cboe("SKEW", "skew"), d).to_numpy()
    return S


def win(S, w): return S[(S.index >= w[0]) & (S.index <= w[1])]


def diff(S, k, thr, w):
    x = win(S, w).dropna(subset=[k]); hi, lo = x.bp[x[k] > thr], x.bp[x[k] <= thr]
    t = stats.ttest_ind(hi, lo, equal_var=False).statistic if len(hi) > 2 and len(lo) > 2 else np.nan
    return dict(n_hi=len(hi), n_lo=len(lo), diff=hi.mean() - lo.mean(), t=t, m_hi=hi.mean(), m_lo=lo.mean())


if __name__ == "__main__":
    S = build()
    if os.environ.get("VD") == "dry":                                  # coverage only: no outcome statistic printed
        for w, nm in ((DEV, "DEV"), (VAL, "VAL"), (HOLD, "HOLD")): print(nm, "signal-days", len(win(S, w)))
        for k in ("G1_VIX", "G2_term", "G3_SKEW"): print(k, "non-null", int(S[k].notna().sum()), "DEV median", round(win(S, DEV)[k].median(), 3), "DEV share >1.0" if k == "G2_term" else "", round((win(S, DEV)[k] > 1).mean(), 2) if k == "G2_term" else "")
    if os.environ.get("VD") == "run":
        rows = []
        for k in ("G1_VIX", "G2_term", "G3_SKEW"):
            thr = 1.0 if k == "G2_term" else win(S, DEV)[k].median(); d, v = diff(S, k, thr, DEV), diff(S, k, thr, VAL)
            acc = bool(min(d["n_hi"], d["n_lo"]) >= 15 and abs(d["t"]) >= 2.4 and np.sign(v["diff"]) == np.sign(d["diff"]) and abs(v["diff"]) >= 0.5 * abs(d["diff"]))
            row = dict(feature=k, thr=round(thr, 3), dev_n=f"{d['n_hi']}/{d['n_lo']}", dev_hi_bp=round(d["m_hi"], 1), dev_lo_bp=round(d["m_lo"], 1), dev_t=round(d["t"], 2),
                       val_n=f"{v['n_hi']}/{v['n_lo']}", val_diff_bp=round(v["diff"], 1), val_t=round(v["t"], 2), accepted=acc)
            if acc:
                h = diff(S, k, thr, HOLD); row.update(hold_diff_bp=round(h["diff"], 1), PASS=bool(np.sign(h["diff"]) == np.sign(d["diff"])))
            rows.append(row)
        txt = pd.DataFrame(rows).to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "VOL_DIP_RESULT.txt"), "w").write(txt)
