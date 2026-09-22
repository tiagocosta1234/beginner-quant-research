import pandas as pd
import numpy as np

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def run_po3_backtest():
    print("Loading engineered data for PO3 Backtest...")
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    times = df['TimeOfDay'].values
    dates = df['Datetime'].dt.date.values
    
    STARTING_BALANCE = 50000.0
    CONTRACTS = 13
    PT_VALUE = 2.0
    FIXED_COST = (1.64 * CONTRACTS) + (1.00 * CONTRACTS) # Commission + Slippage = $34.32 per trade
    
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    blown_account = False
    
    trades = 0
    wins = 0
    losses = 0
    
    session_open = 0
    is_below = False
    is_above = False
    extreme = 0
    
    daily_pnl = 0
    current_day = dates[0]
    
    i = 3
    while i < len(highs) - 1:
        if dates[i] != current_day:
            high_water_mark = max(high_water_mark, account_balance)
            current_day = dates[i]
            daily_pnl = 0
            session_open = 0
            is_below = False
            is_above = False
            
        if account_balance <= high_water_mark - 2000:
            blown_account = True
            break
            
        if daily_pnl <= -1000 or daily_pnl >= 1000:
            i += 1
            continue
            
        # 1. Establish 8:30 AM Anchor
        if times[i] == 830 and session_open == 0:
            session_open = opens[i]
            is_below = False
            is_above = False
            i += 1
            continue
            
        if session_open == 0:
            i += 1
            continue
            
        # 2. Track Bullish Manipulation (Below Open)
        if closes[i] < session_open:
            if not is_below:
                is_below = True
                extreme = lows[i]
                is_above = False
            
            extreme = min(extreme, lows[i])
            
            # Check for Bullish FVG
            is_fvg = lows[i] > highs[i-2] and closes[i-1] > opens[i-1]
            if is_fvg and (session_open - extreme) >= 2.0: # Must have swept at least 2 points
                # Entry!
                entry_price = closes[i]
                stop_loss = extreme - 0.5 # Stop below the sweep extreme
                risk_pts = entry_price - stop_loss
                target_pts = risk_pts * 2.0 # 1:2 Risk Reward
                take_profit = entry_price + target_pts
                
                trade_pnl = 0
                for k in range(1, 40):
                    if i+k >= len(highs): break
                    
                    # Pessimistic execution: Check stop first
                    if lows[i+k] <= stop_loss:
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
                    i += k
                    is_below = False
                    continue
                    
        # 3. Track Bearish Manipulation (Above Open)
        elif closes[i] > session_open:
            if not is_above:
                is_above = True
                extreme = highs[i]
                is_below = False
                
            extreme = max(extreme, highs[i])
            
            # Check for Bearish FVG
            is_fvg = highs[i] < lows[i-2] and closes[i-1] < opens[i-1]
            if is_fvg and (extreme - session_open) >= 2.0:
                entry_price = closes[i]
                stop_loss = extreme + 0.5
                risk_pts = stop_loss - entry_price
                target_pts = risk_pts * 2.0
                take_profit = entry_price - target_pts
                
                trade_pnl = 0
                for k in range(1, 40):
                    if i+k >= len(lows): break
                    
                    if highs[i+k] >= stop_loss:
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
                    i += k
                    is_above = False
                    continue
        
        i += 1
        
    net_profit = account_balance - STARTING_BALANCE
    print("\n==========================================")
    print("   POWER OF 3 (AMD) BACKTEST RESULTS")
    print("==========================================")
    print(f"Total Trades: {trades}")
    if trades > 0:
        print(f"Win Rate:     {round((wins/trades)*100, 2)}% ({wins}W / {losses}L)")
    print(f"Account Blown:{blown_account} (Hit $2k Drawdown)")
    print(f"Net Profit:   ${net_profit:.2f}")

if __name__ == "__main__":
    run_po3_backtest()
