import json
import os
import pandas as pd
import mplfinance as mpf
from datetime import datetime
import matplotlib.pyplot as plt

# הגדרות נתיבים
DATA_DIR = "data"
CHARTS_DIR = "charts"
SITE_URL = "https://almog787.github.io/Stock-information-/"

# יצירת תיקיית גרפים אם לא קיימת
if not os.path.exists(CHARTS_DIR):
    os.makedirs(CHARTS_DIR)

def generate_data_audit():
    audit_results = []
    if not os.path.exists(DATA_DIR): return []
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('_daily.json')]
    for file in files:
        file_path = os.path.join(DATA_DIR, file)
        try:
            with open(file_path, 'r') as f:
                content = json.load(f)
                history = content.get('history', [])
                if not history: continue
                df = pd.DataFrame(history)
                audit_results.append({
                    "symbol": file.split('_')[0].upper(),
                    "records": len(history),
                    "start": str(df['Date'].min()).split(' ')[0],
                    "end": str(df['Date'].max()).split(' ')[0]
                })
        except: continue
    return audit_results

def create_pro_chart(json_path, symbol, score):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data['history'])
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df_plot = df.tail(100).copy()

        apds = []
        if 'SMA50' in df_plot.columns:
            apds.append(mpf.make_addplot(df_plot['SMA50'], color='#2962ff', width=1))
        if 'SMA200' in df_plot.columns:
            apds.append(mpf.make_addplot(df_plot['SMA200'], color='#ff6d00', width=1.5))

        mc = mpf.make_marketcolors(up='#00ff41', down='#ff003c', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle=':', rc={'font.size': 10})

        # שמירה בשם קובץ באותיות קטנות תמיד
        filename = os.path.join(CHARTS_DIR, f"{symbol.lower()}.png")
        
        mpf.plot(df_plot, type='candle', style=s, addplot=apds, volume=True,
                 savefig=dict(fname=filename, dpi=100, bbox_inches='tight'), 
                 figsize=(12, 6))
        print(f"Successfully saved chart for {symbol}")
    except Exception as e:
        print(f"Failed to create chart for {symbol}: {e}")

def generate_readme():
    rankings_path = os.path.join(DATA_DIR, "market_rankings.json")
    if not os.path.exists(rankings_path): return
    with open(rankings_path, 'r') as f:
        rankings = json.load(f)
    
    audit_data = generate_data_audit()
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    md = f"""# 🧠 Institutional AI Market Radar | מודיעין שוק

![Last Update](https://img.shields.io/badge/Last_Update-{now.replace(' ', '--').replace(':', ':-')}-blue?style=for-the-badge)

## 🚀 [Access Live Terminal | כניסה לטרמינל]({SITE_URL})

---

## 🏆 Top Opportunities | הזדמנויות מסחר
"""

    for i in range(min(3, len(rankings))):
        r = rankings[i]
        symbol = r['symbol']
        json_path = os.path.join(DATA_DIR, f"{symbol.lower()}_daily.json")
        
        if os.path.exists(json_path):
            create_pro_chart(json_path, symbol, r['score'])
            # שימוש בנתיב יחסי פשוט ל-GitHub
            md += f"### {i+1}. {symbol.upper()} (Score: {r['score']})\n"
            md += f"![{symbol} Chart](charts/{symbol.lower()}.png)\n\n"

    md += """
---
## 📋 Rankings Table | טבלת דירוג
| Rank | Symbol | Price | Change | Score | RSI |
| :--- | :--- | :---: | :---: | :---: | :---: |
"""
    for i, r in enumerate(rankings):
        trend = "🟢" if r['change'] > 0 else "🔴"
        md += f"| {i+1} | **{r['symbol']}** | ${r['price']:.2f} | {trend} {r['change']:.2f}% | **{r['score']}** | {r['rsi']:.1f} |\n"

    md += f"\n---\n*Auto-generated at {now}*"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    generate_readme() # קריאה ישירה לפונקציה
