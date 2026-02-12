import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime

def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ממוצעים נעים (איתותי מגמה ארוכי טווח)
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    # רצועות בולינגר (לזיהוי חריגות מחיר)
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['Close'].rolling(window=20).mean() + (df['STD'] * 2)
    df['Lower_Band'] = df['Close'].rolling(window=20).mean() - (df['STD'] * 2)
    
    return df

def update_database():
    file_name = 'nvda_full_history.json'
    ticker = "NVDA"
    stock = yf.Ticker(ticker)

    # 1. השגת נתונים חדשים
    if os.path.exists(file_name):
        # אם יש קובץ, נוריד רק את החודש האחרון כדי לעדכן
        new_data = stock.history(period="1mo", interval="1h")
        with open(file_name, 'r') as f:
            old_db = json.load(f)
            df_old = pd.DataFrame(old_db['history'])
            df_old['Datetime'] = pd.to_datetime(df_old['Datetime'])
    else:
        # פעם ראשונה - מוריד את כל ההיסטוריה היומית (מקסימום)
        new_data = stock.history(period="max", interval="1d")
        df_old = pd.DataFrame()

    # 2. מיזוג וניקוי כפילויות
    new_data.reset_index(inplace=True)
    new_data['Datetime'] = pd.to_datetime(new_data['Date'] if 'Date' in new_data else new_data['Datetime'])
    
    combined_df = pd.concat([df_old, new_data]).drop_duplicates(subset=['Datetime'], keep='last')
    combined_df = combined_df.sort_values('Datetime')

    # 3. חישוב אינדיקטורים על כל ההיסטוריה
    combined_df = calculate_indicators(combined_df)
    
    # 4. הכנת פלט
    latest = combined_df.iloc[-1]
    
    # המרה לפורמט JSON ידידותי
    history_list = combined_df.tail(2000).copy() # שומרים 2000 דגימות אחרונות כדי שהקובץ לא יחרוג מנפח סביר
    history_list['Datetime'] = history_list['Datetime'].dt.strftime('%Y-%m-%d %H:%M')
    
    output = {
        "metadata": {
            "symbol": ticker,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "current_price": round(latest['Close'], 2),
            "rsi": round(latest['RSI'], 2) if not pd.isna(latest['RSI']) else 0,
            "sma50": round(latest['SMA50'], 2) if not pd.isna(latest['SMA50']) else 0,
            "sma200": round(latest['SMA200'], 2) if not pd.isna(latest['SMA200']) else 0,
            "recommendation": stock.info.get("recommendationKey", "N/A")
        },
        "history": history_list.to_dict(orient='records')
    }

    with open(file_name, 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    update_database()
