import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime

# הגדרות
JSON_FILE = "tenders_database.json"
KEYWORDS = ["רכב", "למכירה", "דירה", "מגרש", "כינוס", "מרקנטיל"]

async def scrape_government_tenders():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.mr.gov.il/tenders/Pages/SearchTenders.aspx"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] מתחיל סריקה...")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector(".ms-listviewtable", timeout=10000)
            
            tenders_elements = await page.query_selector_all("tr.ms-itmhover")
            new_found_data = []

            for row in tenders_elements:
                cells = await row.query_selector_all("td")
                if len(cells) > 5:
                    title = (await cells[2].inner_text()).strip()
                    publisher = (await cells[3].inner_text()).strip()
                    publish_date = (await cells[5].inner_text()).strip()
                    link_element = await cells[2].query_selector("a")
                    link = await link_element.get_attribute("href") if link_element else ""
                    full_link = f"https://www.mr.gov.il{link}"

                    # בדיקת רלוונטיות לפי מילות מפתח
                    if any(word in title for word in KEYWORDS):
                        new_found_data.append({
                            "id": link.split('ID=')[-1], # מזהה ייחודי מתוך הלינק
                            "title": title,
                            "publisher": publisher,
                            "publish_date": publish_date,
                            "link": full_link,
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "new"
                        })
            
            await browser.close()
            return new_found_data
        except Exception as e:
            print(f"שגיאה במהלך הסריקה: {e}")
            await browser.close()
            return []

def update_json_database(new_items):
    # 1. טעינת בסיס הנתונים הקיים
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                database = json.load(f)
            except json.JSONDecodeError:
                database = []
    else:
        database = []

    # 2. יצירת רשימת מזהים קיימים למניעת כפילויות
    existing_ids = {item['id'] for item in database}
    
    added_count = 0
    for item in new_items:
        if item['id'] not in existing_ids:
            database.append(item)
            existing_ids.add(item['id'])
            added_count += 1
            print(f"✅ מכרז חדש נוסף: {item['title']}")

    # 3. שמירה חזרה לקובץ JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    
    print(f"--- סיום תהליך: נוספו {added_count} מכרזים חדשים. סה''כ בבסיס הנתונים: {len(database)} ---")

async def main():
    scraped_data = await scrape_government_tenders()
    if scraped_data:
        update_json_database(scraped_data)
    else:
        print("לא נמצאו מכרזים חדשים או שהסריקה נכשלה.")

if __name__ == "__main__":
    asyncio.run(main())
