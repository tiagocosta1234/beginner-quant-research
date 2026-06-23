import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("../data/pure_orderflow_trades.csv")
df['Date'] = pd.to_datetime(df['Entry time'], format='mixed', dayfirst=True).dt.date

trade_days_df = df.copy()
trade_days_df['Date'] = pd.to_datetime(trade_days_df['Date'])

if 'PnL' not in trade_days_df.columns and 'Profit' in trade_days_df.columns:
    trade_days_df['PnL'] = trade_days_df['Profit'].replace(r'[\$,]', '', regex=True).astype(float)

daily_pnl_series = trade_days_df.groupby(trade_days_df['Date'].dt.date)['PnL'].sum().reset_index()
daily_pnl_series.columns = ['Date', 'PnL']
daily_pnl_series['Date'] = pd.to_datetime(daily_pnl_series['Date'])

daily_pnl_series['DayOfWeek'] = daily_pnl_series['Date'].dt.dayofweek
daily_pnl_series['Month'] = daily_pnl_series['Date'].dt.month

daily_pnl_series['Win'] = 0
daily_pnl_series.loc[daily_pnl_series['PnL'] > 0, 'Win'] = 1

daily_pnl_series['Rolling_Win_Rate_5'] = daily_pnl_series['Win'].shift(1).rolling(5).mean().fillna(0.5)

streaks = []
current_streak = 0
for val in daily_pnl_series['Win']:
    if val == 0:
        current_streak += 1
    else:
        current_streak = 0
    streaks.append(current_streak)
daily_pnl_series['Losing_Streak'] = pd.Series(streaks, index=daily_pnl_series.index).shift(1).fillna(0)

features = ['DayOfWeek', 'Month', 'Rolling_Win_Rate_5', 'Losing_Streak']

clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
clf.fit(daily_pnl_series[features], daily_pnl_series['Win'])

daily_pnl_series['Win_Probability'] = clf.predict_proba(daily_pnl_series[features])[:, 1]

def get_base_contracts(prob):
    if prob > 0.55:
        return 16
    elif prob < 0.45:
        return 4
    else:
        return 8

daily_pnl_series['Base_Contracts'] = daily_pnl_series['Win_Probability'].apply(get_base_contracts)

export_df = daily_pnl_series[['Date', 'Win_Probability', 'Base_Contracts']].copy()
export_df['Date'] = export_df['Date'].dt.strftime('%Y-%m-%d')
export_df.to_csv("../data/ml_predictions.csv", index=False)
print("Exported ml_predictions.csv!")
