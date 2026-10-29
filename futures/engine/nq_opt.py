import pandas as pd
import numpy as np

print("Loading NQ data for Optimization...")
try:
    df = pd.read_parquet('data/NQ_5m_60d.parquet')
except Exception as e:
    print(f"Could not load data: {e}")
    import sys
    sys.exit(1)

# Ensure datetime index
if 'datetime' in df.columns:
    df.set_index('datetime', inplace=True)
elif not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df.index)

# Ensure Eastern Time
if df.index.tz is not None:
    df = df.tz_convert('America/New_York')
else:
    # Assuming the data is already in some timezone, let's just assume it's ET based on earlier findings
    pass

df['date'] = df.index.date
df['time'] = df.index.time

# Parameters to test
configs = [
    (40.0, 40.0, 10.0),
    (50.0, 50.0, 10.0),
    (60.0, 60.0, 15.0),
    (40.0, 80.0, 15.0),
    (50.0, 100.0, 20.0)
]

print("\n=== NQ 5-BAR ANOMALY OPTIMIZATION ===")

for sl_pts, tp_pts, min_sweep in configs:
    results = []
    
    for date, group in df.groupby('date'):
        lon = group.between_time('02:00', '07:59')
        if lon.empty: continue
        lon_high, lon_low = lon['High'].max() if 'High' in lon else lon['high'].max(), lon['Low'].min() if 'Low' in lon else lon['low'].min()
        
        rth = group.between_time('09:30', '15:55').copy()
        if rth.empty: continue
        
        # VWAP approx
        high_col = 'High' if 'High' in rth else 'high'
        low_col = 'Low' if 'Low' in rth else 'low'
        close_col = 'Close' if 'Close' in rth else 'close'
        vol_col = 'Volume' if 'Volume' in rth else 'volume'
        
        rth['pv'] = ((rth[high_col] + rth[low_col] + rth[close_col]) / 3) * rth[vol_col]
        rth['vwap'] = rth['pv'].cumsum() / rth['vol_col'].cumsum() if 'vol_col' in rth else rth['pv'].cumsum() / rth[vol_col].cumsum()
        
        active = None
        for idx, row in rth.iterrows():
            t = row.name.time()
            if active:
                # Resolve intra-bar pessimistically (assume SL hits first if both hit)
                if active['dir'] == 1:
                    if row[low_col] <= active['sl']: 
                        active['outcome'] = 'LOSS'
                        results.append(active)
                        active = None
                    elif row[high_col] >= active['tp']: 
                        active['outcome'] = 'WIN'
                        results.append(active)
                        active = None
                else:
                    if row[high_col] >= active['sl']: 
                        active['outcome'] = 'LOSS'
                        results.append(active)
                        active = None
                    elif row[low_col] <= active['tp']: 
                        active['outcome'] = 'WIN'
                        results.append(active)
                        active = None
                if active and t >= pd.to_datetime('15:55').time():
                    active['outcome'] = 'FLAT'
                    results.append(active)
                    active = None
                continue
                
            if pd.to_datetime('09:42').time() <= t <= pd.to_datetime('10:45').time():
                sweep_high_depth = row[high_col] - lon_high
                sweep_low_depth = lon_low - row[low_col]
                
                sweep_high = (row[high_col] > lon_high) and (row[close_col] < lon_high) and (sweep_high_depth >= min_sweep) and (row[close_col] <= row['vwap'])
                sweep_low = (row[low_col] < lon_low) and (row[close_col] > lon_low) and (sweep_low_depth >= min_sweep) and (row[close_col] >= row['vwap'])
                
                if sweep_low:
                    active = {'date': row['date'], 'time': t, 'dir': 1, 'sl': lon_low - sl_pts, 'tp': lon_low + tp_pts}
                elif sweep_high:
                    active = {'date': row['date'], 'time': t, 'dir': -1, 'sl': lon_high + sl_pts, 'tp': lon_high - tp_pts}

    df_res = pd.DataFrame(results)
    if df_res.empty:
        print(f"SL={sl_pts}, TP={tp_pts}, Sweep>={min_sweep} -> No trades found.")
        continue
        
    df_res = df_res[df_res['outcome'] != 'FLAT']
    wins = len(df_res[df_res['outcome'] == 'WIN'])
    losses = len(df_res[df_res['outcome'] == 'LOSS'])
    total = wins + losses
    win_rate = (wins/total)*100 if total > 0 else 0
    
    # Using MNQ math ($2 per point)
    # But wait, Broker Test max is 50 MNQ. If they want $1100 risk on 40pt stop:
    # Risk per contract on 40pt SL = $80. 13 MNQ = $1040 risk.
    # Let's just output raw POINTS of profit.
    points_profit = (wins * tp_pts) - (losses * sl_pts)
    
    print(f"Config: SL={sl_pts} | TP={tp_pts} | MinSweep={min_sweep}")
    print(f"Trades: {total} | Win Rate: {win_rate:.1f}%")
    print(f"Net Points: {points_profit:.1f}")
    print("-" * 40)
