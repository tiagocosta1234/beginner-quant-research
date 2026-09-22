"""
High-Precision Filter & Regime Library for CME NQ/MNQ Level 1 Futures
Designed to integrate directly with futures_engine.py.

Provides modular, vectorized and bar-by-bar filters addressing:
1. Market Regimes (Sub-diffusive chop vs trending days: ADX, KER, Variance Ratio)
2. Time-of-Day Windows (09:30-09:45 noise isolation vs 10:00-11:30 institutional expansion)
3. Volatility Filters (ATR Expansion, Dynamic Volatility Percentiles)
4. Day-of-Week Dampening (e.g. OPEX Friday compression, Wednesday macro releases)
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


# ==============================================================================
# 1. VOLATILITY & REGIME METRICS (PURE LEVEL 1 OHLCV)
# ==============================================================================

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Wilder's Average True Range (ATR)."""
    high = df['high']
    low = df['low']
    prev_close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Wilder's Smoothing
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return atr


def compute_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes Average Directional Index (ADX), +DI, and -DI.
    ADX >= 25 indicates a trending regime; ADX < 20-25 indicates sub-diffusive mean-reverting chop.
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    
    up_move = high - prev_high
    down_move = prev_low - low
    
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr = compute_atr(df, period)
    
    pos_dm_smooth = pd.Series(pos_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean()
    neg_dm_smooth = pd.Series(neg_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean()
    
    pos_di = 100.0 * (pos_dm_smooth / atr.replace(0, np.nan))
    neg_di = 100.0 * (neg_dm_smooth / atr.replace(0, np.nan))
    
    dx = 100.0 * ((pos_di - neg_di).abs() / (pos_di + neg_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean().fillna(0)
    
    return adx, pos_di.fillna(0), neg_di.fillna(0)


def compute_kaufman_efficiency_ratio(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """
    Kaufman Efficiency Ratio (KER):
    KER = Net Price Direction / Total Absolute Volatility Traveled
    KER = |Close[t] - Close[t-period]| / SUM(|Close[i] - Close[i-1]|, i=t-period..t)
    
    Interpretation on NQ:
    - KER > 0.40 - 0.50: Clean, institutional persistent trend (Breakouts succeed).
    - KER < 0.20 - 0.25: Sub-diffusive random walk / noise (Breakouts fail, Fade/Judas Sweeps succeed).
    """
    net_change = (df['close'] - df['close'].shift(period)).abs()
    bar_to_bar_change = (df['close'] - df['close'].shift(1)).abs()
    volatility_sum = bar_to_bar_change.rolling(window=period).sum()
    
    ker = net_change / volatility_sum.replace(0, np.nan)
    return ker.fillna(0)


def compute_rolling_vwap(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes Intraday Session VWAP and Standard Deviation Bands (1 and 2 STDV).
    Resets at start of each calendar day.
    """
    cum_vol = df.groupby('date')['volume'].cumsum()
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    cum_vp = df.groupby('date').apply(lambda g: (typical_price.loc[g.index] * g['volume']).cumsum()).reset_index(level=0, drop=True)
    
    vwap = cum_vp / cum_vol.replace(0, np.nan)
    
    # VWAP Variance
    cum_dev_sq = df.groupby('date').apply(
        lambda g: ((typical_price.loc[g.index] - vwap.loc[g.index])**2 * g['volume']).cumsum()
    ).reset_index(level=0, drop=True)
    
    vwap_std = np.sqrt(cum_dev_sq / cum_vol.replace(0, np.nan))
    
    return vwap, vwap + vwap_std, vwap - vwap_std


# ==============================================================================
# 2. MODULAR QUANTITATIVE FILTERS
# ==============================================================================

class FilterPipeline:
    """
    Modular filter pipeline designed to accept a raw signal series (+1, -1, 0)
    and filter out false positives while boosting expectancy and profit factor.
    """

    @staticmethod
    def apply_time_window(
        df: pd.DataFrame, 
        start_time: str = "10:00", 
        end_time: str = "11:30", 
        blackout_open: bool = True
    ) -> pd.Series:
        """
        Filters trades outside institutional prime hours.
        By default suppresses the hyper-noisy 09:30-09:59 trap window.
        """
        time_str = df.index.strftime("%H:%M")
        valid_time = (time_str >= start_time) & (time_str <= end_time)
        
        if blackout_open:
            valid_time = valid_time & ~( (time_str >= "09:30") & (time_str < "10:00") )
            
        return valid_time

    @staticmethod
    def apply_regime_switch(
        df: pd.DataFrame,
        adx_series: pd.Series,
        ker_series: pd.Series,
        mode: str = "trend",
        adx_thresh: float = 25.0,
        ker_thresh: float = 0.35
    ) -> pd.Series:
        """
        Regime switch filter:
        - mode='trend': Returns True only when market is in persistent expansion.
        - mode='mean_reversion' or 'fade': Returns True only when market is in sub-diffusive chop.
        """
        if mode == "trend":
            return (adx_series >= adx_thresh) & (ker_series >= ker_thresh)
        elif mode in ["mean_reversion", "fade", "judas"]:
            return (adx_series < adx_thresh) | (ker_series < ker_thresh)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    @staticmethod
    def apply_volatility_filter(
        df: pd.DataFrame,
        atr_series: pd.Series,
        min_atr_pts: float = 8.0,
        atr_expansion_period: int = 50,
        atr_ratio_threshold: float = 1.05
    ) -> pd.Series:
        """
        Volatility gate:
        Prevents trading during low-liquidity/dead markets (below minimum ATR),
        and optionally requires recent ATR expansion over its rolling benchmark.
        """
        rolling_baseline = atr_series.rolling(atr_expansion_period).mean()
        expansion = atr_series >= (rolling_baseline * atr_ratio_threshold)
        sufficient_vol = atr_series >= min_atr_pts
        return sufficient_vol & expansion

    @staticmethod
    def apply_day_of_week_filter(
        df: pd.DataFrame,
        allowed_days: Tuple[int, ...] = (0, 1, 2, 3), # 0: Mon, 1: Tue, 2: Wed, 3: Thu, 4: Fri
        block_friday_afternoon: bool = True
    ) -> pd.Series:
        """
        Day-of-week filter:
        - Blocks unpredictable Friday 0DTE options pin/chop.
        - Suppresses setups during illiquid Friday afternoons.
        """
        day_of_week = df.index.dayofweek
        valid_day = day_of_week.isin(allowed_days)
        
        if block_friday_afternoon:
            time_str = df.index.strftime("%H:%M")
            friday_afternoon = (day_of_week == 4) & (time_str >= "12:00")
            valid_day = valid_day & (~friday_afternoon)
            
        return valid_day

    @staticmethod
    def apply_all_filters(
        df: pd.DataFrame,
        raw_signals: pd.Series,
        strategy_type: str = "breakout", # "breakout" or "mean_reversion"
        start_time: str = "10:00",
        end_time: str = "11:30",
        adx_period: int = 14,
        adx_thresh: float = 25.0,
        ker_period: int = 10,
        ker_thresh: float = 0.35,
        min_atr_pts: float = 6.0,
        allowed_days: Tuple[int, ...] = (0, 1, 2, 3, 4),
        block_friday_pm: bool = True
    ) -> pd.Series:
        """
        Convenience orchestrator: takes raw signals (+1, -1, 0) and outputs clean signals.
        """
        adx, _, _ = compute_adx(df, period=adx_period)
        ker = compute_kaufman_efficiency_ratio(df, period=ker_period)
        atr = compute_atr(df, period=14)
        
        # 1. Time-of-day
        time_mask = FilterPipeline.apply_time_window(df, start_time, end_time, blackout_open=True)
        
        # 2. Regime
        mode = "trend" if strategy_type == "breakout" else "mean_reversion"
        regime_mask = FilterPipeline.apply_regime_switch(
            df, adx, ker, mode=mode, adx_thresh=adx_thresh, ker_thresh=ker_thresh
        )
        
        # 3. Volatility
        vol_mask = FilterPipeline.apply_volatility_filter(
            df, atr, min_atr_pts=min_atr_pts, atr_ratio_threshold=0.95
        )
        
        # 4. Day of week
        dow_mask = FilterPipeline.apply_day_of_week_filter(
            df, allowed_days=allowed_days, block_friday_afternoon=block_friday_pm
        )
        
        combined_filter = time_mask & regime_mask & vol_mask & dow_mask
        
        filtered_signals = raw_signals.copy()
        filtered_signals[~combined_filter] = 0
        return filtered_signals
