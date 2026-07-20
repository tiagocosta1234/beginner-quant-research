import os
import glob
import random
import pandas as pd
from data_engine import load_ninjatrader_csv

def prepare_data():
    print("Gathering all raw data files...")
    potential_files = glob.glob(os.path.join('raw_exports', 'MNQ *.txt'))
    if os.path.exists('MNQ 06-25.Last.txt'):
        potential_files.append('MNQ 06-25.Last.txt')
        
    potential_files = sorted(list(set(potential_files)))
    
    df_list = []
    for data_file in potential_files:
        df_raw = load_ninjatrader_csv(data_file)
        if not df_raw.empty:
            df_list.append(df_raw)
            
    df_massive = pd.concat(df_list)
    df_massive = df_massive[~df_massive.index.duplicated(keep='last')].sort_index()
    
    total_rows = len(df_massive)
    print(f"Total raw ticks available: {total_rows:,}")
    
    slice_size = 300000
    if total_rows > slice_size:
        start_idx = random.randint(0, total_rows - slice_size)
        df_sliced = df_massive.iloc[start_idx : start_idx + slice_size].copy()
        print(f"🎲 Randomly sliced {slice_size:,} ticks starting at index {start_idx}.")
    else:
        df_sliced = df_massive.copy()
        print(f"Using all {total_rows:,} ticks (less than {slice_size:,}).")
        
    out_path = os.path.join('raw_exports', 'random_300k.csv')
    
    # Save back to NinjaTrader-like CSV format: Timestamp;Open;High;Low;Close;Volume
    df_sliced.reset_index(inplace=True)
    df_sliced['time'] = df_sliced['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_sliced.to_csv(out_path, sep=';', header=False, index=False, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    
    print(f"✅ Saved to {out_path}")

if __name__ == "__main__":
    prepare_data()
