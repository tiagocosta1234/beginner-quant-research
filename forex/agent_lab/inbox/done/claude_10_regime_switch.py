# HYPOTHESIS: markets alternate between trending and ranging; follow 5-day direction when the efficiency ratio says trending, fade 1-day extremes when it says ranging, stay flat in between.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    er = (c - c.shift(120)).abs() / c.diff().abs().rolling(120).sum()
    trend = np.sign(c - c.shift(120))
    r24 = c / c.shift(24) - 1
    z = r24 / r24.rolling(1000, min_periods=300).std()
    fade = pd.Series(np.where(z > 1.5, -1.0, np.where(z < -1.5, 1.0, np.nan))).ffill(limit=12)
    p = np.where(er > 0.3, trend, np.where(er < 0.1, fade, 0.0))
    return np.nan_to_num(p)
