import pandas as pd
import numpy as np

print("Loading continuous MNQ data...")
df = pd.read_csv('futures/data/mnq_1m_continuous.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df.set_index('datetime', inplace=True)
# Resample to 5m to match PineScript/Dual Sprinter logic
df_5m = df.resample('5min', label='left', closed='left').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna()

df_5m['date'] = df_5m.index.date
df_5m['time'] = df_5m.index.time

trades = []
stop_pts = 35.0
target_pts = 40.0
min_sweep = 10.0
max_sweep = 999.0
tick_size = 0.25

print("Running Dual Sprinter backtest on NQ...")
for date, group in df_5m.groupby('date'):
    london = group.between_time('02:00', '08:00')
    if london.empty: continue
    lon_high = london['high'].max()
    lon_low = london['low'].min()
    
    rth = group.between_time('09:30', '15:55').copy()
    if rth.empty: continue
    rth['pv'] = ((rth['high'] + rth['low'] + rth['close']) / 3) * rth['volume']
    rth['vwap'] = rth['pv'].cumsum() / rth['volume'].cumsum()
    
    active_trade = None
    
    for idx, row in rth.iterrows():
        t = row.name.time()
        
        if active_trade:
            # Check exit
            if active_trade['dir'] == 1:
                if row['low'] <= active_trade['sl']:
                    trades.append({'time': active_trade['time'], 'dir': 'Long', 'entry': active_trade['entry'], 'exit': idx, 'pnl': 'LOSS'})
                    active_trade = None
                elif row['high'] >= active_trade['tp']:
                    trades.append({'time': active_trade['time'], 'dir': 'Long', 'entry': active_trade['entry'], 'exit': idx, 'pnl': 'WIN'})
                    active_trade = None
            else:
                if row['high'] >= active_trade['sl']:
                    trades.append({'time': active_trade['time'], 'dir': 'Short', 'entry': active_trade['entry'], 'exit': idx, 'pnl': 'LOSS'})
                    active_trade = None
                elif row['low'] <= active_trade['tp']:
                    trades.append({'time': active_trade['time'], 'dir': 'Short', 'entry': active_trade['entry'], 'exit': idx, 'pnl': 'WIN'})
                    active_trade = None
                    
            if active_trade and t >= pd.to_datetime('15:55').time():
                trades.append({'time': active_trade['time'], 'dir': active_trade['dir'], 'entry': active_trade['entry'], 'exit': idx, 'pnl': 'FLAT'})
                active_trade = None
            continue
            
        # NQ Window: 09:42 (09:45 bar) to 10:45
        if pd.to_datetime('09:45').time() <= t <= pd.to_datetime('10:45').time():
            sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (row['high'] - lon_high >= min_sweep) and (row['close'] <= row['vwap'])
            sweep_low = (row['low'] < lon_low) and (row['close'] > lon_low) and (lon_low - row['low'] >= min_sweep) and (row['close'] >= row['vwap'])
            
            if sweep_low:
                active_trade = {'time': row.name, 'dir': 1, 'entry': lon_low, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts}
            elif sweep_high:
                active_trade = {'time': row.name, 'dir': -1, 'entry': lon_high, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts}

print(f"Total NQ Trades Found: {len(trades)}")
if trades:
    print("\n--- LAST 5 TRADES ---")
    for t in trades[-5:]:
        print(f"{t['time']} | {t['dir']} | Entry: {t['entry']} | Outcome: {t['pnl']} at {t['exit'].time()}")
