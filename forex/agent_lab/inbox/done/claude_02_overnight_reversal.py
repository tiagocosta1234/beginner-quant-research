# HYPOTHESIS: large 24-hour moves partly reverse over the next day because liquidity providers who absorbed them unwind; fade only the top decile of moves.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    r24 = c / c.shift(24) - 1
    s = r24.rolling(2000, min_periods=500).std()
    z = r24 / s
    raw = np.where(z > 1.8, -1, np.where(z < -1.8, 1, 0))
    p = pd.Series(raw).replace(0, np.nan).ffill(limit=24).fillna(0).to_numpy()
    return p
