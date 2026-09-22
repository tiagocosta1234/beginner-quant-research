import pandas as pd
import numpy as np

file_path = r'broker_hacker\data_and_results\MNQ 09-26.Last.txt'
df = pd.read_csv(file_path, sep=';', header=None, names=['datetime', 'open', 'high', 'low', 'close', 'vol'])
df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d %H%M%S')
df.set_index('datetime', inplace=True)

# Resample to 15m. NinjaTrader aligns 15m bars to start of session, but standard 'left' works as a proxy.
df_15m = df.resample('15min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last'}).dropna()

df_15m['is_red'] = df_15m['close'] < df_15m['open']
df_15m['is_green'] = df_15m['close'] > df_15m['open']

df_15m['5_red'] = df_15m['is_red'].rolling(5).sum() == 5
df_15m['5_green'] = df_15m['is_green'].rolling(5).sum() == 5

signals = df_15m[(df_15m['5_red']) | (df_15m['5_green'])].copy()

results = []
for points in range(10, 101, 10):
    wins = 0
    losses = 0
    consec_losses = 0
    max_consec_losses = 0
    
    for idx, row in signals.iterrows():
        trigger_time = idx + pd.Timedelta(minutes=15)
        
        # Optimize: grab slice using index
        # We only need enough future rows, typically it resolves within 2 days. 
        # Using a fixed window slice makes it blazing fast.
        end_time = trigger_time + pd.Timedelta(days=3)
        future = df[(df.index >= trigger_time) & (df.index < end_time)]
        
        entry_price = df_15m.loc[idx, 'close']
        
        if row['5_red']:
            target = entry_price - points
            stop = entry_price + points
            for f_row in future.itertuples():
                if f_row.high >= stop and f_row.low <= target:
                    losses += 1
                    consec_losses += 1
                    max_consec_losses = max(max_consec_losses, consec_losses)
                    break
                elif f_row.high >= stop:
                    losses += 1
                    consec_losses += 1
                    max_consec_losses = max(max_consec_losses, consec_losses)
                    break
                elif f_row.low <= target:
                    wins += 1
                    consec_losses = 0
                    break
                    
        elif row['5_green']:
            target = entry_price + points
            stop = entry_price - points
            for f_row in future.itertuples():
                if f_row.low <= stop and f_row.high >= target:
                    losses += 1
                    consec_losses += 1
                    max_consec_losses = max(max_consec_losses, consec_losses)
                    break
                elif f_row.low <= stop:
                    losses += 1
                    consec_losses += 1
                    max_consec_losses = max(max_consec_losses, consec_losses)
                    break
                elif f_row.high >= target:
                    wins += 1
                    consec_losses = 0
                    break
                    
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    contracts = max(1, int(1000 // (points * 2)))
    
    results.append(f"{points:^8} | {contracts:^10} | {win_rate:^9.2f}% | {max_consec_losses:^18} | {total:^12}")

print(f"{'Points':^8} | {'Contracts':^10} | {'Win Rate':^10} | {'Max Consec Losers':^18} | {'Total Trades':^12}")
print("-" * 70)
for r in results:
    print(r)
