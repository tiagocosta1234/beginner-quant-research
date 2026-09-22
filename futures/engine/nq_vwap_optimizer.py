import pandas as pd
import numpy as np
import itertools
from concurrent.futures import ProcessPoolExecutor
import time

def process_chunk(params):
    stdev_mult, sl_pts, tp_pts, req_adx = params
    
    # We will use the global precalculated signals to fast-evaluate
    global df
    
    # Identify entry signals for this multiplier
    lower_band = df['vwap'] - (stdev_mult * df['vwap_stdev'])
    upper_band = df['vwap'] + (stdev_mult * df['vwap_stdev'])
    
    # sweep_low: low < lower_band AND close > lower_band
    # sweep_high: high > upper_band AND close < upper_band
    is_sweep_low = (df['low'] < lower_band) & (df['close'] > lower_band)
    is_sweep_high = (df['high'] > upper_band) & (df['close'] < upper_band)
    
    if req_adx:
        is_sweep_low = is_sweep_low & (df['adx'] < 25)
        is_sweep_high = is_sweep_high & (df['adx'] < 25)
        
    # Time filter: 10:00 to 11:30
    time_mask = (df.index.time >= pd.to_datetime('10:00').time()) & (df.index.time <= pd.to_datetime('11:30').time())
    is_sweep_low = is_sweep_low & time_mask
    is_sweep_high = is_sweep_high & time_mask
    
    # Test signals (1 for long, -1 for short)
    signals = pd.Series(0, index=df.index)
    signals[is_sweep_low] = 1
    signals[is_sweep_high] = -1
    
    # Get all signal indices
    signal_idx = np.where(signals != 0)[0]
    
    wins = 0
    losses = 0
    net_pnl = 0.0
    
    CONTRACTS = 13 # MNQ = $2 per point * 13 = $26/pt
    
    i = 0
    while i < len(signal_idx):
        entry_idx = signal_idx[i]
        
        # Avoid overlapping trades by enforcing 1 trade at a time
        trade_dir = signals.iloc[entry_idx]
        entry_price = lower_band.iloc[entry_idx] if trade_dir == 1 else upper_band.iloc[entry_idx]
        
        sl_price = entry_price - sl_pts if trade_dir == 1 else entry_price + sl_pts
        tp_price = entry_price + tp_pts if trade_dir == 1 else entry_price - tp_pts
        
        # Scan forward for exit
        exit_found = False
        j = entry_idx + 1
        
        # EOD index boundary (same day)
        current_date = df.index[entry_idx].date()
        
        while j < len(df) and df.index[j].date() == current_date:
            row_low = df['low'].values[j]
            row_high = df['high'].values[j]
            t = df.index[j].time()
            
            # Pessimistic SL first
            if trade_dir == 1:
                if row_low <= sl_price:
                    losses += 1
                    net_pnl -= (sl_pts * 26.0)
                    exit_found = True
                    break
                elif row_high >= tp_price:
                    wins += 1
                    net_pnl += (tp_pts * 26.0)
                    exit_found = True
                    break
            else:
                if row_high >= sl_price:
                    losses += 1
                    net_pnl -= (sl_pts * 26.0)
                    exit_found = True
                    break
                elif row_low <= tp_price:
                    wins += 1
                    net_pnl += (tp_pts * 26.0)
                    exit_found = True
                    break
                    
            if t >= pd.to_datetime('15:55').time():
                # End of day flatten
                close_p = df['close'].values[j]
                diff = (close_p - entry_price) if trade_dir == 1 else (entry_price - close_p)
                if diff > 0: wins += 1
                else: losses += 1
                net_pnl += (diff * 26.0)
                exit_found = True
                break
                
            j += 1
            
        if not exit_found:
            # Flatten at end of available data for that day
            close_p = df['close'].values[j-1] if j > 0 else df['close'].values[0]
            diff = (close_p - entry_price) if trade_dir == 1 else (entry_price - close_p)
            if diff > 0: wins += 1
            else: losses += 1
            net_pnl += (diff * 26.0)
            j += 1
            
        # Move to next valid signal that occurs after this trade exited
        i += 1
        while i < len(signal_idx) and signal_idx[i] < j:
            i += 1
            
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    pf = (wins * tp_pts) / (losses * sl_pts) if (losses * sl_pts) > 0 else 0
    
    return {
        'stdev_mult': stdev_mult,
        'sl_pts': sl_pts,
        'tp_pts': tp_pts,
        'req_adx': req_adx,
        'trades': total_trades,
        'win_rate': win_rate,
        'pf': pf,
        'net_pnl': net_pnl
    }

