import pandas as pd
import numpy as np

def calculate_rsi(prices, n=14):
    deltas = np.diff(prices)
    seed = deltas[:n+1]
    up = seed[seed >= 0].sum()/n
    down = -seed[seed < 0].sum()/n
    rs = up/down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100./(1. + rs)
    for i in range(n, len(prices)):
        delta = deltas[i - 1]
        upval = delta if delta > 0 else 0.
        downval = -delta if delta < 0 else 0.
        up = (up*(n - 1) + upval)/n
        down = (down*(n - 1) + downval)/n
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1. + rs)
    return rsi

print("Loading data...")
df = pd.read_csv('futures/data/MGC_CONTINUOUS.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
df['datetime'] = df['datetime'] - pd.Timedelta(hours=4)
df.set_index('datetime', inplace=True)
df_5m = df.resample('5min', label='left', closed='left').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()

df = df_5m
df_1h = df.resample('1h', label='left', closed='left').agg({'close': 'last'}).dropna()
df_1h['ema50'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df = df.join(df_1h[['ema50']].shift(1).rename(columns={'ema50': 'htf_ema'})).ffill()

df['htfBull'] = df['close'] > df['htf_ema']
df['htfBear'] = df['close'] < df['htf_ema']

df['prev_close'] = df['close'].shift(1)
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['prev_close']), abs(df['low'] - df['prev_close'])))
df['atr'] = df['tr'].ewm(alpha=1/14, adjust=False).mean()
df['avgATR'] = df['atr'].rolling(50).mean()
df['goodVol'] = (df['atr'] > df['avgATR'] * 0.85) & (df['atr'] < df['avgATR'] * 2.2)

df['avgVol'] = df['volume'].rolling(20).mean()
df['volumeConfirmed'] = df['volume'] > (df['avgVol'] * 1.5)

df['rsi'] = calculate_rsi(df['close'].values, 14)
df['momentumUp'] = (df['rsi'] > 55) & (df['rsi'] < 68)
df['momentumDown'] = (df['rsi'] < 45) & (df['rsi'] > 32)

df['strongBull'] = (df['close'] > df['open']) & ((df['close'] - df['open']) > (df['high'] - df['low']) * 0.50)
df['strongBear'] = (df['close'] < df['open']) & ((df['open'] - df['close']) > (df['high'] - df['low']) * 0.50)

df['rollingHigh'] = df['high'].shift(1).rolling(20).max()
df['rollingLow'] = df['low'].shift(1).rolling(20).min()

df['buy_cross'] = (df['close'] > df['rollingHigh']) & (df['close'].shift(1) <= df['rollingHigh'].shift(1))
df['sell_cross'] = (df['close'] < df['rollingLow']) & (df['close'].shift(1) >= df['rollingLow'].shift(1))

df['is_session'] = (df.index.time >= pd.to_datetime('07:00').time()) & (df.index.time <= pd.to_datetime('12:00').time())
df['timeOk'] = df.index.time < pd.to_datetime('10:45').time()

print("goodVol:", df['goodVol'].sum())

df['buySignal'] = df['buy_cross'] & df['volumeConfirmed'] & df['momentumUp'] & df['strongBull'] & df['htfBull'] & df['goodVol'] & df['timeOk'] & df['is_session']
print("buySignal total:", df['buySignal'].sum())

df['sellSignal'] = df['sell_cross'] & df['volumeConfirmed'] & df['momentumDown'] & df['strongBear'] & df['htfBear'] & df['goodVol'] & df['timeOk'] & df['is_session']
print("sellSignal total:", df['sellSignal'].sum())
