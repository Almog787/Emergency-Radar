import yfinance as yf
import pandas as pd
import json
import os
import time
import numpy as np
from datetime import datetime

# 10 החברות הגדולות
TICKERS = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO"]
DATA_DIR = "data"

# יצירת התיקייה אם לא קיימת
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M')
        if isinstance(obj, (np.int64, np.int32, np.integer)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32, np.floating)):
            return round(float(obj), 2) # עיגול ל-2 ספרות לחסכון במקום
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
    return df.fillna(0)

def save_safe(data, filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'w') as f:
            json.dump(data, f, cls=PandasEncoder, indent=0)
        print(f"SUCCESS: Saved {filename}")
    except Exception as e:
        print(f"ERROR saving {filename}: {e}")

def process_stock(symbol):
    print(f"\n--- Starting {symbol} ---")
    
    try:
        stock = yf.Ticker(symbol)
        
        # 1. נתונים יומיים (היסטוריה מלאה)
        # ננסה למשוך, אם נכשל - נחזיר הודעת שגיאה ולא נקריס
        try:
            df_daily = stock.history(period="max", interval="1d")
            if df_daily.empty: raise Exception("No daily data returned")
            
            df_daily = get_indicators(df_daily)
            df_daily.reset_index(inplace=True)
            
            # שמירה יעילה - רק עמודות נחוצות
            daily_data = df_daily[['Date', 'Close', 'SMA200', 'RSI']].tail(5000).to_dict(orient='records') # מגביל ל-5000 ימים אחרונים למניעת עומס
        except Exception as e:
            print(f"Failed fetching Daily for {symbol}: {e}")
            daily_data = []

        # השהייה קצרה למניעת חסימה
        time.sleep(1)

        # 2. נתונים תוך-יומיים (דקות)
        try:
            # במקום 7 ימים, נבקש 5 ימים כדי להקטין עומס וסיכון ל-Timeout
            df_intra = stock.history(period="5d", interval="1m")
            
            if not df_intra.empty:
                df_intra = get_indicators(df_intra)
                df_intra.reset_index(inplace=True)
                # תיקון שם עמודת זמן
                time_col = 'Datetime' if 'Datetime' in df_intra.columns else 'Date'
                df_intra.rename(columns={time_col: 'Date'}, inplace=True)
                
                intraday_data = df_intra[['Date', 'Close', 'SMA200', 'RSI']].tail(2000).to_dict(orient='records')
            else:
                intraday_data = []
        except Exception as e:
            print(f"Failed fetching Intraday for {symbol}: {e}")
            intraday_data = []

        # 3. מטא-דאטה (מידע כללי)
        try:
            info = stock.info
            meta = {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "price": info.get("currentPrice", 0),
                "sector": info.get("sector", "N/A"),
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        except:
            meta = {"symbol": symbol, "updated": datetime.now().strftime("%Y-%m-%d %H:%M")}

        # שמירת הקבצים - רק אם יש נתונים
        if daily_data:
            save_safe({"meta": meta, "data": daily_data}, f"{symbol}_daily.json")
        
        if intraday_data:
            save_safe({"meta": meta, "data": intraday_data}, f"{symbol}_intraday.json")

    except Exception as e:
        print(f"CRITICAL FAIL on {symbol}: {e}")

# ריצה ראשית עם השהיות
if __name__ == "__main__":
    for ticker in TICKERS:
        process_stock(ticker)
        print(f"Sleeping 2s to respect API limits...")
        time.sleep(2) # השהייה קריטית בין מניות
