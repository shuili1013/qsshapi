from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

app = FastAPI()

cached_data = []
last_scrape_time = 0
CACHE_DURATION = 600

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
    return {"message": "歡迎使用清水高中公告 API，請訪問 /news 取得列表，或 /content?url=... 取得內文"}

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

# --- 新增：爬取內文的 API ---
@app.get("/content")
def get_content_api(url: str = Query(..., description="公告的網址")):
    """
    輸入公告網址，回傳內文
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return {"error": "無法連線到該網址", "status_code": response.status_code}

        soup = BeautifulSoup(response.text, 'html.parser')

        # 針對 Rpage 系統抓取主要內容區塊
        # 策略：嘗試找 .mptattach (常見內容區) 或 .mpgdetail (通用詳細區)
        content_div = soup.select_one('.mptattach') or soup.select_one('.mpgdetail') or soup.select_one('.module-detail') or soup.select_one('.art-text')

        if content_div:
            # get_text 使用 separator='\n' 可以保留換行，讓排版好看一點
            text_content = content_div.get_text(separator='\n', strip=True)
            return {"url": url, "content": text_content}
        else:
            return {"error": "找不到內容區塊，可能網頁結構不同", "url": url}

    except Exception as e:
        return {"error": str(e)}