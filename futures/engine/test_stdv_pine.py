import pandas as pd
import numpy as np

def rma(x, n):
    a = np.full_like(x, np.nan)
    if len(x) < n:
        return a
    a[n-1] = x[:n].mean()
    for i in range(n, len(x)):
        a[i] = (x[i] + (n - 1) * a[i - 1]) / n
    return a

def calculate_rsi(prices, n=14):
    deltas = np.diff(prices)
    seed = deltas[:n+1]
    up = seed[seed >= 0].sum()/n
    down = -seed[seed < 0].sum()/n
    rs = up/down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100./(1. + rs)

    for i in range(n, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up*(n - 1) + upval)/n
        down = (down*(n - 1) + downval)/n

        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1. + rs)
    return rsi

def run_stdv_backtest(df):
    # Base timeframe is assumed 5min
    
    # HTF 1H EMA
    df_1h = df.resample('1h', label='left', closed='left').agg({'close': 'last'}).dropna()
    df_1h['ema50'] = df_1h['close'].ewm(span=50, adjust=False).mean()
    # Map HTF back to 5m
    df = df.join(df_1h[['ema50']].shift(1).rename(columns={'ema50': 'htf_ema'})).ffill()

    df['htfBull'] = df['close'] > df['htf_ema']
    df['htfBear'] = df['close'] < df['htf_ema']

    # ATR
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(df['high'] - df['low'], 
               np.maximum(abs(df['high'] - df['prev_close']), 
                          abs(df['low'] - df['prev_close'])))
    df['atr'] = df['tr'].ewm(alpha=1/14, adjust=False).mean()
    df['avgATR'] = df['atr'].rolling(50).mean()
    df['goodVol'] = (df['atr'] > df['avgATR'] * 0.85) & (df['atr'] < df['avgATR'] * 2.2)

    # Volume filter
    df['avgVol'] = df['volume'].rolling(20).mean()
    df['volumeConfirmed'] = df['volume'] > (df['avgVol'] * 1.5)

    # RSI
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['momentumUp'] = (df['rsi'] > 55) & (df['rsi'] < 68)
    df['momentumDown'] = (df['rsi'] < 45) & (df['rsi'] > 32)

    # Strong candle
    df['strongBull'] = (df['close'] > df['open']) & ((df['close'] - df['open']) > (df['high'] - df['low']) * 0.50)
    df['strongBear'] = (df['close'] < df['open']) & ((df['open'] - df['close']) > (df['high'] - df['low']) * 0.50)

    # Rolling Range
    df['rollingHigh'] = df['high'].shift(1).rolling(20).max()
    df['rollingLow'] = df['low'].shift(1).rolling(20).min()
    df['swingSize'] = df['rollingHigh'] - df['rollingLow']

    df['buy_cross'] = (df['close'] > df['rollingHigh']) & (df['close'].shift(1) <= df['rollingHigh'].shift(1))
    df['sell_cross'] = (df['close'] < df['rollingLow']) & (df['close'].shift(1) >= df['rollingLow'].shift(1))

    df['utc1_hour'] = (df.index.hour + 5) % 24  # Assuming index is EST (UTC-4/-5) let's just use EST logic directly
    # Wait, the timezone in verify_gc_txt.py says:
    # df['datetime'] = pd.to_datetime(...) - pd.Timedelta(hours=4)
    # If the original data is EST? Or is original data UTC and we shift -4?
    # Usually MGC.txt from NinjaTrader/TradingView is UTC. So UTC-4 = EST.
    # If index is EST, UTC+1 hour is index.hour + 5.
    
    # Let's define the conditions exactly
    # session 12:00-17:00 UTC+1 => 07:00-12:00 EST
    df['is_session'] = (df.index.time >= pd.to_datetime('07:00').time()) & (df.index.time <= pd.to_datetime('12:00').time())
    
    # timeOk: < 15:45 UTC+1 => < 10:45 EST
    df['timeOk'] = df.index.time < pd.to_datetime('10:45').time()

    df['buySignal'] = df['buy_cross'] & df['volumeConfirmed'] & df['momentumUp'] & df['strongBull'] & df['htfBull'] & df['goodVol'] & df['timeOk'] & df['is_session']
    df['sellSignal'] = df['sell_cross'] & df['volumeConfirmed'] & df['momentumDown'] & df['strongBear'] & df['htfBear'] & df['goodVol'] & df['timeOk'] & df['is_session']

    trades = []
    active_trade = None
    tradesToday = 0
    dailyLosses = 0
    lastDay = None

    for idx, row in df.iterrows():
        current_day = idx.date()
        if current_day != lastDay:
            tradesToday = 0
            dailyLosses = 0
            lastDay = current_day

        canTrade = (dailyLosses < 3) and (tradesToday < 1)

        t_time = idx.time()
        forceClose = t_time >= pd.to_datetime('15:50').time() # Force close at 20:50 UTC+1 -> 15:50 EST

        if active_trade is not None:
            isLong = active_trade['dir'] == 1
            tpHit = row['high'] >= active_trade['tp'] if isLong else row['low'] <= active_trade['tp']
            slHit = row['low'] <= active_trade['sl'] if isLong else row['high'] >= active_trade['sl']
            
            if tpHit or slHit or forceClose:
                if tpHit and slHit:
                    # pessimistic: assume stop loss hit first
                    outcome = 'LOSS'
                    exit_price = active_trade['sl']
                    dailyLosses += 1
                elif tpHit:
                    outcome = 'WIN'
                    exit_price = active_trade['tp']
                elif slHit:
                    outcome = 'LOSS'
                    exit_price = active_trade['sl']
                    dailyLosses += 1
                else:
                    # force close
                    exit_price = row['close']
                    if (isLong and exit_price < active_trade['entry']) or (not isLong and exit_price > active_trade['entry']):
                        dailyLosses += 1
                        outcome = 'LOSS (FC)'
                    else:
                        outcome = 'WIN (FC)'
                        
                active_trade['exit_time'] = idx
                active_trade['exit_price'] = exit_price
                active_trade['outcome'] = outcome
                
                # Sizing logic
                riskAmount = 3000
                pointValue = 10.0 # Standard GC
                swingSize = abs(active_trade['entry'] - active_trade['sl'])
                contracts = riskAmount / (swingSize * pointValue) if swingSize > 0 else 0
                
                if 'WIN' in outcome and not 'FC' in outcome:
                    pnl = riskAmount  # 1:1 reward
                elif 'LOSS' in outcome and not 'FC' in outcome:
                    pnl = -riskAmount
                else:
                    rawMove = (exit_price - active_trade['entry']) if isLong else (active_trade['entry'] - exit_price)
                    pnl = (rawMove * pointValue * contracts)
                    
                active_trade['net_pnl'] = pnl - (2.3 * contracts) # commission
                trades.append(active_trade)
                active_trade = None
            continue
            
        if canTrade:
            if row['buySignal']:
                tradesToday += 1
                active_trade = {
                    'entry_time': idx, 'dir': 1, 'type': 'Long',
                    'entry': row['rollingHigh'], 'sl': row['rollingLow'],
                    'tp': row['rollingHigh'] + row['swingSize'],
                    'swing_size': row['swingSize']
                }
            elif row['sellSignal']:
                tradesToday += 1
                active_trade = {
                    'entry_time': idx, 'dir': -1, 'type': 'Short',
                    'entry': row['rollingLow'], 'sl': row['rollingHigh'],
                    'tp': row['rollingLow'] - row['swingSize'],
                    'swing_size': row['swingSize']
                }

    return trades

if __name__ == "__main__":
    print("Loading data...")
    df = pd.read_csv('futures/data/MGC_CONTINUOUS.txt', sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
    df['datetime'] = df['datetime'] - pd.Timedelta(hours=4)
    df.set_index('datetime', inplace=True)
    
    # We will resample to 5m to match the typical chart
    df_5m = df.resample('5min', label='left', closed='left').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    print("Running backtest for STDV PO3 logic on 5m...")
    trades = run_stdv_backtest(df_5m)
    
    if not trades:
        print("No trades triggered.")
    else:
        wins = sum(1 for t in trades if t['net_pnl'] > 0)
        losses = len(trades) - wins
        net_profit = sum(t['net_pnl'] for t in trades)
        win_rate = (wins/len(trades))*100
        print(f"Total Trades: {len(trades)}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Net PnL: ${net_profit:.2f}")

