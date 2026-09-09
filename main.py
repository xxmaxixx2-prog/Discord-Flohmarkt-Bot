from datetime import datetime
import os
import re
import time
import bs4
from dotenv import load_dotenv
import requests

load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Speichert bereits gesendete Erinnerungsstufen: {"event_id": {"1_week", "1_day", "today"}}
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


# --- SCRAPER 1: Flohmaxx (mit Debug-Ausgaben) ---
def scrape_flohmaxx():
  events = []
  url = "https://flohmaxx.de/flohmarkt/"
  try:
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = bs4.BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")
    current_year = datetime.now().year

    print(f"🔍 [Debug] Tabellenzeilen gefunden: {len(rows)}", flush=True)

    for row in rows:
      text = row.get_text(separator=" ", strip=True)
      if "oldenburg" in text.lower():
        cols = row.find_all("td")
        if len(cols) >= 3:
          date_raw = cols[0].get_text(strip=True)
          location_raw = cols[1].get_text(separator=" ", strip=True)
          time_raw = cols[2].get_text(strip=True)

          date_match = re.search(r"(\d{2})\.(\d{2})\.", date_raw)
          if date_match:
            day, month = map(int, date_match.groups())
            event_date = datetime(current_year, month, day).date()

            clean_location = re.sub(
                r"^OLDENBURG\s*", "", location_raw, flags=re.IGNORECASE
            )

            event = {
                "id": f"flohmaxx_{event_date}_{clean_location}",
                "title": f"Flohmarkt ({clean_location})",
                "date": event_date,
                "date_str": date_raw,
                "time_str": time_raw,
                "location": f"Oldenburg - {clean_location}",
                "url": url,
            }
            events.append(event)
            print(
                f"🎯 [Debug] Event erkannt: {event['title']} am {event_date}",
                flush=True,
            )

  except Exception as e:
    print(f"❌ Fehler bei Flohmaxx: {e}", flush=True)

  print(f"📊 [Debug] Flohmaxx Gesamt-Treffer: {len(events)}", flush=True)
  return events


# --- SCRAPER 2: Schlossfloh Rastede ---
def scrape_schlossfloh():
  events = []
  url = "https://www.schlossfloh.de/termine-marktzeiten/6-schlossfloh-rastede-termine-2020.html"
  try:
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = bs4.BeautifulSoup(res.text, "html.parser")
    pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})", re.IGNORECASE)
    matches = pattern.findall(soup.get_text())

    for date_str in matches:
      day, month, year = map(int, date_str.split("."))
      event_date = datetime(year, month, day).date()

      events.append({
          "id": f"schlossfloh_{event_date}",
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
  # Normaler Live-Betrieb:
  #today = datetime.now().date()

  # Test-Betrieb (Einkommentieren, um den 11.09.2026 zu simulieren):
  today = datetime(2026, 9, 11).date()

  print(f"🔎 Starte Prüfung für heute ({today})...", flush=True)

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