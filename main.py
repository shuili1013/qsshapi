from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

app = FastAPI()

cached_data = []
last_scrape_time = 0
CACHE_DURATION = 43200

def scrape_cssh_news():
    url = "https://www.cssh.ntpc.edu.tw/p/428-1000-1.php?Lang=zh-tw"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        announcements = []
        
        rows = soup.select('table.listTB tr')
        if not rows:
             rows = soup.select('.base-tb tr')

        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3: continue

                dept_div = cells[0].select_one('.d-txt')
                department = dept_div.text.strip() if dept_div else cells[0].text.strip()

                title_container = cells[1].select_one('.mtitle a') or cells[1].select_one('a')
                if not title_container: continue
                
                title = title_container.text.strip()
                link = title_container.get('href')

                date_div = cells[2].select_one('.d-txt')
                date_text = date_div.text.strip() if date_div else cells[2].text.strip()

                announcements.append({
                    "date": date_text,
                    "department": department,
                    "title": title,
                    "link": link
                })

            except:
                continue
        
        return sorted(announcements, key=lambda x: x['date'], reverse=True)

    except Exception as e:
        print(f"Error: {e}")
        return []

@app.get("/")
def home():
    return {"message": "/news"}

@app.get("/news")
def get_news():
    global cached_data, last_scrape_time
    
    current_time = time.time()
    
    if cached_data and (current_time - last_scrape_time < CACHE_DURATION):
        return {
            "source": "cache",
            "updated_at": datetime.fromtimestamp(last_scrape_time).strftime('%Y-%m-%d %H:%M:%S'),
            "data": cached_data
        }
    
    new_data = scrape_cssh_news()
    
    if new_data:
        cached_data = new_data
        last_scrape_time = current_time
    
    return {
        "source": "live",
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data": cached_data
    }