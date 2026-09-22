import pandas as pd
import numpy as np
from itertools import product

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

def load_data(filename):
    df = pd.read_csv(filename, sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S') - pd.Timedelta(hours=4)
    df.set_index('datetime', inplace=True)
    return df.resample('5min', label='left', closed='left').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()

def precalculate_indicators(df, htf_span=50, rsi_period=14, atr_period=14, atr_ma=50):
    df_1h = df.resample('1h', label='left', closed='left').agg({'close': 'last'}).dropna()
    df_1h['ema'] = df_1h['close'].ewm(span=htf_span, adjust=False).mean()
    df = df.join(df_1h[['ema']].shift(1).rename(columns={'ema': 'htf_ema'})).ffill()
    df['htfBull'] = df['close'] > df['htf_ema']
    df['htfBear'] = df['close'] < df['htf_ema']

    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['prev_close']), abs(df['low'] - df['prev_close'])))
    df['atr'] = df['tr'].ewm(alpha=1/atr_period, adjust=False).mean()
    df['avgATR'] = df['atr'].rolling(atr_ma).mean()
    df['goodVol'] = (df['atr'] > df['avgATR'] * 0.85) & (df['atr'] < df['avgATR'] * 2.2)

    df['rsi'] = calculate_rsi(df['close'].values, rsi_period)
    df['strongBull'] = (df['close'] > df['open']) & ((df['close'] - df['open']) > (df['high'] - df['low']) * 0.50)
    df['strongBear'] = (df['close'] < df['open']) & ((df['open'] - df['close']) > (df['high'] - df['low']) * 0.50)

    df['is_session'] = (df.index.time >= pd.to_datetime('07:00').time()) & (df.index.time <= pd.to_datetime('12:00').time())
    df['timeOk'] = df.index.time < pd.to_datetime('10:45').time()
    
    return df

def simulate_strategy(df, pt_val, lookback, vol_mult, rsi_low_up, rsi_high_up, rsi_low_dn, rsi_high_dn, tp_mult=1.0, sl_mult=1.0):
    df['avgVol'] = df['volume'].rolling(20).mean()
    volumeConfirmed = df['volume'] > (df['avgVol'] * vol_mult)

    momentumUp = (df['rsi'] > rsi_low_up) & (df['rsi'] < rsi_high_up)
    momentumDown = (df['rsi'] < rsi_high_dn) & (df['rsi'] > rsi_low_dn)

    rollingHigh = df['high'].shift(1).rolling(lookback).max()
    rollingLow = df['low'].shift(1).rolling(lookback).min()
    swingSize = rollingHigh - rollingLow

    buy_cross = (df['close'] > rollingHigh) & (df['close'].shift(1) <= rollingHigh.shift(1))
    sell_cross = (df['close'] < rollingLow) & (df['close'].shift(1) >= rollingLow.shift(1))

    buySignal = buy_cross & volumeConfirmed & momentumUp & df['strongBull'] & df['htfBull'] & df['goodVol'] & df['timeOk'] & df['is_session']
    sellSignal = sell_cross & volumeConfirmed & momentumDown & df['strongBear'] & df['htfBear'] & df['goodVol'] & df['timeOk'] & df['is_session']

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
        forceClose = idx.time() >= pd.to_datetime('15:50').time()

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
                    
                riskAmount = 1500  # Normalized to $1500 risk to reduce drawdowns
                swing_pts = abs(active_trade['entry'] - active_trade['sl'])
                contracts = riskAmount / (swing_pts * pt_val) if swing_pts > 0 else 0
                
                if 'WIN' in outcome:
                    pnl = riskAmount * tp_mult / sl_mult
                elif 'LOSS' in outcome:
                    pnl = -riskAmount
                else:
                    rawMove = (exit_price - active_trade['entry']) if isLong else (active_trade['entry'] - exit_price)
                    pnl = (rawMove * pt_val * contracts)
                    
                net_pnl = pnl - (2.3 * contracts)
                trades.append(net_pnl)
                active_trade = None
            continue
            
        if canTrade:
            if buySignal.loc[idx]:
                tradesToday += 1
                active_trade = {'dir': 1, 'entry': rollingHigh.loc[idx], 'sl': rollingHigh.loc[idx] - (swingSize.loc[idx] * sl_mult), 'tp': rollingHigh.loc[idx] + (swingSize.loc[idx] * tp_mult)}
            elif sellSignal.loc[idx]:
                tradesToday += 1
                active_trade = {'dir': -1, 'entry': rollingLow.loc[idx], 'sl': rollingLow.loc[idx] + (swingSize.loc[idx] * sl_mult), 'tp': rollingLow.loc[idx] - (swingSize.loc[idx] * tp_mult)}

    cum_pnl = 0.0
    peak_pnl = 0.0
    max_dd = 0.0
    wins = 0
    
    for pnl in trades:
        cum_pnl += pnl
        if pnl > 0: wins += 1
        if cum_pnl > peak_pnl: peak_pnl = cum_pnl
        if peak_pnl - cum_pnl > max_dd: max_dd = peak_pnl - cum_pnl

    return len(trades), (wins/len(trades)*100 if trades else 0), cum_pnl, max_dd

