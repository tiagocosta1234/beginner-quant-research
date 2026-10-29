import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

df = pd.read_csv('futures/data/mnq_1m_continuous.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df.set_index('datetime', inplace=True)
df['date'] = df.index.date
df['time'] = df.index.time

def test_realistic_window(df, start_time, end_time):
    trades = []
    
    # Realistic Parameters: Evaluation Standard (4 MNQ Contracts)
    contracts = 4
    pt_val = 2.0
    min_sweep, max_sweep, stop_pts, target_pts = 2.0, 25.0, 25.0, 50.0
    
    # Real World Frictions
    comms_round_trip = 1.64 * contracts  # Tradovate typical micro fees
    slippage_pts_on_stop = 0.5           # 2 ticks slippage on stop market orders
    slippage_dlr = slippage_pts_on_stop * pt_val * contracts
    
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
                        # Stop Loss Hit (Full Risk + Slippage + Comms)
                        pnl = -(stop_pts * pt_val * contracts) - slippage_dlr - comms_round_trip
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif row['high'] >= active_trade['tp']: 
                        # Take Profit Hit (Limit Order, no slippage, just comms)
                        pnl = (target_pts * pt_val * contracts) - comms_round_trip
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif t >= pd.to_datetime('15:55').time(): 
                        # Time Flatten (Market Order, 1 tick slippage)
                        pts_gained = row['close'] - active_trade['entry']
                        pnl = (pts_gained * pt_val * contracts) - (0.25 * pt_val * contracts) - comms_round_trip
                        trades.append({'date': date, 'pnl': pnl})
                        break
                else:
                    if row['high'] >= active_trade['sl']: 
                        pnl = -(stop_pts * pt_val * contracts) - slippage_dlr - comms_round_trip
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif row['low'] <= active_trade['tp']: 
                        pnl = (target_pts * pt_val * contracts) - comms_round_trip
                        trades.append({'date': date, 'pnl': pnl})
                        break
                    elif t >= pd.to_datetime('15:55').time(): 
                        pts_gained = active_trade['entry'] - row['close']
                        pnl = (pts_gained * pt_val * contracts) - (0.25 * pt_val * contracts) - comms_round_trip
                        trades.append({'date': date, 'pnl': pnl})
                        break
                continue
                
            if pd.to_datetime(start_time).time() <= t <= pd.to_datetime(end_time).time():
                sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (min_sweep <= (row['high'] - lon_high) <= max_sweep) and (row['close'] <= row['vwap'])
                sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (min_sweep <= (lon_low - row['low']) <= max_sweep) and (row['close'] >= row['vwap'])
                if sweep_low: active_trade = {'dir': 1, 'entry': lon_low, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts}
                elif sweep_high: active_trade = {'dir': -1, 'entry': lon_high, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts}
                
    if not trades: return None
    return pd.DataFrame(trades)

print("Calculating Hyper-Realistic Backtest...")
res = test_realistic_window(df, '14:30', '15:30')
res['cum_pnl'] = res['pnl'].cumsum()

# End Of Day (EOD) Trailing Drawdown Logic (BROKER Rules)
# BROKER calculates max drawdown based on End of Day balance, not intraday open equity.
daily_pnl = res.groupby('date')['pnl'].sum().reset_index()
daily_pnl['cum_pnl'] = daily_pnl['pnl'].cumsum()
daily_pnl['eod_peak'] = daily_pnl['cum_pnl'].cummax()
daily_pnl['eod_drawdown'] = daily_pnl['eod_peak'] - daily_pnl['cum_pnl']

max_dd = daily_pnl['eod_drawdown'].max()
win_rate = len(res[res['pnl'] > 0]) / len(res) * 100
total_pnl = res['cum_pnl'].iloc[-1]
max_loss_streak = (res['pnl'] < 0).astype(int).groupby(res['pnl'].ge(0).cumsum()).sum().max()
total_comms = len(res) * (1.64 * 4)

plt.figure(figsize=(12, 6))
plt.plot(res.index, res['cum_pnl'], label='Cumulative PnL (Net of Fees)', color='blue', linewidth=2)
plt.title(f'HYPER REALISTIC MNQ (4 Contracts) - 1.3 Years\nTotal Net PnL: ${total_pnl:,.2f} | EOD Max DD: ${max_dd:,.2f} | WR: {win_rate:.1f}%')
plt.xlabel('Trade Number')
plt.ylabel('Net PnL ($)')
plt.legend()
plt.grid(True, alpha=0.5)
out_path = 'MNQ_Realistic_Equity_Curve.png'
plt.savefig(out_path)

print(f"Total Net PnL: ${total_pnl:.2f}")
print(f"Total Commissions Paid: ${total_comms:.2f}")
print(f"EOD Trailing Max Drawdown: ${max_dd:.2f}")
print(f"Max Losing Streak: {max_loss_streak} trades")
print(f"Win Rate: {win_rate:.1f}%")
