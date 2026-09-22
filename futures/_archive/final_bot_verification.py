import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def run_final_verification():
    print("Loading engineered data...")
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    times = df['TimeOfDay'].values
    dates = df['Datetime'].dt.date.values
    
    STARTING_BALANCE = 50000.0
    CONTRACTS = 3
    PT_VALUE = 2.0
    FIXED_COST = (1.64 * CONTRACTS) + (1.00 * CONTRACTS) 
    
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    blown_account = False
    
    trades = 0
    wins = 0
    losses = 0
    breakevens = 0
    
    equity_curve = [STARTING_BALANCE]
    drawdowns = []
    
    session_open = 0
    acc_high = 0
    acc_low = 999999
    valid_acc = False
    
    is_below = False
    is_above = False
    extreme = 0
    daily_pnl = 0
    current_day = dates[0]
    
    print("Running simulation (HTF Filter Disabled)...")
    i = 3
    while i < len(highs) - 1:
        if dates[i] != current_day:
            high_water_mark = max(high_water_mark, account_balance)
            current_day = dates[i]
            daily_pnl = 0
            session_open = 0
            acc_high = 0
            acc_low = 999999
            valid_acc = False
            is_below = False
            is_above = False
            
        current_drawdown = high_water_mark - account_balance
        drawdowns.append(current_drawdown)
            
        if current_drawdown >= 2000:
            blown_account = True
            break
            
        if daily_pnl <= -950 or daily_pnl >= 1000:
            i += 1
            continue
            
        if times[i] < 830:
            acc_high = max(acc_high, highs[i])
            acc_low = min(acc_low, lows[i])
            
        if times[i] == 830 and session_open == 0:
            session_open = opens[i]
            if (acc_high - acc_low) <= 400:
                valid_acc = True
            is_below = False
            is_above = False
            i += 1
            continue
            
        if session_open == 0 or not valid_acc:
            i += 1
            continue
            
        if closes[i] < session_open:
            if not is_below:
                is_below = True
                extreme = lows[i]
                is_above = False
            extreme = min(extreme, lows[i])
            
            is_fvg = lows[i] > highs[i-2] and closes[i-1] > opens[i-1]
            
            # HTF DISABLED to match C# defaults
            if is_fvg and (session_open - extreme) >= 2.0: 
                entry_price = closes[i]
                stop_loss = extreme - 0.5 
                risk_pts = entry_price - stop_loss
                target_pts = risk_pts * 2.0 
                take_profit = entry_price + target_pts
                
                trade_pnl = 0
                stop_moved = False
                
                for k in range(1, 100):
                    if i+k >= len(highs): break
                    
                    # 1. Check if we hit Breakeven threshold (1R)
                    # if not stop_moved and highs[i+k] >= entry_price + risk_pts:
                    #     stop_loss = entry_price + 0.25 # Breakeven + 1 tick
                    #     stop_moved = True
                        
                    # 2. Evaluate exit
                    if lows[i+k] <= stop_loss:
                        if stop_moved:
                            trade_pnl = (0.25 * CONTRACTS * PT_VALUE) - FIXED_COST
                            breakevens += 1
                        else:
                            trade_pnl = -(risk_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                            losses += 1
                        break
                    elif highs[i+k] >= take_profit:
                        trade_pnl = (target_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                        wins += 1
                        break
                        
                if trade_pnl != 0:
                    daily_pnl += trade_pnl
                    account_balance += trade_pnl
                    trades += 1
                    equity_curve.append(account_balance)
                    i += k
                    is_below = False
                    continue
                    
        elif closes[i] > session_open:
            if not is_above:
                is_above = True
                extreme = highs[i]
                is_below = False
            extreme = max(extreme, highs[i])
            
            is_fvg = highs[i] < lows[i-2] and closes[i-1] < opens[i-1]
            
            if is_fvg and (extreme - session_open) >= 2.0:
                entry_price = closes[i]
                stop_loss = extreme + 0.5
                risk_pts = stop_loss - entry_price
                target_pts = risk_pts * 2.0
                take_profit = entry_price - target_pts
                
                trade_pnl = 0
                stop_moved = False
                
                for k in range(1, 100):
                    if i+k >= len(lows): break
                    
                    # if not stop_moved and lows[i+k] <= entry_price - risk_pts:
                    #     stop_loss = entry_price - 0.25
                    #     stop_moved = True
                        
                    if highs[i+k] >= stop_loss:
                        if stop_moved:
                            trade_pnl = (0.25 * CONTRACTS * PT_VALUE) - FIXED_COST
                            breakevens += 1
                        else:
                            trade_pnl = -(risk_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                            losses += 1
                        break
                    elif lows[i+k] <= take_profit:
                        trade_pnl = (target_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                        wins += 1
                        break
                        
                if trade_pnl != 0:
                    daily_pnl += trade_pnl
                    account_balance += trade_pnl
                    trades += 1
                    equity_curve.append(account_balance)
                    i += k
                    is_above = False
                    continue
        i += 1

    print("\n==========================================")
    print("   FINAL MANUAL BOT VERIFICATION (3 MNQ)")
    print("==========================================")
    print(f"Total Trades: {trades}")
    if trades > 0:
        win_rate = (wins/trades)*100
        print(f"Wins: {wins} | Losses: {losses} | Breakevens: {breakevens}")
        print(f"Win Rate (Excl. BE): {win_rate:.2f}%")
    
    print(f"Broker Blown: {blown_account}")
    print(f"Max Drawdown: ${max(drawdowns):.2f}")
    print(f"Final Profit: ${account_balance - STARTING_BALANCE:.2f}")
    
    plt.style.use('dark_background')
    plt.figure(figsize=(10, 5))
    plt.plot(equity_curve, color='lime', linewidth=2, marker='o', markersize=4)
    plt.axhline(50000, color='gray', linestyle='--')
    plt.title(f'Final Master Bot (3 MNQ): ${account_balance - STARTING_BALANCE:,.2f} Profit | Max DD: ${max(drawdowns):,.2f}')
    plt.savefig(r'data_and_results\final_bot_curve.png')

if __name__ == "__main__":
    run_final_verification()
