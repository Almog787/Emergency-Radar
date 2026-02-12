import yfinance as yf
import pandas as pd
import json
from datetime import datetime

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_nvda_intelligence():
    nvda = yf.Ticker("NVDA")
    hist = nvda.history(period="1y") # נתונים של שנה אחרונה
    
    # חישוב אינדיקטורים למסחר
    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
    hist['RSI'] = calculate_rsi(hist['Close'])
    
    latest = hist.iloc[-1]
    prev = hist.iloc[-2]

    # איסוף המידע למבנה JSON
    intel = {
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "price": round(latest['Close'], 2),
        "change_pct": round(((latest['Close'] - prev['Close']) / prev['Close']) * 100, 2),
        "technical": {
            "rsi": round(latest['RSI'], 2),
            "sma50": round(latest['SMA50'], 2),
            "sma200": round(latest['SMA200'], 2),
            "high_52w": round(hist['High'].max(), 2),
            "low_52w": round(hist['Low'].min(), 2)
        },
        "fundamental": {
            "pe_ratio": nvda.info.get("forwardPE"),
            "analyst_target": nvda.info.get("targetMeanPrice"),
            "recommendation": nvda.info.get("recommendationKey")
        },
        "news": nvda.news[:5], # 5 חדשות אחרונות
        "history": hist[['Close', 'RSI']].tail(30).to_dict(orient='list') # 30 ימים לגרף
    }
    
    with open('nvda_intel.json', 'w') as f:
        json.dump(intel, f, indent=4)

if __name__ == "__main__":
    get_nvda_intelligence()
