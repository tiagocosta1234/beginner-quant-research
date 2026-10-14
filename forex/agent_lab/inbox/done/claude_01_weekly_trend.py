# HYPOTHESIS: slow trend (price above its 20-day mean, 480 hourly bars) persists because institutional flows rebalance slowly; trade only when the move is large versus volatility.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    m = c.rolling(480).mean()
    vol = c.pct_change().rolling(480).std() * np.sqrt(480)
    z = (c / m - 1) / vol
    p = np.where(z > 0.5, 1, np.where(z < -0.5, -1, 0))
    return np.nan_to_num(p)
