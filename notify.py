import os

import requests


def build_change_message(changes):
    if not any(changes.values()):
        return None

    lines = ["Spor İstanbul etkinlik listesinde değişiklik var."]

    for title in changes["added"]:
        lines.append(f"Eklenen: {title}")

    for title in changes["removed"]:
        lines.append(f"Kaldırılan: {title}")

    for event in changes["public_runs"]:
        lines.append(
            f"Halk Koşusu bulundu: {event['title']} ({event['date']})"
        )

    lines.append("https://event.spor.istanbul/member.aspx")
    return "\n".join(lines)


def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID tanımlanmalı."
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": message},
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError(
            "Telegram isteği başarısız oldu; mesajın teslimi doğrulanamadı."
        ) from None

    if not result.get("ok"):
        raise RuntimeError("Telegram mesaj gönderimini onaylamadı.")
