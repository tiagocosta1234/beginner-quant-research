import pandas as pd
import numpy as np
import time
from concurrent.futures import ProcessPoolExecutor
import itertools

def preprocess_data(df_1m):
    print("Resampling to 5m...")
    df_resampled = df_1m.resample('5min', label='left', closed='left').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    df_resampled['date'] = df_resampled.index.date
    df_resampled['time'] = df_resampled.index.time
    
    days_data = []
    
    print("Grouping by date and calculating VWAP...")
    for date, group in df_resampled.groupby('date'):
        lon = group.between_time('02:00', '07:59')
        if lon.empty: continue
        lon_high, lon_low = lon['high'].max(), lon['low'].min()
        
        rth = group.between_time('09:30', '15:55').copy()
        if rth.empty: continue
        
        rth['pv'] = ((rth['high'] + rth['low'] + rth['close']) / 3) * rth['volume']
        rth['vwap'] = rth['pv'].cumsum() / rth['volume'].cumsum()
        
        # Pre-convert to list of dicts for extreme speed
        bars = []
        for idx, row in rth.iterrows():
            bars.append({
                'time': row['time'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'vwap': row['vwap']
            })
            
        days_data.append({
            'date': date,
            'lon_high': lon_high,
            'lon_low': lon_low,
            'bars': bars
        })
        
    return days_data

def run_simulation_fast(days_data, stop_pts, target_pts, risk_usd, commission_per_contract=2.30, slippage_ticks=1):
    tick_size = 0.1
    point_value = 10.0
    slippage_pts = slippage_ticks * tick_size
    
    # Calculate contracts based on risk
    # Risk = contracts * stop_pts * 10
    contracts = max(1, int(round(risk_usd / (stop_pts * point_value))))
    daily_profit_cap = 5000.0
    
    START_BAL = 250000.0
    PROFIT_TARGET = START_BAL + 15000.0
    MAX_DD = 10000.0
    DAILY_LOSS_LIMIT = 5000.0
    
    accounts = []
    
    def new_account(start_date):
        return {
            'start_date': start_date,
            'end_date': None,
            'balance': START_BAL,
            'highest_eod_balance': START_BAL,
            'liquidation_level': START_BAL - MAX_DD,
            'status': 'ACTIVE',
            'trades': 0, 'wins': 0, 'losses': 0
        }
        
    if not days_data: return accounts
    
    current_account = new_account(days_data[0]['date'])
    active_trade = None
    
    # Time constants
    t_start = pd.to_datetime('09:42').time()
    t_end = pd.to_datetime('10:44').time()
    t_exit = pd.to_datetime('15:55').time()
    
    for day in days_data:
        date = day['date']
        if current_account['status'] != 'ACTIVE':
            current_account = new_account(date)
            
        lon_high = day['lon_high']
        lon_low = day['lon_low']
        
        daily_pnl = 0.0
        
        for bar in day['bars']:
            t = bar['time']
            is_entry_window = (t_start <= t <= t_end)
            
            if active_trade is not None:
                pnl = 0.0
                trade_closed = False
                
                if active_trade['dir'] == 1:
                    if bar['low'] <= active_trade['sl']:
                        pnl = (active_trade['sl'] - active_trade['entry']) * point_value * contracts
                        trade_closed = True
                    elif bar['high'] >= active_trade['tp']:
                        pnl = (active_trade['tp'] - active_trade['entry']) * point_value * contracts
                        trade_closed = True
                    elif t >= t_exit:
                        pnl = (bar['close'] - active_trade['entry']) * point_value * contracts
                        trade_closed = True
                else:
                    if bar['high'] >= active_trade['sl']:
                        pnl = (active_trade['entry'] - active_trade['sl']) * point_value * contracts
                        trade_closed = True
                    elif bar['low'] <= active_trade['tp']:
                        pnl = (active_trade['entry'] - active_trade['tp']) * point_value * contracts
                        trade_closed = True
                    elif t >= t_exit:
                        pnl = (active_trade['entry'] - bar['close']) * point_value * contracts
                        trade_closed = True
                        
                if trade_closed:
                    net_pnl = pnl - (commission_per_contract * contracts)
                    daily_pnl += net_pnl
                    current_account['balance'] += net_pnl
                    current_account['trades'] += 1
                    if net_pnl > 0:
                        current_account['wins'] += 1
                    else:
                        current_account['losses'] += 1
                        
                    active_trade = None
                    
                    if current_account['balance'] <= current_account['liquidation_level']:
                        current_account['status'] = 'BLOWN'
                        current_account['end_date'] = date
                        accounts.append(current_account)
                        break
                        
                    if daily_pnl <= -DAILY_LOSS_LIMIT:
                        current_account['status'] = 'BLOWN'
                        current_account['end_date'] = date
                        accounts.append(current_account)
                        break
                        
                    if daily_pnl >= daily_profit_cap:
                        break
                        
                    if current_account['balance'] >= PROFIT_TARGET:
                        current_account['status'] = 'PASSED'
                        current_account['end_date'] = date
                        accounts.append(current_account)
                        break
                continue
                
            if is_entry_window and current_account['status'] == 'ACTIVE':
                sweep_high = (bar['high'] > lon_high) and (bar['close'] < lon_high) and (1.0 <= (bar['high'] - lon_high) <= 25.0) and (bar['close'] <= bar['vwap'])
                sweep_low  = (bar['low'] < lon_low) and (bar['close'] > lon_low) and (1.0 <= (lon_low - bar['low']) <= 25.0) and (bar['close'] >= bar['vwap'])
                
                if sweep_low:
                    entry_px = bar['close'] + slippage_pts
                    active_trade = {'dir': 1, 'entry': entry_px, 'sl': entry_px - stop_pts, 'tp': entry_px + target_pts}
                elif sweep_high:
                    entry_px = bar['close'] - slippage_pts
                    active_trade = {'dir': -1, 'entry': entry_px, 'sl': entry_px + stop_pts, 'tp': entry_px - target_pts}
                    
        if current_account['status'] == 'ACTIVE':
            if current_account['balance'] > current_account['highest_eod_balance']:
                current_account['highest_eod_balance'] = current_account['balance']
                new_liq = current_account['highest_eod_balance'] - MAX_DD
                if new_liq > 250100.0:
                    new_liq = 250100.0
                current_account['liquidation_level'] = new_liq
                
    if current_account['status'] == 'ACTIVE':
        current_account['end_date'] = days_data[-1]['date']
        accounts.append(current_account)
        
    passed = sum(1 for a in accounts if a['status'] == 'PASSED')
    blown = sum(1 for a in accounts if 'BLOWN' in a['status'])
    active = sum(1 for a in accounts if a['status'] == 'ACTIVE')
    wr = passed / (passed + blown) if (passed + blown) > 0 else 0
    avg_days_to_pass = np.mean([(a['end_date'] - a['start_date']).days for a in accounts if a['status'] == 'PASSED']) if passed > 0 else 0
    
    return {
        'sl': stop_pts,
        'tp': target_pts,
        'risk': risk_usd,
        'contracts': contracts,
        'passed': passed,
        'blown': blown,
        'active': active,
        'win_rate': wr,
        'avg_days': avg_days_to_pass
    }

def worker(args):
    days_data, sl, tp, risk = args
    return run_simulation_fast(days_data, sl, tp, risk)

if __name__ == "__main__":
    print("Loading continuous MGC data...")
    df = pd.read_csv('futures/data/MGC_CONTINUOUS.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S').dt.tz_localize('UTC').dt.tz_convert('US/Eastern').dt.tz_localize(None)
    df.set_index('datetime', inplace=True)
    
    days_data = preprocess_data(df)
    
    sl_options = [15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
    tp_options = [15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0]
    risk_options = [1000, 1500, 2000, 2500, 3000]
    
    combos = list(itertools.product(sl_options, tp_options, risk_options))
    print(f"Testing {len(combos)} combinations...")
    
    results = []
    start_time = time.time()
    
    # Use multiprocessing for speed
    with ProcessPoolExecutor() as executor:
        args_list = [(days_data, sl, tp, risk) for sl, tp, risk in combos]
        for res in executor.map(worker, args_list):
            results.append(res)
            
    print(f"Optimization finished in {time.time() - start_time:.2f} seconds.")
    
    df_res = pd.DataFrame(results)
    # Sort by Most Passed, then Fewest Blown, then Win Rate, then Fastest
    df_res = df_res.sort_values(by=['passed', 'win_rate', 'blown', 'avg_days'], ascending=[False, False, True, True])
    
    print("\nTop 15 Configurations:")
    print(df_res.head(15).to_string(index=False))
    
    df_res.to_csv('futures/data/optimization_results.csv', index=False)
