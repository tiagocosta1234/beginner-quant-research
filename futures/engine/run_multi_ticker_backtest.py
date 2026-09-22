import pandas as pd
import numpy as np
import glob
import os

def backtest_london_sweep(file_path, symbol, point_value):
    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path, sep=';', header=None, names=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d %H%M%S')
    df.set_index('datetime', inplace=True)
    
    # Pre-calculate features
    df['date'] = df.index.date
    df['time'] = df.index.time
    
    trades = []
    
    for date, group in df.groupby('date'):
        # 1. London Session (02:00 to 08:00)
        london_data = group.between_time('02:00', '08:00')
        if london_data.empty: continue
        
        lon_high = london_data['high'].max()
        lon_low = london_data['low'].min()
        
        # 2. RTH VWAP (09:30 onwards)
        rth_data = group.between_time('09:30', '16:00').copy()
        if rth_data.empty: continue
        
        rth_data['typ_price'] = (rth_data['high'] + rth_data['low'] + rth_data['close']) / 3
        rth_data['pv'] = rth_data['typ_price'] * rth_data['volume']
        rth_data['cum_vol'] = rth_data['volume'].cumsum()
        rth_data['cum_pv'] = rth_data['pv'].cumsum()
        rth_data['vwap'] = rth_data['cum_pv'] / rth_data['cum_vol']
        
        active_trade = None
        
        for idx, row in rth_data.iterrows():
            t = row.name.time()
            
            # Position Management
            if active_trade is not None:
                if active_trade['dir'] == 1: # LONG
                    if row['low'] <= active_trade['sl']:
                        active_trade['exit_time'] = row.name
                        active_trade['exit_price'] = active_trade['sl']
                        active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry']) * point_value
                        trades.append(active_trade)
                        break # End of day for trading
                    elif row['high'] >= active_trade['tp']:
                        active_trade['exit_time'] = row.name
                        active_trade['exit_price'] = active_trade['tp']
                        active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry']) * point_value
                        trades.append(active_trade)
                        break
                    elif t >= pd.to_datetime('15:55').time():
                        active_trade['exit_time'] = row.name
                        active_trade['exit_price'] = row['close']
                        active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry']) * point_value
                        trades.append(active_trade)
                        break
                        
                elif active_trade['dir'] == -1: # SHORT
                    if row['high'] >= active_trade['sl']:
                        active_trade['exit_time'] = row.name
                        active_trade['exit_price'] = active_trade['sl']
                        active_trade['pnl'] = (active_trade['entry'] - active_trade['exit_price']) * point_value
                        trades.append(active_trade)
                        break
                    elif row['low'] <= active_trade['tp']:
                        active_trade['exit_time'] = row.name
                        active_trade['exit_price'] = active_trade['tp']
                        active_trade['pnl'] = (active_trade['entry'] - active_trade['exit_price']) * point_value
                        trades.append(active_trade)
                        break
                    elif t >= pd.to_datetime('15:55').time():
                        active_trade['exit_time'] = row.name
                        active_trade['exit_price'] = row['close']
                        active_trade['pnl'] = (active_trade['entry'] - active_trade['exit_price']) * point_value
                        trades.append(active_trade)
                        break
                continue
                
            # Entry Logic (09:42 to 10:45)
            if pd.to_datetime('09:42').time() <= t <= pd.to_datetime('10:45').time():
                if symbol in ['MNQ', 'NQ']:
                    min_sweep, max_sweep, stop_pts, target_pts = 2.0, 25.0, 25.0, 50.0
                elif symbol in ['MES', 'ES']:
                    min_sweep, max_sweep, stop_pts, target_pts = 0.5, 6.25, 6.25, 12.5
                elif symbol in ['MGC', 'GC']:
                    min_sweep, max_sweep, stop_pts, target_pts = 0.2, 2.5, 2.5, 5.0
                elif symbol in ['MYM', 'YM']:
                    min_sweep, max_sweep, stop_pts, target_pts = 4.0, 50.0, 50.0, 100.0
                else:
                    min_sweep, max_sweep, stop_pts, target_pts = 2.0, 25.0, 25.0, 50.0

                vwap_bullish = row['close'] >= row['vwap']
                vwap_bearish = row['close'] <= row['vwap']
                
                sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (min_sweep <= (row['high'] - lon_high) <= max_sweep) and vwap_bearish
                sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (min_sweep <= (lon_low - row['low']) <= max_sweep) and vwap_bullish
                
                if sweep_low:
                    active_trade = {
                        'date': date,
                        'entry_time': row.name,
                        'dir': 1,
                        'entry': lon_low,
                        'sl': lon_low - stop_pts,
                        'tp': lon_low + target_pts
                    }
                elif sweep_high:
                    active_trade = {
                        'date': date,
                        'entry_time': row.name,
                        'dir': -1,
                        'entry': lon_high,
                        'sl': lon_high + stop_pts,
                        'tp': lon_high - target_pts
                    }

    # Summary
    if not trades: return {"Total Trades": 0}
    
    res = pd.DataFrame(trades)
    wins = res[res['pnl'] > 0]
    losses = res[res['pnl'] <= 0]
    win_rate = len(wins) / len(res) * 100
    total_pnl = res['pnl'].sum()
    
    return {
        "Total Bars": f"{len(df):,}",
        "Total Trades": len(res),
        "Wins": len(wins),
        "Losses": len(losses),
        "Win Rate %": round(win_rate, 2),
        "Gross PnL (1 Contract)": round(total_pnl, 2),
        "Avg Win": round(wins['pnl'].mean(), 2) if not wins.empty else 0,
        "Avg Loss": round(losses['pnl'].mean(), 2) if not losses.empty else 0,
        "Expectancy": round(res['pnl'].mean(), 2)
    }

print("Running Multi-Ticker Backtest...\n")
symbols = {
    'MNQ': 2.0,
    'MES': 5.0,
    'MGC': 10.0,
    'MYM': 0.5
}
for sym, pval in symbols.items():
    fp = f"futures/data/{sym}.txt"
    if os.path.exists(fp):
        metrics = backtest_london_sweep(fp, sym, pval)
        print(f"\n--- {sym} Results ---")
        for k, v in metrics.items():
            print(f"{k}: {v}")
