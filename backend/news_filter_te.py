# news_filter_te.py (Corrected to use the proper Polygon.io Tickers API for events)

import os
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

# Get the API key you stored
API_KEY = os.getenv("POLYGON_API_KEY")

# --- In-memory cache to avoid spamming the API ---
CACHE = {
    "data": [],
    "last_fetch_time": None
}
CACHE_DURATION_SECONDS = 6 * 60 * 60  # 6 hours

def get_economic_calendar():
    """
    Fetches economic calendar data from Polygon.io using the correct
    v2/reference/news endpoint, and then filters for economic events.
    """
    now = datetime.now(timezone.utc)

    # 1. Check cache
    if CACHE["last_fetch_time"]:
        time_since_last_fetch = (now - CACHE["last_fetch_time"]).total_seconds()
        if time_since_last_fetch < CACHE_DURATION_SECONDS:
            return CACHE["data"]

    # 2. Fetch new data
    if not API_KEY:
        print("[NEWS FILTER] POLYGON_API_KEY not found in .env file. News filter is disabled.")
        return []

    try:
        # CORRECTED ENDPOINT: This is the general news endpoint. We will filter it.
        # It fetches the most recent 100 news articles.
        url = f"https://api.polygon.io/v2/reference/news?limit=100&apiKey={API_KEY}"

        response = requests.get(url)
        response.raise_for_status()
        
        all_news = response.json().get("results", [])

        # --- Filter for actual economic events ---
        # We identify economic events by looking for keywords in the title.
        economic_keywords = ['cpi', 'ppi', 'gdp', 'unemployment', 'interest rate', 'fed', 'ecb', 'boj', 'boe', 'fomc', 'inflation']
        
        economic_events = []
        for article in all_news:
            title = article.get("title", "").lower()
            if any(keyword in title for keyword in economic_keywords):
                # We need to manually assign impact based on keywords
                if "interest rate" in title or "fomc" in title or "fed" in title:
                    article['impact'] = 'high'
                elif "cpi" in title or "gdp" in title or "unemployment" in title:
                    article['impact'] = 'high'
                else:
                    article['impact'] = 'medium'
                economic_events.append(article)
        
        # 3. Update cache
        CACHE["data"] = economic_events
        CACHE["last_fetch_time"] = now
        print(f"[NEWS FILTER] Fetched {len(all_news)} articles, filtered to {len(economic_events)} economic events from Polygon.io.")
        return economic_events

    except requests.exceptions.HTTPError as http_err:
        print(f"[NEWS FILTER ERROR] HTTP error occurred: {http_err} - Check your Polygon.io API key and subscription.")
        return []
    except Exception as e:
        print(f"[NEWS FILTER ERROR] An error occurred while fetching news: {e}")
        return []


def map_symbol_to_tickers(symbol: str) -> list[str]:
    """
    Maps a forex symbol to the ticker format Polygon.io uses (e.g., C:GBPUSD).
    """
    return [f"C:{symbol.upper()}"]


def check_upcoming_high_impact(symbol: str, minutes_ahead: int = 60) -> bool:
    """
    Returns True if a high-impact news event related to the symbol is found.
    """
    all_events = get_economic_calendar()
    if not all_events:
        return False

    relevant_tickers = map_symbol_to_tickers(symbol)
    if not relevant_tickers:
        return False

    now_utc = datetime.now(timezone.utc)
    time_limit = now_utc + timedelta(minutes=minutes_ahead)

    for event in all_events:
        # Check for high impact and if the symbol is related to the event
        if event.get("impact") == "high":
            event_tickers = event.get("tickers", [])
            is_relevant = any(ticker in event_tickers for ticker in relevant_tickers)

            if is_relevant:
                try:
                    event_time_str = event.get("published_utc")
                    event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))

                    if now_utc <= event_time <= time_limit:
                        print(f"[NEWS ALERT] High impact event '{event.get('title')}' may affect {symbol}. Pausing trades.")
                        return True

                except (ValueError, TypeError):
                    continue

    return False

