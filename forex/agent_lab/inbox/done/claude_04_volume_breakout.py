# HYPOTHESIS: a break of the 3-day range on unusually high tick volume carries real order flow (informed participants), so it follows through; low-volume breaks are noise and are ignored.
import numpy as np
import pandas as pd

def strategy(df):
    c, h, l = df.close, df.high, df.low
    hh, ll = h.rolling(72).max().shift(1), l.rolling(72).min().shift(1)
    tv = df.tick_volume
    tvr = tv / tv.rolling(240, min_periods=100).median()
    raw = pd.Series(np.where((c > hh) & (tvr > 1.5), 1.0, np.where((c < ll) & (tvr > 1.5), -1.0, np.nan)))
    return np.nan_to_num(raw.ffill(limit=24).fillna(0).to_numpy())
