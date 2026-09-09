from datetime import datetime
import os
import re
import time
import bs4
from dotenv import load_dotenv
import requests

load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Speichert gesendete Stufen pro Event: {"event_id": {"1_week", "1_day", "today"}}
notified_stages = {}


def send_discord_reminder(
    stage_name, title, date_str, time_str, location, source_url
):
  stage_config = {
      "1_week": {"prefix": "📅 In 1 Woche: ", "color": 3447003},  # Blau
      "1_day": {"prefix": "⏰ Morgen: ", "color": 15105570},  # Orange
      "today": {"prefix": "🚨 HEUTE: ", "color": 15158332},  # Rot
  }

  config = stage_config.get(
      stage_name, {"prefix": "📢 Flohmarkt: ", "color": 3066993}
  )

  payload = {
      "embeds": [{
          "title": f"{config['prefix']}{title}",
          "color": config["color"],
          "fields": [
              {"name": "Datum", "value": date_str, "inline": True},
              {"name": "Uhrzeit", "value": time_str, "inline": True},
              {"name": "Ort", "value": location, "inline": False},
              {"name": "Quelle", "value": source_url, "inline": False},
          ],
      }]
  }
  res = requests.post(WEBHOOK_URL, json=payload)
  return res.status_code in [200, 204]


# --- SCRAPER 1: Flohmaxx (Text-Normalisierung) ---
def scrape_flohmaxx():
  events = []
  url = "https://flohmaxx.de/flohmarkt/"
  try:
    res = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
        },
        timeout=10,
    )
    soup = bs4.BeautifulSoup(res.text, "html.parser")
    current_year = datetime.now().year

    # Entfernt Umbrüche/HTML-Lücken für robuste Regex-Erkennung
    clean_text = re.sub(r"\s+", " ", soup.get_text())

    pattern = re.compile(
        r"((?:Sa|So|Mo|Di|Mi|Do|Fr)\.?,?\s*\d{2}\.\d{2}\.?)\s+OLDENBURG\s+(.*?)\s+(\d{2}\s+bis\s+\d{2}\s+Uhr)",
        re.IGNORECASE,
    )
    matches = pattern.findall(clean_text)

    for date_raw, location, time_raw in matches:
      date_match = re.search(r"(\d{2})\.(\d{2})\.", date_raw)
      if date_match:
        day, month = map(int, date_match.groups())
        event_date = datetime(current_year, month, day).date()
        clean_location = location.strip()
        event_id = f"flohmaxx_{event_date}_{clean_location}"

        if not any(e["id"] == event_id for e in events):
          events.append({
              "id": event_id,
              "title": f"Flohmarkt ({clean_location})",
              "date": event_date,
              "date_str": date_raw,
              "time_str": time_raw,
              "location": f"Oldenburg - {clean_location}",
              "url": url,
          })
  except Exception as e:
    print(f"❌ Fehler bei Flohmaxx: {e}", flush=True)

  return events


# --- SCRAPER 2: Schlossfloh Rastede ---
def scrape_schlossfloh():
  events = []
  url = "https://www.schlossfloh.de/termine-marktzeiten/6-schlossfloh-rastede-termine-2020.html"
  try:
    res = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
        },
        timeout=10,
    )
    soup = bs4.BeautifulSoup(res.text, "html.parser")
    pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})", re.IGNORECASE)
    matches = pattern.findall(soup.get_text())

    for date_str in set(matches):
      day, month, year = map(int, date_str.split("."))
      event_date = datetime(year, month, day).date()
      event_id = f"schlossfloh_{event_date}"

      events.append({
          "id": event_id,
          "title": "Schlossfloh Rastede",
          "date": event_date,
          "date_str": date_str,
          "time_str": "Siehe Webseite",
          "location": "Rastede / Schlosspark",
          "url": url,
      })
  except Exception as e:
    print(f"❌ Fehler bei Schlossfloh: {e}", flush=True)

  return events


# --- ZENTRALER ERINNERUNGS-CHECK ---
def check_all_sources_and_notify():
  # Live-Betrieb (Aktiv):
  #today = datetime.now().date()

  # Zum Testen des 12.09.2026 den 11.09.2026 simulieren:
   today = datetime(2026, 9, 11).date()

  print(f"🔎 Starte Prüfung für Datum: {today}...", flush=True)

  all_events = []
  all_events.extend(scrape_flohmaxx())
  all_events.extend(scrape_schlossfloh())

  for event in all_events:
    event_id = event["id"]
    days_until = (event["date"] - today).days

    if event_id not in notified_stages:
      notified_stages[event_id] = set()

    stage_to_send = None
    if days_until == 7:
      stage_to_send = "1_week"
    elif days_until == 1:
      stage_to_send = "1_day"
    elif days_until == 0:
      stage_to_send = "today"

    if (
        stage_to_send
        and stage_to_send not in notified_stages[event_id]
    ):
      success = send_discord_reminder(
          stage_name=stage_to_send,
          title=event["title"],
          date_str=event["date_str"],
          time_str=event["time_str"],
          location=event["location"],
          source_url=event["url"],
      )
      if success:
        notified_stages[event_id].add(stage_to_send)
        print(
            f"✅ [{stage_to_send}] Benachrichtigung gesendet für:"
            f" {event['title']}",
            flush=True,
        )


if __name__ == "__main__":
  print("🚀 Multi-Source Flohmarkt-Erinnerer gestartet!", flush=True)
  while True:
    check_all_sources_and_notify()
    print("💤 Durchlauf beendet. Warten auf den nächsten Tag...", flush=True)
    time.sleep(86400)