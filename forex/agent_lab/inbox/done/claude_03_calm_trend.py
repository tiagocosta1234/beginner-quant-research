# HYPOTHESIS: a 10-day trend that forms while short-term volatility is below its long-term level reflects slow institutional accumulation, not news noise, and persists.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    r = np.log(c).diff()
    mom = np.log(c / c.shift(240))
    calm = r.rolling(48).std() < 0.8 * r.rolling(480).std()
    raw = pd.Series(np.where(calm & (mom > 0), 1.0, np.where(calm & (mom < 0), -1.0, np.nan)))
    return np.nan_to_num(raw.ffill(limit=48).fillna(0).to_numpy())
