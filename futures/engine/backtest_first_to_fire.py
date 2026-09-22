import pandas as pd
import numpy as np

def load_data(filepath):
    print(f"Loading {filepath}...")
    df = pd.read_csv(filepath, sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
    # NinjaTrader exports UTC. Convert to NY time.
    df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None)
    df = df.drop_duplicates(subset='datetime').sort_values('datetime')
    df.set_index('datetime', inplace=True)
    df['date'] = df.index.date
    return df

print("Loading datasets...")
df_nq = load_data(r'futures\data\MNQ_CONTINUOUS.txt')
df_gc = load_data(r'futures\data\MGC_CONTINUOUS.txt')

print("Calculating NQ ORB Signals (2.5 sigma Wick Rejection)...")
# NQ Logic: 10:00 - 13:30. VWAP + 2.5 stdev.
nq_trades = []
for date, group in df_nq.groupby('date'):
    rth_data = group.between_time('09:30', '16:00').copy()
    if rth_data.empty: continue
    
    # Calculate Session VWAP
    rth_data['typ'] = (rth_data['high'] + rth_data['low'] + rth_data['close']) / 3.0
    rth_data['pv'] = rth_data['typ'] * rth_data['volume']
    rth_data['cum_vol'] = rth_data['volume'].cumsum()
    rth_data['vwap'] = rth_data['pv'].cumsum() / rth_data['cum_vol']
    
    # Calculate Variance
    rth_data['dev_sq'] = ((rth_data['typ'] - rth_data['vwap']) ** 2) * rth_data['volume']
    rth_data['var'] = rth_data['dev_sq'].cumsum() / rth_data['cum_vol']
    rth_data['stdev'] = np.sqrt(np.maximum(rth_data['var'], 0))
    
    rth_data['upper'] = rth_data['vwap'] + 2.5 * rth_data['stdev']
    rth_data['lower'] = rth_data['vwap'] - 2.5 * rth_data['stdev']
    
    # Signal Window 10:00 - 13:30
    sig_window = rth_data.between_time('10:00', '13:30')
    for idx, row in sig_window.iterrows():
        sig_long = (row['low'] < row['lower']) and (row['close'] > row['lower'])
        sig_short = (row['high'] > row['upper']) and (row['close'] < row['upper'])
        
        if sig_long:
            nq_trades.append({'datetime': idx, 'asset': 'NQ', 'dir': 1, 'entry': row['close']})
        elif sig_short:
            nq_trades.append({'datetime': idx, 'asset': 'NQ', 'dir': -1, 'entry': row['close']})

print("Calculating GC Radar Signals (London Sweep)...")
# GC Logic: 09:42 - 10:45. Sweep of London 02:00 - 08:00
gc_trades = []
for date, group in df_gc.groupby('date'):
    london = group.between_time('02:00', '08:00')
    if london.empty: continue
    lon_high, lon_low = london['high'].max(), london['low'].min()
    
    sig_window = group.between_time('09:42', '10:45')
    for idx, row in sig_window.iterrows():
        # simplified GC rules based on Institutional Radar defaults
        sweep_long = (row['low'] < lon_low) and (row['close'] > lon_low) and ((lon_low - row['low']) >= 1.0)
        sweep_short = (row['high'] > lon_high) and (row['close'] < lon_high) and ((row['high'] - lon_high) >= 1.0)
        
        if sweep_long:
            gc_trades.append({'datetime': idx, 'asset': 'GC', 'dir': 1, 'entry': row['close']})
        elif sweep_short:
            gc_trades.append({'datetime': idx, 'asset': 'GC', 'dir': -1, 'entry': row['close']})

df_nq_trades = pd.DataFrame(nq_trades)
df_gc_trades = pd.DataFrame(gc_trades)

if not df_nq_trades.empty and not df_gc_trades.empty:
    df_all_trades = pd.concat([df_nq_trades, df_gc_trades]).sort_values('datetime')
    df_all_trades['date'] = df_all_trades['datetime'].dt.date

    # First to Fire Logic: Keep only the FIRST trade per day
    df_first = df_all_trades.drop_duplicates(subset='date', keep='first').copy()
    
    print("\n--- FIRST-TO-FIRE PROTOCOL SUMMARY ---")
    print(f"Total Combined Trading Days Examined: {len(df_first)}")
    
    nq_count = len(df_first[df_first['asset'] == 'NQ'])
    gc_count = len(df_first[df_first['asset'] == 'GC'])
    print(f"Trades Allocated to NQ: {nq_count}")
    print(f"Trades Allocated to GC: {gc_count}")
    
    # Calculate hypothetical 10-day sprint stats
    # We assume standard sprint metrics (1:1.5 RR, 57% WR on NQ, 50% WR on GC)
    print("\nSimulating 10-Day Sprint Math based on historical frequency...")
    # Average days between trades
    total_days_in_dataset = (df_nq.index.max() - df_nq.index.min()).days
    trades_per_month = (len(df_first) / total_days_in_dataset) * 30
    print(f"Average Setups per Month (Combined): {trades_per_month:.1f}")
    
    expected_10d_trades = (len(df_first) / total_days_in_dataset) * 14 # 10 trading days = ~14 calendar days
    print(f"Expected Setups in a 14-Day Calendar Sprint (10 Trading Days): {expected_10d_trades:.1f}")
else:
    print("Not enough data to calculate combined trades.")
