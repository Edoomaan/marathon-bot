import re
import unicodedata
from datetime import datetime

EXPECTED_TITLES = {
    "TÜRKİYE İŞ BANKASI 48. İSTANBUL MARATONU",
    "TÜRKİYE İŞ BANKASI 48. İSTANBUL MARATONU GÖNÜLLÜ",
}


def compare_events(events):
    current_titles = {event["title"] for event in events}

    return {
        "added": sorted(current_titles - EXPECTED_TITLES),
        "removed": sorted(EXPECTED_TITLES - current_titles),
        "public_runs": find_public_runs(events, year=2026),
    }


def normalize_text(text):
    text = unicodedata.normalize("NFC", text)
    text = text.translate(str.maketrans({"İ": "i", "I": "ı"})).casefold()
    return " ".join(text.split())


def find_public_runs(events, year):
    matches = []
    for event in events:
        texts = [event["title"], *event["categories"]]
        if not any(
            re.search(r"\bhalk koşusu\b", normalize_text(text)) for text in texts
        ):
            continue

        try:
            event_date = datetime.strptime(event["date"], "%d.%m.%Y")
        except ValueError:
            raise RuntimeError(
                "Halk Koşusu bulundu ancak etkinlik tarihi doğrulanamadı."
            ) from None

        if event_date.year == year:
            matches.append(event)

    return matches
