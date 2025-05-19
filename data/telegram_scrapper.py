import json
import time
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import User
from telethon.errors import UsernameNotOccupiedError, ChannelPrivateError, FloodWaitError
import asyncio

# === ⚙️ Конфігурація ===
api_id = 26514301  # ← заміни на свій
api_hash = '8b0a81e45f14b5282c4c3eeabe1411b4'  # ← заміни на свій
session_name = 'telegram_session'
output_dir = Path("telegram_exports")
output_dir.mkdir(exist_ok=True)

# === 📤 Форматування повідомлення ===
def get_sender_name(sender: User):
    if sender is None:
        return "Unknown"
    if getattr(sender, "bot", False):
        return f"{sender.username or 'bot'}_bot"
    return sender.username or f"{sender.first_name or ''} {sender.last_name or ''}".strip()

def message_to_dict(message):
    sender = message.sender
    return {
        "user_id": get_sender_name(sender),
        "text": message.message or "",
        "timestamp": message.date.timestamp(),
    }

# === 🚀 Основна функція ===
async def export_chat(chat_name: str, limit: int = 100):
    async with TelegramClient(session_name, api_id, api_hash) as client:
        print(f"🔍 Завантаження чату: {chat_name}")

        try:
            entity = await client.get_entity(chat_name)
        except UsernameNotOccupiedError:
            print("❌ Помилка: Користувач або чат не знайдено.")
            return
        except ChannelPrivateError:
            print("🔒 Помилка: Це приватний канал або ви не є учасником.")
            return
        except FloodWaitError as e:
            print(f"⏳ Flood wait: зачекайте {e.seconds} секунд.")
            return
        except Exception as e:
            print(f"⚠️ Невідома помилка: {e}")
            return

        messages_data = []
        count = 0

        async for message in client.iter_messages(entity, limit=limit):
            if not message.message or not message.sender:
                continue
            await message.get_sender()  # потрібен для коректного sender
            messages_data.append(message_to_dict(message))
            count += 1

        if not messages_data:
            print("⚠️ Не знайдено повідомлень для збереження.")
            return

        # За бажанням: повідомлення від найстаріших до найновіших
        messages_data.reverse()

        filename = output_dir / f"{chat_name.replace(' ', '_')}_{int(time.time())}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"messages": messages_data}, f, ensure_ascii=False, indent=2)

        print(f"✅ Збережено {count} повідомлень у: {filename}")

# === ▶️ Запуск
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("⚠️ Використання: python telegram_scraper.py chat_username або 'https://t.me/...'\n")
        sys.exit(1)

    chat_input = sys.argv[1]
    asyncio.run(export_chat(chat_input))
