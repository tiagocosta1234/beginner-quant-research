# HYPOTHESIS: an extreme 6-hour move on extreme tick volume is forced selling or buying (stops, margin calls); liquidity providers who take the other side are paid as price reverts over the next half day.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    r6 = c / c.shift(6) - 1
    z = r6 / r6.rolling(1000, min_periods=300).std()
    tvr = df.tick_volume.rolling(6).sum() / df.tick_volume.rolling(6).sum().rolling(500, min_periods=200).median()
    raw = pd.Series(np.where((z < -3) & (tvr > 2.5), 1.0, np.where((z > 3) & (tvr > 2.5), -1.0, np.nan)))
    return np.nan_to_num(raw.ffill(limit=12).fillna(0).to_numpy())
