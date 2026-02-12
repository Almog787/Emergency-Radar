import yfinance as yf
import pandas as pd
import json
import os
import time
import numpy as np
from datetime import datetime

TICKERS = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO"]
DATA_DIR = "data"
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp): return obj.strftime('%Y-%m-%d %H:%M')
        if isinstance(obj, (np.int64, np.int32, np.integer)): return int(obj)
        if isinstance(obj, (np.float64, np.float32, np.floating)): return round(float(obj), 2)
        return super(PandasEncoder, self).default(obj)

def calculate_manual_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    # SMA
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    return df.fillna(0)

def process_ticker(symbol):
    file_path = os.path.join(DATA_DIR, f"{symbol.lower()}_daily.json")
    stock = yf.Ticker(symbol)
    
    # 1. טעינת המאגר הקיים מהדיסק (אם קיים)
    existing_df = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                old_data = json.load(f)
                existing_df = pd.DataFrame(old_data['history'])
                existing_df['Date'] = pd.to_datetime(existing_df['Date'])
        except:
            print(f"Could not load old data for {symbol}")

    # 2. משיכת נתונים חדשים (רק החודש האחרון כדי לעדכן)
    new_data = stock.history(period="1mo", interval="1d")
    if new_data.empty: return
    new_data.reset_index(inplace=True)
    new_data['Date'] = pd.to_datetime(new_data['Date'])

    # 3. מיזוג (Merging)
    # אנחנו מחברים את הטבלאות ומוחקים כפילויות לפי תאריך
    combined_df = pd.concat([existing_df, new_data]).drop_duplicates(subset=['Date'], keep='last')
    combined_df = combined_df.sort_values('Date')

    # 4. חישוב אינדיקטורים מחדש על כל המאגר המאוחד (חובה לדיוק)
    combined_df = calculate_manual_indicators(combined_df)

    # 5. הכנת פלט
    latest = combined_df.iloc[-1]
    meta = {
        "symbol": symbol,
        "name": stock.info.get("longName", symbol),
        "price": latest['Close'],
        "score": 50, # כאן אפשר להוסיף את לוגיקת הציון
        "rsi": latest['RSI'],
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    # שמירת כל ההיסטוריה המצטברת
    history_data = combined_df[['Date', 'Close', 'SMA200', 'SMA50', 'Volume']].to_dict(orient='records')
    
    with open(file_path, 'w') as f:
        json.dump({"meta": meta, "history": history_data}, f, cls=PandasEncoder, indent=0)

if __name__ == "__main__":
    for ticker in TICKERS:
        process_ticker(ticker)
        time.sleep(2)
