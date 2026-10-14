# HYPOTHESIS: inside a 50-day trend, a sharp 1-day move against it is liquidity-driven and gets bought back by trend holders; enter with the trend after the dip, hold one day.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    ema = c.ewm(span=1200, adjust=False).mean()
    r24 = c / c.shift(24) - 1
    s = r24.rolling(1000, min_periods=300).std()
    up, dn = (c > ema) & (r24 < -1.5 * s), (c < ema) & (r24 > 1.5 * s)
    raw = pd.Series(np.where(up, 1.0, np.where(dn, -1.0, np.nan)))
    return np.nan_to_num(raw.ffill(limit=24).fillna(0).to_numpy())
