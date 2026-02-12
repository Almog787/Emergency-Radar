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
        if isinstance(obj, (np.int64, np.int32)): return int(obj)
        if isinstance(obj, (np.float64, np.float32)): return round(float(obj), 2)
        return super(PandasEncoder, self).default(obj)

def get_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # SMA
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    return df.fillna(0)

def save_file(data, filename):
    with open(os.path.join(DATA_DIR, filename), 'w') as f:
        json.dump(data, f, cls=PandasEncoder, indent=0)

def process_stock(symbol):
    print(f"Processing {symbol}...")
    try:
        stock = yf.Ticker(symbol)
        
        # 1. נתונים יומיים (Daily) - היסטוריה מלאה
        df_daily = stock.history(period="max", interval="1d")
        if not df_daily.empty:
            df_daily = get_indicators(df_daily)
            df_daily.reset_index(inplace=True)
            # שומרים OHLCV לגרף נרות
            cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'RSI', 'SMA200', 'SMA50']
            daily_data = df_daily[cols].tail(3000).to_dict(orient='records')
        else:
            daily_data = []

        # 2. נתונים תוך-יומיים (Intraday) - 60 דקות (שנתיים אחרונות)
        # שימוש ב-60m נותן היסטוריה ארוכה יותר מ-1m ועדיין מאפשר ניתוח תוך יומי
        df_intra = stock.history(period="2y", interval="60m")
        if not df_intra.empty:
            df_intra = get_indicators(df_intra)
            df_intra.reset_index(inplace=True)
            col_date = 'Datetime' if 'Datetime' in df_intra.columns else 'Date'
            df_intra.rename(columns={col_date: 'Date'}, inplace=True)
            
            cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'RSI', 'SMA200']
            intraday_data = df_intra[cols].tail(1000).to_dict(orient='records')
        else:
            intraday_data = []

        # מטא-דאטה
        info = stock.info
        meta = {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice", 0),
            "change": info.get("regularMarketChangePercent", 0) * 100,
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        if daily_data: save_file({"meta": meta, "data": daily_data}, f"{symbol}_daily.json")
        if intraday_data: save_file({"meta": meta, "data": intraday_data}, f"{symbol}_intraday.json")

    except Exception as e:
        print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    for ticker in TICKERS:
        process_stock(ticker)
        time.sleep(2)
