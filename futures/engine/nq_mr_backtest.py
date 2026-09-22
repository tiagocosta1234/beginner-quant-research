import pandas as pd
import numpy as np

print("Loading 1.3 Million Rows of MNQ Continuous Data...")
df = pd.read_csv('futures/data/MNQ_CONTINUOUS.txt', 
                 sep=';', header=None, names=['dt', 'open', 'high', 'low', 'close', 'volume'])

df['datetime'] = pd.to_datetime(df['dt'], format='%Y%m%d %H%M%S')
df.set_index('datetime', inplace=True)
df = df.between_time('09:30', '16:00')

# Resample to 5-minute bars
df5 = df.resample('5Min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

# Calculate ADX (14)
def calculate_adx(df, period=14):
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['plus_di'] = 100 * (df['plus_dm'].rolling(window=period).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].rolling(window=period).mean() / df['atr'])
    
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].rolling(window=period).mean()
    return df

df5 = calculate_adx(df5)

print("Running Broker NQ Mean Reversion Backtest...")

wins = 0
losses = 0
net_pnl = 0.0

# 35 Stop, 40 Target, 2.5 Min Sweep (adjusting for MR)
SL_PTS = 35.0
TP_PTS = 40.0
MIN_SWEEP = 5.0
MAX_SWEEP = 40.0
CONTRACTS = 13 # MNQ contracts -> $26 per point

dates = np.unique(df5.index.date)
for d in dates:
    day_df = df5.loc[str(d)]
    
    # Needs at least until 11:30
    if len(day_df.between_time('10:00', '11:30')) == 0:
        continue
        
    or_df = day_df.between_time('09:30', '09:55') # First 6 5m bars
    if len(or_df) < 6:
        continue
        
    or_high = or_df['high'].max()
    or_low = or_df['low'].min()
    
    # Calculate VWAP
    day_df = day_df.copy()
    day_df['typ'] = (day_df['high'] + day_df['low'] + day_df['close']) / 3
    day_df['pv'] = day_df['typ'] * day_df['volume']
    day_df['vwap'] = day_df['pv'].cumsum() / day_df['volume'].cumsum()
    
    trade_active = False
    active_dir = 0
    active_entry = 0.0
    active_sl = 0.0
    active_tp = 0.0
    
    traded_today = False
    
    for idx, row in day_df.between_time('10:00', '15:59').iterrows():
        t = idx.time()
        
        if not trade_active and not traded_today and t <= pd.to_datetime('11:30').time():
            adx = row['adx']
            if pd.isna(adx): continue
            
            is_chop = adx < 25.0
            
            # Short Sweep
            sweep_high = is_chop and (row['high'] > or_high) and (row['close'] < or_high) and (row['high'] - or_high >= MIN_SWEEP) and (row['high'] - or_high <= MAX_SWEEP) and (row['close'] <= row['vwap'])
            
            # Long Sweep
            sweep_low = is_chop and (row['low'] < or_low) and (row['close'] > or_low) and (or_low - row['low'] >= MIN_SWEEP) and (or_low - row['low'] <= MAX_SWEEP) and (row['close'] >= row['vwap'])
            
            if sweep_high:
                trade_active = True
                active_dir = -1
                active_entry = or_high # Fill at OR High on close / limit
                active_sl = active_entry + SL_PTS
                active_tp = active_entry - TP_PTS
                traded_today = True
                continue
                
            elif sweep_low:
                trade_active = True
                active_dir = 1
                active_entry = or_low
                active_sl = active_entry - SL_PTS
                active_tp = active_entry + TP_PTS
                traded_today = True
                continue
                
        if trade_active:
            if active_dir == 1:
                # Pessimistic check
                if row['low'] <= active_sl:
                    losses += 1
                    net_pnl -= (SL_PTS * 2.0 * CONTRACTS)
                    trade_active = False
                elif row['high'] >= active_tp:
                    wins += 1
                    net_pnl += (TP_PTS * 2.0 * CONTRACTS)
                    trade_active = False
            elif active_dir == -1:
                if row['high'] >= active_sl:
                    losses += 1
                    net_pnl -= (SL_PTS * 2.0 * CONTRACTS)
                    trade_active = False
                elif row['low'] <= active_tp:
                    wins += 1
                    net_pnl += (TP_PTS * 2.0 * CONTRACTS)
                    trade_active = False
            
            # Flatten 15:59
            if trade_active and t == pd.to_datetime('15:55').time():
                diff = (row['close'] - active_entry) if active_dir == 1 else (active_entry - row['close'])
                if diff > 0: wins += 1
                else: losses += 1
                net_pnl += (diff * 2.0 * CONTRACTS)
                trade_active = False

print(f"--- RESULTS (3.5 Years) ---")
print(f"Total Trades: {wins + losses}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
win_rate = (wins / (wins+losses)) * 100 if (wins+losses) > 0 else 0
print(f"Win Rate: {win_rate:.2f}%")
print(f"Net PnL (13 MNQ): ${net_pnl:.2f}")
