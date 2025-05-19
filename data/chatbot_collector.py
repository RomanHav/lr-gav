from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import hashlib
from pathlib import Path

class Message:
    def __init__(self, user_id: str, text: str, timestamp: float):
        self.user_id = user_id
        self.text = text
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "text": self.text,
            "timestamp": self.timestamp
        }

def init_driver():
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def determine_author(span):
    try:
        parent = span.find_element(By.XPATH, "..")
        while parent:
            class_attr = parent.get_attribute("class") or ""
            if "lc-meenek" in class_attr:
                return "human"
            elif "lc-ybm78f" in class_attr:
                return "bot"
            parent = parent.find_element(By.XPATH, "..")
    except:
        pass
    return "unknown"

def monitor_chat(output_file: str, check_interval: float = 2.0):
    driver = init_driver()
    driver.get("https://www.chatbot.com/")

    print("➡️ Вручну відкрий чат (натисни віджет). Потім натисни Enter.")
    input("⏳ Натисни Enter, коли чат відкрито...")

    iframe = driver.find_element(By.ID, "chat-widget")
    driver.switch_to.frame(iframe)
    print("✅ Успішно переключено на iframe")

    seen_hashes = set()
    collected = []

    print("📡 Запуск моніторингу. Ctrl+C для завершення.")
    try:
        while True:
            linkify_spans = driver.find_elements(By.CLASS_NAME, "Linkify")
            unknown_blocks = driver.find_elements(By.CLASS_NAME, "lc-ybm78f")
            spans = linkify_spans + unknown_blocks

            for span in spans:
                try:
                    text = span.text.strip()
                    if not text:
                        continue

                    h = get_hash(text)
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)

                    author = determine_author(span)
                    msg = Message(user_id=author, text=text, timestamp=time.time())
                    collected.append(msg)
                    print(f"💬 [{author}] {text}")
                except Exception as e:
                    continue

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([m.to_dict() for m in collected], f, ensure_ascii=False, indent=2)

            time.sleep(check_interval)

    except KeyboardInterrupt:
        print(f"\n🛑 Моніторинг завершено. Повідомлень зібрано: {len(collected)}")
        driver.quit()

if __name__ == "__main__":
    monitor_chat("chatbot_messages.json")
