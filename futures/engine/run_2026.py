import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_data_5min(filepath):
    df = pd.read_csv(filepath, sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
    df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None)
    df = df.drop_duplicates(subset='datetime').sort_values('datetime')
    df.set_index('datetime', inplace=True)
    
    df_5m = df.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_5m['session_day'] = (df_5m.index + pd.Timedelta(hours=6)).date
    return df_5m

df_nq = load_data_5min(r'futures\data\MNQ_CONTINUOUS.txt')
df_gc = load_data_5min(r'futures\data\MGC_CONTINUOUS.txt')

# FILTER FOR 2026 ONLY
start_date = pd.to_datetime('2026-01-01').date()
df_nq = df_nq[df_nq['session_day'] >= start_date]
df_gc = df_gc[df_gc['session_day'] >= start_date]

nq_trades = []
for session_date, group in df_nq.groupby('session_day'):
    if group.empty: continue
    group = group.copy()
    group['typ'] = (group['high'] + group['low'] + group['close']) / 3.0
    group['pv'] = group['typ'] * group['volume']
    group['cum_vol'] = group['volume'].cumsum()
    group['vwap'] = group['pv'].cumsum() / group['cum_vol']
    group['dev_sq'] = ((group['typ'] - group['vwap']) ** 2) * group['volume']
    group['var'] = group['dev_sq'].cumsum() / group['cum_vol']
    group['stdev'] = np.sqrt(np.maximum(group['var'], 0))
    group['upper'] = group['vwap'] + 2.5 * group['stdev']
    group['lower'] = group['vwap'] - 2.5 * group['stdev']
    
    active_trade = None
    for idx, row in group.iterrows():
        if active_trade is not None:
            dir = active_trade['dir']
            sl = active_trade['sl']
            tp = active_trade['tp']
            hit_sl = (row['low'] <= sl) if dir == 1 else (row['high'] >= sl)
            hit_tp = (row['high'] >= tp) if dir == 1 else (row['low'] <= tp)
            if hit_sl or hit_tp or idx.time() >= pd.to_datetime('15:45').time():
                pnl = 4000 if hit_tp else (-2000 if hit_sl else 0)
                active_trade['pnl'] = pnl
                nq_trades.append(active_trade)
                break
            continue
            
        if pd.to_datetime('10:00').time() <= idx.time() <= pd.to_datetime('13:30').time():
            sig_l = (row['low'] < row['lower']) and (row['close'] > row['lower'])
            sig_s = (row['high'] > row['upper']) and (row['close'] < row['upper'])
            if sig_l:
                active_trade = {'datetime': idx, 'asset': 'NQ', 'dir': 1, 'sl': row['close']-20, 'tp': row['close']+40}
            elif sig_s:
                active_trade = {'datetime': idx, 'asset': 'NQ', 'dir': -1, 'sl': row['close']+20, 'tp': row['close']-40}

gc_trades = []
for session_date, group in df_gc.groupby('session_day'):
    lon = group.between_time('02:00', '08:00')
    if lon.empty: continue
    lon_h, lon_l = lon['high'].max(), lon['low'].min()
    
    active_trade = None
    for idx, row in group.between_time('09:40', '16:00').iterrows():
        if active_trade is not None:
            dir = active_trade['dir']
            sl = active_trade['sl']
            tp = active_trade['tp']
            hit_sl = (row['low'] <= sl) if dir == 1 else (row['high'] >= sl)
            hit_tp = (row['high'] >= tp) if dir == 1 else (row['low'] <= tp)
            if hit_sl or hit_tp or idx.time() >= pd.to_datetime('15:45').time():
                pnl = 3000 if hit_tp else (-2000 if hit_sl else 0)
                active_trade['pnl'] = pnl
                gc_trades.append(active_trade)
                break
            continue
            
        if pd.to_datetime('09:40').time() <= idx.time() <= pd.to_datetime('10:45').time():
            sig_l = (row['low'] < lon_l) and (row['close'] > lon_l) and ((lon_l - row['low']) >= 1.0)
            sig_s = (row['high'] > lon_h) and (row['close'] < lon_h) and ((row['high'] - lon_h) >= 1.0)
            if sig_l:
                active_trade = {'datetime': idx, 'asset': 'GC', 'dir': 1, 'sl': row['close']-2.0, 'tp': row['close']+3.0}
            elif sig_s:
                active_trade = {'datetime': idx, 'asset': 'GC', 'dir': -1, 'sl': row['close']+2.0, 'tp': row['close']-3.0}

df_all = pd.DataFrame(nq_trades + gc_trades)
if not df_all.empty:
    df_all = df_all.sort_values('datetime')
    df_all['date'] = df_all['datetime'].dt.date
    
    df_first = df_all.drop_duplicates(subset='date', keep='first').copy()
    df_first['cum_pnl'] = df_first['pnl'].cumsum()
    
    total_trades = len(df_first)
    total_days = (pd.to_datetime('today').date() - start_date).days
    avg_trades_per_day = total_trades / (total_days * (5/7)) # approximate trading days
    
    out_md = []
    out_md.append(f"Total 2026 Trades: {total_trades}")
    out_md.append(f"Avg Trades per Trading Day (Since Jan 1): {avg_trades_per_day:.2f}")
    out_md.append(f"Expected Trades in 10 Days: {avg_trades_per_day * 10:.1f}")
    
    plt.figure(figsize=(10,5))
    plt.plot(df_first['date'], df_first['cum_pnl'], color='#00E676', linewidth=2)
    plt.fill_between(df_first['date'], df_first['cum_pnl'], 0, color='#00E676', alpha=0.1)
    plt.title('First-to-Fire Equity Curve (2026 YTD)')
    plt.xlabel('Date')
    plt.ylabel('Cumulative PnL ($)')
    plt.grid(True, alpha=0.2)
    
    out_path = 'Curve_2026.png'
    plt.savefig(out_path, facecolor='#0d1117')
    
    with open('out_2026.txt', 'w') as f:
        f.write('\n'.join(out_md))
