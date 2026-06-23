import pandas as pd
import numpy as np

def compute_ib_features(df):
    print("Extracting Initial Balance (IB) Features...")
    
    if 'Time' in df.columns:
        df['Time'] = pd.to_datetime(df['Time'])
        df = df.set_index('Time')
    
    df['Date'] = df.index.date
    daily_records = []
    
    for date, day_df in df.groupby('Date'):
        # Initial Balance is defined as 09:30 to 10:30 EST
        ib_df = day_df.between_time('09:30', '10:30')
        if ib_df.empty or len(ib_df) < 30:
            continue
            
        after_ib_df = day_df.between_time('10:31', '16:00')
        if after_ib_df.empty:
            continue
            
        ib_high = ib_df['High'].max()
        ib_low = ib_df['Low'].min()
        
        ib_volume = ib_df['TotalVolume'].sum()
        ib_buy_vol = ib_df['BuyVolume'].sum()
        ib_sell_vol = ib_df['SellVolume'].sum()
        ib_delta = ib_buy_vol - ib_sell_vol
        
        # VWAP at exactly 10:30
        typical_price = (ib_df['High'] + ib_df['Low'] + ib_df['Close']) / 3
        vol = ib_df['TotalVolume']
        if vol.sum() > 0:
            vwap = (typical_price * vol).sum() / vol.sum()
        else:
            vwap = ib_df['Close'].iloc[-1]
            
        close_1030 = ib_df['Close'].iloc[-1]
        dist_to_vwap = close_1030 - vwap
        
        ib_range = ib_high - ib_low
        
        delta_percentage = ib_delta / ib_volume if ib_volume > 0 else 0
        
        # Overnight Context (18:00 to 09:29)
        # Handle the fact that overnight belongs to the "session"
        overnight_start = pd.Timestamp(date) - pd.Timedelta(days=1) + pd.Timedelta(hours=18)
        overnight_end = pd.Timestamp(date) + pd.Timedelta(hours=9, minutes=29)
        
        overnight_df = df.loc[overnight_start:overnight_end]
        
        if not overnight_df.empty:
            on_high = overnight_df['High'].max()
            on_low = overnight_df['Low'].min()
            on_vol = overnight_df['TotalVolume'].sum()
        else:
            on_high = ib_high
            on_low = ib_low
            on_vol = 0
            
        daily_records.append({
            'Session_Date': date,
            'IB_High': ib_high,
            'IB_Low': ib_low,
            'IB_Range': ib_range,
            'IB_Volume': ib_volume,
            'IB_Delta': ib_delta,
            'IB_Delta_Pct': delta_percentage,
            'Close_1030': close_1030,
            'Dist_To_VWAP': dist_to_vwap,
            'ON_High': on_high,
            'ON_Low': on_low,
            'ON_Vol': on_vol,
            'After_IB_Highs': after_ib_df['High'].values,
            'After_IB_Lows': after_ib_df['Low'].values,
        })
        
    return pd.DataFrame(daily_records)
