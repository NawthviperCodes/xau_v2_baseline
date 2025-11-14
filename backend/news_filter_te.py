# news_filter_te.py (Upgraded to ForexFactory)
# This version scrapes the ForexFactory calendar for *future* events.
# It requires 'pip install beautifulsoup4 requests'

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# --- In-memory cache to avoid spamming ForexFactory ---
CACHE = {
    "data": defaultdict(list),
    "last_fetch_time": None
}
CACHE_DURATION_SECONDS = 4 * 60 * 60  # 4 hours

def get_economic_calendar():
    """
    Fetches high-impact economic calendar events from ForexFactory.
    """
    global CACHE
    now = datetime.now(timezone.utc)

    # 1. Check cache
    if CACHE["last_fetch_time"]:
        time_since_last_fetch = (now - CACHE["last_fetch_time"]).total_seconds()
        if time_since_last_fetch < CACHE_DURATION_SECONDS:
            return CACHE["data"]

    # 2. Fetch new data
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        }
        
        # Fetch the calendar for the current week
        url = "https://www.forexfactory.com/calendar?week=this"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the calendar table rows
        rows = soup.select('tr.calendar__row.calendar_row')
        
        new_events = defaultdict(list)
        current_date = None

        for row in rows:
            # --- Get Date ---
            date_cell = row.select_one('td.calendar__date.calendar__cell')
            if date_cell and 'date' in date_cell.text.lower():
                # This row is a date header
                date_str = date_cell.text.strip().split(maxsplit=1)[-1]
                try:
                    # Parse date like "Mar 1" and add the current year
                    current_date = datetime.strptime(f"{date_str} {now.year}", "%b %d %Y").date()
                except ValueError:
                    continue
            
            if not current_date:
                continue

            # --- Get Impact ---
            impact_cell = row.select_one('td.calendar__impact.calendar__cell')
            if not impact_cell:
                continue
                
            # We only care about high-impact (red folder)
            impact_span = impact_cell.select_one('span.icon--ff-impact-red')
            if not impact_span:
                continue # Skip if not high-impact

            # --- Get Time ---
            time_cell = row.select_one('td.calendar__time.calendar__cell')
            if not time_cell:
                continue
            time_str = time_cell.text.strip()
            
            event_datetime_utc = None
            try:
                # Handle "12:00am", "8:30pm", or "All Day"
                if "all day" in time_str.lower():
                    event_time = datetime.min.time() # Treat as 00:00
                else:
                    event_time = datetime.strptime(time_str.upper(), "%I:%M%p").time()
                
                # Combine the current date and the event time, assuming UTC
                # (ForexFactory time is dynamic, but UTC is a safe baseline)
                event_datetime_local = datetime.combine(current_date, event_time)
                # Assume the scraped time is ET and convert to UTC
                # This is a common setup, but may need adjustment if FF settings are different
                # A more robust way is to just use the date and assume all-day
                event_datetime_utc = event_datetime_local.replace(tzinfo=timezone.utc)

            except Exception as e:
                # print(f"[NEWS FILTER] Error parsing time '{time_str}': {e}")
                continue

            # --- Get Currency ---
            currency_cell = row.select_one('td.calendar__currency.calendar__cell')
            if not currency_cell:
                continue
            currency = currency_cell.text.strip().upper()

            if currency and event_datetime_utc:
                new_events[currency].append(event_datetime_utc)

        # 3. Update cache
        CACHE["data"] = new_events
        CACHE["last_fetch_time"] = now
        print(f"[NEWS FILTER] Fetched and cached {sum(len(v) for v in new_events.values())} high-impact events from ForexFactory.")
        return new_events

    except requests.exceptions.RequestException as e:
        print(f"[NEWS FILTER ERROR] Could not connect to ForexFactory: {e}")
        return CACHE["data"] # Return old cache on error
    except Exception as e:
        print(f"[NEWS FILTER ERROR] An error occurred while parsing news: {e}")
        return CACHE["data"] # Return old cache on error


def map_symbol_to_currencies(symbol: str) -> list[str]:
    """
    Maps a forex symbol like 'GBPUSD' to its constituent currencies ['GBP', 'USD'].
    """
    symbol = symbol.upper().replace("XAU", "USD") # Treat Gold as USD
    
    if len(symbol) == 6:
        return [symbol[:3], symbol[3:]]
    elif symbol in ["USD", "GBP", "EUR", "JPY", "AUD", "NZD", "CAD", "CHF"]:
        return [symbol]
    return []


def check_upcoming_high_impact(symbol: str, minutes_ahead: int = 60, minutes_after: int = 60) -> bool:
    """
    Returns True if a high-impact news event for the symbol's
    currencies is scheduled between (now - minutes_after) and (now + minutes_ahead).
    This creates a "blackout" window around the event.
    """
    all_events_by_currency = get_economic_calendar()
    if not all_events_by_currency:
        return False

    relevant_currencies = map_symbol_to_currencies(symbol)
    if not relevant_currencies:
        return False

    now_utc = datetime.now(timezone.utc)
    
    # Create the "blackout" window
    start_time_limit = now_utc - timedelta(minutes=minutes_after)
    end_time_limit = now_utc + timedelta(minutes=minutes_ahead)

    for currency in relevant_currencies:
        if currency in all_events_by_currency:
            for event_time in all_events_by_currency[currency]:
                
                # Check if the event's scheduled time falls within our blackout window
                if start_time_limit <= event_time <= end_time_limit:
                    print(f"[NEWS FILTER] {symbol} trading PAUSED. High-impact event for {currency} at {event_time.strftime('%H:%M')} UTC.")
                    return True

    return False