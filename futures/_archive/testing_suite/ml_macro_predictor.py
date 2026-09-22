import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import csv
from datetime import datetime, timedelta
import os

def build_features():
    print("Downloading macro data from Yahoo Finance...")
    # S&P 500
    sp500 = yf.download("^GSPC", start="2020-01-01", end="2026-08-30", progress=False)
    # VIX
    vix = yf.download("^VIX", start="2020-01-01", end="2026-08-30", progress=False)
    # 10 Year Yield
    tnx = yf.download("^TNX", start="2020-01-01", end="2026-08-30", progress=False)

    df = pd.DataFrame(index=sp500.index)
    
    # Feature 1: S&P 500 Daily Return
    df['SP500_Ret'] = sp500['Close'].pct_change()
    # Feature 2: S&P 500 Volatility (5-day rolling)
    df['SP500_Vol'] = df['SP500_Ret'].rolling(window=5).std()
    
    # Feature 3: VIX level and change
    df['VIX_Close'] = vix['Close']
    df['VIX_Ret'] = vix['Close'].pct_change()
    
    # Feature 4: 10Y Yield level and change
    df['TNX_Close'] = tnx['Close']
    df['TNX_Ret'] = tnx['Close'].pct_change()
    
    # Target: Next day's return direction
    # If tomorrow closes higher than today, it's Bullish (1). Else Bearish (0).
    df['Target'] = (sp500['Close'].shift(-1) > sp500['Close']).astype(int)
    
    # Drop NaNs from rolling/shifting
    df = df.dropna()
    return df

def train_model(df):
    print("Training Random Forest Classifier...")
    features = ['SP500_Ret', 'SP500_Vol', 'VIX_Close', 'VIX_Ret', 'TNX_Close', 'TNX_Ret']
    
    X = df[features]
    y = df['Target']
    
    # Split chronologically to avoid look-ahead bias during evaluation
    train_size = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
    
    model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy on Test Set (Out of Sample): {acc * 100:.2f}%")
    
    return model, features

def predict_history(model, df, features):
    print("Predicting historical daily biases...")
    predictions = {}
    
    # We will predict for every row in the dataset
    X_all = df[features]
    
    # Predict probabilities. class 1 = Bullish, class 0 = Bearish
    probs = model.predict_proba(X_all)
    
    for i in range(len(df)):
        date_str = df.index[i].strftime("%Y-%m-%d")
        
        prob_bullish = probs[i][1]
        prob_bearish = probs[i][0]
        
        if prob_bullish > 0.55:
            bias = "Bullish"
            score = prob_bullish * 100
        elif prob_bearish > 0.55:
            bias = "Bearish"
            score = prob_bearish * 100
        else:
            bias = "Neutral"
            score = max(prob_bullish, prob_bearish) * 100
            
        predictions[date_str] = {
            "Bias": bias,
            "Score": round(score, 1)
        }
        
    return predictions

def merge_and_save(predictions):
    csv_path = 'macro_history.csv'
    
    # Read existing CSV to grab ForexFactory dates
    existing_news = {}
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader) # skip header
            for row in reader:
                if len(row) >= 4:
                    existing_news[row[0]] = row[3]
                    
    # We will write out from Aug 2024 to Aug 2026 (matching the scraper)
    start_dt = datetime(2024, 8, 1)
    end_dt = datetime(2026, 8, 1)
    delta = timedelta(days=1)
    
    print(f"Writing merged data to {csv_path}...")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Bias', 'Score', 'NextRedNewsTime'])
        
        curr_dt = start_dt
        while curr_dt <= end_dt:
            date_str = curr_dt.strftime("%Y-%m-%d")
            
            # Find closest previous trading day prediction if weekend/holiday
            bias = "Neutral"
            score = 50.0
            
            # Walk backwards up to 4 days to find the last known prediction
            for offset in range(5):
                check_dt = curr_dt - timedelta(days=offset)
                check_str = check_dt.strftime("%Y-%m-%d")
                if check_str in predictions:
                    bias = predictions[check_str]["Bias"]
                    score = predictions[check_str]["Score"]
                    break
                    
            news_time = existing_news.get(date_str, "")
            writer.writerow([date_str, bias, score, news_time])
            curr_dt += delta

    print("Success! macro_history.csv is now fully populated with ML predictions and ForexFactory dates.")

if __name__ == "__main__":
    df = build_features()
    model, features = train_model(df)
    predictions = predict_history(model, df, features)
    merge_and_save(predictions)
