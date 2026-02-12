import yfinance as yf
import pandas as pd
import json
import os
import time
import numpy as np
from datetime import datetime

# הגדרות
TICKERS = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO"]
DATA_DIR = "data"

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp): return obj.strftime('%Y-%m-%d %H:%M')
        if isinstance(obj, (np.int64, np.int32)): return int(obj)
        if isinstance(obj, (np.float64, np.float32)): return round(float(obj), 2)
        return super(PandasEncoder, self).default(obj)

def calculate_technical_analysis(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    df['STD'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['Close'].rolling(window=20).mean() + (df['STD'] * 2)
    df['BB_Lower'] = df['Close'].rolling(window=20).mean() - (df['STD'] * 2)
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()

    return df.fillna(0)

def analyze_stock_score(row):
    score = 50
    signals = []

    # Trend
    if row['Close'] > row['SMA200']:
        score += 20
        signals.append("📈 Uptrend")
    else:
        score -= 20
        signals.append("📉 Downtrend")

    # Cross
    if row['SMA50'] > row['SMA200']: score += 10
    
    # Momentum
    if row['RSI'] < 30:
        score += 15
        signals.append("🟢 Oversold")
    elif row['RSI'] > 70:
        score -= 15
        signals.append("🔴 Overbought")

    # Volatility / Dip
    if row['Close'] < row['BB_Lower']:
        score += 10
        signals.append("🛒 Dip Buy Zone")
    
    return max(0, min(100, score)), signals

def save_json(data, filename):
    with open(os.path.join(DATA_DIR, filename), 'w') as f:
        json.dump(data, f, cls=PandasEncoder, indent=0)

def process_market():
    rankings = []
    print("--- Starting Data Collection ---")

    for symbol in TICKERS:
        print(f"Processing {symbol}...")
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period="2y", interval="1d") # שנתיים מספיקות לניתוח טכני בסיסי
            
            if df.empty:
                print(f"No data for {symbol}")
                continue

            df = calculate_technical_analysis(df)
            df.reset_index(inplace=True)
            
            # הכנת נתונים לשמירה
            cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'SMA200', 'SMA50']
            graph_data = df[cols].tail(1000).to_dict(orient='records')
            
            latest = df.iloc[-1]
            score, signals = analyze_stock_score(latest)
            
            info = stock.info
            meta = {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "price": latest['Close'],
                "change": ((latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100,
                "score": score,
                "signals": signals,
                "rsi": latest['RSI'],
                "atr": latest['ATR'],
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            save_json({"meta": meta, "history": graph_data}, f"{symbol}_daily.json")
            rankings.append(meta)
            time.sleep(1)

        except Exception as e:
            print(f"Error on {symbol}: {e}")

    # שמירת קובץ הדירוגים
    rankings.sort(key=lambda x: x['score'], reverse=True)
    with open(os.path.join(DATA_DIR, "market_rankings.json"), 'w') as f:
        json.dump(rankings, f, cls=PandasEncoder, indent=2)
    
    print("Data collection complete.")

if __name__ == "__main__":
    process_market()
