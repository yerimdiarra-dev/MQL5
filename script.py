#!/usr/bin/env python3
"""
MQL5 Job Monitor Script
Monitors MQL5 freelance RSS feed for new job postings and sends Telegram notifications
"""

import os
import sys
import time
import feedparser
import requests
from datetime import datetime
import hashlib

# Configuration
RSS_URL = "https://www.mql5.com/en/job/rss"
LAST_FILE = "last_seen.txt"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def log_message(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def read_last_seen():
    """Read the last seen job identifier from file"""
    if not os.path.exists(LAST_FILE):
        return None
    try:
        with open(LAST_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        log_message(f"Error reading last_seen file: {e}")
        return None

def write_last_seen(identifier):
    """Write the last seen job identifier to file"""
    try:
        with open(LAST_FILE, "w", encoding="utf-8") as f:
            f.write(identifier)
        log_message(f"Updated last_seen to: {identifier[:50]}...")
    except Exception as e:
        log_message(f"Error writing last_seen file: {e}")

def generate_job_id(entry):
    """Generate a unique identifier for a job entry"""
    # Use link as primary identifier, with title and published date as fallback
    link = entry.get("link", "").strip()
    if link:
        return link
    
    # Fallback to hash of title + published date
    title = entry.get("title", "").strip()
    published = entry.get("published", entry.get("pubDate", "")).strip()
    content = f"{title}|{published}"
    return hashlib.md5(content.encode()).hexdigest()

def send_telegram_message(text):
    """Send message via Telegram Bot API"""
    if not BOT_TOKEN or not CHAT_ID:
        log_message("Missing Telegram credentials")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            log_message("Telegram message sent successfully")
            return True
        else:
            log_message(f"Telegram API error: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.exceptions.Timeout:
        log_message("Telegram request timeout")
        return False
    except requests.exceptions.RequestException as e:
        log_message(f"Telegram request error: {e}")
        return False
    except Exception as e:
        log_message(f"Unexpected error sending Telegram message: {e}")
        return False

def fetch_rss_feed():
    """Fetch and parse RSS feed"""
    try:
        log_message(f"Fetching RSS feed: {RSS_URL}")
        
        # Add headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Use requests to fetch with custom headers, then parse with feedparser
        response = requests.get(RSS_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        if hasattr(feed, 'bozo') and feed.bozo:
            log_message(f"RSS feed warning: {feed.get('bozo_exception', 'Unknown parsing issue')}")
        
        if not feed.entries:
            log_message("No entries found in RSS feed")
            return None
        
        log_message(f"Found {len(feed.entries)} entries in RSS feed")
        return feed
        
    except requests.exceptions.RequestException as e:
        log_message(f"Error fetching RSS feed: {e}")
        return None
    except Exception as e:
        log_message(f"Unexpected error parsing RSS feed: {e}")
        return None

def format_job_message(entry):
    """Format job entry into Telegram message"""
    title = entry.get("title", "No title").strip()
    link = entry.get("link", "").strip()
    published = entry.get("published", entry.get("pubDate", "Unknown date")).strip()
    
    # Get description/summary if available
    description = ""
    if "summary" in entry:
        desc = entry.summary.strip()
        # Limit description length
        if len(desc) > 200:
            desc = desc[:200] + "..."
        description = f"\n\n<i>{desc}</i>"
    
    message = f"""🚨 <b>New MQL5 Job Posted!</b>

<b>{title}</b>

🔗 <a href="{link}">View Job Details</a>

📅 Published: {published}{description}

#MQL5 #FreelanceJob"""
    
    return message

def main():
    """Main monitoring function"""
    log_message("Starting MQL5 job monitor...")
    
    # Validate environment variables
    if not BOT_TOKEN:
        log_message("ERROR: TELEGRAM_BOT_TOKEN environment variable not set")
        sys.exit(1)
    
    if not CHAT_ID:
        log_message("ERROR: TELEGRAM_CHAT_ID environment variable not set")
        sys.exit(1)
    
    # Fetch RSS feed
    feed = fetch_rss_feed()
    if not feed or not feed.entries:
        log_message("No RSS entries to process")
        return
    
    # Get the most recent entry
    latest_entry = feed.entries[0]
    current_job_id = generate_job_id(latest_entry)
    
    if not current_job_id:
        log_message("Could not generate job ID for latest entry")
        return
    
    # Read last seen job ID
    last_seen_id = read_last_seen()
    
    # First run - just save the current job ID without sending notification
    if last_seen_id is None:
        write_last_seen(current_job_id)
        log_message("First run: saved current job ID, no notification sent")
        return
    
    # Check if there's a new job
    if current_job_id != last_seen_id:
        log_message("New job detected!")
        
        # Format and send notification
        message = format_job_message(latest_entry)
        
        if send_telegram_message(message):
            # Only update last_seen if notification was sent successfully
            write_last_seen(current_job_id)
            log_message("New job notification sent and last_seen updated")
        else:
            log_message("Failed to send notification - will retry next run")
    else:
        log_message("No new jobs found")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        log_message(f"Unexpected error in main: {e}")
        sys.exit(1)
