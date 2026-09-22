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

def optimize_fast(filename, pt_val, name):
    print(f"Loading {name}...")
    df = pd.read_csv(filename, sep=';', header=None, names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S') - pd.Timedelta(hours=4)
    df.set_index('datetime', inplace=True)
    df = df.resample('5min', label='left', closed='left').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    
    df_1h = df.resample('1h', label='left', closed='left').agg({'close': 'last'}).dropna()
    df_1h['ema'] = df_1h['close'].ewm(span=50, adjust=False).mean()
    df = df.join(df_1h[['ema']].shift(1).rename(columns={'ema': 'htf_ema'})).ffill()
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    vols = df['volume'].values
    dates = df.index.date
    times = df.index.time
    
    htfBull = closes > df['htf_ema'].values
    htfBear = closes < df['htf_ema'].values
    
    prev_close = np.roll(closes, 1)
    prev_close[0] = closes[0]
    tr = np.maximum(highs - lows, np.maximum(abs(highs - prev_close), abs(lows - prev_close)))
    atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean().values
    avgATR = pd.Series(atr).rolling(50).mean().values
    goodVol = (atr > avgATR * 0.85) & (atr < avgATR * 2.2)
    
    avgVol = pd.Series(vols).rolling(20).mean().values
    volConf = vols > (avgVol * 1.5)
    
    rsi = calculate_rsi(closes, 14)
    momUp = (rsi > 55) & (rsi < 68)
    momDn = (rsi < 45) & (rsi > 32)
    
    strBull = (closes > opens) & ((closes - opens) > (highs - lows) * 0.5)
    strBear = (closes < opens) & ((opens - closes) > (highs - lows) * 0.5)
    
    rollHigh = pd.Series(highs).shift(1).rolling(20).max().values
    rollLow = pd.Series(lows).shift(1).rolling(20).min().values
    
    buy_cross = (closes > rollHigh) & (prev_close <= pd.Series(rollHigh).shift(1).values)
    sell_cross = (closes < rollLow) & (prev_close >= pd.Series(rollLow).shift(1).values)
    
    time_arr = pd.to_datetime(df.index).time
    is_sess = (time_arr >= pd.to_datetime('07:00').time()) & (time_arr <= pd.to_datetime('12:00').time())
    timeOk = time_arr < pd.to_datetime('10:45').time()
    
    bSig = buy_cross & volConf & momUp & strBull & htfBull & goodVol & timeOk & is_sess
    sSig = sell_cross & volConf & momDn & strBear & htfBear & goodVol & timeOk & is_sess
    
    # Grid Search
    lookbacks = [20]
    tp_sl_ratios = [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0)]
    risk_amts = [1000]
    
    best_score = -999999
    best_cfg = None
    
    for tpm, slm in tp_sl_ratios:
        for risk in risk_amts:
            active = False
            adir = 0
            aent = 0.0
            asl = 0.0
            atp = 0.0
            
            pnl = 0.0
            peak = 0.0
            mdd = 0.0
            trds = 0
            wns = 0
            
            lastD = None
            tT = 0
            
            # Fast loop
            for i in range(len(closes)):
                cd = dates[i]
                if cd != lastD:
                    tT = 0
                    lastD = cd
                    
                if active:
                    tpHit = (highs[i] >= atp) if adir == 1 else (lows[i] <= atp)
                    slHit = (lows[i] <= asl) if adir == 1 else (highs[i] >= asl)
                    fc = time_arr[i] >= pd.to_datetime('15:50').time()
                    
                    if tpHit or slHit or fc:
                        if tpHit and slHit:
                            outc = 'L'
                            ep = asl
                        elif tpHit:
                            outc = 'W'
                            ep = atp
                        elif slHit:
                            outc = 'L'
                            ep = asl
                        else:
                            ep = closes[i]
                            if (adir==1 and ep<aent) or (adir==-1 and ep>aent): outc = 'L'
                            else: outc = 'W'
                            
                        ss = abs(aent - asl)
                        cts = risk / (ss * pt_val) if ss > 0 else 0
                        
                        if outc == 'W' and not fc: rpnl = risk * (tpm/slm)
                        elif outc == 'L' and not fc: rpnl = -risk
                        else:
                            rm = (ep - aent) if adir==1 else (aent - ep)
                            rpnl = rm * pt_val * cts
                            
                        npnl = rpnl - (2.3 * cts)
                        pnl += npnl
                        trds += 1
                        if npnl > 0: wns += 1
                        if pnl > peak: peak = pnl
                        if peak - pnl > mdd: mdd = peak - pnl
                        
                        active = False
                    continue
                    
                if tT < 1:
                    if bSig[i]:
                        tT += 1
                        active = True
                        adir = 1
                        ssz = rollHigh[i] - rollLow[i]
                        aent = rollHigh[i]
                        asl = aent - (ssz * slm)
                        atp = aent + (ssz * tpm)
                    elif sSig[i]:
                        tT += 1
                        active = True
                        adir = -1
                        ssz = rollHigh[i] - rollLow[i]
                        aent = rollLow[i]
                        asl = aent + (ssz * slm)
                        atp = aent - (ssz * tpm)
                        
            score = pnl / (mdd + 1)
            if score > best_score and mdd < 8000 and trds > 100:
                best_score = score
                best_cfg = (tpm, slm, risk, trds, wns, pnl, mdd)
                
    if best_cfg:
        print(f"[{name}] Best -> TP:{best_cfg[0]} SL:{best_cfg[1]} Risk:${best_cfg[2]}")
        print(f"Trades: {best_cfg[3]}, WR: {best_cfg[4]/best_cfg[3]*100:.2f}%, PnL: ${best_cfg[5]:.2f}, MaxDD: -${best_cfg[6]:.2f}")
    else:
        print(f"[{name}] No configuration found with Drawdown < $8k")

if __name__ == "__main__":
    optimize_fast('futures/data/MGC_CONTINUOUS.txt', 10.0, 'Gold (GC)')
    optimize_fast('futures/data/MNQ_CONTINUOUS.txt', 20.0, 'Nasdaq (NQ)')
