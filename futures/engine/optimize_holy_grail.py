import pandas as pd
import numpy as np
import time
from concurrent.futures import ProcessPoolExecutor
import itertools

def preprocess_data(df_1m):
    df_resampled = df_1m.resample('5min', label='left', closed='left').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    df_resampled['date'] = df_resampled.index.date
    df_resampled['time'] = df_resampled.index.time
    
    days_data = []
    for date, group in df_resampled.groupby('date'):
        lon = group.between_time('02:00', '07:59')
        if lon.empty: continue
        lon_high, lon_low = lon['high'].max(), lon['low'].min()
        
        rth = group.between_time('09:30', '15:55').copy()
        if rth.empty: continue
        
        rth['pv'] = ((rth['high'] + rth['low'] + rth['close']) / 3) * rth['volume']
        rth['vwap'] = rth['pv'].cumsum() / rth['volume'].cumsum()
        
        bars = [{'time': row['time'], 'high': row['high'], 'low': row['low'], 'close': row['close'], 'vwap': row['vwap']} for idx, row in rth.iterrows()]
        days_data.append({'date': date, 'lon_high': lon_high, 'lon_low': lon_low, 'bars': bars})
    return days_data

def run_simulation_grail(days_data, stop_pts, target_pts, min_sweep, commission_per_contract=2.30, slippage_ticks=1):
    tick_size = 0.1
    point_value = 10.0
    slippage_pts = slippage_ticks * tick_size
    
    # 50% Rule Constraint: Max profit per trade cannot exceed $7,500
    # contracts * target_pts * 10 <= 7500
    contracts = int(7500.0 / (target_pts * point_value))
    if contracts < 1: contracts = 1
    
    daily_profit_cap = 7500.0 
    
    START_BAL = 250000.0
    PROFIT_TARGET = START_BAL + 15000.0
    MAX_DD = 10000.0
    DAILY_LOSS_LIMIT = 5000.0
    
    accounts = []
    def new_account(start_date):
        return {'start_date': start_date, 'end_date': None, 'balance': START_BAL, 'highest_eod_balance': START_BAL, 'liquidation_level': START_BAL - MAX_DD, 'status': 'ACTIVE', 'trades': 0, 'wins': 0, 'losses': 0}
        
    if not days_data: return accounts
    current_account = new_account(days_data[0]['date'])
    active_trade = None
    t_start, t_end, t_exit = pd.to_datetime('09:42').time(), pd.to_datetime('10:44').time(), pd.to_datetime('15:55').time()
    
    for day in days_data:
        date = day['date']
        if current_account['status'] != 'ACTIVE':
            current_account = new_account(date)
            
        lon_high, lon_low = day['lon_high'], day['lon_low']
        daily_pnl = 0.0
        
        for bar in day['bars']:
            t = bar['time']
            is_entry_window = (t_start <= t <= t_end)
            
            if active_trade is not None:
                pnl, trade_closed = 0.0, False
                if active_trade['dir'] == 1:
                    if bar['low'] <= active_trade['sl']:
                        pnl, trade_closed = (active_trade['sl'] - active_trade['entry']) * point_value * contracts, True
                    elif bar['high'] >= active_trade['tp']:
                        pnl, trade_closed = (active_trade['tp'] - active_trade['entry']) * point_value * contracts, True
                    elif t >= t_exit:
                        pnl, trade_closed = (bar['close'] - active_trade['entry']) * point_value * contracts, True
                else:
                    if bar['high'] >= active_trade['sl']:
                        pnl, trade_closed = (active_trade['entry'] - active_trade['sl']) * point_value * contracts, True
                    elif bar['low'] <= active_trade['tp']:
                        pnl, trade_closed = (active_trade['entry'] - active_trade['tp']) * point_value * contracts, True
                    elif t >= t_exit:
                        pnl, trade_closed = (active_trade['entry'] - bar['close']) * point_value * contracts, True
                        
                if trade_closed:
                    net_pnl = pnl - (commission_per_contract * contracts)
                    daily_pnl += net_pnl
                    current_account['balance'] += net_pnl
                    current_account['trades'] += 1
                    if net_pnl > 0: current_account['wins'] += 1
                    else: current_account['losses'] += 1
                    active_trade = None
                    
                    if current_account['balance'] <= current_account['liquidation_level'] or daily_pnl <= -DAILY_LOSS_LIMIT:
                        current_account['status'], current_account['end_date'] = 'BLOWN', date
                        accounts.append(current_account)
                        break
                    if current_account['balance'] >= PROFIT_TARGET:
                        current_account['status'], current_account['end_date'] = 'PASSED', date
                        accounts.append(current_account)
                        break
                    if daily_pnl >= daily_profit_cap:
                        break # Done trading for the day (50% rule cap)
                continue
                
            if is_entry_window and current_account['status'] == 'ACTIVE':
                sweep_high = (bar['high'] > lon_high) and (bar['close'] < lon_high) and (min_sweep <= (bar['high'] - lon_high) <= 25.0) and (bar['close'] <= bar['vwap'])
                sweep_low  = (bar['low'] < lon_low) and (bar['close'] > lon_low) and (min_sweep <= (lon_low - bar['low']) <= 25.0) and (bar['close'] >= bar['vwap'])
                
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
                if new_liq > 250100.0: new_liq = 250100.0
                current_account['liquidation_level'] = new_liq
                
    if current_account['status'] == 'ACTIVE':
        current_account['end_date'] = days_data[-1]['date']
        accounts.append(current_account)
        
    passed = sum(1 for a in accounts if a['status'] == 'PASSED')
    blown = sum(1 for a in accounts if 'BLOWN' in a['status'])
    wr = passed / (passed + blown) if (passed + blown) > 0 else 0
    avg_days = np.mean([(a['end_date'] - a['start_date']).days for a in accounts if a['status'] == 'PASSED']) if passed > 0 else 0
    
    return {'sl': stop_pts, 'tp': target_pts, 'min_sweep': min_sweep, 'contracts': contracts, 'risk_usd': contracts*stop_pts*10, 'passed': passed, 'blown': blown, 'win_rate': wr, 'avg_days': avg_days}

