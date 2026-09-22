import pandas as pd
import numpy as np

# 1. Load the 1.3-Year Continuous Data
df1 = pd.read_csv('futures/data/mnq_1m_continuous.csv')
df1['datetime'] = pd.to_datetime(df1['datetime'])

# 2. Load the recent 3-Month Data (MNQ.txt)
df2 = pd.read_csv('futures/data/MNQ.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
df2['datetime'] = pd.to_datetime(df2['datetime_str'], format='%Y%m%d %H%M%S')
df2.drop(columns=['datetime_str'], inplace=True)

# 3. Merge, Standardize, and Timezone Shift
df = pd.concat([df1, df2])
df = df.drop_duplicates(subset='datetime').sort_values('datetime')
df['datetime'] = df['datetime'] - pd.Timedelta(hours=4) # Convert UTC to NY Time (EDT)
df.set_index('datetime', inplace=True)
df['date'] = df.index.date

def run_realistic_backtest(df, start_time, end_time, name):
    trades = []
    contracts = 4
    pt_val = 2.0
    min_sweep, max_sweep, stop_pts, target_pts = 2.0, 25.0, 25.0, 50.0
    comms_rt = 1.64 * contracts
    slip_dlr = 0.5 * pt_val * contracts
    
    for date, group in df.groupby('date'):
        london_data = group.between_time('02:00', '08:00')
        if london_data.empty: continue
        lon_high, lon_low = london_data['high'].max(), london_data['low'].min()
        
        rth_data = group.between_time('09:30', '16:00').copy()
        if rth_data.empty: continue
        rth_data['pv'] = ((rth_data['high'] + rth_data['low'] + rth_data['close'])/3) * rth_data['volume']
        rth_data['vwap'] = rth_data['pv'].cumsum() / rth_data['volume'].cumsum()
        
        active_trade = None
        for idx, row in rth_data.iterrows():
            t = row.name.time()
            if active_trade is not None:
                if active_trade['dir'] == 1:
                    if row['low'] <= active_trade['sl']: 
                        pnl = -(stop_pts * pt_val * contracts) - slip_dlr - comms_rt
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif row['high'] >= active_trade['tp']: 
                        pnl = (target_pts * pt_val * contracts) - comms_rt
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif t >= pd.to_datetime('15:55').time(): 
                        pts = row['close'] - active_trade['entry']
                        pnl = (pts * pt_val * contracts) - (0.25 * pt_val * contracts) - comms_rt
                        trades.append({'date': date, 'pnl': pnl})
                        break
                else:
                    if row['high'] >= active_trade['sl']: 
                        pnl = -(stop_pts * pt_val * contracts) - slip_dlr - comms_rt
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif row['low'] <= active_trade['tp']: 
                        pnl = (target_pts * pt_val * contracts) - comms_rt
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif t >= pd.to_datetime('15:55').time(): 
                        pts = active_trade['entry'] - row['close']
                        pnl = (pts * pt_val * contracts) - (0.25 * pt_val * contracts) - comms_rt
                        trades.append({'date': date, 'pnl': pnl})
                        break
                continue
                
            if pd.to_datetime(start_time).time() <= t <= pd.to_datetime(end_time).time():
                sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (min_sweep <= (row['high'] - lon_high) <= max_sweep) and (row['close'] <= row['vwap'])
                sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (min_sweep <= (lon_low - row['low']) <= max_sweep) and (row['close'] >= row['vwap'])
                
                if sweep_low: active_trade = {'dir': 1, 'entry': lon_low, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts}
                elif sweep_high: active_trade = {'dir': -1, 'entry': lon_high, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts}
                
    if not trades: return None
    res = pd.DataFrame(trades)
    wins = len(res[res['pnl'] > 0])
    wr = wins / len(res) * 100
    res['cum_pnl'] = res['pnl'].cumsum()
    daily = res.groupby('date')['pnl'].sum().reset_index()
    daily['cum'] = daily['pnl'].cumsum()
    max_dd = (daily['cum'].cummax() - daily['cum']).max()
    net = res['cum_pnl'].iloc[-1]
    
    print(f"\n--- TRUE NY TIME: {name} ({start_time} - {end_time}) ---")
    print(f"Total Trades: {len(res)}")
    print(f"Win Rate: {wr:.1f}%")
    print(f"Net PnL (After Fees): ${net:.2f}")
    print(f"Max EOD Drawdown: ${max_dd:.2f}")
    
run_realistic_backtest(df, '09:42', '10:45', 'AM Institutional Window')
run_realistic_backtest(df, '14:30', '15:30', 'PM Power Hour Window')
