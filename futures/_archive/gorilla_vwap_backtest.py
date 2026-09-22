import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def run_gorilla_backtest():
    print("Loading 1m data and calculating Extended Session VWAP...")
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    # Identify Extended Session resets (TimeOfDay format is HMM or HHMM, so 18:00 is 1800)
    df['IsNewSession'] = (df['TimeOfDay'] >= 1800) & (df['TimeOfDay'].shift(1) < 1800)
    df.loc[0, 'IsNewSession'] = True
    df['SessionID'] = df['IsNewSession'].cumsum()
    
    # Calculate VWAP
    df['TypicalPrice'] = (df['High'] + df['Low'] + df['Close']) / 3.0
    df['TypPriceVol'] = df['TypicalPrice'] * df['Volume']
    df['CumVol'] = df.groupby('SessionID')['Volume'].cumsum()
    df['CumTypPriceVol'] = df.groupby('SessionID')['TypPriceVol'].cumsum()
    df['VWAP'] = df['CumTypPriceVol'] / df['CumVol']
    
    print("Resampling to 5m for Gorilla Sweep Entry logic...")
    df_5m = df.set_index('Datetime').resample('5min').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna().reset_index()
    
    # Forward fill VWAP to the 5m bar for reference
    df_5m = pd.merge_asof(df_5m, df[['Datetime', 'VWAP']], on='Datetime', direction='backward')
    
    times_5m = (df_5m['Datetime'].dt.hour * 100) + df_5m['Datetime'].dt.minute
    highs_5m = df_5m['High'].values
    lows_5m = df_5m['Low'].values
    opens_5m = df_5m['Open'].values
    closes_5m = df_5m['Close'].values
    vwaps_5m = df_5m['VWAP'].values
    
    times_1m = df['TimeOfDay'].values
    highs_1m = df['High'].values
    lows_1m = df['Low'].values
    vwaps_1m = df['VWAP'].values
    
    STARTING_BALANCE = 50000.0
    CONTRACTS = 3
    PT_VALUE = 2.0
    FIXED_COST = 2.64 * CONTRACTS
    
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    blown_account = False
    
    trades, wins, losses = 0, 0, 0
    onh, onl = -1, 999999
    locked_onh, locked_onl = -1, -1
    swept_onl, swept_onh = False, False
    extreme_low, extreme_high = 999999, -1
    daily_pnl = 0
    has_traded = False
    
    equity_curve = [STARTING_BALANCE]
    
    for i in range(1, len(df_5m)):
        # Session Reset (18:00 EST)
        if times_5m[i] >= 1800 and times_5m[i-1] < 1800:
            high_water_mark = max(high_water_mark, account_balance)
            if account_balance <= high_water_mark - 2000:
                blown_account = True
                break
            
            onh, onl = -1, 999999
            locked_onh, locked_onl = -1, -1
            swept_onl, swept_onh = False, False
            extreme_low, extreme_high = 999999, -1
            daily_pnl = 0
            has_traded = False
            
        if blown_account: break
            
        # 18:00 to 09:30 range building
        if times_5m[i] >= 1800 or times_5m[i] <= 930:
            onh = max(onh, highs_5m[i])
            onl = min(onl, lows_5m[i])
            
        if times_5m[i] == 930:
            locked_onh = onh
            locked_onl = onl
            
        if has_traded or locked_onh == -1 or locked_onl == -1:
            continue
            
        # NY Session 09:35 - 15:45
        if 930 < times_5m[i] <= 1545:
            # Detect Sweeps
            if lows_5m[i] < locked_onl:
                swept_onl = True
                extreme_low = min(extreme_low, lows_5m[i])
            if highs_5m[i] > locked_onh:
                swept_onh = True
                extreme_high = max(extreme_high, highs_5m[i])
                
            # Sweep & Reclaim (Long)
            if swept_onl and closes_5m[i] > locked_onl and closes_5m[i] > opens_5m[i]:
                target_price = vwaps_5m[i]
                if target_price - closes_5m[i] >= 15.0:
                    entry_price = closes_5m[i]
                    stop_loss = extreme_low - 1.0 # 4 ticks
                    
                    idx_1m = np.searchsorted(df['Datetime'].values, df_5m['Datetime'].values[i] + pd.Timedelta(minutes=5))
                    trade_pnl = 0
                    for k in range(idx_1m, min(idx_1m + 1500, len(highs_1m))):
                        dynamic_vwap = vwaps_1m[k]
                        if lows_1m[k] <= stop_loss:
                            risk_pts = entry_price - stop_loss
                            trade_pnl = -(risk_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                            losses += 1
                            break
                        elif highs_1m[k] >= dynamic_vwap:
                            reward_pts = dynamic_vwap - entry_price
                            trade_pnl = (reward_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                            wins += 1
                            break
                    if trade_pnl != 0:
                        account_balance += trade_pnl
                        trades += 1
                        has_traded = True
                        swept_onl = False
                        equity_curve.append(account_balance)
                        continue

            # Sweep & Reclaim (Short)
            elif swept_onh and closes_5m[i] < locked_onh and closes_5m[i] < opens_5m[i]:
                target_price = vwaps_5m[i]
                if closes_5m[i] - target_price >= 15.0:
                    entry_price = closes_5m[i]
                    stop_loss = extreme_high + 1.0
                    
                    idx_1m = np.searchsorted(df['Datetime'].values, df_5m['Datetime'].values[i] + pd.Timedelta(minutes=5))
                    trade_pnl = 0
                    for k in range(idx_1m, min(idx_1m + 1500, len(lows_1m))):
                        dynamic_vwap = vwaps_1m[k]
                        if highs_1m[k] >= stop_loss:
                            risk_pts = stop_loss - entry_price
                            trade_pnl = -(risk_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                            losses += 1
                            break
                        elif lows_1m[k] <= dynamic_vwap:
                            reward_pts = entry_price - dynamic_vwap
                            trade_pnl = (reward_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                            wins += 1
                            break
                    if trade_pnl != 0:
                        account_balance += trade_pnl
                        trades += 1
                        has_traded = True
                        swept_onh = False
                        equity_curve.append(account_balance)
                        continue

    print("\n==========================================")
    print("  GORILLA VWAP SWEEP REVERSAL (3 MNQ)     ")
    print("==========================================")
    print(f"Total Trades: {trades}")
    if trades > 0:
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {(wins/trades)*100:.2f}%")
    print(f"Broker Blown: {blown_account}")
    print(f"Final Profit: ${account_balance - STARTING_BALANCE:,.2f}")
    print("==========================================")

    plt.style.use('dark_background')
    plt.figure(figsize=(10, 5))
    plt.plot(equity_curve, color='magenta', linewidth=2)
    plt.axhline(50000, color='gray', linestyle='--')
    plt.title(f'Gorilla VWAP Sweep Engine (3 MNQ): ${account_balance - STARTING_BALANCE:,.2f} Profit')
    plt.tight_layout()
    plt.savefig(r'data_and_results\gorilla_vwap_curve.png')

if __name__ == "__main__":
    run_gorilla_backtest()
