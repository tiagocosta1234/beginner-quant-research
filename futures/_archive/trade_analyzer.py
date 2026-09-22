import pandas as pd
import numpy as np

DATA_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def analyze_bias_edge():
    df = pd.read_csv(DATA_PATH)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    
    # Simulate a human's "Daily Bias" using the 4H trend
    df_4h = df.set_index('Datetime').resample('4h').agg({'Close':'last'}).dropna()
    df_4h['EMA_50'] = df_4h['Close'].ewm(span=50, adjust=False).mean()
    df = df.join(df_4h[['EMA_50']], on='Datetime', how='left').ffill()
    
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    times = df['TimeOfDay'].values
    dates = df['Datetime'].dt.date.values
    daily_bias_emas = df['EMA_50'].values
    
    session_open = 0
    is_below = False
    is_above = False
    extreme = 0
    current_day = dates[0]
    
    trade_log = []
    
    i = 3
    while i < len(highs) - 1:
        if dates[i] != current_day:
            current_day = dates[i]
            session_open = 0
            is_below = False
            is_above = False
            
        if times[i] == 830 and session_open == 0:
            session_open = opens[i]
            is_below = False
            is_above = False
            i += 1
            continue
            
        if session_open == 0:
            i += 1
            continue
            
        # Determine Daily Bias (What the human would input)
        # If current price is > 4H EMA, bias is BULLISH. 
        # Therefore, we ONLY look for manipulation BELOW the open.
        is_bullish_bias = closes[i] > daily_bias_emas[i]
        
        # BULLISH (Only if Daily Bias is Bullish)
        if is_bullish_bias and closes[i] < session_open:
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
                
                result = 0
                for k in range(1, 100):
                    if i+k >= len(highs): break
                    if lows[i+k] <= stop_loss:
                        result = -1
                        break
                    elif highs[i+k] >= take_profit:
                        result = 1
                        break
                
                trade_log.append({'Type': 'Long', 'Time': times[i], 'Result': result})
                i += k
                is_below = False
                continue
                
        # BEARISH (Only if Daily Bias is Bearish)
        elif not is_bullish_bias and closes[i] > session_open:
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
                
                result = 0
                for k in range(1, 100):
                    if i+k >= len(lows): break
                    if highs[i+k] >= stop_loss:
                        result = -1
                        break
                    elif lows[i+k] <= take_profit:
                        result = 1
                        break
                        
                trade_log.append({'Type': 'Short', 'Time': times[i], 'Result': result})
                i += k
                is_above = False
                continue
        i += 1

    df_trades = pd.DataFrame(trade_log)
    print("--- FILTER: TRUE DAILY BIAS (HUMAN OVERRIDE PROXY) ---")
    print(f"Total Trades: {len(df_trades)}")
    print(f"Win Rate: {(df_trades['Result'] == 1).mean()*100:.1f}%")
    
    am_trades = df_trades[(df_trades['Time'] >= 830) & (df_trades['Time'] <= 1100)]
    print("\n--- FILTER: TRUE DAILY BIAS + NY AM KILLZONE ---")
    print(f"Total Trades: {len(am_trades)}")
    print(f"Win Rate: {(am_trades['Result'] == 1).mean()*100:.1f}%")

if __name__ == "__main__":
    analyze_bias_edge()
