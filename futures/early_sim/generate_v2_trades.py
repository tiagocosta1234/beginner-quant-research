import pandas as pd
import numpy as np
import time
import os

def load_data(filepath):
    df = pd.read_csv(filepath)
    df['DateTime'] = pd.to_datetime(df['Time'])
    df = df.set_index('DateTime')
    df['Date'] = df.index.date
    df['TimeStr'] = df.index.time
    df['Volume'] = df['TotalVolume']
    return df

def simulate_v2(df, min_delta=1000, max_ib_range=200, enable_shorts=True):
    t930 = pd.to_datetime('09:30').time()
    t1030 = pd.to_datetime('10:30').time()
    
    trades = []
    trade_number = 1
    
    days = df.groupby('Date')
    
    for date, day_df in days:
        ib_df = day_df[(day_df['TimeStr'] >= t930) & (day_df['TimeStr'] < t1030)]
        if ib_df.empty: continue
        
        ib_high = ib_df['High'].max()
        ib_low = ib_df['Low'].min()
        ib_range = ib_high - ib_low
        
        buy_vol = ib_df['BuyVolume'].sum()
        sell_vol = ib_df['SellVolume'].sum()
        delta = buy_vol - sell_vol
        
        if ib_range > max_ib_range: continue
        
        entry_direction = 0
        entry_price = 0
        entry_time_str = "10:31:00" # Approximate entry time
        
        if delta > min_delta:
            entry_direction = 1
            entry_price = ib_high
        elif delta < -min_delta and enable_shorts:
            entry_direction = -1
            entry_price = ib_low
        else:
            continue
            
        trade_df = day_df[(day_df['TimeStr'] >= t1030) & (day_df['TimeStr'] < pd.to_datetime('15:45').time())]
        if trade_df.empty: continue
        
        in_trade = False
        stop_loss = 0
        target = 0
        
        exit_price = 0
        exit_time_str = "15:45:00"
        pnl = 0
        
        # Simulating tick-by-tick within 1m bars using high/low
        for idx, row in trade_df.iterrows():
            high = row['High']
            low = row['Low']
            curr_time = row['TimeStr'].strftime('%H:%M:00')
            
            if not in_trade:
                if entry_direction == 1 and high >= entry_price:
                    in_trade = True
                    entry_time_str = curr_time
                    stop_loss = entry_price - 80
                    target = entry_price + 50
                elif entry_direction == -1 and low <= entry_price:
                    in_trade = True
                    entry_time_str = curr_time
                    stop_loss = entry_price + 80
                    target = entry_price - 50
                    
            if in_trade:
                # To be conservative, if a bar engulfs both target and stop, we assume stop was hit first.
                if entry_direction == 1:
                    if low <= stop_loss:
                        exit_price = stop_loss
                        exit_time_str = curr_time
                        pnl = stop_loss - entry_price - 0.5
                        break
                    if high >= target:
                        exit_price = target
                        exit_time_str = curr_time
                        pnl = target - entry_price - 0.5
                        break
                else:
                    if high >= stop_loss:
                        exit_price = stop_loss
                        exit_time_str = curr_time
                        pnl = entry_price - stop_loss - 0.5
                        break
                    if low <= target:
                        exit_price = target
                        exit_time_str = curr_time
                        pnl = entry_price - target - 0.5
                        break
                        
        if in_trade and exit_price == 0:
            last_close = trade_df.iloc[-1]['Close']
            exit_price = last_close
            exit_time_str = "15:44:00"
            if entry_direction == 1: pnl = last_close - entry_price - 0.5
            else: pnl = entry_price - last_close - 0.5
                
        if in_trade:
            # Format PnL in dollars assuming 5 MNQ contracts
            dollar_profit = pnl * 10 
            
            date_str = date.strftime('%d/%m/%Y')
            
            trades.append({
                'Trade number': trade_number,
                'Instrument': 'MNQ 09-26',
                'Account': 'Backtest',
                'Strategy': 'Pure_OrderFlow_Sniper_V2',
                'Market pos.': 'Long' if entry_direction == 1 else 'Short',
                'Qty': 5,
                'Entry price': entry_price,
                'Exit price': exit_price,
                'Entry time': f"{date_str} {entry_time_str}",
                'Exit time': f"{date_str} {exit_time_str}",
                'Entry name': 'IB_Long' if entry_direction == 1 else 'IB_Short',
                'Exit name': 'Sim_Exit',
                'Profit': f"${dollar_profit:.2f}",
                'Cum. net profit': "$0.00",
                'Commission': "$6.00",
                'Clearing Fee': "$0.00",
                'Exchange Fee': "$0.00",
                'IP Fee': "$0.00",
                'NFA Fee': "$0.00",
                'MAE': "$0.00",
                'MFE': "$0.00",
                'ETD': "$0.00",
                'Bars': 0
            })
            trade_number += 1
            
    return pd.DataFrame(trades)

if __name__ == "__main__":
    filepath = "../data/MNQ_OrderFlow.csv"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        exit()
        
    print("Loading OrderFlow data...")
    df = load_data(filepath)
    
    print("Simulating V2 trades (MinDelta=1000, MaxIBRange=200)...")
    trades_df = simulate_v2(df)
    
    out_path = "../data/pure_orderflow_trades.csv"
    trades_df.to_csv(out_path, index=False)
    print(f"Successfully generated {len(trades_df)} V2 trades and saved to {out_path}.")
