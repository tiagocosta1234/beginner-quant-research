import pandas as pd
import numpy as np
from ib_features import compute_ib_features

def test_ib_delta_filter():
    print("Loading MNQ Order Flow Data...")
    df_raw = pd.read_csv("../data/MNQ_OrderFlow.csv")
    df_ib = compute_ib_features(df_raw)
    
    tp_points = 50
    sl_points = 80
    
    wins = 0
    losses = 0
    trade_records = []
    
    print(f"Testing IB Breakout filtered by Overnight Order Flow Delta...")
    
    for i in range(len(df_ib)):
        on_delta = df_ib['IB_Delta'].iloc[i] # Actually, this is IB Delta, not Overnight.
        
        ib_high = df_ib['IB_High'].iloc[i]
        ib_low = df_ib['IB_Low'].iloc[i]
        highs = df_ib['After_IB_Highs'].iloc[i]
        lows = df_ib['After_IB_Lows'].iloc[i]
        
        buy_tp = ib_high + tp_points
        buy_sl = ib_high - sl_points
        sell_tp = ib_low - tp_points
        sell_sl = ib_low + sl_points
        
        buy_outcome = 0
        sell_outcome = 0
        
        buy_active = False
        sell_active = False
        
        for j in range(len(highs)):
            if not buy_active and highs[j] >= ib_high:
                buy_active = True
            if not sell_active and lows[j] <= ib_low:
                sell_active = True
                
            if buy_active and buy_outcome == 0:
                if lows[j] <= buy_sl: buy_outcome = -1
                elif highs[j] >= buy_tp: buy_outcome = 1
                
            if sell_active and sell_outcome == 0:
                if highs[j] >= sell_sl: sell_outcome = -1
                elif lows[j] <= sell_tp: sell_outcome = 1
                
            if buy_outcome != 0 and sell_outcome != 0:
                break
                
        # --- THE FILTER ---
        pnl = 0.0
        trade_taken = False
        
        # If IB Delta is POSITIVE, we ONLY take longs.
        if on_delta > 0:
            if buy_outcome == 1: 
                wins += 1
                pnl = (tp_points * 2.0 * 5) - (2.20 * 5)
                trade_taken = True
            elif buy_outcome == -1: 
                losses += 1
                pnl = -(sl_points * 2.0 * 5) - (2.20 * 5)
                trade_taken = True
                
        # If IB Delta is NEGATIVE, we ONLY take shorts.
        elif on_delta < 0:
            if sell_outcome == 1: 
                wins += 1
                pnl = (tp_points * 2.0 * 5) - (2.20 * 5)
                trade_taken = True
            elif sell_outcome == -1: 
                losses += 1
                pnl = -(sl_points * 2.0 * 5) - (2.20 * 5)
                trade_taken = True

        if trade_taken:
            trade_records.append({
                'Session_Date': df_ib['Session_Date'].iloc[i],
                'PnL': pnl
            })

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0
    
    trades_df = pd.DataFrame(trade_records)
    trades_df.to_csv("../data/pure_orderflow_trades.csv", index=False)
    
    print(f"--- FILTERED IB BREAKOUT ---")
    print(f"Trades: {total} | Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {wr:.1f}%")

if __name__ == "__main__":
    test_ib_delta_filter()
