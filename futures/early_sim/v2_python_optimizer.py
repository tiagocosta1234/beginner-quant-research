import pandas as pd
import numpy as np
import itertools
import time
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

df = None

def load_data(filepath):
    df = pd.read_csv(filepath)
    df['DateTime'] = pd.to_datetime(df['Time'])
    df = df.set_index('DateTime')
    df['Date'] = df.index.date
    df['TimeStr'] = df.index.time
    df['Volume'] = df['TotalVolume']
    return df

def init_worker(filepath):
    global df
    df = load_data(filepath)

def simulate_day(day_df, min_delta, max_ib_range, be_trigger, enable_shorts):
    t930 = pd.to_datetime('09:30').time()
    t1030 = pd.to_datetime('10:30').time()
    
    ib_df = day_df[(day_df['TimeStr'] >= t930) & (day_df['TimeStr'] < t1030)]
    if ib_df.empty: return None
    
    ib_high = ib_df['High'].max()
    ib_low = ib_df['Low'].min()
    ib_range = ib_high - ib_low
    
    buy_vol = ib_df['BuyVolume'].sum()
    sell_vol = ib_df['SellVolume'].sum()
    delta = buy_vol - sell_vol
    
    if ib_range > max_ib_range: return None
    
    entry_direction = 0
    entry_price = 0
    
    if delta > min_delta:
        entry_direction = 1
        entry_price = ib_high
    elif delta < -min_delta and enable_shorts:
        entry_direction = -1
        entry_price = ib_low
    else:
        return None
        
    trade_df = day_df[(day_df['TimeStr'] >= t1030) & (day_df['TimeStr'] < pd.to_datetime('15:45').time())]
    if trade_df.empty: return None
    
    in_trade = False
    stop_loss = 0
    target = 0
    be_moved = False
    
    for _, row in trade_df.iterrows():
        high = row['High']
        low = row['Low']
        
        if not in_trade:
            if entry_direction == 1 and high >= entry_price:
                in_trade = True
                stop_loss = entry_price - 80
                target = entry_price + 50
            elif entry_direction == -1 and low <= entry_price:
                in_trade = True
                stop_loss = entry_price + 80
                target = entry_price - 50
                
        if in_trade:
            if entry_direction == 1:
                if low <= stop_loss:
                    return stop_loss - entry_price - 0.5
                if high >= target:
                    return target - entry_price - 0.5
                if not be_moved and high >= entry_price + be_trigger:
                    stop_loss = entry_price
                    be_moved = True
            else:
                if high >= stop_loss:
                    return entry_price - stop_loss - 0.5
                if low <= target:
                    return entry_price - target - 0.5
                if not be_moved and low <= entry_price - be_trigger:
                    stop_loss = entry_price
                    be_moved = True
                    
    if in_trade:
        last_close = trade_df.iloc[-1]['Close']
        if entry_direction == 1: return last_close - entry_price - 0.5
        else: return entry_price - last_close - 0.5
            
    return None

def run_backtest_wrapper(args):
    d, r, b, s = args
    global df
    days = df.groupby('Date')
    total_profit = 0
    wins = 0
    losses = 0
    
    for date, day_df in days:
        pnl = simulate_day(day_df, d, r, b, s)
        if pnl is not None:
            if pnl > 0: wins += 1
            else: losses += 1
            total_profit += pnl
            
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'MinDelta': d,
        'MaxIBRange': r,
        'BE_Trigger': b,
        'Shorts': s,
        'Trades': total_trades,
        'WinRate': win_rate,
        'NetPoints': total_profit
    }

if __name__ == "__main__":
    filepath = "../data/MNQ_OrderFlow.csv"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        exit()
        
    df = load_data(filepath)
    
    deltas = [200, 300, 500, 800, 1000]
    ib_ranges = [80, 100, 150, 200]
    be_triggers = [20, 30, 40, 50, 999]
    shorts = [True]
    
    combinations = list(itertools.product(deltas, ib_ranges, be_triggers, shorts))
    print(f"Testing {len(combinations)} parameter combinations using Multiprocessing...")
    
    results = []
    start_time = time.time()
    
    with ProcessPoolExecutor(initializer=init_worker, initargs=(filepath,)) as executor:
        futures = {executor.submit(run_backtest_wrapper, combo): combo for combo in combinations}
        for i, future in enumerate(as_completed(futures)):
            if i % 10 == 0 and i > 0:
                print(f"Progress: {i}/{len(combinations)} ({(time.time()-start_time):.1f}s)")
            res = future.result()
            if res['Trades'] >= 10:
                results.append(res)
            
    print(f"Optimization complete in {time.time() - start_time:.2f} seconds.")
    
    res_df = pd.DataFrame(results)
    if not res_df.empty:
        print("\n=== Top 5 Most Profitable Combinations ===")
        print(res_df.sort_values('NetPoints', ascending=False).head(5).to_string(index=False))
        
        print("\n=== Top 5 Highest Win Rate Combinations (Min 30 trades) ===")
        sig_df = res_df[res_df['Trades'] >= 30]
        if not sig_df.empty:
            print(sig_df.sort_values('WinRate', ascending=False).head(5).to_string(index=False))
        else:
            print("No combinations had 30+ trades.")
    else:
        print("No combinations resulted in enough trades.")
