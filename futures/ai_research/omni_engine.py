import os
import pandas as pd
import numpy as np
import datetime
import threading
import time
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

class OmniState:
    def __init__(self):
        self.bar_history = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'es_close'])
        self.regime = "WAITING"
        self.grid_distance = 30.0
        self.profit_target = 15.0
        self.yesterday_settlement = None
        self.lock = threading.Lock()
        
        self.pdh = None
        self.pdl = None
        self.ib_high = None
        self.ib_low = None
        self.ib_set_for_day = None

state = OmniState()

# ==========================================
# PHASE 2: WALK-FORWARD OPTIMIZER
# ==========================================
def walk_forward_optimizer():
    while True:
        try:
            time.sleep(60) 
            with state.lock:
                if len(state.bar_history) < 60: continue
                df = state.bar_history.copy()
                df['high_low'] = df['high'] - df['low']
                rolling_atr = df['high_low'].rolling(60).mean().iloc[-1]
                if pd.notna(rolling_atr) and rolling_atr > 0:
                    multiplier = max(1.0, rolling_atr / 15.0)
                    multiplier = min(3.0, multiplier)
                    state.grid_distance = round(30.0 * multiplier * 4) / 4.0 
                    state.profit_target = round(15.0 * multiplier * 4) / 4.0
        except Exception as e:
            print(f"WFO Thread Error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- 🧠 Booting Massive Omni-Engine (Omniscient Eye Edition) ---")
    print("✅ Structure Module (FVGs & Liquidity Sweeps) Loaded.")
    print("✅ Statistical Module (Session VWAP) Loaded.")
    print("✅ Correlation Module (ES vs NQ) Loaded.")
    print("✅ Regime Module (HMM Volatility) Loaded.")
    print("✅ Anti-Retail Trap Detection (Parabolic Fades) Loaded.")
    print("✅ Overnight Gap Fill Arbitrage Loaded.")
    print("✅ Liquidity Pool Tracking (PDH/PDL) Loaded.")
    print("✅ Initial Balance (IB) Profiling Loaded.")
    print("✅ 3-Push Exhaustion Divergence Loaded.")
    print("✅ [PHASE 4] Macro Trend Veto (60-Minute) Loaded.")
    print("✅ [PHASE 4] VPA Absorption (Effort vs Result) Loaded.")
    print("✅ [PHASE 4] Volatility Squeeze Detection Loaded.")
    threading.Thread(target=walk_forward_optimizer, daemon=True).start()
    yield

app = FastAPI(title="Omni-Engine Live Bridge", lifespan=lifespan)

class OmniBarData(BaseModel):
    timestamp: str 
    open: float
    high: float
    low: float
    close: float
    volume: float
    es_close: float  
    position: float 
    unrealized_pnl: float

# ==========================================
# MODULE 1: STRUCTURE
# ==========================================
def analyze_structure(df_1m, df_15m):
    if len(df_15m) < 5 or len(df_1m) < 5: return 0
    bullish_fvg = (df_15m['low'].iloc[-1] > df_15m['high'].iloc[-3])
    bearish_fvg = (df_15m['high'].iloc[-1] < df_15m['low'].iloc[-3])
    last_1m_close = df_1m['close'].iloc[-1]
    bullish_sweep = (df_1m['low'].iloc[-1] < df_1m['low'].iloc[-2]) and (last_1m_close > df_1m['low'].iloc[-2])
    bearish_sweep = (df_1m['high'].iloc[-1] > df_1m['high'].iloc[-2]) and (last_1m_close < df_1m['high'].iloc[-2])
    if bullish_sweep and bullish_fvg: return 2 
    elif bullish_sweep: return 1
    if bearish_sweep and bearish_fvg: return -2 
    elif bearish_sweep: return -1
    return 0

# ==========================================
# MODULE 2: STATISTICAL VWAP
# ==========================================
def analyze_statistics(df_1m):
    if len(df_1m) < 10: return 0
    today_str = df_1m.index[-1].strftime('%Y-%m-%d')
    session_df = df_1m.loc[today_str:]
    if len(session_df) < 5: return 0
    tp = (session_df['high'] + session_df['low'] + session_df['close']) / 3
    vwap = (tp * session_df['volume']).cumsum() / session_df['volume'].cumsum()
    variance = ((tp - vwap)**2 * session_df['volume']).cumsum() / session_df['volume'].cumsum()
    std_dev = np.sqrt(variance)
    if std_dev.iloc[-1] == 0: return 0
    z_score = (session_df['close'].iloc[-1] - vwap.iloc[-1]) / std_dev.iloc[-1]
    if z_score <= -2.5: return 1 
    elif z_score >= 2.5: return -1 
    return 0

