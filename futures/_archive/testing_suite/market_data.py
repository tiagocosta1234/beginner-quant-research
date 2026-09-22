import yfinance as yf
import argparse

def get_market_data(symbol, days=5):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d")
        if df.empty:
            print(f"No data found for symbol {symbol}")
            return
        
        print(f"--- OHLCV Data for {symbol} (Last {days} Days) ---")
        print(df[['Open', 'High', 'Low', 'Close', 'Volume']].to_string())
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="NQ=F")
    parser.add_argument("--days", type=int, default=5)
    args = parser.parse_args()
    get_market_data(args.symbol, args.days)
