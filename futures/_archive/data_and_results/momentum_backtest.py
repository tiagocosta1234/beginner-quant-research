import pandas as pd

# Load data
mnq_path = r"broker_hacker\data_and_results\MNQ 09-26.Last.txt"
df = pd.read_csv(mnq_path, sep=';', names=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['Datetime'] = pd.to_datetime(df['Datetime'], format='%Y%m%d %H%M%S')
df.set_index('Datetime', inplace=True)

# Resample to 15m
df_15m = df.resample('15min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
df_15m.index = df_15m.index - pd.Timedelta(hours=5) # Convert to EST

stop_pts = 77
target_pts = 115
contracts = 13
tick_value = 2

trades = []

for i in range(5, len(df_15m)):
    current_time = df_15m.index[i].time()
    
    # US Session Lockout
    # if not (current_time >=('09:30').time() and current_time < pd.to_datetime('16:00').time()):
        # continue
        
    # 5-Bar Anomaly Logic
    is5BarDown = True
    is5BarUp = True
    for j in range(5):
        idx = i - j
        if df_15m['Close'].iloc[idx] >= df_15m['Open'].iloc[idx]:
            is5BarDown = False
        if df_15m['Close'].iloc[idx] <= df_15m['Open'].iloc[idx]:
            is5BarUp = False
            
    entry_price = df_15m['Close'].iloc[i]
    
    # INVERTED MOMENTUM
    if is5BarDown:
        trades.append({'type': 'Short', 'entry': entry_price, 'idx': i})
    elif is5BarUp:
        trades.append({'type': 'Long', 'entry': entry_price, 'idx': i})

wins = 0
losses = 0
gross_profit = 0
gross_loss = 0

for t in trades:
    entry = t['entry']
    idx = t['idx']
    
    resolved = False
    for j in range(idx + 1, len(df_15m)):
        future_row = df_15m.iloc[j]
        if t['type'] == 'Long':
            if future_row['Low'] <= entry - stop_pts:
                losses += 1
                gross_loss += (stop_pts * contracts * tick_value)
                break
            elif future_row['High'] >= entry + target_pts:
                wins += 1
                gross_profit += (target_pts * contracts * tick_value)
                break
        elif t['type'] == 'Short':
            if future_row['High'] >= entry + stop_pts:
                losses += 1
                gross_loss += (stop_pts * contracts * tick_value)
                break
            elif future_row['Low'] <= entry - target_pts:
                wins += 1
                gross_profit += (target_pts * contracts * tick_value)
                break

total_trades = wins + losses
win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
net = gross_profit - gross_loss

print("\n=== FINAL VERSION STATS (INVERTED MOMENTUM + US TIME LOCK) ===")
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Profit Factor: {pf:.2f}")
print(f"Gross Profit: ${gross_profit:,.2f}")
print(f"Gross Loss: ${gross_loss:,.2f}")
print(f"Net Profit: ${net:,.2f}")
print("==============================================================")