# ==========================================
# MODULE 3: CORRELATION
# ==========================================
def analyze_correlation(df_1m):
    if len(df_1m) < 5: return 0
    es_change = df_1m['es_close'].iloc[-1] - df_1m['es_close'].iloc[-5]
    nq_change = df_1m['close'].iloc[-1] - df_1m['close'].iloc[-5]
    if es_change > 0 and nq_change < 0: return 1 
    elif es_change < 0 and nq_change > 0: return -1 
    return 0
    
# ==========================================
# MODULE 4: REGIME
# ==========================================
def analyze_regime(df_15m):
    if len(df_15m) < 10: return 1
    high_low = df_15m['high'] - df_15m['low']
    atr_15m = high_low.rolling(10).mean().iloc[-1]
    ema_20 = df_15m['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    price_dist = abs(df_15m['close'].iloc[-1] - ema_20)
    if price_dist > (atr_15m * 2.5): return 2 
    elif atr_15m > np.percentile(high_low.dropna(), 80): return 3 
    else: return 1 

# ==========================================
# PHASE 2: TRAPS & GAPS
# ==========================================
def analyze_traps(df_1m):
    if len(df_1m) < 5: return 0
    c1, c2 = df_1m.iloc[-2], df_1m.iloc[-1]
    avg_vol = df_1m['volume'].rolling(20).mean().iloc[-1]
    avg_range = (df_1m['high'] - df_1m['low']).rolling(20).mean().iloc[-1]
    if (c1['open'] - c1['close']) > (avg_range * 2) and c1['volume'] > (avg_vol * 1.5) and c2['close'] > c1['open']: return 2 
    if (c1['close'] - c1['open']) > (avg_range * 2) and c1['volume'] > (avg_vol * 1.5) and c2['close'] < c1['open']: return -2 
    return 0

def analyze_gap(df_1m):
    if len(df_1m) < 100: return 0
    current_time = df_1m.index[-1]
    yesterday = current_time - datetime.timedelta(days=1 if current_time.weekday() < 5 else 3)
    try:
        yday_df = df_1m.loc[yesterday.strftime('%Y-%m-%d')]
        settlement = yday_df.between_time('15:55', '16:00')['close'].iloc[-1]
    except: return 0 
    gap = df_1m['close'].iloc[-1] - settlement
    if gap > 50: return -1
    elif gap < -50: return 1
    return 0

def get_seasonality_gate(time_only):
    t_0930, t_0945, t_1130, t_1300, t_1500, t_1550 = datetime.time(9,30), datetime.time(9,45), datetime.time(11,30), datetime.time(13,0), datetime.time(15,0), datetime.time(15,50)
    if time_only >= t_0930 and time_only <= t_0945: return {"allow_trend": False, "allow_reversion": False, "allow_traps": True}
    elif time_only > t_1130 and time_only <= t_1300: return {"allow_trend": False, "allow_reversion": True, "allow_traps": False}
    elif time_only >= t_1500 and time_only <= t_1550: return {"allow_trend": True, "allow_reversion": False, "allow_traps": True}
    return {"allow_trend": True, "allow_reversion": True, "allow_traps": True}

# ==========================================
# PHASE 3: MASTER TRADER LOGIC
# ==========================================
def analyze_liquidity_pools(df_1m, current_time):
    global state
    if len(df_1m) < 100: return 0
    today_str = current_time.strftime('%Y-%m-%d')
    if state.pdh is None or getattr(state, 'last_pdh_update', None) != today_str:
        yesterday = current_time - datetime.timedelta(days=1 if current_time.weekday() < 5 else 3)
        yday_str = yesterday.strftime('%Y-%m-%d')
        try:
            yday_df = df_1m.loc[yday_str].between_time('09:30', '16:00')
            state.pdh = yday_df['high'].max()
            state.pdl = yday_df['low'].min()
            state.last_pdh_update = today_str
        except: pass
    if state.pdh is None or state.pdl is None: return 0
    c1, c2 = df_1m.iloc[-2], df_1m.iloc[-1]
    if c1['high'] > state.pdh and c2['close'] < state.pdh: return -2 
    if c1['low'] < state.pdl and c2['close'] > state.pdl: return 2 
    return 0

def analyze_initial_balance(df_1m, current_time):
    global state
    today_str = current_time.strftime('%Y-%m-%d')
    time_only = current_time.time()
    if state.ib_set_for_day != today_str:
        state.ib_high = None; state.ib_low = None; state.ib_set_for_day = None
    if time_only >= datetime.time(10, 30) and state.ib_set_for_day != today_str:
        try:
            ib_df = df_1m.loc[today_str].between_time('09:30', '10:30')
            state.ib_high = ib_df['high'].max()
            state.ib_low = ib_df['low'].min()
            state.ib_set_for_day = today_str
        except: pass
    if state.ib_high is None or state.ib_low is None: return 0
    current_price = df_1m['close'].iloc[-1]
    current_vol = df_1m['volume'].iloc[-1]
    avg_vol = df_1m['volume'].rolling(20).mean().iloc[-1]
    if current_price > state.ib_high and current_vol < avg_vol: return -1
    if current_price < state.ib_low and current_vol < avg_vol: return 1
    return 0

def analyze_exhaustion(df_1m):
    if len(df_1m) < 15: return 0
    highs = df_1m['high'].rolling(5).max()
    swings = df_1m[df_1m['high'] == highs]
    if len(swings) < 3: return 0
    s1, s2, s3 = swings.iloc[-3], swings.iloc[-2], swings.iloc[-1]
    if s3['high'] > s2['high'] > s1['high'] and s3['volume'] < s2['volume'] < s1['volume']: return -2 
    if s3['low'] < s2['low'] < s1['low'] and s3['volume'] < s2['volume'] < s1['volume']: return 2 
    return 0

# ==========================================
# PHASE 4: THE OMNISCIENT EYE
# ==========================================
def analyze_macro_alignment(df_60m):
    """Calculates the 60M EMA. Returns +1 if Bullish Macro, -1 if Bearish Macro."""
    if len(df_60m) < 5: return 0
    ema_10 = df_60m['close'].ewm(span=10, adjust=False).mean().iloc[-1]
    current_price = df_60m['close'].iloc[-1]
    if current_price > ema_10: return 1
    elif current_price < ema_10: return -1
    return 0

def analyze_absorption(df_1m):
    """VPA: Detects extreme effort (volume) with zero result (doji body) = Passive Limit Order Absorption"""
    if len(df_1m) < 20: return 0
    c1 = df_1m.iloc[-1]
    avg_vol = df_1m['volume'].rolling(20).mean().iloc[-1]
    avg_range = (df_1m['high'] - df_1m['low']).rolling(20).mean().iloc[-1]
    
    body = abs(c1['open'] - c1['close'])
    spread = c1['high'] - c1['low']
    
    # If volume is 3x normal, but the body is less than 20% of the spread (Doji)
    if c1['volume'] > (avg_vol * 3) and body < (spread * 0.2):
        # Determine absorption direction by where the close is relative to the range
        midpoint = (c1['high'] + c1['low']) / 2
        if c1['close'] > midpoint:
            return 2 # Massive selling effort was absorbed by passive buyers (Bullish)
        else:
            return -2 # Massive buying effort was absorbed by passive sellers (Bearish)
    return 0

def analyze_squeeze(df_15m):
    """Detects volatility compression (Bollinger Bands inside Keltner Channels)"""
    if len(df_15m) < 20: return False
    
    # Bollinger Bands
    sma_20 = df_15m['close'].rolling(20).mean()
    std_20 = df_15m['close'].rolling(20).std()
    bb_upper = sma_20 + (std_20 * 2)
    bb_lower = sma_20 - (std_20 * 2)
    
    # Keltner Channels
    atr_20 = (df_15m['high'] - df_15m['low']).rolling(20).mean()
    kc_upper = sma_20 + (atr_20 * 1.5)
    kc_lower = sma_20 - (atr_20 * 1.5)
    
    # Squeeze is ON when BB is completely inside KC
    is_sqz = (bb_upper.iloc[-1] < kc_upper.iloc[-1]) and (bb_lower.iloc[-1] > kc_lower.iloc[-1])
    return is_sqz

# ==========================================
# MASTER PREDICTION LOOP
# ==========================================
@app.post("/omni_predict")
def predict_bar(bar: OmniBarData):
    global state
    try:
        try: time_obj = pd.to_datetime(bar.timestamp[:22], format='%Y%m%d %H%M%S %f')
        except: time_obj = pd.to_datetime(bar.timestamp)
        time_only = time_obj.time()
        
        if time_only < datetime.time(9, 30) or time_only >= datetime.time(15, 55): return {"action": 0, "status": "TIME_GATE"}
            
        with state.lock:
            state.bar_history.loc[time_obj] = [bar.open, bar.high, bar.low, bar.close, bar.volume, bar.es_close]
            if len(state.bar_history) > 5000: state.bar_history = state.bar_history.iloc[-5000:] # Increased buffer for 60m chart
            if len(state.bar_history) < 60: return {"action": 0, "status": "WARMUP"}
            df_1m = state.bar_history.copy()
            
        df_15m = df_1m.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'es_close': 'last'}).dropna()
        df_60m = df_1m.resample('60min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'es_close': 'last'}).dropna()

        # Gather signals
        regime = analyze_regime(df_15m)
        struct_signal = analyze_structure(df_1m, df_15m)
        stat_signal = analyze_statistics(df_1m)
        corr_signal = analyze_correlation(df_1m)
        trap_signal = analyze_traps(df_1m)
        gap_bias = analyze_gap(df_1m)
        seasonality = get_seasonality_gate(time_only)
        liquidity_signal = analyze_liquidity_pools(df_1m, time_obj)
        ib_signal = analyze_initial_balance(df_1m, time_obj)
        exhaustion_signal = analyze_exhaustion(df_1m)
        
        # Phase 4 Omniscient Signals
        macro_alignment = analyze_macro_alignment(df_60m)
        absorption_signal = analyze_absorption(df_1m)
        is_squeezing = analyze_squeeze(df_15m)
        
        # --- THE MASTER ENSEMBLE VOTING SYSTEM ---
        final_action = 0
        
        # 0. THE MACRO VETO (Phase 4)
        # If the 60-Minute trend is aggressively down (-1), we block all minor Longs.
        macro_veto_long = (macro_alignment == -1)
        macro_veto_short = (macro_alignment == 1)

        # 1. IMMEDIATE OVERRIDES (Highest Conviction Institutional Logic)
        if absorption_signal != 0:
            return {"action": 1 if absorption_signal > 0 else -1, "status": "VPA_ABSORPTION", "tuned_grid": state.grid_distance, "tuned_target": state.profit_target}
            
        if liquidity_signal != 0:
            return {"action": 1 if liquidity_signal > 0 else -1, "status": "LIQUIDITY_SWEEP", "tuned_grid": state.grid_distance, "tuned_target": state.profit_target}
            
        if exhaustion_signal != 0:
            return {"action": 1 if exhaustion_signal > 0 else -1, "status": "EXHAUSTION_WEDGE", "tuned_grid": state.grid_distance, "tuned_target": state.profit_target}
            
        if seasonality["allow_traps"] and trap_signal != 0:
            return {"action": 1 if trap_signal > 0 else -1, "status": "TRAP_EXECUTION", "tuned_grid": state.grid_distance, "tuned_target": state.profit_target}
            
        # 2. Chop Regime / Mean Reversion
        if regime == 1 and seasonality["allow_reversion"] and not is_squeezing:
            vote_score = (struct_signal * 1.5) + (stat_signal * 2.0) + (ib_signal * 1.5) + (gap_bias * 0.5)
            if vote_score >= 2.0 and not macro_veto_long: final_action = 1 
            elif vote_score <= -2.0 and not macro_veto_short: final_action = -1 
                
        # 3. Trend Regime (or Post-Squeeze Breakout)
        elif (regime == 2 or is_squeezing) and seasonality["allow_trend"]:
            if struct_signal > 0 and corr_signal > 0 and gap_bias >= 0 and not macro_veto_long: final_action = 1
            elif struct_signal < 0 and corr_signal < 0 and gap_bias <= 0 and not macro_veto_short: final_action = -1
                
        # 4. Expansion Regime
        elif regime == 3:
            if struct_signal >= 2 and corr_signal > 0 and not macro_veto_long: final_action = 1
            if struct_signal <= -2 and corr_signal < 0 and not macro_veto_short: final_action = -1

        return {
            "action": final_action, 
            "status": "ACTIVE",
            "tuned_grid": state.grid_distance,
            "tuned_target": state.profit_target
        }
    except Exception as e:
        import traceback
        print(f"Omni-Engine Master Error: {e}\n{traceback.format_exc()}")
        return {"action": 0, "status": "ERROR"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("omni_engine:app", host="127.0.0.1", port=5001, log_level="warning", access_log=False)
