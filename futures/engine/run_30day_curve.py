import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_data(filepath):
    df = pd.read_csv(filepath, sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
    df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None)
    df = df.drop_duplicates(subset='datetime').sort_values('datetime')
    df.set_index('datetime', inplace=True)
    df['date'] = df.index.date
    return df

df_nq = load_data(r'futures\data\MNQ_CONTINUOUS.txt')
df_gc = load_data(r'futures\data\MGC_CONTINUOUS.txt')

max_date = max(df_nq.index.max(), df_gc.index.max())
start_date = max_date - pd.Timedelta(days=30)

df_nq = df_nq[df_nq.index >= start_date]
df_gc = df_gc[df_gc.index >= start_date]

nq_trades = []
for date, group in df_nq.groupby('date'):
    rth = group.between_time('09:30', '16:00').copy()
    if rth.empty: continue
    
    rth['typ'] = (rth['high'] + rth['low'] + rth['close']) / 3.0
    rth['pv'] = rth['typ'] * rth['volume']
    rth['cum_vol'] = rth['volume'].cumsum()
    rth['vwap'] = rth['pv'].cumsum() / rth['cum_vol']
    
    rth['dev_sq'] = ((rth['typ'] - rth['vwap']) ** 2) * rth['volume']
    rth['var'] = rth['dev_sq'].cumsum() / rth['cum_vol']
    rth['stdev'] = np.sqrt(np.maximum(rth['var'], 0))
    
    rth['upper'] = rth['vwap'] + 2.5 * rth['stdev']
    rth['lower'] = rth['vwap'] - 2.5 * rth['stdev']
    
    sig_window = rth.between_time('10:00', '13:30')
    active_trade = None
    for idx, row in rth.iterrows():
        if active_trade is not None:
            # Check exit
            dir = active_trade['dir']
            sl = active_trade['sl']
            tp = active_trade['tp']
            hit_sl = (row['low'] <= sl) if dir == 1 else (row['high'] >= sl)
            hit_tp = (row['high'] >= tp) if dir == 1 else (row['low'] <= tp)
            if hit_sl or hit_tp or idx.time() >= pd.to_datetime('15:45').time():
                pnl = 3750 if hit_tp else (-2500 if hit_sl else 0)
                active_trade['exit_time'] = idx
                active_trade['pnl'] = pnl
                nq_trades.append(active_trade)
                break
            continue
            
        if pd.to_datetime('10:00').time() <= idx.time() <= pd.to_datetime('13:30').time():
            sig_l = (row['low'] < row['lower']) and (row['close'] > row['lower'])
            sig_s = (row['high'] > row['upper']) and (row['close'] < row['upper'])
            if sig_l:
                active_trade = {'datetime': idx, 'asset': 'NQ', 'dir': 1, 'entry': row['close'], 'sl': row['close']-25, 'tp': row['close']+37.5}
            elif sig_s:
                active_trade = {'datetime': idx, 'asset': 'NQ', 'dir': -1, 'entry': row['close'], 'sl': row['close']+25, 'tp': row['close']-37.5}

gc_trades = []
for date, group in df_gc.groupby('date'):
    lon = group.between_time('02:00', '08:00')
    if lon.empty: continue
    lon_h, lon_l = lon['high'].max(), lon['low'].min()
    
    active_trade = None
    for idx, row in group.between_time('09:42', '16:00').iterrows():
        if active_trade is not None:
            dir = active_trade['dir']
            sl = active_trade['sl']
            tp = active_trade['tp']
            hit_sl = (row['low'] <= sl) if dir == 1 else (row['high'] >= sl)
            hit_tp = (row['high'] >= tp) if dir == 1 else (row['low'] <= tp)
            if hit_sl or hit_tp or idx.time() >= pd.to_datetime('15:45').time():
                pnl = 3000 if hit_tp else (-2000 if hit_sl else 0)
                active_trade['exit_time'] = idx
                active_trade['pnl'] = pnl
                gc_trades.append(active_trade)
                break
            continue
            
        if pd.to_datetime('09:42').time() <= idx.time() <= pd.to_datetime('10:45').time():
            sig_l = (row['low'] < lon_l) and (row['close'] > lon_l) and ((lon_l - row['low']) >= 1.0)
            sig_s = (row['high'] > lon_h) and (row['close'] < lon_h) and ((row['high'] - lon_h) >= 1.0)
            if sig_l:
                active_trade = {'datetime': idx, 'asset': 'GC', 'dir': 1, 'entry': row['close'], 'sl': row['close']-2.0, 'tp': row['close']+3.0}
            elif sig_s:
                active_trade = {'datetime': idx, 'asset': 'GC', 'dir': -1, 'entry': row['close'], 'sl': row['close']+2.0, 'tp': row['close']-3.0}

df_all = pd.DataFrame(nq_trades + gc_trades)
if not df_all.empty:
    df_all = df_all.sort_values('datetime')
    df_all['date'] = df_all['datetime'].dt.date
    df_first = df_all.drop_duplicates(subset='date', keep='first').copy()
    
    df_first['cum_pnl'] = df_first['pnl'].cumsum()
    
    out_md = []
    out_md.append("| Date | Asset | Direction | Outcome | PnL |")
    out_md.append("|---|---|---|---|---|")
    
    for _, r in df_first.iterrows():
        d = 'LONG' if r['dir']==1 else 'SHORT'
        res = 'WIN' if r['pnl'] > 0 else 'LOSS'
        out_md.append(f"| {r['datetime'].strftime('%Y-%m-%d %H:%M')} | {r['asset']} | {d} | {res} | ${r['pnl']} |")
        
    plt.figure(figsize=(10,5))
    plt.plot(df_first['date'], df_first['cum_pnl'], marker='o', linestyle='-', color='#00E676')
    plt.title('First-to-Fire Protocol: Last 30 Days Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Cumulative PnL ($)')
    plt.grid(True, alpha=0.3)
    plt.axhline(0, color='white', alpha=0.5, linestyle='--')
    
    out_path = 'FirstToFire_30Day_Curve.png'
    plt.savefig(out_path, facecolor='#0d1117')
    
    with open('out.md', 'w') as f:
        f.write('\n'.join(out_md))
