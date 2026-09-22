import pandas as pd
import numpy as np

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
        upval = delta if delta > 0 else 0.
        downval = -delta if delta < 0 else 0.
        up = (up*(n - 1) + upval)/n
        down = (down*(n - 1) + downval)/n
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1. + rs)
    return rsi

def run_stdv_backtest(df, pt_val):
    df_1h = df.resample('1h', label='left', closed='left').agg({'close': 'last'}).dropna()
    df_1h['ema50'] = df_1h['close'].ewm(span=50, adjust=False).mean()
    df = df.join(df_1h[['ema50']].shift(1).rename(columns={'ema50': 'htf_ema'})).ffill()

    df['htfBull'] = df['close'] > df['htf_ema']
    df['htfBear'] = df['close'] < df['htf_ema']

    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['prev_close']), abs(df['low'] - df['prev_close'])))
    df['atr'] = df['tr'].ewm(alpha=1/14, adjust=False).mean()
    df['avgATR'] = df['atr'].rolling(50).mean()
    df['goodVol'] = (df['atr'] > df['avgATR'] * 0.85) & (df['atr'] < df['avgATR'] * 2.2)

    df['avgVol'] = df['volume'].rolling(20).mean()
    df['volumeConfirmed'] = df['volume'] > (df['avgVol'] * 1.5)

    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['momentumUp'] = (df['rsi'] > 55) & (df['rsi'] < 68)
    df['momentumDown'] = (df['rsi'] < 45) & (df['rsi'] > 32)

    df['strongBull'] = (df['close'] > df['open']) & ((df['close'] - df['open']) > (df['high'] - df['low']) * 0.50)
    df['strongBear'] = (df['close'] < df['open']) & ((df['open'] - df['close']) > (df['high'] - df['low']) * 0.50)

    df['rollingHigh'] = df['high'].shift(1).rolling(20).max()
    df['rollingLow'] = df['low'].shift(1).rolling(20).min()
    df['swingSize'] = df['rollingHigh'] - df['rollingLow']

    df['buy_cross'] = (df['close'] > df['rollingHigh']) & (df['close'].shift(1) <= df['rollingHigh'].shift(1))
    df['sell_cross'] = (df['close'] < df['rollingLow']) & (df['close'].shift(1) >= df['rollingLow'].shift(1))

    df['is_session'] = (df.index.time >= pd.to_datetime('07:00').time()) & (df.index.time <= pd.to_datetime('12:00').time())
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
        forceClose = t_time >= pd.to_datetime('15:50').time()

        if active_trade is not None:
            isLong = active_trade['dir'] == 1
            tpHit = row['high'] >= active_trade['tp'] if isLong else row['low'] <= active_trade['tp']
            slHit = row['low'] <= active_trade['sl'] if isLong else row['high'] >= active_trade['sl']
            
            if tpHit or slHit or forceClose:
                if tpHit and slHit:
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
                    exit_price = row['close']
                    if (isLong and exit_price < active_trade['entry']) or (not isLong and exit_price > active_trade['entry']):
                        dailyLosses += 1
                        outcome = 'LOSS (FC)'
                    else:
                        outcome = 'WIN (FC)'
                        
                riskAmount = 3000
                swingSize = abs(active_trade['entry'] - active_trade['sl'])
                contracts = riskAmount / (swingSize * pt_val) if swingSize > 0 else 0
                
                if 'WIN' in outcome and not 'FC' in outcome:
                    pnl = riskAmount
                elif 'LOSS' in outcome and not 'FC' in outcome:
                    pnl = -riskAmount
                else:
                    rawMove = (exit_price - active_trade['entry']) if isLong else (active_trade['entry'] - exit_price)
                    pnl = (rawMove * pt_val * contracts)
                    
                net_pnl = pnl - (2.3 * contracts)
                
                active_trade['net_pnl'] = net_pnl
                trades.append(active_trade)
                active_trade = None
            continue
            
        if canTrade:
            if row['buySignal']:
                tradesToday += 1
                active_trade = {
                    'dir': 1, 'entry': row['rollingHigh'], 'sl': row['rollingLow'],
                    'tp': row['rollingHigh'] + row['swingSize']
                }
            elif row['sellSignal']:
                tradesToday += 1
                active_trade = {
                    'dir': -1, 'entry': row['rollingLow'], 'sl': row['rollingHigh'],
                    'tp': row['rollingLow'] - row['swingSize']
                }

    # Calculate Drawdown
    cum_pnl = 0.0
    peak_pnl = 0.0
    max_dd = 0.0
    
    for t in trades:
        cum_pnl += t['net_pnl']
        if cum_pnl > peak_pnl:
            peak_pnl = cum_pnl
        dd = peak_pnl - cum_pnl
        if dd > max_dd:
            max_dd = dd

    wins = sum(1 for t in trades if t['net_pnl'] > 0)
    losses = len(trades) - wins
    net_profit = sum(t['net_pnl'] for t in trades)
    win_rate = (wins/len(trades))*100 if len(trades) > 0 else 0

    return {
        'total': len(trades),
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'net_pnl': net_profit,
        'max_dd': max_dd
    }

def process_file(filename, pt_val, name):
    print(f"Loading {name}...")
    df = pd.read_csv(filename, sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
    df['datetime'] = df['datetime'] - pd.Timedelta(hours=4)
    df.set_index('datetime', inplace=True)
    df_5m = df.resample('5min', label='left', closed='left').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    res = run_stdv_backtest(df_5m, pt_val)
    print(f"--- {name} Results ---")
    print(f"Total Trades: {res['total']}")
    print(f"Win Rate: {res['win_rate']:.2f}%")
    print(f"Net PnL: ${res['net_pnl']:.2f}")
    print(f"Max Drawdown: -${res['max_dd']:.2f}")
    print("----------------------")

if __name__ == "__main__":
    process_file('futures/data/MGC_CONTINUOUS.txt', 10.0, "Gold (GC)")
    process_file('futures/data/MNQ_CONTINUOUS.txt', 20.0, "Nasdaq (NQ)")
