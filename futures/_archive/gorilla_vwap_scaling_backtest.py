import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = os.path.join(os.path.dirname(__file__), "data_and_results", "MNQ_Features_Engineered.csv")

def run_gorilla_scaling_backtest():
    print("Loading 1m data and calculating Extended Session VWAP...")
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    df['IsNewSession'] = (df['TimeOfDay'] >= 1800) & (df['TimeOfDay'].shift(1) < 1800)
    df.loc[0, 'IsNewSession'] = True
    df['SessionID'] = df['IsNewSession'].cumsum()
    
    df['TypicalPrice'] = (df['High'] + df['Low'] + df['Close']) / 3.0
    df['TypPriceVol'] = df['TypicalPrice'] * df['Volume']
    df['CumVol'] = df.groupby('SessionID')['Volume'].cumsum()
    df['CumTypPriceVol'] = df.groupby('SessionID')['TypPriceVol'].cumsum()
    df['VWAP'] = df['CumTypPriceVol'] / df['CumVol']
    
    print("Resampling to 5m...")
    df_5m = df.set_index('Datetime').resample('5min').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna().reset_index()
    
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
    
    # 50K Broker Rules
    STARTING_BALANCE = 50000.0
    PT_VALUE = 2.0
    
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    blown_account = False
    
    trades, wins, losses = 0, 0, 0
    onh, onl = -1, 999999
    locked_onh, locked_onl = -1, -1
    swept_onl, swept_onh = False, False
    extreme_low, extreme_high = 999999, -1
    has_traded = False
    
    equity_curve = [STARTING_BALANCE]
    contract_history = []
    
    for i in range(1, len(df_5m)):
        # Calculate dynamic size based on current available drawdown cushion
        # Broker trails $2,000 from High Water Mark until HWM >= $52,100, then locks permanently at $50,100.
        if high_water_mark >= 52100.0:
            current_dd_limit = 50100.0
        else:
            current_dd_limit = min(50000.0, high_water_mark - 2000.0)
        available_cushion = max(0.0, account_balance - current_dd_limit)
        
        # Risk Parameters
        base_risk_dollars = 100.0 # Absolute minimum risk if cushion is low
        risk_fraction = 0.15 # Risk 15% of available cushion
        
        target_risk_dollars = max(base_risk_dollars, available_cushion * risk_fraction)
        
        # Session Reset
        if times_5m[i] >= 1800 and times_5m[i-1] < 1800:
            high_water_mark = max(high_water_mark, account_balance)
            if high_water_mark >= 52100.0:
                eod_dd_limit = 50100.0
            else:
                eod_dd_limit = min(50000.0, high_water_mark - 2000.0)
            if account_balance <= eod_dd_limit:
                blown_account = True
                break
            
            onh, onl = -1, 999999
            locked_onh, locked_onl = -1, -1
            swept_onl, swept_onh = False, False
            extreme_low, extreme_high = 999999, -1
            has_traded = False
            
        if blown_account: break
            
        if times_5m[i] >= 1800 or times_5m[i] <= 930:
            onh = max(onh, highs_5m[i])
            onl = min(onl, lows_5m[i])
            
        if times_5m[i] == 930:
            locked_onh = onh
            locked_onl = onl
            
        if has_traded or locked_onh == -1 or locked_onl == -1:
            continue
            
        if 930 < times_5m[i] <= 1545:
            if lows_5m[i] < locked_onl:
                swept_onl = True
                extreme_low = min(extreme_low, lows_5m[i])
            if highs_5m[i] > locked_onh:
                swept_onh = True
                extreme_high = max(extreme_high, highs_5m[i])
                
            # LONG
            if swept_onl and closes_5m[i] > locked_onl and closes_5m[i] > opens_5m[i]:
                target_price = vwaps_5m[i]
                if target_price - closes_5m[i] >= 15.0:
                    entry_price = closes_5m[i]
                    stop_loss = extreme_low - 1.0 
                    risk_pts = entry_price - stop_loss
                    if risk_pts > 80.0:
                        continue
                    
                    # Size the trade exactly to target risk
                    contracts = int(max(1, target_risk_dollars / (risk_pts * PT_VALUE)))
                    contracts = min(contracts, 50) # Max 50 MNQ
                    fixed_cost = 2.64 * contracts
                    
                    idx_1m = np.searchsorted(df['Datetime'].values, df_5m['Datetime'].values[i] + pd.Timedelta(minutes=5))
                    trade_pnl = 0
                    for k in range(idx_1m, min(idx_1m + 1500, len(highs_1m))):
                        dynamic_vwap = vwaps_1m[k]
                        if lows_1m[k] <= stop_loss:
                            trade_pnl = -(risk_pts * contracts * PT_VALUE) - fixed_cost
                            losses += 1
                            break
                        elif highs_1m[k] >= dynamic_vwap:
                            reward_pts = dynamic_vwap - entry_price
                            trade_pnl = (reward_pts * contracts * PT_VALUE) - fixed_cost
                            wins += 1
                            break
                    if trade_pnl != 0:
                        account_balance += trade_pnl
                        trades += 1
                        has_traded = True
                        swept_onl = False
                        equity_curve.append(account_balance)
                        contract_history.append(contracts)
                        continue

            # SHORT
            elif swept_onh and closes_5m[i] < locked_onh and closes_5m[i] < opens_5m[i]:
                target_price = vwaps_5m[i]
                if closes_5m[i] - target_price >= 15.0:
                    entry_price = closes_5m[i]
                    stop_loss = extreme_high + 1.0
                    risk_pts = stop_loss - entry_price
                    if risk_pts > 80.0:
                        continue
                    
                    # Size the trade exactly to target risk
                    contracts = int(max(1, target_risk_dollars / (risk_pts * PT_VALUE)))
                    contracts = min(contracts, 50)
                    fixed_cost = 2.64 * contracts
                    
                    idx_1m = np.searchsorted(df['Datetime'].values, df_5m['Datetime'].values[i] + pd.Timedelta(minutes=5))
                    trade_pnl = 0
                    for k in range(idx_1m, min(idx_1m + 1500, len(lows_1m))):
                        dynamic_vwap = vwaps_1m[k]
                        if highs_1m[k] >= stop_loss:
                            trade_pnl = -(risk_pts * contracts * PT_VALUE) - fixed_cost
                            losses += 1
                            break
                        elif lows_1m[k] <= dynamic_vwap:
                            reward_pts = entry_price - dynamic_vwap
                            trade_pnl = (reward_pts * contracts * PT_VALUE) - fixed_cost
                            wins += 1
                            break
                    if trade_pnl != 0:
                        account_balance += trade_pnl
                        trades += 1
                        has_traded = True
                        swept_onh = False
                        equity_curve.append(account_balance)
                        contract_history.append(contracts)
                        # LOSS PAUSE FILTER: Stop trading for the day if we lose
                        if trade_pnl < 0:
                            blown_account = False # Don't break completely, just stop for the day
                            # The has_traded = True will handle skipping the rest of the day
                        continue

    print("\n==========================================")
    print("  DYNAMIC SCALING VWAP SWEEP REVERSAL     ")
    print("==========================================")
    print(f"Total Trades: {trades}")
    if trades > 0:
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {(wins/trades)*100:.2f}%")
        print(f"Max Contracts Used: {max(contract_history)} MNQ")
    print(f"Broker Blown: {blown_account}")
    print(f"Final Profit: ${account_balance - STARTING_BALANCE:,.2f}")
    print("==========================================")
    
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    ax1.plot(equity_curve, color='cyan', linewidth=2)
    ax1.axhline(50000, color='gray', linestyle='--')
    ax1.set_title(f'Dynamic Scale VWAP Sweep: ${account_balance - STARTING_BALANCE:,.2f} Profit')
    ax1.set_ylabel('Account Balance ($)')
    
    ax2.plot(contract_history, color='orange', drawstyle='steps-mid')
    ax2.set_title('Dynamic Position Sizing (Contracts)')
    ax2.set_ylabel('MNQ Contracts')
    ax2.set_xlabel('Trade Number')
    
    out_chart = os.path.join(os.path.dirname(__file__), "data_and_results", "gorilla_dynamic_scale_curve.png")
    plt.savefig(out_chart)
    print(f"Chart saved to {out_chart}")

if __name__ == "__main__":
    run_gorilla_scaling_backtest()