def calculate_vwap_and_stdev(df):
    df['typ'] = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = df['typ'] * df['volume']
    
    # Calculate VWAP daily
    df['date'] = df.index.date
    df['cum_pv'] = df.groupby('date')['pv'].cumsum()
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['vwap'] = df['cum_pv'] / df['cum_vol']
    
    # Calculate VWAP Variance/StDev
    df['dev_sq'] = ((df['typ'] - df['vwap']) ** 2) * df['volume']
    df['cum_dev_sq'] = df.groupby('date')['dev_sq'].cumsum()
    df['vwap_var'] = df['cum_dev_sq'] / df['cum_vol']
    df['vwap_stdev'] = np.sqrt(df['vwap_var'].replace([np.inf, -np.inf], 0).clip(lower=0))
    return df

def init_worker(shared_df):
    global df
    df = shared_df

if __name__ == '__main__':
    print("Loading 1.3M row MNQ dataset...")
    df = pd.read_csv('futures/data/MNQ_CONTINUOUS.txt', 
                     sep=';', header=None, names=['dt', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['dt'], format='%Y%m%d %H%M%S')
    df.set_index('datetime', inplace=True)
    df = df.between_time('09:30', '16:00')
    
    print("Calculating Daily VWAP & Standard Deviations...")
    df = calculate_vwap_and_stdev(df)
    
    # Fast ADX calculation
    period = 14
    df['up'] = df['high'].diff()
    df['dn'] = -df['low'].diff()
    df['+dm'] = np.where((df['up'] > df['dn']) & (df['up'] > 0), df['up'], 0)
    df['-dm'] = np.where((df['dn'] > df['up']) & (df['dn'] > 0), df['dn'], 0)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(period).mean()
    df['+di'] = 100 * (df['+dm'].rolling(period).mean() / df['atr'])
    df['-di'] = 100 * (df['-dm'].rolling(period).mean() / df['atr'])
    df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
    df['adx'] = df['dx'].rolling(period).mean()
    
    # Create parameter grid
    stdev_mults = [2.0, 2.5, 3.0, 3.5, 4.0]
    sl_pts = [20.0, 30.0, 40.0, 50.0, 75.0, 100.0]
    tp_pts = [20.0, 30.0, 40.0, 50.0, 75.0, 100.0, 150.0]
    req_adx = [False, True]
    
    param_grid = list(itertools.product(stdev_mults, sl_pts, tp_pts, req_adx))
    print(f"Matrix initialized. Testing {len(param_grid)} configurations across 3.5 years of 1M data...")
    
    results = []
    t0 = time.time()
    
    # Run multiprocessing
    with ProcessPoolExecutor(initializer=init_worker, initargs=(df,)) as executor:
        for res in executor.map(process_chunk, param_grid):
            results.append(res)
            
    print(f"Matrix calculation finished in {time.time()-t0:.1f} seconds.")
    
    res_df = pd.DataFrame(results)
    res_df = res_df[res_df['trades'] >= 100] # Filter out statistical anomalies (too few trades)
    
    if len(res_df) == 0:
        print("No configurations met the minimum 100 trades threshold.")
    else:
        top_pnl = res_df.sort_values('net_pnl', ascending=False).head(5)
        print("\n--- TOP 5 BY NET PNL ---")
        print(top_pnl.to_string(index=False))
        
        top_pf = res_df.sort_values('pf', ascending=False).head(5)
        print("\n--- TOP 5 BY PROFIT FACTOR ---")
        print(top_pf.to_string(index=False))
