import pandas as pd
import numpy as np
import os
import itertools

def load_data(file_path):
    df = pd.read_csv(file_path, sep=';', header=None, names=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d %H%M%S')
    df.set_index('datetime', inplace=True)
    df['date'] = df.index.date
    df['time'] = df.index.time
    return df

def test_london_sweep(df, symbol, point_value, start_time, end_time):
    trades = []
    min_sweep = 0.5 if symbol == 'MES' else (0.2 if symbol == 'MGC' else (4.0 if symbol == 'MYM' else 2.0))
    max_sweep = min_sweep * 12.5
    stop_pts = max_sweep
    target_pts = stop_pts * 2
    
    for date, group in df.groupby('date'):
        london_data = group.between_time('02:00', '08:00')
        if london_data.empty: continue
        lon_high, lon_low = london_data['high'].max(), london_data['low'].min()
        
        rth_data = group.between_time('09:30', '16:00').copy()
        if rth_data.empty: continue
        
        # simplified VWAP
        rth_data['pv'] = ((rth_data['high'] + rth_data['low'] + rth_data['close'])/3) * rth_data['volume']
        rth_data['vwap'] = rth_data['pv'].cumsum() / rth_data['volume'].cumsum()
        
        active_trade = None
        for idx, row in rth_data.iterrows():
            t = row.name.time()
            if active_trade is not None:
                if active_trade['dir'] == 1:
                    if row['low'] <= active_trade['sl']:
                        trades.append({'pnl': (active_trade['sl'] - active_trade['entry']) * point_value})
                        break
                    elif row['high'] >= active_trade['tp']:
                        trades.append({'pnl': (active_trade['tp'] - active_trade['entry']) * point_value})
                        break
                    elif t >= pd.to_datetime('15:55').time():
                        trades.append({'pnl': (row['close'] - active_trade['entry']) * point_value})
                        break
                else:
                    if row['high'] >= active_trade['sl']:
                        trades.append({'pnl': (active_trade['entry'] - active_trade['sl']) * point_value})
                        break
                    elif row['low'] <= active_trade['tp']:
                        trades.append({'pnl': (active_trade['entry'] - active_trade['tp']) * point_value})
                        break
                    elif t >= pd.to_datetime('15:55').time():
                        trades.append({'pnl': (active_trade['entry'] - row['close']) * point_value})
                        break
                continue
                
            if pd.to_datetime(start_time).time() <= t <= pd.to_datetime(end_time).time():
                sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (min_sweep <= (row['high'] - lon_high) <= max_sweep) and (row['close'] <= row['vwap'])
                sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (min_sweep <= (lon_low - row['low']) <= max_sweep) and (row['close'] >= row['vwap'])
                
                if sweep_low: active_trade = {'dir': 1, 'entry': lon_low, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts}
                elif sweep_high: active_trade = {'dir': -1, 'entry': lon_high, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts}
                
    if not trades: return 0.0, 0, 0
    res = pd.DataFrame(trades)
    wins = res[res['pnl'] > 0]
    return len(wins)/len(res)*100, len(res), res['pnl'].sum()

print("Starting Brute Force Scan...")
symbols = {'MNQ': 2.0, 'MES': 5.0, 'MGC': 10.0, 'MYM': 0.5}
windows = [('09:30','10:30'), ('10:30','11:30'), ('13:30','14:30'), ('14:30','15:30')]

results = []
for sym, pval in symbols.items():
    fp = f"futures/data/{sym}.txt"
    if not os.path.exists(fp): continue
    df = load_data(fp)
    for start, end in windows:
        wr, trades, pnl = test_london_sweep(df, sym, pval, start, end)
        results.append(f"{sym} | Window: {start}-{end} | Trades: {trades} | WR: {wr:.1f}% | PnL: ${pnl:.2f}")

with open("futures/engine/brute_force_results.txt", "w") as f:
    f.write("\n".join(results))
print("Done. Saved to brute_force_results.txt")
