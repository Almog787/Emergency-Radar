import yfinance as yf
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime

# רשימת 10 הגדולות
TICKERS = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO"]
DATA_DIR = "data"

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M') # שמירת תאריך ושעה
        if isinstance(obj, (np.int64, np.int32, np.integer)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32, np.floating)):
            return float(obj)
        return super(PandasEncoder, self).default(obj)

def calculate_indicators(df):
    # חישוב אינדיקטורים על רזולוציה שעתית
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # SMA שעתית (50 שעות ו-200 שעות מסחר)
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def process_ticker(symbol):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    file_path = os.path.join(DATA_DIR, f"{symbol.lower()}_data.json")
    stock = yf.Ticker(symbol)
    
    # 1. טעינת נתונים קיימים
    df_old = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                old_data = json.load(f)
                df_old = pd.DataFrame(old_data['history'])
                df_old['Datetime'] = pd.to_datetime(df_old['Datetime'])
            print(f"Loaded {len(df_old)} existing hours for {symbol}")
        except:
            print(f"Starting fresh for {symbol}")

    # 2. הבאת נתונים שעתים חדשים (7 ימים אחרונים כדי למנוע חורים)
    # interval="1h" נותן נתוני פתיחה/סגירה לכל שעת מסחר
    df_new = stock.history(period="7d", interval="1h")
    
    if df_new.empty: 
        print(f"No new hourly data for {symbol}")
        return

    df_new.reset_index(inplace=True)
    # ב-yfinance נתונים שעתים מגיעים עם עמודת Datetime
    df_new['Datetime'] = pd.to_datetime(df_new['Datetime'])
    
    # 3. מיזוג ומניעת כפילויות שעתיוות
    combined_df = pd.concat([df_old, df_new]).drop_duplicates(subset=['Datetime'], keep='last')
    combined_df = combined_df.sort_values('Datetime')

    # 4. חישוב אינדיקטורים
    combined_df = calculate_indicators(combined_df)
    
    # הגבלת גודל הקובץ (למשל 5000 שעות מסחר אחרונות - בערך שנתיים)
    if len(combined_df) > 5000:
        combined_df = combined_df.tail(5000)

    latest = combined_df.iloc[-1]
    
    # הכנה לשמירה
    history_to_save = combined_df[['Datetime', 'Close', 'RSI', 'SMA50', 'SMA200']].copy()
    history_to_save['Datetime'] = history_to_save['Datetime'].dt.strftime('%Y-%m-%d %H:%M')

    output = {
        "metadata": {
            "symbol": symbol,
            "name": stock.info.get("longName", symbol),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "resolution": "1h",
            "current_price": float(latest['Close']),
            "rsi": float(latest['RSI']),
            "sma200": float(latest['SMA200'])
        },
        "history": history_to_save.to_dict(orient='records')
    }

    with open(file_path, 'w') as f:
        json.dump(output, f, cls=PandasEncoder, indent=2)
    print(f"Synced {symbol} - Total Hourly Records: {len(history_to_save)}")

if __name__ == "__main__":
    for ticker in TICKERS:
        try:
            process_ticker(ticker)
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