if __name__ == "__main__":
    print("Loading GC data...")
    df_gc = load_data('futures/data/MGC_CONTINUOUS.txt')
    df_gc = precalculate_indicators(df_gc)
    
    print("Optimizing GC...")
    lookbacks = [10, 20, 30]
    vol_mults = [1.2, 1.5, 2.0]
    tp_sl_ratios = [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0)] # TP mult, SL mult
    
    best_gc = None
    best_score_gc = -999999
    
    for lb, vm, (tpm, slm) in product(lookbacks, vol_mults, tp_sl_ratios):
        trades, wr, pnl, dd = simulate_strategy(df_gc, 10.0, lb, vm, 55, 68, 32, 45, tp_mult=tpm, sl_mult=slm)
        if trades > 100:
            score = pnl / (dd + 1)
            if score > best_score_gc and dd < 8000: # We want DD < 8k at $1500 risk
                best_score_gc = score
                best_gc = (lb, vm, tpm, slm, trades, wr, pnl, dd)
                
    if best_gc:
        print(f"Best GC -> Lookback: {best_gc[0]}, Vol: {best_gc[1]}, TP:SL={best_gc[2]}:{best_gc[3]}")
        print(f"Trades: {best_gc[4]}, WR: {best_gc[5]:.2f}%, PnL: ${best_gc[6]:.2f}, MaxDD: -${best_gc[7]:.2f}")
    else:
        print("No GC config found with DD < $8k")

    print("\nLoading NQ data...")
    df_nq = load_data('futures/data/MNQ_CONTINUOUS.txt')
    df_nq = precalculate_indicators(df_nq)
    
    best_nq = None
    best_score_nq = -999999
    
    for lb, vm, (tpm, slm) in product(lookbacks, vol_mults, tp_sl_ratios):
        trades, wr, pnl, dd = simulate_strategy(df_nq, 20.0, lb, vm, 55, 68, 32, 45, tp_mult=tpm, sl_mult=slm)
        if trades > 100:
            score = pnl / (dd + 1)
            if score > best_score_nq and dd < 8000:
                best_score_nq = score
                best_nq = (lb, vm, tpm, slm, trades, wr, pnl, dd)
                
    if best_nq:
        print(f"Best NQ -> Lookback: {best_nq[0]}, Vol: {best_nq[1]}, TP:SL={best_nq[2]}:{best_nq[3]}")
        print(f"Trades: {best_nq[4]}, WR: {best_nq[5]:.2f}%, PnL: ${best_nq[6]:.2f}, MaxDD: -${best_nq[7]:.2f}")
    else:
        print("No NQ config found with DD < $8k")
