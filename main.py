from datetime import datetime
import os
import time
import requests

# Webhook URL aus der .env / den Umgebungsvariablen laden
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


def send_discord_reminder(
    stage_name, title, date_str, time_str, location, source_url
):
  if not WEBHOOK_URL:
    print(
        "❌ FEHLER: Keine WEBHOOK_URL in den Umgebungsvariablen/der .env"
        " gefunden!",
        flush=True,
    )
    return False

  stage_config = {
      "1_week": {"prefix": "📅 In 1 Woche: ", "color": 3447003},
      "1_day": {"prefix": "⏰ Morgen: ", "color": 15105570},
      "today": {"prefix": "🚨 HEUTE: ", "color": 15158332},
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

  try:
    res = requests.post(WEBHOOK_URL, json=payload)
    return res.status_code in [200, 204]
  except Exception as e:
    print(f"❌ Fehler beim Senden an Discord: {e}", flush=True)
    return False


def scrape_flohmaxx():
  # Hier steht deine Scraper-Logik für Flohmaxx
  return []


def scrape_schlossfloh():
  # Hier steht deine Scraper-Logik für Schlossfloh
  return []


def check_all_sources_and_notify():
  # Echter aktueller Tag im Normalbetrieb
  today = datetime.now().date()

  print(f"🔎 Starte Prüfung für Datum: {today}...", flush=True)

  all_events = []
  all_events.extend(scrape_flohmaxx())
  all_events.extend(scrape_schlossfloh())

  print(f"📊 Geholte Events von Webseiten: {len(all_events)}", flush=True)

  for event in all_events:
    days_until = (event["date"] - today).days

    stage_name = None
    if days_until == 7:
      stage_name = "1_week"
    elif days_until == 1:
      stage_name = "1_day"
    elif days_until == 0:
      stage_name = "today"

    if stage_name:
      send_discord_reminder(
          stage_name=stage_name,
          title=event["title"],
          date_str=event["date_str"],
          time_str=event["time_str"],
          location=event["location"],
          source_url=event["url"],
      )


if __name__ == "__main__":
  print("🚀 Multi-Source Flohmarkt-Erinnerer gestartet!", flush=True)

  while True:
    check_all_sources_and_notify()
    print(
        "💤 Durchlauf beendet. Warten auf den nächsten Tag...",
        flush=True,
    )
    time.sleep(86400)  # Prüft alle 24 Stunden erneut