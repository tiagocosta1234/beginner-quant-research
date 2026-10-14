# HYPOTHESIS: trends are real only when the 1-day and the 10-day trend agree; disagreement is chop where trend following bleeds costs, so stay flat then.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close
    fast = np.sign(c.ewm(span=24, adjust=False).mean() - c.ewm(span=120, adjust=False).mean())
    slow = np.sign(c.ewm(span=240, adjust=False).mean() - c.ewm(span=1200, adjust=False).mean())
    p = np.where(fast == slow, slow, 0.0)
    p[:1200] = 0
    return np.nan_to_num(p)
