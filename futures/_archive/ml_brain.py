import pandas as pd
import numpy as np
import os

DATA_PATH = r"data_and_results\MNQ 09-26.Last.txt"
OUTPUT_PATH = r"data_and_results\MNQ_Features_Engineered.csv"

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def engineer_features():
    print("Loading raw NinjaTrader data...")
    # Format: yyyyMMdd HHmmss;Open;High;Low;Close;Volume
    df = pd.read_csv(DATA_PATH, sep=';', header=None, 
                     names=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    print(f"Loaded {len(df)} 1-minute bars.")
    
    # 1. Time Features (Killzones)
    df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S')
    df['Hour'] = df['Datetime'].dt.hour
    df['Minute'] = df['Datetime'].dt.minute
    df['TimeOfDay'] = df['Hour'] * 100 + df['Minute']
    
    print("Extracting DNA (Candle Geometry)...")
    # 2. Geometry (The Sweep Detectors)
    df['Range'] = df['High'] - df['Low']
    # Avoid division by zero
    df['Range'] = df['Range'].replace(0, 0.0001)
    
    df['Body'] = np.abs(df['Close'] - df['Open'])
    df['UpperWick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['LowerWick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    
    df['Body_Ratio'] = df['Body'] / df['Range']
    df['UpperWick_Ratio'] = df['UpperWick'] / df['Range']
    df['LowerWick_Ratio'] = df['LowerWick'] / df['Range']
    
    print("Calculating Volatility (ATR)...")
    # 3. Volatility
    df['ATR_14'] = calculate_atr(df, 14)
    
    # 4. Target Generation (What is a successful AMD Setup?)
    # A simplified label for the ML model: We want to find moments where price drops, 
    # leaves a long wick, and then surges up in the next 10 minutes (Distribution).
    df['Future_10m_High'] = df['High'].shift(-10).rolling(10).max()
    df['Future_10m_Low'] = df['Low'].shift(-10).rolling(10).min()
    
    print("Saving Engineered Features...")
    df.dropna(inplace=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Data successfully engineered and saved to {OUTPUT_PATH}")
    print("The Python Brain is now ready to begin training.")

if __name__ == "__main__":
    engineer_features()
