import os
import time
import socket
import struct
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SAMP_IP = os.getenv("SAMP_IP", "127.0.0.1")
SAMP_PORT = int(os.getenv("SAMP_PORT", "7777"))
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def query_samp():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        packet = b'SAMP' + socket.inet_aton(SAMP_IP) + struct.pack('H', SAMP_PORT)
        sock.sendto(packet, (SAMP_IP, SAMP_PORT))
        data, _ = sock.recvfrom(2048)
        sock.close()
        if len(data) < 11 or data[:4] != b'SAMP':
            return None
        name_len = struct.unpack('I', data[10:14])[0]
        name = data[14:14+name_len].decode('cp1251', errors='ignore')
        offset = 14 + name_len
        gm_len = struct.unpack('I', data[offset:offset+4])[0]
        gamemode = data[offset+4:offset+4+gm_len].decode('cp1251', errors='ignore')
        offset += 4 + gm_len
        lang_len = struct.unpack('I', data[offset:offset+4])[0]
        language = data[offset+4:offset+4+lang_len].decode('cp1251', errors='ignore')
        offset += 4 + lang_len
        players = struct.unpack('H', data[offset:offset+2])[0]
        max_players = struct.unpack('H', data[offset+2:offset+4])[0]
        return {"name": name, "gamemode": gamemode, "language": language, "players": players, "max_players": max_players}
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None

def send_message(chat_id, text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_updates(offset):
    try:
        r = requests.get(f"{API_URL}/getUpdates?offset={offset}&timeout=10", timeout=15)
        return r.json()
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return None

def main():
    print("Бот запущен. Ожидание команд...")
    offset = 0
    start_time = time.time()
    # Работаем 4 минуты (GitHub Actions запускает каждые 5 минут)
    while time.time() - start_time < 240:
        data = get_updates(offset)
        if data and "result" in data:
            for update in data["result"]:
                offset = update["update_id"] + 1
                if "message" not in update:
                    continue
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                if text == "/start":
                    send_message(chat_id, "Привет! Я бот мониторинга SAMP.\nНапиши /status, чтобы узнать онлайн.")
                elif text == "/status":
                    info = query_samp()
                    if info:
                        reply = (f"🎮 Сервер: {info['name']}\n"
                                 f"👥 Игроки: {info['players']}/{info['max_players']}\n"
                                 f"🗺 Режим: {info['gamemode']}\n"
                                 f"🌐 Язык: {info['language']}")
                    else:
                        reply = "❌ Не удалось подключиться к серверу."
                    send_message(chat_id, reply)
        else:
            time.sleep(3)
    print("Сессия завершена, ждём следующего запуска...")

if __name__ == "__main__":
    main()
