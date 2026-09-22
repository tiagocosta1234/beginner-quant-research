import pandas as pd
import numpy as np

# Paths
mnq_path = r"broker_hacker\data_and_results\MNQ 09-26.Last.txt"
mes_path = r"broker_hacker\data_and_results\MES 09-26.Last.txt"

def load_data(filepath):
    print(f"Loading {filepath}...")
    df = pd.read_csv(filepath, sep=';', names=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], format='%Y%m%d %H%M%S')
    df.set_index('Datetime', inplace=True)
    return df

mnq = load_data(mnq_path)
mes = load_data(mes_path)

# Resample to 15-minute
print("Resampling to 15-minute Structural Candles...")
def resample_15m(df):
    return df.resample('15min').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

mnq_15m = resample_15m(mnq)
mes_15m = resample_15m(mes)

# Merge datasets
df = mnq_15m.join(mes_15m, lsuffix='_mnq', rsuffix='_mes', how='inner')

# Shift timezone to EST (assuming local NinjaTrader export was UTC+1)
# 15:00 UTC+1 = 10:00 AM EST (Shift by -5 hours)
df.index = df.index - pd.Timedelta(hours=5)

# Strategy Parameters
lookback = 20
stop_pts = 40
target_pts = 40
contracts = 13
tick_value = 2 # MNQ is $2 per point

# Donchian Channels (Shifted so it evaluates the previous 20 bars, not including current)
df['mnq_lowest'] = df['Low_mnq'].rolling(lookback).min().shift(1)
df['mnq_highest'] = df['High_mnq'].rolling(lookback).max().shift(1)
df['mes_lowest'] = df['Low_mes'].rolling(lookback).min().shift(1)
df['mes_highest'] = df['High_mes'].rolling(lookback).max().shift(1)

trades = []

# Scan for SMT
print("Scanning for SMT Divergence...")
for i in range(lookback + 1, len(df)):
    current_time = df.index[i].time()
    
    # US Session Lockout
    if not (current_time >= pd.to_datetime('09:30').time() and current_time < pd.to_datetime('16:00').time()):
        continue
        
    row = df.iloc[i]
    
    # SMT Logic
    mnq_swept_low = row['Low_mnq'] < row['mnq_lowest']
    mes_swept_low = row['Low_mes'] < row['mes_lowest']
    
    mnq_swept_high = row['High_mnq'] > row['mnq_highest']
    mes_swept_high = row['High_mes'] > row['mes_highest']
    
    bullish_smt = (mnq_swept_low and not mes_swept_low) or (not mnq_swept_low and mes_swept_low)
    bearish_smt = (mnq_swept_high and not mes_swept_high) or (not mnq_swept_high and mes_swept_high)
    
    bullish_conf = bullish_smt and (row['Close_mnq'] > row['Open_mnq'])
    bearish_conf = bearish_smt and (row['Close_mnq'] < row['Open_mnq'])
    
    if bullish_conf:
        trades.append({'type': 'Long', 'entry': row['Close_mnq'], 'idx': i, 'date': df.index[i]})
    elif bearish_conf:
        trades.append({'type': 'Short', 'entry': row['Close_mnq'], 'idx': i, 'date': df.index[i]})

# Resolve Trades
wins = 0
losses = 0
gross_profit = 0
gross_loss = 0

for t in trades:
    entry = t['entry']
    idx = t['idx']
    
    resolved = False
    # Forward look to resolve trade
    for j in range(idx + 1, len(df)):
        future_row = df.iloc[j]
        
        if t['type'] == 'Long':
            if future_row['Low_mnq'] <= entry - stop_pts:
                losses += 1
                gross_loss += (stop_pts * contracts * tick_value)
                resolved = True
                break
            elif future_row['High_mnq'] >= entry + target_pts:
                wins += 1
                gross_profit += (target_pts * contracts * tick_value)
                resolved = True
                break
        elif t['type'] == 'Short':
            if future_row['High_mnq'] >= entry + stop_pts:
                losses += 1
                gross_loss += (stop_pts * contracts * tick_value)
                resolved = True
                break
            elif future_row['Low_mnq'] <= entry - target_pts:
                wins += 1
                gross_profit += (target_pts * contracts * tick_value)
                resolved = True
                break

total_trades = wins + losses
win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

print("\n=== MULTI-ASSET SMT DIVERGENCE (MNQ + MES) ===")
print(f"Total Trades: {total_trades}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Gross Profit: ${gross_profit:,.2f}")
print(f"Gross Loss: ${gross_loss:,.2f}")
print(f"Net Profit: ${gross_profit - gross_loss:,.2f}")
print(f"Profit Factor: {profit_factor:.2f}")
print("==============================================")
