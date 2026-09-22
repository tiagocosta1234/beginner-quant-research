import pandas as pd
df = pd.read_csv('futures/data/MNQ.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')

# Data is in UTC. Convert to New York Time (EST/EDT -> UTC-4 in summer)
df['datetime'] = df['datetime'] - pd.Timedelta(hours=4)

df.set_index('datetime', inplace=True)
df['date'] = df.index.date

trades = []
min_sweep, max_sweep, stop_pts, target_pts = 2.0, 25.0, 25.0, 50.0

for date, group in df.groupby('date'):
    london_data = group.between_time('02:00', '08:00')
    if london_data.empty: continue
    lon_high, lon_low = london_data['high'].max(), london_data['low'].min()
    rth_data = group.between_time('09:30', '16:00').copy()
    if rth_data.empty: continue
    rth_data['pv'] = ((rth_data['high'] + rth_data['low'] + rth_data['close'])/3) * rth_data['volume']
    rth_data['vwap'] = rth_data['pv'].cumsum() / rth_data['volume'].cumsum()
    
    active_trade = None
    for idx, row in rth_data.iterrows():
        t = row.name.time()
        if active_trade is not None:
            if active_trade['dir'] == 1:
                if row['low'] <= active_trade['sl']: 
                    trades.append({'time': active_trade['time'], 'dir': 'Long', 'entry': active_trade['entry'], 'exit_time': row.name, 'pnl': 'LOSS'})
                    break
                elif row['high'] >= active_trade['tp']: 
                    trades.append({'time': active_trade['time'], 'dir': 'Long', 'entry': active_trade['entry'], 'exit_time': row.name, 'pnl': 'WIN'})
                    break
                elif t >= pd.to_datetime('15:55').time(): 
                    pnl_str = 'WIN' if row['close'] > active_trade['entry'] else 'LOSS'
                    trades.append({'time': active_trade['time'], 'dir': 'Long', 'entry': active_trade['entry'], 'exit_time': row.name, 'pnl': f'FLAT ({pnl_str})'})
                    break
            else:
                if row['high'] >= active_trade['sl']: 
                    trades.append({'time': active_trade['time'], 'dir': 'Short', 'entry': active_trade['entry'], 'exit_time': row.name, 'pnl': 'LOSS'})
                    break
                elif row['low'] <= active_trade['tp']: 
                    trades.append({'time': active_trade['time'], 'dir': 'Short', 'entry': active_trade['entry'], 'exit_time': row.name, 'pnl': 'WIN'})
                    break
                elif t >= pd.to_datetime('15:55').time(): 
                    pnl_str = 'WIN' if row['close'] < active_trade['entry'] else 'LOSS'
                    trades.append({'time': active_trade['time'], 'dir': 'Short', 'entry': active_trade['entry'], 'exit_time': row.name, 'pnl': f'FLAT ({pnl_str})'})
                    break
            continue
            
        if pd.to_datetime('14:30').time() <= t <= pd.to_datetime('15:30').time():
            sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (min_sweep <= (row['high'] - lon_high) <= max_sweep) and (row['close'] <= row['vwap'])
            sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (min_sweep <= (lon_low - row['low']) <= max_sweep) and (row['close'] >= row['vwap'])
            
            if sweep_low: 
                active_trade = {'time': row.name, 'dir': 1, 'entry': lon_low, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts}
            elif sweep_high: 
                active_trade = {'time': row.name, 'dir': -1, 'entry': lon_high, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts}

if not trades:
    print("No trades found.")
else:
    for t in trades[-5:]:
        print(f"{t['time']} | {t['dir']} | Entry: {t['entry']} | Outcome: {t['pnl']} at {t['exit_time'].time()}")
