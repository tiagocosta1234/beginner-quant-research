import pandas as pd
import numpy as np

def main():
    filepath = r'broker_hacker\live_backtest_results.csv'
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}")
        return

    print("========================================")
    print(" DEEP QUANTITATIVE TRADE ANALYSIS")
    print("========================================")

    # Clean currency columns if they exist as strings
    currency_cols = ['Profit', 'Commission', 'Cum. net profit', 'MAE', 'MFE', 'ETD']
    for col in currency_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[\$,]', '', regex=True).str.replace(r'\((.*)\)', r'-\1', regex=True), errors='coerce').fillna(0.0)
            
    # Clean Entry/Exit times
    if 'Entry time' in df.columns:
        df['Entry time'] = pd.to_datetime(df['Entry time'], dayfirst=True)
        df['DayOfWeek'] = df['Entry time'].dt.day_name()
        df['Hour'] = df['Entry time'].dt.hour
        
        # FILTER OUT MONDAYS
        df = df[df['DayOfWeek'] != 'Monday']
        
    total_trades = len(df)
    if total_trades == 0:
        print("No trades found.")
        return
        
    wins = df[df['Profit'] > 0]
    losses = df[df['Profit'] < 0]
    
    win_rate = (len(wins) / total_trades) * 100
    gross_profit = wins['Profit'].sum() if not wins.empty else 0
    gross_loss = losses['Profit'].sum() if not losses.empty else 0
    net_profit = gross_profit + gross_loss
    profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
    
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Net Profit: ${net_profit:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    print("\n--- PERFORMANCE BY DAY OF WEEK ---")
    if 'DayOfWeek' in df.columns:
        day_perf = df.groupby('DayOfWeek')['Profit'].agg(['count', 'sum', lambda x: (x>0).mean()*100])
        day_perf.columns = ['Trades', 'Net Profit', 'Win Rate %']
        # Sort by day order
        days = ['Tuesday', 'Wednesday', 'Thursday', 'Friday']
        day_perf = day_perf.reindex(days).dropna()
        print(day_perf.to_string())
        
    print("\n--- PERFORMANCE BY MONTH ---")
    if 'Entry time' in df.columns:
        df['MonthYear'] = df['Entry time'].dt.to_period('M')
        monthly_perf = df.groupby('MonthYear')['Profit'].agg(['count', 'sum'])
        monthly_perf.columns = ['Trades', 'Net Profit']
        print(monthly_perf.to_string())
        avg_month = monthly_perf['Net Profit'].mean()
        print(f"\nAverage Monthly Profit: ${avg_month:.2f}")
    
    print("\n--- MAE / MFE ANALYSIS ---")
    if 'MAE' in df.columns and 'MFE' in df.columns:
        avg_mae_win = wins['MAE'].mean() if not wins.empty else 0
        avg_mfe_win = wins['MFE'].mean() if not wins.empty else 0
        avg_mae_loss = losses['MAE'].mean() if not losses.empty else 0
        print(f"Avg Adverse Excursion (Winners): ${avg_mae_win:.2f}")
        print(f"Avg Favorable Excursion (Winners): ${avg_mfe_win:.2f}")
        print(f"Avg Adverse Excursion (Losers): ${avg_mae_loss:.2f}")
        print("Insight: This shows how much heat your winners take, and how far your losers go in profit before reversing.")
        
    print("\n========================================")

if __name__ == "__main__":
    main()
