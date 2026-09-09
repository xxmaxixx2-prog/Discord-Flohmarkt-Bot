import re
import bs4
import requests

# Deine kopierte Webhook-URL hier einfügen:
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"


def fetch_and_send():
  url = "https://flohmaxx.de/flohmarkt/"
  response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
  soup = bs4.BeautifulSoup(response.text, "html.parser")

  pattern = re.compile(
      r"(Sa\.|So\.),\s*(\d{2}\.\d{2}\.)\s+Oldenburg\s+(.*?)\s+(\d{2})\s+bis\s+(\d{2})\s+Uhr",
      re.IGNORECASE,
  )
  matches = pattern.findall(soup.get_text())

  for match in matches:
    day_name, date_str, location, start_h, end_h = match

    # Erstellt die Discord Embed-Nachricht
    payload = {
        "embeds": [{
            "title": f"🛒 Flohmarkt Oldenburg ({location.strip()})",
            "color": 3066993,  # Grün
            "fields": [
                {
                    "name": "Datum",
                    "value": f"{day_name} {date_str}",
                    "inline": True,
                },
                {
                    "name": "Uhrzeit",
                    "value": f"{start_h}:00 - {end_h}:00 Uhr",
                    "inline": True,
                },
                {
                    "name": "Quelle",
                    "value": "https://flohmaxx.de/flohmarkt/",
                    "inline": False,
                },
            ],
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)


if __name__ == "__main__":
  fetch_and_send()