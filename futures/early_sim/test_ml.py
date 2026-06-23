import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Load data
df = pd.read_csv("../data/pure_orderflow_trades.csv")

# Clean
df['PnL'] = df['Profit'].replace(r'[\$,]', '', regex=True).astype(float)
df['Win'] = (df['PnL'] > 0).astype(int)

# Time features
df['Date'] = pd.to_datetime(df['Entry time'], format='mixed', dayfirst=True)
df['Hour'] = df['Date'].dt.hour
df['DayOfWeek'] = df['Date'].dt.dayofweek
df['Month'] = df['Date'].dt.month

# Categorical
df['Is_Long'] = (df['Market pos.'] == 'Long').astype(int)

# Rolling features
df['Rolling_Win_Rate_5'] = df['Win'].shift(1).rolling(5).mean().fillna(0.5)
df['Rolling_PnL_5'] = df['PnL'].shift(1).rolling(5).sum().fillna(0)

def calc_streak(series):
    streaks = []
    current_streak = 0
    for val in series:
        if val == 0: # loss
            current_streak += 1
        else:
            current_streak = 0
        streaks.append(current_streak)
    return pd.Series(streaks).shift(1).fillna(0)

df['Losing_Streak'] = calc_streak(df['Win'])

# Features
features = ['Hour', 'DayOfWeek', 'Is_Long', 'Rolling_Win_Rate_5', 'Rolling_PnL_5', 'Losing_Streak']

X = df[features]
y = df['Win']

# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
clf.fit(X_train, y_train)

preds = clf.predict(X_test)
probs = clf.predict_proba(X_test)[:, 1]

print("Accuracy:", accuracy_score(y_test, preds))
print("Classification Report:")
print(classification_report(y_test, preds))
