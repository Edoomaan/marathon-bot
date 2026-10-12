import os
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from monitor import compare_events
from notify import build_change_message, send_telegram_message

LOGIN_URL = "https://event.spor.istanbul/entry.aspx"
MEMBER_URL = "https://event.spor.istanbul/member.aspx"


def login(session, username, password):
    response = session.get(LOGIN_URL, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", id="form1")
    if form is None or form.select_one('input[name="txtUserPassword"]') is None:
        raise RuntimeError("Beklenen giriş formu bulunamadı.")

    action_url = urljoin(response.url, form.get("action", ""))
    target = urlparse(action_url)
    if target.scheme != "https" or target.netloc != urlparse(LOGIN_URL).netloc:
        raise RuntimeError("Giriş formunun hedef adresi beklenenden farklı.")

    payload = {
        field["name"]: field.get("value", "")
        for field in form.select('input[type="hidden"][name]')
    }
    payload.update(
        txtMailKimlikNo=username,
        txtUserPassword=password,
        btnLogin="Giriş Yap",
    )

    response = session.post(action_url, data=payload, timeout=20, allow_redirects=False)
    response.raise_for_status()

    response = session.get(MEMBER_URL, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    if soup.select_one('input[name="txtUserPassword"]') is not None:
        raise RuntimeError("Giriş tamamlanamadı; giriş formuna geri dönüldü.")

    if response.url.split("?", 1)[0].lower() != MEMBER_URL.lower():
        raise RuntimeError("Beklenen üye sayfasına ulaşılamadı.")

    titles = soup.select(".card .card-body h5:first-of-type")
    if not titles:
        raise RuntimeError(
            "Üye sayfasında beklenen etkinlikler bulunamadı. Liste boş olabilir; "
            "giriş başarısı henüz doğrulanamadı."
        )

    events = []
    for card in soup.select(".card"):
        headings = card.select(".card-body h5")
        if not headings:
            continue
        events.append({
            "title": headings[0].get_text(" ", strip=True),
            "date": headings[1].get_text(" ", strip=True) if len(headings) > 1 else "",
            "categories": [
                category.get_text(" ", strip=True)
                for category in card.select(".wrapper small")
            ],
        })
    return events


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    username = os.environ.get("SPOR_ISTANBUL_USERNAME")
    password = os.environ.get("SPOR_ISTANBUL_PASSWORD")
    if not username or not password:
        raise SystemExit(
            "SPOR_ISTANBUL_USERNAME ve SPOR_ISTANBUL_PASSWORD "
            "ortam değişkenlerini tanımlayın."
        )

    try:
        with requests.Session() as session:
            events = login(session, username, password)
        changes = compare_events(events)
        message = build_change_message(changes)
        if message is not None:
            send_telegram_message(message)
            print("Telegram bildirimi gönderildi.")
    except requests.RequestException:
        raise SystemExit("HTTP isteği başarısız oldu; bağlantıyı kontrol edin.") from None
    except RuntimeError as error:
        raise SystemExit(str(error)) from None

    print("Giriş doğrulandı. Etkinlikler:")
    for event in events:
        print(f"- {event['title']}")

    for title in changes["added"]:
        print(f"Eklenen etkinlik: {title}")
    for title in changes["removed"]:
        print(f"Kaldırılan etkinlik: {title}")

    if changes["public_runs"]:
        print("2026 Halk Koşusu listede bulundu. Kayıt durumunu siteden kontrol edin:")
        for event in changes["public_runs"]:
            print(f"- {event['title']} ({event['date']})")
        print(MEMBER_URL)
    else:
        print("Mevcut listede 2026 Halk Koşusu bulunamadı.")

    if not any(changes.values()):
        print("Referans listeye göre değişiklik yok.")


if __name__ == "__main__":
    main()
