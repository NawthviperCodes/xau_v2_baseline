# telegram_notifier.py
import requests
import time
import threading
import queue

from dotenv import load_dotenv
import os

load_dotenv()  # read .env file if present


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# --- Config ---
MIN_INTERVAL = 2       # Minimum seconds between messages
MAX_RETRY_DELAY = 60   # Cap backoff at 60s

# --- Internal State ---
_message_queue = queue.Queue()
_last_sent_time = 0
_worker_running = False


def _worker():
    global _last_sent_time, _worker_running
    _worker_running = True
    while True:
        try:
            message = _message_queue.get()
            if message is None:
                break  # stop signal

            # Ensure minimum spacing
            now = time.time()
            if now - _last_sent_time < MIN_INTERVAL:
                time.sleep(MIN_INTERVAL - (now - _last_sent_time))

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": message}

            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("[Telegram] Message sent.")
                _last_sent_time = time.time()
            elif response.status_code == 429:
                # Too Many Requests → obey retry_after if provided
                data = response.json()
                retry_after = data.get("parameters", {}).get("retry_after", 10)
                retry_after = min(retry_after, MAX_RETRY_DELAY)
                print(f"[Telegram] Rate limited. Retrying after {retry_after}s")
                time.sleep(retry_after)
                # requeue message
                _message_queue.put(message)
            else:
                print(f"[Telegram ERROR] {response.text}")
        except Exception as e:
            print(f"[Telegram ERROR] {e}")
        finally:
            _message_queue.task_done()

    _worker_running = False


def send_telegram_message(message: str):
    """Queue a message for safe delivery to Telegram"""
    global _worker_running
    _message_queue.put(message)
    if not _worker_running:
        t = threading.Thread(target=_worker, daemon=True)
        t.start()


def stop_notifier():
    """Stop background worker gracefully"""
    _message_queue.put(None)
