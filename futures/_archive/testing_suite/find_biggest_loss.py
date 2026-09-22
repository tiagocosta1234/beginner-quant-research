import pandas as pd

def load_and_clean(filepath, symbol):
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        return pd.DataFrame()

    if 'Profit' in df.columns:
        df['Profit'] = pd.to_numeric(df['Profit'].astype(str).str.replace(r'[\$,]', '', regex=True).str.replace(r'\((.*)\)', r'-\1', regex=True), errors='coerce').fillna(0.0)
            
    if 'Entry time' in df.columns:
        df['Entry time'] = pd.to_datetime(df['Entry time'], dayfirst=True)
        # Use only the date part for daily aggregation
        df['Date'] = df['Entry time'].dt.date
        df['DayOfWeek'] = df['Entry time'].dt.day_name()
        df = df[df['DayOfWeek'] != 'Monday'].copy()
        
    df['Symbol'] = symbol
    return df

def main():
    mnq_filepath = r'broker_hacker\live_backtest_results.csv'
    mgc_filepath = r'broker_hacker\mgc_live_backtest_results.csv'
    
    df_mnq = load_and_clean(mnq_filepath, 'MNQ')
    df_mgc = load_and_clean(mgc_filepath, 'MGC')
    
    df = pd.concat([df_mnq, df_mgc], ignore_index=True)
    
    if df.empty:
        print("No data.")
        return
        
    daily_pnl = df.groupby('Date')['Profit'].sum()
    biggest_loss_date = daily_pnl.idxmin()
    biggest_loss_amount = daily_pnl.min()
    
    print(f"PORTFOLIO Biggest Losing Day: {biggest_loss_date} | Loss: ${biggest_loss_amount:.2f}")
    
    if not df_mnq.empty:
        mnq_daily = df_mnq.groupby('Date')['Profit'].sum()
        mnq_date = mnq_daily.idxmin()
        mnq_amount = mnq_daily.min()
        print(f"MNQ Only Biggest Losing Day: {mnq_date} | Loss: ${mnq_amount:.2f}")
        
    if not df_mgc.empty:
        mgc_daily = df_mgc.groupby('Date')['Profit'].sum()
        mgc_date = mgc_daily.idxmin()
        mgc_amount = mgc_daily.min()
        print(f"MGC Only Biggest Losing Day: {mgc_date} | Loss: ${mgc_amount:.2f}")

if __name__ == "__main__":
    main()
