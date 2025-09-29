# news_filter_te.py

import tradingeconomics as te
from datetime import datetime, timedelta
import pytz

# --- Hard-coded login (your username:password) ---
API_KEY = "nawthviper:Thabo@0727"
te.login(API_KEY)

def check_upcoming_high_impact(symbol: str, minutes_ahead: int = 60) -> bool:
    """
    Returns True if there is high-impact news for the given currency pair
    within the next X minutes.
    """
    countries = map_symbol_to_countries(symbol)
    if not countries:
        return False

    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    end_time = now + timedelta(minutes=minutes_ahead)

    for country in countries:
        try:
            events = te.getCalendarData(country=country)
        except Exception as e:
            print(f"[NEWS] Failed fetching calendar for {country}: {e}")
            continue

        for evt in events:
            date_str = evt.get("Date") or evt.get("date")
            impact = evt.get("Importance") or evt.get("Impact") or ""

            try:
                event_time = datetime.fromisoformat(date_str).replace(tzinfo=pytz.utc)
            except Exception:
                try:
                    event_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                except Exception:
                    continue

            if now <= event_time <= end_time and impact.lower().startswith("high"):
                return True

    return False


def map_symbol_to_countries(symbol: str) -> list[str]:
    """
    Map a forex symbol to one or two relevant countries.
    Extend this mapping as needed.
    """
    mapping = {
        "GBPUSD": ["united kingdom", "united states"],
        "EURUSD": ["euro area", "united states"],
        "USDJPY": ["united states", "japan"],
        "AUDUSD": ["australia", "united states"],
        "USDCAD": ["united states", "canada"],
        "USDCHF": ["united states", "switzerland"],
        "NZDUSD": ["new zealand", "united states"],
        "XAUUSD": ["united states"],  # gold mainly reacts to USD
    }
    return mapping.get(symbol.upper(), [])
