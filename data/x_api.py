import requests
import json
import time
import re
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# === ⚙️ Конфігурація ===
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}"}
OUTPUT_DIR = Path("x_exports")
OUTPUT_DIR.mkdir(exist_ok=True)

# === 🔍 Парсинг URL ===
def extract_tweet_id_and_username(tweet_url):
    match = re.search(r"x\.com/([^/]+)/status/(\d+)", tweet_url)
    if not match:
        print("❌ Неправильний формат посилання. Очікується https://x.com/username/status/tweet_id")
        return None, None
    username, tweet_id = match.group(1), match.group(2)
    return username, tweet_id

# === 📥 Отримання відповідей ===
def get_replies_to_tweet(conversation_id, username, limit=50):
    url = "https://api.twitter.com/2/tweets/search/recent"
    query = f"conversation_id:{conversation_id} to:{username}"
    params = {
        "query": query,
        "max_results": min(limit, 100),
        "tweet.fields": "created_at,author_id",
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        print("❌ Помилка API:", response.json())
        return []
    return response.json().get("data", [])

# === 📤 Експорт ===
def export_replies(tweet_url, limit=50):
    username, tweet_id = extract_tweet_id_and_username(tweet_url)
    if not tweet_id:
        return

    print(f"🔍 Завантаження відповідей на твіт {tweet_id} від @{username}")
    replies = get_replies_to_tweet(tweet_id, username, limit)

    messages = [
        {
            "user_id": reply["author_id"],
            "text": reply["text"],
            "timestamp": time.mktime(time.strptime(reply["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")),
        }
        for reply in replies
    ]

    filename = OUTPUT_DIR / f"replies_{username}_{tweet_id}_{int(time.time())}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)

    print(f"✅ Збережено {len(messages)} відповідей у: {filename}")

# === ▶️ Запуск з терміналу ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("⚠️ Використання: python x_reply_scraper.py https://x.com/username/status/tweet_id")
        exit(1)

    tweet_url = sys.argv[1]
    export_replies(tweet_url)
