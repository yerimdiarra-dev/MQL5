# script.py
import os
import feedparser
import requests

RSS_URL = "https://www.mql5.com/en/job/rss"
LAST_FILE = "last_seen.txt"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def read_last():
    if not os.path.exists(LAST_FILE):
        return None
    with open(LAST_FILE, "r") as f:
        return f.read().strip()

def write_last(val):
    with open(LAST_FILE, "w") as f:
        f.write(val)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print("Telegram send error:", e)
        return False

def main():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("No RSS entries found.")
        return

    latest = feed.entries[0]
    link = latest.get("link", "").strip()
    title = latest.get("title", "").strip()
    pub = latest.get("published", latest.get("pubDate", ""))

    if not link:
        print("No link in latest entry.")
        return

    last = read_last()
    if last is None or last == "":
        # First run: save last but don't notify
        write_last(link)
        print("Initialized last_seen; no notification on first run.")
        return

    if link != last:
        msg = f"🚨 New MQL5 Job:\n{title}\n🔗 {link}\nPublished: {pub}"
        ok = send_telegram(msg)
        if ok:
            write_last(link)
            print("New job notified and saved.")
        else:
            print("Failed to send telegram; will retry next run.")
    else:
        print("No new job.")

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables.")
    else:
        main()
