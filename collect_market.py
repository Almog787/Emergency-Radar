import yfinance as yf
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime

TICKERS = ["NVDA", "AAPL", "MSFT"] # צמצמנו ל-3 כדי למנוע חסימה מהירה של ה-API
DATA_DIR = "data"

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        return super(PandasEncoder, self).default(obj)

def calculate_indicators(df):
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().where(lambda x: x > 0, 0).rolling(14).mean() / -df['Close'].diff().where(lambda x: x < 0, 0).rolling(14).mean())))
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def process_ticker(symbol):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    file_path = os.path.join(DATA_DIR, f"{symbol.lower()}_intraday_data.json")
    stock = yf.Ticker(symbol)
    
    # 1. טעינת נתונים קיימים
    df_old = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                old_data = json.load(f)
                df_old = pd.DataFrame(old_data['history'])
                df_old['Datetime'] = pd.to_datetime(df_old['Datetime'])
            print(f"Loaded {len(df_old)} existing records for {symbol}")
        except:
            print(f"Starting fresh for {symbol}")

    # 2. הבאת נתונים חדשים - רזולוציית דקה (7 ימים אחרונים)
    df_new = stock.history(period="7d", interval="1m")
    
    if df_new.empty: 
        print(f"No new intraday data for {symbol}")
        # אם אין נתונים חדשים, פשוט שמור את הישן כדי לעדכן מטא-דאטה
        combined_df = df_old if not df_old.empty else pd.DataFrame()
    else:
        df_new.reset_index(inplace=True)
        df_new['Datetime'] = pd.to_datetime(df_new['Datetime'])
        
        # 3. מיזוג
        combined_df = pd.concat([df_old, df_new]).drop_duplicates(subset=['Datetime'], keep='last')
        combined_df = combined_df.sort_values('Datetime')

    if combined_df.empty: return

    # 4. חישוב אינדיקטורים
    combined_df = calculate_indicators(combined_df)
    
    # הגבלת גודל הקובץ (20,000 רשומות אחרונות)
    if len(combined_df) > 20000:
        combined_df = combined_df.tail(20000)

    latest = combined_df.iloc[-1]
    
    history_to_save = combined_df[['Datetime', 'Close', 'RSI', 'SMA200']].copy()
    history_to_save['Datetime'] = history_to_save['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    output = {
        "metadata": {
            "symbol": symbol,
            "name": stock.info.get("longName", symbol),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "resolution": "1m",
            "current_price": float(latest['Close']),
            "rsi": float(latest['RSI'])
        },
        "history": history_to_save.to_dict(orient='records')
    }

    with open(file_path, 'w') as f:
        json.dump(output, f, cls=PandasEncoder, indent=2)
    print(f"Synced {symbol} - Total Intraday Records: {len(history_to_save)}")

if __name__ == "__main__":
    for ticker in TICKERS:
        try:
            process_ticker(ticker)
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
