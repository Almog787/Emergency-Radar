import yfinance as yf
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime

TICKERS = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO"]
DATA_DIR = "data"

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, (np.int64, np.int32, np.integer)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32, np.floating)):
            return float(obj)
        return super(PandasEncoder, self).default(obj)

def calculate_indicators(df):
    # חישוב RSI ו-SMA על כל המאגר המאוחד כדי לשמור על דיוק
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def process_ticker(symbol):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    file_path = os.path.join(DATA_DIR, f"{symbol.lower()}_data.json")
    stock = yf.Ticker(symbol)
    
    # 1. טעינת נתונים קיימים אם יש
    df_old = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                old_data = json.load(f)
                df_old = pd.DataFrame(old_data['history'])
                df_old['Datetime'] = pd.to_datetime(df_old['Datetime'])
            print(f"Loaded existing data for {symbol} ({len(df_old)} rows)")
        except:
            print(f"Could not load old data for {symbol}, starting fresh.")

    # 2. הבאת נתונים חדשים
    if df_old.empty:
        # הורדה מלאה אם אין קובץ
        df_new = stock.history(period="max", interval="1d")
    else:
        # הורדת רק החודש האחרון כדי לעדכן
        df_new = stock.history(period="1mo", interval="1d")

    if df_new.empty: return

    df_new.reset_index(inplace=True)
    date_col = 'Date' if 'Date' in df_new.columns else 'Datetime'
    df_new['Datetime'] = pd.to_datetime(df_new[date_col])
    
    # 3. מיזוג (Merge) ומניעת כפילויות
    # concat מחבר את הטבלאות, drop_duplicates משאיר את הגרסה החדשה ביותר של כל תאריך
    combined_df = pd.concat([df_old, df_new]).drop_duplicates(subset=['Datetime'], keep='last')
    combined_df = combined_df.sort_values('Datetime')

    # 4. חישוב מחדש של אינדיקטורים על הכל
    combined_df = calculate_indicators(combined_df)
    
    latest = combined_df.iloc[-1]
    
    # צמצום עמודות לשמירה על נפח קובץ
    history_to_save = combined_df[['Datetime', 'Close', 'RSI', 'SMA50', 'SMA200']].copy()
    history_to_save['Datetime'] = history_to_save['Datetime'].dt.strftime('%Y-%m-%d')

    output = {
        "metadata": {
            "symbol": symbol,
            "name": stock.info.get("longName", symbol),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "first_trade_date": history_to_save['Datetime'].iloc[0],
            "current_price": float(latest['Close']),
            "rsi": float(latest['RSI']),
            "sma200": float(latest['SMA200']),
            "recommendation": str(stock.info.get("recommendationKey", "hold"))
        },
        "history": history_to_save.to_dict(orient='records')
    }

    with open(file_path, 'w') as f:
        json.dump(output, f, cls=PandasEncoder, indent=2)
    print(f"Successfully synced {symbol}. Total rows: {len(history_to_save)}")

if __name__ == "__main__":
    for ticker in TICKERS:
        try:
            process_ticker(ticker)
        except Exception as e:
            print(f"Error with {ticker}: {e}")
