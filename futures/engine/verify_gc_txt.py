import pandas as pd
import numpy as np

def run_backtest(df_1m, timeframe_min, stop_pts, target_pts):
    # Resample to the specified timeframe
    df_resampled = df_1m.resample(f'{timeframe_min}min', label='left', closed='left').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_resampled['date'] = df_resampled.index.date
    trades = []
    
    for date, group in df_resampled.groupby('date'):
        # London Session: 02:00 - 07:59
        london_data = group.between_time('02:00', '07:59')
        if london_data.empty: continue
        lon_high, lon_low = london_data['high'].max(), london_data['low'].min()
        
        # NY Session VWAP anchors at 09:30
        rth_data = group.between_time('09:30', '15:55').copy()
        if rth_data.empty: continue
        
        rth_data['pv'] = ((rth_data['high'] + rth_data['low'] + rth_data['close']) / 3) * rth_data['volume']
        rth_data['vwap'] = rth_data['pv'].cumsum() / rth_data['volume'].cumsum()
        
        active_trade = None
        for idx, row in rth_data.iterrows():
            t = row.name.time()
            is_entry_window = pd.to_datetime('09:42').time() <= t <= pd.to_datetime('10:44').time()
            
            if active_trade is not None:
                # Pessimistic execution: Check loss before win
                if active_trade['dir'] == 1:
                    if row['low'] <= active_trade['sl']:
                        active_trade.update({'exit_time': row.name, 'exit_price': active_trade['sl'], 'pnl_outcome': 'LOSS'})
                        trades.append(active_trade)
                        active_trade = None
                    elif row['high'] >= active_trade['tp']:
                        active_trade.update({'exit_time': row.name, 'exit_price': active_trade['tp'], 'pnl_outcome': 'WIN'})
                        trades.append(active_trade)
                        active_trade = None
                    elif t >= pd.to_datetime('15:55').time():
                        pnl_str = 'WIN' if row['close'] > active_trade['entry'] else 'LOSS'
                        active_trade.update({'exit_time': row.name, 'exit_price': row['close'], 'pnl_outcome': f'FLAT ({pnl_str})'})
                        trades.append(active_trade)
                        active_trade = None
                else:
                    if row['high'] >= active_trade['sl']:
                        active_trade.update({'exit_time': row.name, 'exit_price': active_trade['sl'], 'pnl_outcome': 'LOSS'})
                        trades.append(active_trade)
                        active_trade = None
                    elif row['low'] <= active_trade['tp']:
                        active_trade.update({'exit_time': row.name, 'exit_price': active_trade['tp'], 'pnl_outcome': 'WIN'})
                        trades.append(active_trade)
                        active_trade = None
                    elif t >= pd.to_datetime('15:55').time():
                        pnl_str = 'WIN' if row['close'] < active_trade['entry'] else 'LOSS'
                        active_trade.update({'exit_time': row.name, 'exit_price': row['close'], 'pnl_outcome': f'FLAT ({pnl_str})'})
                        trades.append(active_trade)
                        active_trade = None
                continue
                
            if is_entry_window:
                sweep_high = (row['high'] > lon_high) and (row['close'] < lon_high) and (2.0 <= (row['high'] - lon_high) <= 25.0) and (row['close'] <= row['vwap'])
                sweep_low  = (row['low'] < lon_low) and (row['close'] > lon_low) and (2.0 <= (lon_low - row['low']) <= 25.0) and (row['close'] >= row['vwap'])
                
                if sweep_low:
                    entry_px = row['close']
                    active_trade = {'entry_time': row.name, 'dir': 1, 'type': 'Long', 'entry': entry_px, 'sl': entry_px - stop_pts, 'tp': entry_px + target_pts}
                elif sweep_high:
                    entry_px = row['close']
                    active_trade = {'entry_time': row.name, 'dir': -1, 'type': 'Short', 'entry': entry_px, 'sl': entry_px + stop_pts, 'tp': entry_px - target_pts}
                    
    return trades

