import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def run_true_anomaly_backtest():
    print("Loading 1m data to execute the 15-Minute ORB (5-Bar Anomaly)...")
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    times_1m = df['TimeOfDay'].values
    highs_1m = df['High'].values
    lows_1m = df['Low'].values
    closes_1m = df['Close'].values
    dates_1m = df['Datetime'].dt.date.values
    
    # 50k Broker Math
    STARTING_BALANCE = 50000.0
    CONTRACTS = 13
    PT_VALUE = 2.0
    FIXED_COST = (1.64 * CONTRACTS) + (1.00 * CONTRACTS) # $34.32 per trade
    STOP_PTS = 40.0
    TARGET_PTS = 40.0
    DAILY_PROFIT_LIMIT = 1000.0
    DAILY_LOSS_LIMIT = -1000.0
    
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    blown_account = False
    
    trades = 0
    wins = 0
    losses = 0
    daily_pnl = 0
    current_day = dates_1m[0]
    
    orb_high = -1
    orb_low = 999999
    orb_active = False
    
    trade_log = []
    equity_curve = [STARTING_BALANCE]
    
    i = 0
    while i < len(highs_1m) - 1:
        if dates_1m[i] != current_day:
            high_water_mark = max(high_water_mark, account_balance)
            current_day = dates_1m[i]
            daily_pnl = 0
            orb_high = -1
            orb_low = 999999
            orb_active = False
            
        if account_balance <= high_water_mark - 2000:
            blown_account = True
            break
            
        if daily_pnl >= DAILY_PROFIT_LIMIT or daily_pnl <= DAILY_LOSS_LIMIT:
            i += 1
            continue
            
        # 1. Build the 09:30 - 09:44 ORB Range
        if 930 <= times_1m[i] < 945:
            orb_high = max(orb_high, highs_1m[i])
            orb_low = min(orb_low, lows_1m[i])
            i += 1
            continue
            
        # 2. At 09:45, the ORB is set. Activate OCO bracket orders.
        if times_1m[i] == 945 and orb_high != -1:
            orb_active = True
            # We don't advance i here, we want to evaluate this bar for the breakout
            
        if orb_active:
            # Check for Long Breakout (1 tick above ORB high)
            long_trigger = orb_high + 0.25
            short_trigger = orb_low - 0.25
            
            triggered_long = highs_1m[i] >= long_trigger
            triggered_short = lows_1m[i] <= short_trigger
            
            if triggered_long and triggered_short:
                # Intra-bar ambiguity on 1m chart. Did it go up or down first?
                # Assume pessimistic (it stopped us out first).
                # Actually, in a true momentum ORB, we'll assume the side closer to the open of the bar triggered first.
                if closes_1m[i-1] > ((orb_high + orb_low) / 2):
                    triggered_short = False
                else:
                    triggered_long = False
                    
            if triggered_long:
                entry_price = long_trigger
                stop_loss = entry_price - STOP_PTS
                take_profit = entry_price + TARGET_PTS
                
                trade_pnl = 0
                for k in range(0, 1000): # Scan forward until target or stop is hit
                    if i+k >= len(highs_1m): break
                    if lows_1m[i+k] <= stop_loss:
                        trade_pnl = -(STOP_PTS * CONTRACTS * PT_VALUE) - FIXED_COST
                        losses += 1
                        break
                    elif highs_1m[i+k] >= take_profit:
                        trade_pnl = (TARGET_PTS * CONTRACTS * PT_VALUE) - FIXED_COST
                        wins += 1
                        break
                        
                if trade_pnl != 0:
                    daily_pnl += trade_pnl
                    account_balance += trade_pnl
                    trades += 1
                    equity_curve.append(account_balance)
                    orb_active = False # Trade is done for the day
                    i += k
                    continue
                    
            elif triggered_short:
                entry_price = short_trigger
                stop_loss = entry_price + STOP_PTS
                take_profit = entry_price - TARGET_PTS
                
                trade_pnl = 0
                for k in range(0, 1000):
                    if i+k >= len(lows_1m): break
                    if highs_1m[i+k] >= stop_loss:
                        trade_pnl = -(STOP_PTS * CONTRACTS * PT_VALUE) - FIXED_COST
                        losses += 1
                        break
                    elif lows_1m[i+k] <= take_profit:
                        trade_pnl = (TARGET_PTS * CONTRACTS * PT_VALUE) - FIXED_COST
                        wins += 1
                        break
                        
                if trade_pnl != 0:
                    daily_pnl += trade_pnl
                    account_balance += trade_pnl
                    trades += 1
                    equity_curve.append(account_balance)
                    orb_active = False # Trade is done for the day
                    i += k
                    continue
                    
        i += 1

    print("\n=======================================================")
    print("   THE 5-BAR ANOMALY (9:45 AM ORB SPRINT ARCHITECTURE) ")
    print("=======================================================")
    print(f"Total Trades Taken: {trades}")
    if trades > 0:
        win_rate = (wins/trades)*100
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        
    print(f"Broker Blown: {blown_account}")
    print(f"Final Account Balance: ${account_balance:,.2f}")
    print(f"Net Profit: ${account_balance - STARTING_BALANCE:,.2f}")
    print("=======================================================")
    
    plt.style.use('dark_background')
    plt.figure(figsize=(10, 5))
    plt.plot(equity_curve, color='magenta', linewidth=2)
    plt.axhline(50000, color='gray', linestyle='--')
    plt.title(f'15m 5-Bar Anomaly (Evaluation Sprint): ${account_balance - STARTING_BALANCE:,.2f} Profit')
    plt.savefig(r'data_and_results\anomaly_curve.png')

if __name__ == "__main__":
    run_true_anomaly_backtest()
