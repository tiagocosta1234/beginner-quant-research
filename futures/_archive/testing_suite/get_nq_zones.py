import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_swings(df, strength=5):
    highs = []
    lows = []
    for i in range(strength, len(df) - strength):
        is_high = True
        is_low = True
        for j in range(1, strength + 1):
            if df['High'].iloc[i] <= df['High'].iloc[i-j] or df['High'].iloc[i] <= df['High'].iloc[i+j]:
                is_high = False
            if df['Low'].iloc[i] >= df['Low'].iloc[i-j] or df['Low'].iloc[i] >= df['Low'].iloc[i+j]:
                is_low = False
        if is_high: highs.append((df.index[i], df['High'].iloc[i]))
        if is_low: lows.append((df.index[i], df['Low'].iloc[i]))
    return highs, lows

print('--- NQ=F DATA ---')
ticker = yf.Ticker('NQ=F')

df_w = ticker.history(period='2y', interval='1wk')
hw, lw = get_swings(df_w, 3)
print('\nWEEKLY SWINGS (Last 5):')
for date, p in hw[-5:]: print(f'Supply: {p:.2f} ({date.date()})')
for date, p in lw[-5:]: print(f'Demand: {p:.2f} ({date.date()})')

df_d = ticker.history(period='6mo', interval='1d')
hd, ld = get_swings(df_d, 5)
print('\nDAILY SWINGS (Last 5):')
for date, p in hd[-5:]: print(f'Supply: {p:.2f} ({date.date()})')
for date, p in ld[-5:]: print(f'Demand: {p:.2f} ({date.date()})')

df_1h = ticker.history(period='1mo', interval='1h')
h1h, l1h = get_swings(df_1h, 10)
print('\n1H SWINGS (Last 5):')
for date, p in h1h[-5:]: print(f'Supply: {p:.2f} ({date.strftime("%m-%d %H:%M")})')
for date, p in l1h[-5:]: print(f'Demand: {p:.2f} ({date.strftime("%m-%d %H:%M")})')

curr_price = df_1h['Close'].iloc[-1]
print(f'\nCURRENT PRICE: {curr_price:.2f}')
