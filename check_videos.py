#!/usr/bin/env python3
# check_videos.py
# Run: python check_videos.py

import os
import json
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparse
from datetime import datetime

# CONFIG (read from environment variables)
RSS_URL = os.environ.get("CHANNEL_RSS_URL")  # e.g. https://www.youtube.com/feeds/videos.xml?channel_id=UC...
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
KEYWORD = os.environ.get("KEYWORD", "Ankit Agrawal").lower()
SEEN_FILE = "seen.json"
ENABLE_OCR = os.environ.get("ENABLE_OCR", "false").lower() == "true"

if not RSS_URL or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise SystemExit("Missing required environment variables (CHANNEL_RSS_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")

def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen(seen_set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_set), f, indent=2)

def send_telegram(text):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False
    }
    r = requests.post(send_url, data=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def fetch_rss_entries(rss_url):
    r = requests.get(rss_url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    entries = []
    for entry in soup.find_all("entry"):
        video_id = entry.find("yt:videoId").text
        title = entry.find("title").text
        link = entry.find("link")["href"]
        published = entry.find("published").text
        description_tag = entry.find("media:description")
        description = description_tag.text if description_tag else ""
        thumbnail_tag = entry.find("media:thumbnail")
        thumbnail = thumbnail_tag["url"] if thumbnail_tag else ""
        entries.append({
            "id": video_id,
            "title": title,
            "link": link,
            "published": published,
            "description": description,
            "thumbnail": thumbnail
        })
    # sort by published ascending
    entries.sort(key=lambda e: dateparse.parse(e["published"]))
    return entries

def video_matches(entry, keyword):
    text_to_search = (entry["title"] + " " + entry["description"] + " " + entry.get("thumbnail", "")).lower()
    if keyword in text_to_search:
        return True
    # Optional: thumbnail OCR could be added here (ENABLE_OCR)
    return False

def main():
    seen = load_seen()
    entries = fetch_rss_entries(RSS_URL)
    new_seen = set(seen)
    notified = []
    for e in entries:
        vid = e["id"]
        if vid in seen:
            continue
        # it's a new upload we haven't seen before
        if video_matches(e, KEYWORD):
            # send telegram message with link and basic info
            text = f"🔔 New Ankit Agrawal video detected!\n\n{e['title']}\n{e['link']}\n\nPublished: {e['published']}"
            try:
                send_telegram(text)
                print("Notified for:", vid)
            except Exception as ex:
                print("Failed to send Telegram:", ex)
        # mark as seen (so we don't process again)
        new_seen.add(vid)
        notified.append(vid)
    # save updated seen list
    save_seen(new_seen)
    print("Done. Total entries processed:", len(entries))

if __name__ == "__main__":
    main()
