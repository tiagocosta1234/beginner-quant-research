import pandas as pd
import numpy as np

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineers Level 1 market features from OHLCV bar data (e.g. 500-Tick bars).
    Assumes df has columns: ['time', 'open', 'high', 'low', 'close', 'volume']
    """
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    
    if not df.index.is_monotonic_increasing:
        df.sort_index(inplace=True)
        
    df_copy = df.copy()

    # 0. Continuous Time Encodings (Sine/Cosine Transformation)
    df_copy['hour_sin'] = np.sin(2 * np.pi * df_copy.index.hour / 24.0)
    df_copy['hour_cos'] = np.cos(2 * np.pi * df_copy.index.hour / 24.0)
    df_copy['minute_sin'] = np.sin(2 * np.pi * df_copy.index.minute / 60.0)
    df_copy['minute_cos'] = np.cos(2 * np.pi * df_copy.index.minute / 60.0)
    df_copy['day_of_week_sin'] = np.sin(2 * np.pi * df_copy.index.dayofweek / 7.0)
    df_copy['day_of_week_cos'] = np.cos(2 * np.pi * df_copy.index.dayofweek / 7.0)

    # 1. Volume Delta (Direction based on close vs previous close)
    price_diff = df_copy['close'].diff()
    trade_dir = np.where(price_diff > 0, 1, np.where(price_diff < 0, -1, 0))
    df_copy['trade_dir'] = trade_dir
    df_copy['trade_dir'] = df_copy['trade_dir'].replace(0, np.nan).ffill().fillna(0)    
    df_copy['volume_delta'] = df_copy['volume'] * df_copy['trade_dir']
    
    df_copy['date'] = df_copy.index.date
    df_copy['cvd'] = df_copy.groupby('date')['volume_delta'].cumsum()
    df_copy['date'] = df_copy.index.date
    df_copy['cum_vol'] = df_copy.groupby('date')['volume'].cumsum()
    df_copy['pv'] = df_copy['close'] * df_copy['volume']
    df_copy['cum_pv'] = df_copy.groupby('date')['pv'].cumsum()
    
    df_copy['vwap'] = df_copy['cum_pv'] / df_copy['cum_vol']
    df_copy['vwap_dev'] = df_copy['close'] - df_copy['vwap']

    # 3. Bar Velocity Removed
    # 1-Minute bars have static 60-second intervals, so velocity is irrelevant.
    
    # 4. EMA Distance
    df_copy['ema_9'] = df_copy['close'].ewm(span=9, adjust=False).mean()
    df_copy['ema_21'] = df_copy['close'].ewm(span=21, adjust=False).mean()
    df_copy['ema_distance'] = df_copy['ema_9'] - df_copy['ema_21']
    
    # 5. VWAP Slope
    df_copy['vwap_slope'] = df_copy['vwap'] - df_copy['vwap'].shift(5)
    
    # 6. ORB (Opening Range Breakout) Features
    import datetime
    time_only = pd.Series(df_copy.index, index=df_copy.index).dt.time
    t_0930 = datetime.time(9, 30)
    t_1030 = datetime.time(10, 30)
    t_0945 = datetime.time(9, 45)
    
    df_copy['orb_active'] = np.where((time_only >= t_0930) & (time_only <= t_1030), 1.0, 0.0)
    
    df_copy['is_orb_period'] = (time_only >= t_0930) & (time_only <= t_0945)
    df_copy['orb_high_step'] = np.where(df_copy['is_orb_period'], df_copy['high'], np.nan)
    df_copy['orb_low_step'] = np.where(df_copy['is_orb_period'], df_copy['low'], np.nan)
    
    df_copy['orb_high'] = df_copy.groupby('date')['orb_high_step'].cummax()
    df_copy['orb_low'] = df_copy.groupby('date')['orb_low_step'].cummin()
    
    df_copy['orb_high'] = df_copy.groupby('date')['orb_high'].ffill()
    df_copy['orb_low'] = df_copy.groupby('date')['orb_low'].ffill()
    
    df_copy['orb_high'] = df_copy['orb_high'].fillna(df_copy['close'])
    df_copy['orb_low'] = df_copy['orb_low'].fillna(df_copy['close'])

    # 7. ATR (Average True Range) - 14 Period on the OHLC bars
    prev_close = df_copy['close'].shift(1)
    tr1 = df_copy['high'] - df_copy['low']
    tr2 = (df_copy['high'] - prev_close).abs()
    tr3 = (df_copy['low'] - prev_close).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df_copy['atr_14'] = true_range.rolling(window=14, min_periods=1).mean()
    df_copy['atr_14'] = df_copy['atr_14'].fillna(0.0)

    # Pure Pandas ADX (Average Directional Index) Calculation
    def calc_adx(df, length=14):
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm_true = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
        minus_dm_true = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
        
        tr = np.maximum.reduce([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ])
        
        tr_smooth = pd.Series(tr).ewm(alpha=1/length, adjust=False).mean()
        plus_di = 100 * (pd.Series(plus_dm_true).ewm(alpha=1/length, adjust=False).mean() / tr_smooth)
        minus_di = 100 * (pd.Series(minus_dm_true).ewm(alpha=1/length, adjust=False).mean() / tr_smooth)
        
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8) * 100
        dx = dx.fillna(0.0)
        adx = dx.ewm(alpha=1/length, adjust=False).mean()
        return adx.fillna(0.0)
        
    df_copy['adx_14'] = calc_adx(df_copy, length=14)
    
    # Pure Pandas RSI (Relative Strength Index) Calculation
    def calc_rsi(df, length=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = np.where(avg_loss == 0, 100.0, rsi)
        return pd.Series(rsi, index=df.index).fillna(0.0)
        
    df_copy['rsi_14'] = calc_rsi(df_copy, length=14)

    # 8. Macro Trend Alignment (EMA 200)
    df_copy['ema_200'] = df_copy['close'].ewm(span=200, adjust=False).mean()
    df_copy['ema_200_dist'] = df_copy['close'] - df_copy['ema_200']

    # 9. Wick Rejection Ratio (Candle Psychology)
    # Ratio of wick size to total candle size. Top wick for rejection, bottom wick for support.
    candle_range = df_copy['high'] - df_copy['low']
    candle_range = candle_range.replace(0, 0.0001) # Prevent division by zero
    
    top_wick = df_copy['high'] - df_copy[['open', 'close']].max(axis=1)
    bottom_wick = df_copy[['open', 'close']].min(axis=1) - df_copy['low']
    
    # Positive means heavy bottom wick (buying pressure), Negative means heavy top wick (selling pressure)
    df_copy['wick_rejection_ratio'] = (bottom_wick - top_wick) / candle_range

    # 10. Institutional Price Memory (Distance to Yesterday's H/L/C)
    daily_high = df_copy.groupby('date')['high'].max()
    daily_low = df_copy.groupby('date')['low'].min()
    daily_close = df_copy.groupby('date')['close'].last()
    
    # Shift by 1 to get "Yesterday's" data
    yday_high = daily_high.shift(1)
    yday_low = daily_low.shift(1)
    yday_close = daily_close.shift(1)
    
    # Map back to intraday rows
    df_copy['yday_high_dist'] = df_copy['close'] - df_copy['date'].map(yday_high)
    df_copy['yday_low_dist'] = df_copy['close'] - df_copy['date'].map(yday_low)
    df_copy['yday_close_dist'] = df_copy['close'] - df_copy['date'].map(yday_close)
    
    # Fill NAs for the very first day in the dataset
    df_copy['yday_high_dist'] = df_copy['yday_high_dist'].fillna(0.0)
    df_copy['yday_low_dist'] = df_copy['yday_low_dist'].fillna(0.0)
    df_copy['yday_close_dist'] = df_copy['yday_close_dist'].fillna(0.0)

    # 11. Liquidity Pool Proxies (Swing Pivots)
    df_copy['rolling_max_20'] = df_copy['high'].rolling(20, min_periods=1).max()
    df_copy['rolling_min_20'] = df_copy['low'].rolling(20, min_periods=1).min()
    df_copy['liq_high_dist'] = df_copy['rolling_max_20'] - df_copy['close']
    df_copy['liq_low_dist'] = df_copy['close'] - df_copy['rolling_min_20']

    # 12. Multi-Timeframe (MTF) Engine
    df_15m = df_copy.resample('15min', closed='right', label='right').agg({'close': 'last', 'high': 'max', 'low': 'min'}).dropna()
    df_15m['ema_15m'] = df_15m['close'].ewm(span=20, adjust=False).mean()
    df_15m['rsi_15m'] = calc_rsi(df_15m, length=14)
    
    df_15m['ema_12'] = df_15m['close'].ewm(span=12, adjust=False).mean()
    df_15m['ema_26'] = df_15m['close'].ewm(span=26, adjust=False).mean()
    df_15m['macd_15m'] = df_15m['ema_12'] - df_15m['ema_26']
    df_15m['macd_signal_15m'] = df_15m['macd_15m'].ewm(span=9, adjust=False).mean()
    df_15m['macd_hist_15m'] = df_15m['macd_15m'] - df_15m['macd_signal_15m']
    
    df_1h = df_copy.resample('1h', closed='right', label='right').agg({'close': 'last'}).dropna()
    df_1h['ema_1h'] = df_1h['close'].ewm(span=20, adjust=False).mean()
    
    df_copy = df_copy.join(df_15m[['ema_15m', 'rsi_15m', 'macd_hist_15m']], how='left').ffill()
    df_copy = df_copy.join(df_1h[['ema_1h']], how='left').ffill()
    
    df_copy['ema_15m'] = df_copy['ema_15m'].fillna(df_copy['close'])
    df_copy['rsi_15m'] = df_copy['rsi_15m'].fillna(0.0)
    df_copy['macd_hist_15m'] = df_copy['macd_hist_15m'].fillna(0.0)
    df_copy['ema_1h'] = df_copy['ema_1h'].fillna(df_copy['close'])
    
    df_copy['ema_15m_dist'] = df_copy['close'] - df_copy['ema_15m']
    df_copy['ema_1h_dist'] = df_copy['close'] - df_copy['ema_1h']

    # 13. Advanced Regime Detection (Volatility Compression)
    # Uses Bollinger Band Width to detect trending vs choppy regimes
    rolling_std = df_copy['close'].rolling(20, min_periods=1).std()
    rolling_std = rolling_std.fillna(0.0001).replace(0, 0.0001)
    bb_upper = df_copy['ema_21'] + (rolling_std * 2)
    bb_lower = df_copy['ema_21'] - (rolling_std * 2)
    df_copy['bb_width'] = (bb_upper - bb_lower) / df_copy['ema_21']

    # Clean up
    noise_cols = [
        'cum_vol', 'pv', 'cum_pv', 'date', 'trade_dir', 'ema_9', 'ema_21', 'ema_200', 
        'is_orb_period', 'orb_high_step', 'orb_low_step', 'rolling_max_20', 'rolling_min_20', 
        'ema_15m', 'ema_1h', 'orb_active', 'orb_high', 'orb_low', 'ema_200_dist', 
        'yday_high_dist', 'yday_low_dist', 'yday_close_dist', 'adx_14', 'rsi_15m',
        'minute_sin', 'minute_cos', 'day_of_week_sin', 'day_of_week_cos', 'hour_sin', 'hour_cos'
    ]
    df_copy.drop(columns=noise_cols, inplace=True, errors='ignore')
    df_copy.fillna(0, inplace=True)

    return df_copy

def load_ninjatrader_csv(filepath: str) -> pd.DataFrame:
    """
    Reads a standard NinjaTrader exported historical 1-Minute OHLCV data CSV.
    Expected format: Timestamp;Open;High;Low;Close;Volume
    """
    try:
        df = pd.read_csv(filepath, sep=';', header=None, 
                         names=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 1-Minute exports don't have microseconds (%f), they look like "20251214 171500"
        try:
            df['time'] = pd.to_datetime(df['time'], format='%Y%m%d %H%M%S')
        except ValueError:
            # Fallback if there are still microseconds or different formats
            df['time'] = pd.to_datetime(df['time'])
            
        df.set_index('time', inplace=True)
        
        req_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in req_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column in CSV: {col}. Found: {df.columns}")
                
        df = df[req_cols].copy()
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    except Exception as e:
        print(f"Error loading NinjaTrader OHLCV CSV from {filepath}: {e}")
        return pd.DataFrame()
