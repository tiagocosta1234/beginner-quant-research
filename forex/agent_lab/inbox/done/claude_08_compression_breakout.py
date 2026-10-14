# HYPOTHESIS: when daily-scale volatility is compressed to 60% of its 20-day norm, positions build quietly; the first 2-day range break releases them and the move continues for two days.
import numpy as np
import pandas as pd

def strategy(df):
    c, h, l = df.close, df.high, df.low
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    comp = tr.rolling(24).mean() < 0.6 * tr.rolling(480).mean()
    was = comp.shift(1).fillna(False).astype(bool)
    hh, ll = h.rolling(48).max().shift(1), l.rolling(48).min().shift(1)
    raw = pd.Series(np.where(was & (c > hh), 1.0, np.where(was & (c < ll), -1.0, np.nan)))
    return np.nan_to_num(raw.ffill(limit=48).fillna(0).to_numpy())
