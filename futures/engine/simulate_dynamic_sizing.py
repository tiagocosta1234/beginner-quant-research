import pandas as pd
import numpy as np

print("Loading continuous MGC data for Sizing Simulation...")
df = pd.read_csv('futures/data/MGC_CONTINUOUS.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S') - pd.Timedelta(hours=4)
df.set_index('datetime', inplace=True)

df_5m = df.resample('5min', label='left', closed='left').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
df_5m['date'] = df_5m.index.date
df_5m['time'] = df_5m.index.time

stop_pts = 25.0
target_pts = 40.0
min_sweep = 1.0

results = []

for date, group in df_5m.groupby('date'):
    lon = group.between_time('02:00', '07:59')
    if lon.empty: continue
    lon_high, lon_low = lon['high'].max(), lon['low'].min()
    
    rth = group.between_time('09:30', '15:55').copy()
    if rth.empty: continue
    rth['pv'] = ((rth['high'] + rth['low'] + rth['close']) / 3) * rth['volume']
    rth['vwap'] = rth['pv'].cumsum() / rth['volume'].cumsum()
    
    active = None
    for idx, row in rth.iterrows():
        t = row.name.time()
        
        if active:
            if active['dir'] == 1:
                if row['low'] <= active['sl']: 
                    active['outcome'] = 'LOSS'
                    results.append(active)
                    active = None
                elif row['high'] >= active['tp']: 
                    active['outcome'] = 'WIN'
                    results.append(active)
                    active = None
            else:
                if row['high'] >= active['sl']: 
                    active['outcome'] = 'LOSS'
                    results.append(active)
                    active = None
                elif row['low'] <= active['tp']: 
                    active['outcome'] = 'WIN'
                    results.append(active)
                    active = None
                    
            if active and t >= pd.to_datetime('15:55').time():
                active['outcome'] = 'FLAT'
                results.append(active)
                active = None
            continue
            
        if pd.to_datetime('09:42').time() <= t <= pd.to_datetime('10:45').time():
            sweep_high_depth = row['high'] - lon_high
            sweep_low_depth = lon_low - row['low']
            
            sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (sweep_high_depth >= min_sweep) and (row['close'] <= row['vwap'])
            sweep_low = (row['low'] < lon_low) and (row['close'] > lon_low) and (sweep_low_depth >= min_sweep) and (row['close'] >= row['vwap'])
            
            if sweep_low:
                active = {'date': row['date'], 'time': t, 'dir': 1, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts, 'sweep_depth': sweep_low_depth, 'vwap_dist': row['close'] - row['vwap']}
            elif sweep_high:
                active = {'date': row['date'], 'time': t, 'dir': -1, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts, 'sweep_depth': sweep_high_depth, 'vwap_dist': row['vwap'] - row['close']}

df_res = pd.DataFrame(results)
df_res = df_res[df_res['outcome'] != 'FLAT']

# Assign Grades
def get_grade(row):
    t = pd.to_datetime(str(row['time'])).time()
    if t >= pd.to_datetime('10:30').time():
        return 'F'
    sd = row['sweep_depth']
    if 3.0 <= sd <= 6.0: return 'A'
    if sd > 10.0: return 'B'
    if sd < 3.0: return 'C'
    return 'D'

df_res['grade'] = df_res.apply(get_grade, axis=1)

models = {
    '1. Static (1 GC / $2500 Risk)': {'A': 10, 'B': 10, 'C': 10, 'D': 10, 'F': 10},
    '2. Smart Static (Skip F)': {'A': 10, 'B': 10, 'C': 10, 'D': 10, 'F': 0},
    '3. Defensive (Skip C/D/F)': {'A': 10, 'B': 10, 'C': 0, 'D': 0, 'F': 0},
    '4. Proportional Sizing': {'A': 15, 'B': 10, 'C': 5, 'D': 2, 'F': 0},
    '5. Hyper-Aggressive (A Only)': {'A': 20, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
}

pt_val = 10.0 # Using MGC contracts (10 MGC = 1 GC)

print("\n=== SIZING MODEL SIMULATION (3.5 YEARS) ===\n")

for model_name, sizing in models.items():
    equity = 0
    max_equity = 0
    max_dd = 0
    wins = 0
    losses = 0
    gross_profit = 0
    gross_loss = 0
    
    for idx, row in df_res.iterrows():
        contracts = sizing[row['grade']]
        if contracts == 0: continue
        
        risk = stop_pts * pt_val * contracts
        reward = target_pts * pt_val * contracts
        
        if row['outcome'] == 'WIN':
            equity += reward
            wins += 1
            gross_profit += reward
        else:
            equity -= risk
            losses += 1
            gross_loss += risk
            
        if equity > max_equity:
            max_equity = equity
        dd = max_equity - equity
        if dd > max_dd:
            max_dd = dd
            
    total_trades = wins + losses
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    print(f"Model: {model_name}")
    print(f"Total Trades: {total_trades} | Win Rate: {win_rate:.1f}%")
    print(f"Net Profit: ${equity:,.2f} | Max Drawdown: ${max_dd:,.2f}")
    print(f"Profit Factor: {pf:.2f} | Return/MaxDD: {(equity/max_dd) if max_dd > 0 else 0:.2f}")
    print("-" * 50)
