import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def run_po3_backtest_18():
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
    FIXED_COST = (1.64 * CONTRACTS) + (1.00 * CONTRACTS) 
    
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    blown_account = False
    
    trades = 0
    equity_curve = [STARTING_BALANCE]
    
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
            
        # EXACT LOGIC: Break if $2k trailing drawdown is breached
        if account_balance <= high_water_mark - 2000:
            blown_account = True
            break
            
        if daily_pnl <= -1000 or daily_pnl >= 1000:
            i += 1
            continue
            
        if times[i] == 830 and session_open == 0:
            session_open = opens[i]
            is_below = False
            is_above = False
            i += 1
            continue
            
        if session_open == 0:
            i += 1
            continue
            
        if closes[i] < session_open:
            if not is_below:
                is_below = True
                extreme = lows[i]
                is_above = False
            extreme = min(extreme, lows[i])
            is_fvg = lows[i] > highs[i-2] and closes[i-1] > opens[i-1]
            if is_fvg and (session_open - extreme) >= 2.0: 
                entry_price = closes[i]
                stop_loss = extreme - 0.5 
                risk_pts = entry_price - stop_loss
                target_pts = risk_pts * 2.0 
                take_profit = entry_price + target_pts
                
                trade_pnl = 0
                for k in range(1, 40):
                    if i+k >= len(highs): break
                    if lows[i+k] <= stop_loss:
                        trade_pnl = -(risk_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                        break
                    elif highs[i+k] >= take_profit:
                        trade_pnl = (target_pts * CONTRACTS * PT_VALUE) - FIXED_COST
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
                for k in range(1, 40):
                    if i+k >= len(lows): break
                    if highs[i+k] >= stop_loss:
                        trade_pnl = -(risk_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                        break
                    elif lows[i+k] <= take_profit:
                        trade_pnl = (target_pts * CONTRACTS * PT_VALUE) - FIXED_COST
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

    # Plot Equity Curve
    plt.style.use('dark_background')
    plt.figure(figsize=(10, 5))
    plt.plot(equity_curve, color='lime', linewidth=2, marker='o', markersize=5)
    
    # Mark the high water mark
    plt.axhline(max(equity_curve), color='gold', linestyle='--', label=f'High Water Mark (${max(equity_curve):,.2f})')
    
    # Mark the failure point (HWM - 2000)
    plt.axhline(max(equity_curve) - 2000, color='red', linestyle='-', linewidth=2, label='Broker Kill Switch (-$2,000)')
    
    plt.title(f'The 18-Trade Sprint: ${account_balance - STARTING_BALANCE:,.2f} Profit (Blown)')
    plt.xlabel('Trades Taken')
    plt.ylabel('Account Balance ($)')
    plt.legend()
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    
    chart_path = r'data_and_results\po3_18_trades.png'
    plt.savefig(chart_path)

if __name__ == "__main__":
    run_po3_backtest_18()