def worker(args):
    return run_simulation_grail(*args)

if __name__ == "__main__":
    df = pd.read_csv('futures/data/MGC_CONTINUOUS.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S').dt.tz_localize('UTC').dt.tz_convert('US/Eastern').dt.tz_localize(None)
    df.set_index('datetime', inplace=True)
    
    days_data = preprocess_data(df)
    
    sl_options = [10.0, 15.0, 20.0, 25.0]
    tp_options = [30.0, 40.0, 50.0, 60.0, 75.0]
    min_sweep_options = [1.0, 1.5, 2.0, 2.5, 3.0]
    
    combos = list(itertools.product(sl_options, tp_options, min_sweep_options))
    
    results = []
    with ProcessPoolExecutor() as executor:
        args_list = [(days_data, sl, tp, ms) for sl, tp, ms in combos]
        for res in executor.map(worker, args_list):
            results.append(res)
            
    df_res = pd.DataFrame(results)
    
    # Target: >70% win rate AND <30 avg_days
    df_target = df_res[(df_res['win_rate'] >= 0.70) & (df_res['avg_days'] <= 35) & (df_res['passed'] >= 2)]
    df_target = df_target.sort_values(by=['win_rate', 'avg_days'], ascending=[False, True])
    
    print("\nHoly Grail Setups (>70% WR, <35 Days):")
    if not df_target.empty:
        print(df_target.to_string(index=False))
    else:
        print("No setups strictly hit >70% WR and <35 days. Showing closest matches:")
        df_close = df_res[(df_res['win_rate'] >= 0.60) & (df_res['passed'] >= 3)].sort_values(by=['avg_days', 'win_rate'], ascending=[True, False])
        print(df_close.head(15).to_string(index=False))
        
    df_res.to_csv('futures/data/optimization_grail.csv', index=False)