def print_and_analyze(trades, name, target_pts):
    print(f"\n=== {name} ===")
    if not trades:
        print("No trades found.")
        return

    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    streak_type = None
    
    equity = 0.0
    peak_equity = 0.0
    max_drawdown = 0.0
    
    pt_value = 100.0  # $100 per point for standard GC
    commission = 2.30 # $2.30 round trip approx

    print(f"{'Entry Time':<20} | {'Type':<5} | {'Entry Price':<11} | {'Exit Time':<20} | {'Exit Price':<10} | {'Outcome':<12} | {'Net PnL'}")
    print("-" * 110)
    
    for t in trades:
        is_win = 'WIN' in t['pnl_outcome']
        is_loss = 'LOSS' in t['pnl_outcome']
        
        # Calculate strict PnL
        pnl_pts = 0.0
        if is_win:
            if 'FLAT' in t['pnl_outcome']:
                pnl_pts = (t['exit_price'] - t['entry']) if t['dir'] == 1 else (t['entry'] - t['exit_price'])
            else:
                pnl_pts = target_pts
        elif is_loss:
            if 'FLAT' in t['pnl_outcome']:
                pnl_pts = (t['exit_price'] - t['entry']) if t['dir'] == 1 else (t['entry'] - t['exit_price'])
            else:
                pnl_pts = -25.0  # Hardcoded stop loss pts

        net_pnl = (pnl_pts * pt_value) - commission
        
        if net_pnl > 0:
            wins += 1
            gross_profit += net_pnl
            if streak_type == 'WIN':
                current_streak += 1
            else:
                streak_type = 'WIN'
                current_streak = 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            losses += 1
            gross_loss += abs(net_pnl)
            if streak_type == 'LOSS':
                current_streak += 1
            else:
                streak_type = 'LOSS'
                current_streak = 1
            max_loss_streak = max(max_loss_streak, current_streak)
            
        equity += net_pnl
        peak_equity = max(peak_equity, equity)
        drawdown = peak_equity - equity
        max_drawdown = max(max_drawdown, drawdown)

        print(f"{str(t['entry_time']):<20} | {t['type']:<5} | {t['entry']:<11.2f} | {str(t['exit_time']):<20} | {t['exit_price']:<10.2f} | {t['pnl_outcome']:<12} | ${net_pnl:>7.2f}")

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    net_profit = gross_profit - gross_loss
    
    print("-" * 110)
    print("--- Performance Summary ---")
    print(f"Total Trades:       {total}")
    print(f"Wins / Losses:      {wins} / {losses}")
    print(f"Win Rate:           {win_rate:.2f}%")
    print(f"Profit Factor:      {profit_factor:.2f}")
    print(f"Max Win Streak:     {max_win_streak}")
    print(f"Max Loss Streak:    {max_loss_streak}")
    print(f"Max Drawdown:       ${max_drawdown:.2f}")
    print(f"Net Profit:         ${net_profit:.2f}")
    print("===================================================\n")

if __name__ == "__main__":
    df = pd.read_csv('futures/data/MGC_CONTINUOUS.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
    df['datetime'] = df['datetime'] - pd.Timedelta(hours=4)
    df.set_index('datetime', inplace=True)
    
    stop_points = 25.0
    target_points_1to1 = 25.0
    target_points_1to15 = 37.5
    target_points_1to2 = 50.0
    
    trades_5m = run_backtest(df, 5, stop_points, target_points_1to1)
    print_and_analyze(trades_5m, "GC Backtest: 5-Minute Timeframe (1:1 R:R)", target_points_1to1)
    
    trades_5m_15 = run_backtest(df, 5, stop_points, target_points_1to15)
    print_and_analyze(trades_5m_15, "GC Backtest: 5-Minute Timeframe (1:1.5 R:R)", target_points_1to15)
    
    trades_15m = run_backtest(df, 15, stop_points, target_points_1to2)
    print_and_analyze(trades_15m, "GC Backtest: 15-Minute Timeframe (1:2 R:R)", target_points_1to2)
