import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

DATA_DIR = "data"
CHARTS_DIR = "charts"
SITE_URL = "https://almog787.github.io/Stock-information-/" # הקישור לאתר שלך

if not os.path.exists(CHARTS_DIR): os.makedirs(CHARTS_DIR)

def create_chart(json_path, symbol, score):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # טעינת נתונים לגרף (לוקחים את ה-200 ימים האחרונים לתצוגה ברורה)
    df = pd.DataFrame(data['history'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.tail(200) 
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # קו מחיר וקו ממוצע
    ax.plot(df['Date'], df['Close'], label='Price', color='#00ff41', linewidth=1.5)
    ax.plot(df['Date'], df['SMA200'], label='SMA 200', color='#ff003c', linestyle='--', linewidth=1)
    
    ax.set_title(f"{symbol} | AI Score: {score}/100", color='white', fontweight='bold')
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax.grid(True, color='#333', linestyle=':', linewidth=0.5)
    
    # הסרת מסגרות
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(f"{CHARTS_DIR}/{symbol}.png", dpi=100)
    plt.close()

def generate_readme():
    rankings_path = os.path.join(DATA_DIR, "market_rankings.json")
    if not os.path.exists(rankings_path): return

    with open(rankings_path, 'r') as f:
        rankings = json.load(f)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    # --- בניית ה-README ---
    md = f"""# 📊 Market AI Radar
**Automated Financial Intelligence System**

## 🚀 [Click Here to Open Live Interactive Terminal]({SITE_URL})

> 🕒 **Last System Update:** {now}

---

## 🏆 Top Opportunities (Live Charts)
"""
    
    for i in range(min(3, len(rankings))):
        r = rankings[i]
        json_path = os.path.join(DATA_DIR, f"{r['symbol'].lower()}_daily.json")
        if os.path.exists(json_path):
            create_chart(json_path, r['symbol'], r['score'])
            md += f"### {i+1}. {r['symbol']} (Score: {r['score']})\n![{r['symbol']}](charts/{r['symbol']}.png)\n\n"

    md += """## 📋 Full Market Rankings
| Rank | Ticker | Price | Change | Score | Trend | RSI |
| :--: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    
    for i, r in enumerate(rankings):
        trend_icon = "🟢 Up" if r['change'] > 0 else "🔴 Down"
        score_icon = "🔥" if r['score'] >= 80 else ("❄️" if r['score'] <= 30 else "⚖️")
        md += f"| {i+1} | **{r['symbol']}** | ${r['price']:.2f} | {r['change']:.2f}% | {score_icon} **{r['score']}** | {trend_icon} | {r['rsi']:.1f} |\n"

    # --- חלק ההסברים החדש ---
    md += """
---
## 📘 Legend & Definitions (מקרא והסברים)

### 🧠 AI Score (0-100)
ציון משוקלל שנותן האלגוריתם למניה.
*   **80-100 (Strong Buy):** המניה במגמת עלייה חזקה או במצב מכירת יתר קיצוני (הזדמנות).
*   **0-30 (Sell/Avoid):** המניה במגמת ירידה או במצב קניית יתר קיצוני (סיכון).
*   **40-60 (Hold):** אין כיוון מובהק.

### 📉 RSI (Relative Strength Index)
מדד המומנטום (0 עד 100).
*   **מתחת ל-30:** "מכירת יתר" (Oversold) - המחיר ירד מהר מדי, ייתכן תיקון למעלה.
*   **מעל 70:** "קניית יתר" (Overbought) - המחיר עלה מהר מדי, ייתכן תיקון למטה.

### 🟠 SMA 200 (Simple Moving Average)
הממוצע של המחיר ב-200 הימים האחרונים.
*   **מחיר מעל הקו:** מגמה חיובית ארוכת טווח (Bullish).
*   **מחיר מתחת לקו:** מגמה שלילית (Bearish).

### 📡 System Status
*   **Update Frequency:** Every 15 minutes during US market hours.
*   **Data Source:** yfinance (Yahoo Finance API).
*   **History:** Full historical data maintained incrementally.

---
*Data generated automatically by GitHub Actions.*
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    generate_readme()
