"""Strategy specs for the self-improving trader: sample, mutate, hash, and turn a spec into trades on the point-in-time tables."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

FAM = {
    "rsi_dip":   dict(n=(2, 3, 4), th=(5, 10, 15, 20, 25), trend=(0, 100, 200), volf=("any", "hi", "lo"), exit=("sma5", "sma10", "rsi", "hold"), hold=(2, 3, 5, 8)),
    "low_dip":   dict(k=(2, 3, 5, 7, 10), trend=(0, 100, 200), volf=("any", "hi", "lo"), exit=("sma5", "sma10", "hold"), hold=(2, 3, 5, 8)),
    "pop_short": dict(n=(2, 3), th=(80, 85, 90, 95), trend=(0, 200), volf=("any", "hi", "lo"), exit=("sma5", "sma10", "rsi", "hold"), hold=(2, 3, 5, 8)),
    "breakout":  dict(k=(20, 50, 100), volf=("any", "hi", "lo"), exit=("sma10", "sma20", "hold"), hold=(5, 10, 20)),
}


def sample(rng):
    f = list(FAM)[rng.integers(len(FAM))]; return dict(fam=f, **{k: v[rng.integers(len(v))] for k, v in FAM[f].items()})


def mutate(spec, rng):
    s = dict(spec); keys = list(FAM[s["fam"]]);
    for k in rng.choice(keys, size=int(rng.integers(1, 3)), replace=False):
        vals = FAM[s["fam"]][k]; i = vals.index(s[k]); j = i + int(rng.choice([-1, 1])); s[k] = vals[min(max(j, 0), len(vals) - 1)]
    return s


def key(spec): return hashlib.md5(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]


def entry_mask(t, s):
    f = s["fam"]
    if f == "rsi_dip": m = t[f"rsi{s['n']}"] < s["th"]
    elif f == "low_dip": m = t[f"low{s['k']}"] > 0
    elif f == "pop_short": m = t[f"rsi{s['n']}"] > s["th"]
    else: m = t[f"hi{s['k']}"] > 0
    L = s.get("trend", 0)
    if L:
        if f == "pop_short": m &= t.b < t[f"sma{L}"]
        else: m &= t.b > t[f"sma{L}"]
    if s["volf"] == "hi": m &= t.volhi == 1
    elif s["volf"] == "lo": m &= t.volhi == 0
    return (m & t.sd.notna()).fillna(False).to_numpy()


def exit_now(t, s, j, side):
    e = s["exit"]; b = t.b.iat[j]
    if e in ("sma5", "sma10", "sma20"): x = t[e].iat[j]; return (b > x) if side > 0 else (b < x)
    if e == "rsi": r = t["rsi2"].iat[j]; return (r > 70) if side > 0 else (r < 30)
    return False


def trades(tab, s, drift=None, carry=0.0):
    """tab: {market: table}. Returns a frame mkt, date, t_in, t_out, e, sd, ret (fraction, after the real bid/ask), side.
    drift {market: mean daily return}: v2 null -- ret becomes the EXCESS over holding the index for the same days (a short is charged the drift)."""
    rows = []; side = -1 if s["fam"] == "pop_short" else 1
    for m, t in tab.items():
        mask = entry_mask(t, s); i = 200; n = len(t); a = t.a.values; b = t.b.values; tt = t.t.values; idx = t.index
        while i < n - 1:
            if mask[i]:
                j = i + 1
                while j < n - 1 and j - i < s["hold"] and not exit_now(t, s, j, side): j += 1
                r = (b[j] / a[i] - 1) if side > 0 else (b[i] / a[j] - 1)
                if drift is not None: r -= side * drift[m] * (j - i)
                r -= carry * 1e-4 * (tt[j] - tt[i]) / 86400.0
                rows.append((m, idx[i], int(tt[i]), int(tt[j]), float(a[i]), float(t.sd.iat[i]), float(r), side, i, j - i)); i = j + 1
            else: i += 1
    return pd.DataFrame(rows, columns=["mkt", "date", "t_in", "t_out", "e", "sd", "ret", "side", "i", "h"])
