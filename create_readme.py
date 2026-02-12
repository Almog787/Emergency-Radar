import json
import os
import pandas as pd
import mplfinance as mpf
from datetime import datetime

DATA_DIR = "data"
CHARTS_DIR = "charts"
SITE_URL = "https://almog787.github.io/Stock-information-/"

if not os.path.exists(CHARTS_DIR): os.makedirs(CHARTS_DIR)

def get_file_size(file_path):
    size_bytes = os.path.getsize(file_path)
    return f"{size_bytes / 1024:.1f} KB"

def generate_data_audit():
    """סורק את קבצי ה-JSON ומפיק דוח סטטיסטי על המאגר"""
    audit_results = []
    
    # חיפוש כל קבצי הנתונים בתיקייה
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('_daily.json')]
    
    for file in files:
        file_path = os.path.join(DATA_DIR, file)
        with open(file_path, 'r') as f:
            content = json.load(f)
            history = content.get('history', [])
            meta = content.get('meta', {})
            
            if not history: continue
            
            df = pd.DataFrame(history)
            
            audit_results.append({
                "symbol": meta.get('symbol', file.split('_')[0].upper()),
                "records": len(history),
                "start_date": df['Date'].min(),
                "end_date": df['Date'].max(),
                "file_size": get_file_size(file_path),
                "total_vol": f"{df['Volume'].sum() / 1e9:.2f}B shares"
            })
    
    return audit_results

def create_pro_chart(json_path, symbol, score):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['history'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df = df.tail(120)

    apds = [
        mpf.make_addplot(df['EMA_50'], color='#2962ff', width=1.5),
        mpf.make_addplot(df['EMA_200'], color='#ff6d00', width=1.5),
    ]

    market_style = mpf.make_mpf_style(
        base_mpf_style='nightclouds', 
        marketcolors=mpf.make_marketcolors(up='#00ff41', down='#ff003c', edge='inherit', wick='inherit', volume='in'),
        gridstyle=':', 
        rc={'axes.edgecolor': '#333', 'font.size': 10}
    )

    filename = f"{CHARTS_DIR}/{symbol}.png"
    mpf.plot(df, type='candle', style=market_style, addplot=apds, volume=True,
             savefig=dict(fname=filename, dpi=100, bbox_inches='tight'), figsize=(12, 6))

def generate_markdown():
    # 1. קריאת הדירוגים
    rankings_path = os.path.join(DATA_DIR, "market_rankings.json")
    with open(rankings_path, 'r') as f:
        rankings = json.load(f)
    
    # 2. הרצת ביקורת נתונים
    audit_data = generate_data_audit()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    md = f"""# 🧠 Institutional AI Market Radar
**Powered by `pandas-ta` & `mplfinance`**

## 🚀 [Access Live Terminal]({SITE_URL})

> **System Status:** 🟢 Online | **Last Scan:** {now}

## 📊 Top 3 Asset Analysis (Candlestick View)
"""
    
    for i in range(3):
        if i < len(rankings):
            r = rankings[i]
            json_path = os.path.join(DATA_DIR, f"{r['symbol']}_daily.json")
            if os.path.exists(json_path):
                create_pro_chart(json_path, r['symbol'], r['score'])
                signals = ", ".join(r['signals']) if r['signals'] else "Neutral Trend"
                md += f"### {i+1}. {r['symbol']} (Score: {r['score']})\n"
                md += f"> **Signals:** {signals}\n\n"
                md += f"![{r['symbol']} Analysis](charts/{r['symbol']}.png)\n\n"

    md += """## 📋 Full Market Intelligence
| Rank | Asset | Price | Change | AI Score | Trend (ADX) | RSI |
| :--: | :---- | :---: | :----: | :------: | :---------: | :--: |
"""
    for i, r in enumerate(rankings):
        trend = "🟢" if r['change'] > 0 else "🔴"
        adx_str = "Strong" if r['adx'] > 25 else "Weak"
        md += f"| {i+1} | **{r['symbol']}** | ${r['price']:.2f} | {trend} {r['change']:.2f}% | **{r['score']}** | {adx_str} | {r['rsi']:.1f} |\n"

    # --- הוספת חלק התיעוד החדש ---
    md += f"""
## 🗄️ Database Audit & Data Integrity
**Cumulative Metadata across local JSON storage.**

| Ticker | Records | Time Period Covered | DB Size | Total Traded Vol (Dataset) |
| :--- | :---: | :--- | :---: | :--- |
"""
    for a in sorted(audit_data, key=lambda x: x['records'], reverse=True):
        md += f"| {a['symbol']} | {a['records']} | `{a['start_date']}` to `{a['end_date']}` | {a['file_size']} | {a['total_vol']} |\n"

    md += f"\n\n---\n*Audit performed by scanning `{DATA_DIR}/` storage. Total records synced: {sum(x['records'] for x in audit_data)}*"
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("README.md updated with Data Audit.")

if __name__ == "__main__":
    generate_markdown()
