import pandas as pd
import numpy as np
import json
import time
import random

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def simulate_htf_amd(highs, lows, closes, times, dates, htf_res, htf_sup, swing_strength, min_sweep_ticks, max_sweep_ticks, max_duration, stop_loss_pts, take_profit_pts):
    STARTING_BALANCE = 50000.0
    EOD_TRAILING_DRAWDOWN = 2000.0
    DAILY_LOSS_LIMIT = 1000.0
    DAILY_PROFIT_LIMIT = 1000.0
    CONTRACTS = 13
    PT_VALUE = 2.0
    FIXED_COST = (1.64 * CONTRACTS) + (1.00 * CONTRACTS) 
    
    tick_size = 0.25
    account_balance = STARTING_BALANCE
    high_water_mark = STARTING_BALANCE
    trades_taken = 0
    blown_account = False
    
    if len(dates) == 0: return 0, 0, True
    
    current_day = dates[0]
    daily_pnl = 0.0
    
    i = swing_strength
    while i < len(highs) - 20:
        if dates[i] != current_day:
            high_water_mark = max(high_water_mark, account_balance)
            if account_balance <= high_water_mark - EOD_TRAILING_DRAWDOWN:
                blown_account = True
                break
            current_day = dates[i]
            daily_pnl = 0.0 
            
        t = times[i]
        in_killzone = (930 <= t <= 1100) or (1400 <= t <= 1530)
        hit_daily_limits = (daily_pnl <= -DAILY_LOSS_LIMIT) or (daily_pnl >= DAILY_PROFIT_LIMIT)
        
        if not in_killzone or hit_daily_limits or blown_account:
            i += 1
            continue

        recent_lows = lows[i-swing_strength:i]
        recent_highs = highs[i-swing_strength:i]
        
        # Bullish AMD Setup with HTF Context
        swing_low = np.min(recent_lows)
        if lows[i] < swing_low:
            sweep_depth_ticks = (swing_low - lows[i]) / tick_size
            
            # HTF ALIGNMENT: The manipulation leg MUST reach into the 15m HTF Support zone
            htf_proximity = abs(lows[i] - htf_sup[i])
            valid_htf_tap = htf_proximity <= (10 * tick_size) # Must be within 10 ticks of 15m Support
            
            if min_sweep_ticks <= sweep_depth_ticks <= max_sweep_ticks and valid_htf_tap:
                reclaim_bar = -1
                for j in range(1, max_duration + 1):
                    if i + j >= len(closes): break
                    if closes[i+j] >= swing_low:
                        reclaim_bar = i + j
                        break
                
                # FVG Displacement
                if reclaim_bar != -1:
                    fvg_confirmed = False
                    fvg_entry_bar = -1
                    for f in range(1, 4):
                        if reclaim_bar + f + 2 >= len(highs): break
                        c1_high = highs[reclaim_bar + f]
                        c3_low = lows[reclaim_bar + f + 2]
                        if c3_low > c1_high:
                            fvg_confirmed = True
                            fvg_entry_bar = reclaim_bar + f + 2
                            break
                            
                    if fvg_confirmed:
                        entry_price = closes[fvg_entry_bar]
                        trade_pnl = 0
                        for k in range(1, 40):
                            if fvg_entry_bar+k >= len(highs): break
                            if lows[fvg_entry_bar+k] <= entry_price - stop_loss_pts:
                                trade_pnl = -(stop_loss_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                                break
                            elif highs[fvg_entry_bar+k] >= entry_price + take_profit_pts:
                                trade_pnl = (take_profit_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                                break
                                
                        if trade_pnl != 0:
                            daily_pnl += trade_pnl
                            account_balance += trade_pnl
                            trades_taken += 1
                            i = fvg_entry_bar + k
                            continue
                            
        # Bearish AMD Setup with HTF Context
        swing_high = np.max(recent_highs)
        if highs[i] > swing_high:
            sweep_depth_ticks = (highs[i] - swing_high) / tick_size
            
            # HTF ALIGNMENT: The manipulation leg MUST reach into the 15m HTF Resistance zone
            htf_proximity = abs(highs[i] - htf_res[i])
            valid_htf_tap = htf_proximity <= (10 * tick_size)
            
            if min_sweep_ticks <= sweep_depth_ticks <= max_sweep_ticks and valid_htf_tap:
                reclaim_bar = -1
                for j in range(1, max_duration + 1):
                    if i + j >= len(closes): break
                    if closes[i+j] <= swing_high:
                        reclaim_bar = i + j
                        break
                        
                if reclaim_bar != -1:
                    fvg_confirmed = False
                    fvg_entry_bar = -1
                    for f in range(1, 4):
                        if reclaim_bar + f + 2 >= len(lows): break
                        c1_low = lows[reclaim_bar + f]
                        c3_high = highs[reclaim_bar + f + 2]
                        if c3_high < c1_low:
                            fvg_confirmed = True
                            fvg_entry_bar = reclaim_bar + f + 2
                            break
                            
                    if fvg_confirmed:
                        entry_price = closes[fvg_entry_bar]
                        trade_pnl = 0
                        for k in range(1, 40):
                            if fvg_entry_bar+k >= len(lows): break
                            if highs[fvg_entry_bar+k] >= entry_price + stop_loss_pts:
                                trade_pnl = -(stop_loss_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                                break
                            elif lows[fvg_entry_bar+k] <= entry_price - take_profit_pts:
                                trade_pnl = (take_profit_pts * CONTRACTS * PT_VALUE) - FIXED_COST
                                break
                        if trade_pnl != 0:
                            daily_pnl += trade_pnl
                            account_balance += trade_pnl
                            trades_taken += 1
                            i = fvg_entry_bar + k
                            continue
        i += 1
        
    net_profit = account_balance - STARTING_BALANCE
    return net_profit, trades_taken, blown_account

def run_htf_wfo():
    print("Building Multi-Timeframe Brain (1m + 15m HTF Context)...")
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    print("Resampling 1-minute data into 15-minute HTF Candles...")
    df.set_index('Datetime', inplace=True)
    df_15m = df.resample('15min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'})
    df_15m.dropna(inplace=True)
    
    # Calculate 15m HTF Support and Resistance (3-bar swing)
    df_15m['HTF_Resistance'] = df_15m['High'].rolling(5, center=True).max()
    df_15m['HTF_Support'] = df_15m['Low'].rolling(5, center=True).min()
    df_15m.ffill(inplace=True)
    df_15m.bfill(inplace=True)
    
    # Map HTF levels back to the 1-minute timeframe
    df = df.join(df_15m[['HTF_Resistance', 'HTF_Support']], how='left')
    df['HTF_Resistance'].ffill(inplace=True)
    df['HTF_Support'].ffill(inplace=True)
    df.reset_index(inplace=True)
    df['Date'] = df['Datetime'].dt.date
    
    split_idx = int(len(df) * 0.75)
    train_df = df.iloc[:split_idx].reset_index(drop=True)
    test_df = df.iloc[split_idx:].reset_index(drop=True)
    
    POPULATION_SIZE = 50
    GENERATIONS = 12
    
    population = [[random.randint(5, 30), random.randint(2, 10), random.randint(15, 60), 
                   random.randint(1, 10), random.randint(15, 35), random.randint(20, 80)] 
                  for _ in range(POPULATION_SIZE)]

    best_overall_dna = None
    best_overall_fitness = -999999

    print("--- IN-SAMPLE TRAINING PHASE (Hunting HTF Traps) ---")
    for gen in range(GENERATIONS):
        fitness_scores = []
        for dna in population:
            profit, trades, blown = simulate_htf_amd(train_df['High'].values, train_df['Low'].values, 
                                                      train_df['Close'].values, train_df['TimeOfDay'].values, 
                                                      train_df['Date'].values, train_df['HTF_Resistance'].values, 
                                                      train_df['HTF_Support'].values, *dna)
            # Fitness logic
            fitness = -50000 if blown else (-10000 if trades < 2 else profit)
            fitness_scores.append((fitness, dna, trades, profit))
            
        fitness_scores.sort(key=lambda x: x[0], reverse=True)
        best_gen_fitness, best_gen_dna, gen_trades, raw_profit = fitness_scores[0]
        
        if best_gen_fitness > best_overall_fitness:
            best_overall_fitness = best_gen_fitness
            best_overall_dna = best_gen_dna
            
        next_gen = [x[1] for x in fitness_scores[:POPULATION_SIZE // 2]]
        while len(next_gen) < POPULATION_SIZE:
            parent1 = random.choice(next_gen[:5])
            parent2 = random.choice(next_gen[:5])
            child = []
            for i in range(len(parent1)):
                if random.random() < 0.25:
                    ranges = [(5,30), (2,10), (15,60), (1,10), (15,35), (20,80)]
                    child.append(random.randint(ranges[i][0], ranges[i][1]))
                else:
                    child.append(random.choice([parent1[i], parent2[i]]))
            next_gen.append(child)
        population = next_gen

    print(f"\nBest In-Sample Training Profit: ${best_overall_fitness:.2f}")
    print(f"Winning DNA: {best_overall_dna}")
    
    print("\n--- OUT-OF-SAMPLE TESTING PHASE (BLIND DATA) ---")
    oos_profit, oos_trades, oos_blown = simulate_htf_amd(test_df['High'].values, test_df['Low'].values, 
                                                          test_df['Close'].values, test_df['TimeOfDay'].values, 
                                                          test_df['Date'].values, test_df['HTF_Resistance'].values,
                                                          test_df['HTF_Support'].values, *best_overall_dna)
                                                          
    if not oos_blown and oos_profit > 0:
        print(f"Out-Of-Sample Status: PASSED 50K EVAL [VERIFIED]")
    else:
        print(f"Out-Of-Sample Status: {'BLOWN' if oos_blown else 'FAILED (UNPROFITABLE)'}")
        
    print(f"Out-Of-Sample Profit: ${oos_profit:.2f} | Sniper Trades Taken: {oos_trades}")
    
if __name__ == "__main__":
    run_htf_wfo()
