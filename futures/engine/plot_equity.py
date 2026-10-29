import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

df = pd.read_csv('futures/data/mnq_1m_continuous.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df.set_index('datetime', inplace=True)
df['date'] = df.index.date
df['time'] = df.index.time

def test_window(df, start_time, end_time):
    trades = []
    min_sweep, max_sweep, stop_pts, target_pts = 2.0, 25.0, 25.0, 50.0
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
                    if row['low'] <= active_trade['sl']: trades.append({'date': date, 'pnl': -500.0}); break
                    elif row['high'] >= active_trade['tp']: trades.append({'date': date, 'pnl': 1000.0}); break
                    elif t >= pd.to_datetime('15:55').time(): trades.append({'date': date, 'pnl': (row['close'] - active_trade['entry']) * 20.0}); break
                else:
                    if row['high'] >= active_trade['sl']: trades.append({'date': date, 'pnl': -500.0}); break
                    elif row['low'] <= active_trade['tp']: trades.append({'date': date, 'pnl': 1000.0}); break
                    elif t >= pd.to_datetime('15:55').time(): trades.append({'date': date, 'pnl': (active_trade['entry'] - row['close']) * 20.0}); break
                continue
                
            if pd.to_datetime(start_time).time() <= t <= pd.to_datetime(end_time).time():
                sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (min_sweep <= (row['high'] - lon_high) <= max_sweep) and (row['close'] <= row['vwap'])
                sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (min_sweep <= (lon_low - row['low']) <= max_sweep) and (row['close'] >= row['vwap'])
                if sweep_low: active_trade = {'dir': 1, 'entry': lon_low, 'sl': lon_low - stop_pts, 'tp': lon_low + target_pts}
                elif sweep_high: active_trade = {'dir': -1, 'entry': lon_high, 'sl': lon_high + stop_pts, 'tp': lon_high - target_pts}
                
    if not trades: return None
    res = pd.DataFrame(trades)
    return res

print("Calculating...")
res = test_window(df, '14:30', '15:30')
res['cum_pnl'] = res['pnl'].cumsum()
res['peak'] = res['cum_pnl'].cummax()
res['drawdown'] = res['peak'] - res['cum_pnl']
max_dd = res['drawdown'].max()
win_rate = len(res[res['pnl'] > 0]) / len(res) * 100
total_pnl = res['cum_pnl'].iloc[-1]
max_loss_streak = (res['pnl'] < 0).astype(int).groupby(res['pnl'].ge(0).cumsum()).sum().max()

plt.figure(figsize=(12, 6))
plt.plot(res.index, res['cum_pnl'], label='Cumulative PnL', color='blue', linewidth=2)
plt.fill_between(res.index, res['cum_pnl'], res['peak'], color='red', alpha=0.3, label='Drawdown')
plt.title(f'MNQ Power Hour (14:30-15:30) Equity Curve (1.3 Years)\nTotal PnL: ${total_pnl:,.2f} | Max DD: ${max_dd:,.2f} | WR: {win_rate:.1f}%')
plt.xlabel('Trade Number')
plt.ylabel('PnL ($)')
plt.legend()
plt.grid(True, alpha=0.5)
out_path = 'MNQ_Equity_Curve.png'
plt.savefig(out_path)
print(f'MaxDrawdown: ${max_dd}')
print(f'MaxLossStreak: {max_loss_streak}')
print(f'TotalPnL: ${total_pnl}')
