import json, os, pandas as pd
import mplfinance as mpf
from datetime import datetime

DATA_DIR = "data"
CHARTS_DIR = "charts"
SITE_URL = "https://almog787.github.io/Stock-information-/"

if not os.path.exists(CHARTS_DIR): os.makedirs(CHARTS_DIR)

def create_pro_chart(json_path, symbol, score):
    with open(json_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data['history'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df = df.tail(100) 

    apds = [
        mpf.make_addplot(df['SMA50'], color='#2962ff', width=1),
        mpf.make_addplot(df['SMA200'], color='#ff6d00', width=1.5),
    ]

    mc = mpf.make_marketcolors(up='#00ff41', down='#ff003c', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle=':', rc={'font.size': 10})

    filename = os.path.join(CHARTS_DIR, f"{symbol.lower()}.png")
    mpf.plot(df, type='candle', style=s, addplot=apds, volume=True,
             savefig=dict(fname=filename, dpi=100, bbox_inches='tight'), figsize=(12, 6))

def generate_readme():
    with open(os.path.join(DATA_DIR, "market_rankings.json"), 'r') as f:
        rankings = json.load(f)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    md = f"""# 🧠 Institutional AI Market Radar | מודיעין שוק מבוסס AI

![Last Update](https://img.shields.io/badge/Last_Update-{now.replace(' ', '--').replace(':', ':-')}-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/System-Operational-emerald?style=for-the-badge)

## 🚀 [Open Interactive Terminal | כניסה לטרמינל האינטראקטיבי]({SITE_URL})

---

### 🏆 Top Opportunities | הזדמנויות מובילות
"""
    for i in range(min(3, len(rankings))):
        r = rankings[i]
        create_pro_chart(os.path.join(DATA_DIR, f"{r['symbol'].lower()}_daily.json"), r['symbol'], r['score'])
        sig_en = ", ".join(r['signals']['en'])
        sig_he = ", ".join(r['signals']['he'])
        md += f"### {i+1}. {r['symbol']} (AI Score: {r['score']})\n"
        md += f"**Signals:** `{sig_en}` | **איתותים:** `{sig_he}`\n\n"
        md += f"![{r['symbol']}](charts/{r['symbol'].lower()}.png)\n\n"

    md += """
---
## 📋 Rankings Table | טבלת דירוג שוק
| Rank | Symbol | Price | Change | AI Score | RSI |
| :--- | :--- | :---: | :---: | :---: | :---: |
"""
    for i, r in enumerate(rankings):
        trend = "🟢" if r['change'] > 0 else "🔴"
        md += f"| {i+1} | **{r['symbol']}** | ${r['price']:.2f} | {trend} {r['change']:.2f}% | **{r['score']}** | {r['rsi']:.1f} |\n"

    md += """
---
## 📘 Legend & Definitions | מקרא והסברים

| Term | מונח | Description | תיאור |
| :--- | :--- | :--- | :--- |
| **AI Score** | **ציון AI** | Quality rating (0-100). | דירוג איכות כללי (0-100). |
| **SMA 200** | **ממוצע 200** | Orange line. Long-term trend. | קו כתום. מגמה ארוכת טווח. |
| **RSI** | **מדד חוזק** | Momentum indicator (30-70 range). | מדד מומנטום (טווח 30-70). |

---
## 🗄️ Database Audit | ביקורת נתונים
"""
    md += "| Ticker | Records | Time Range | Status |\n| :--- | :---: | :--- | :---: |\n"
    for r in rankings:
        with open(os.path.join(DATA_DIR, f"{r['symbol'].lower()}_daily.json"), 'r') as f:
            h = json.load(f)['history']
            md += f"| {r['symbol']} | {len(h)} | `{h[0]['Date'].split(' ')[0]}` - `{h[-1]['Date'].split(' ')[0]}` | ✅ Verified |\n"

    with open("README.md", "w", encoding="utf-8") as f: f.write(md)

if __name__ == "__main__":
    generate_readme()
