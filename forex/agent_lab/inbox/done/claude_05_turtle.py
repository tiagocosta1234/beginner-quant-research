# HYPOTHESIS: classic 20-day breakout with 10-day exit (turtle) earns the trend risk premium paid by hedgers and late chasers; it trades rarely so costs stay small.
import numpy as np
import pandas as pd

def strategy(df):
    c = df.close.to_numpy()
    hi = df.high.rolling(480).max().shift(1).to_numpy()
    lo = df.low.rolling(480).min().shift(1).to_numpy()
    xh = df.high.rolling(240).max().shift(1).to_numpy()
    xl = df.low.rolling(240).min().shift(1).to_numpy()
    p = np.zeros(len(c))
    pos = 0
    for i in range(len(c)):
        if np.isnan(hi[i]):
            continue
        if pos == 0:
            if c[i] > hi[i]:
                pos = 1
            elif c[i] < lo[i]:
                pos = -1
        elif pos == 1 and c[i] < xl[i]:
            pos = 0
        elif pos == -1 and c[i] > xh[i]:
            pos = 0
        p[i] = pos
    return p
