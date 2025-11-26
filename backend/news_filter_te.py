# news_filter_te.py (Threaded / Non-Blocking ForexFactory High-Impact News Filter)

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import threading
import time

# === Shared State for Threading ===
_NEWS_CACHE = {
    "data": defaultdict(list),
    "last_update": None,
    "lock": threading.Lock()
}

UPDATE_INTERVAL = 4 * 3600  # 4 hours


# ======================================================
# 🔄 BACKGROUND WORKER
# ======================================================
def _fetch_worker():
    """Background worker: refreshes calendar every 4 hours."""
    while True:
        try:
            print("[NewsThread] Fetching fresh calendar data...")
            fresh_data = _scrape_forex_factory()
            if fresh_data:
                with _NEWS_CACHE["lock"]:
                    _NEWS_CACHE["data"] = fresh_data
                    _NEWS_CACHE["last_update"] = datetime.now(timezone.utc)

            print(f"[NewsThread] Updated. Events: "
                  f"{sum(len(v) for v in fresh_data.values())}")

        except Exception as e:
            print(f"[NewsThread] ERROR: {e}")

        time.sleep(UPDATE_INTERVAL)


def start_news_thread():
    """Starts the background thread automatically."""
    t = threading.Thread(target=_fetch_worker, daemon=True)
    t.start()
    print("[NewsThread] Background news service started.")


# ======================================================
# 📰 SCRAPER LOGIC
# ======================================================
def _scrape_forex_factory():
    """
    Scrapes ONLY high-impact (red) events for THIS week.
    Returns dict: { 'USD': [datetime1, datetime2], 'GBP': [...], ... }
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://www.forexfactory.com/calendar?week=this"

        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, 'html.parser')
        rows = soup.select('tr.calendar__row.calendar_row')

        new_events = defaultdict(list)
        now = datetime.now(timezone.utc)
        curr_date = None

        for row in rows:
            # --- Detect date row --------------------------------
            date_cell = row.select_one('td.calendar__date.calendar__cell')
            if date_cell and 'date' in date_cell.text.lower():
                ds = date_cell.text.strip().split(maxsplit=1)[-1]
                try:
                    curr_date = datetime.strptime(f"{ds} {now.year}",
                                                  "%b %d %Y").date()
                except:
                    continue

            if not curr_date:
                continue

            # --- Filter only RED impact events -------------------
            impact = row.select_one('span.icon--ff-impact-red')
            if not impact:
                continue

            # --- Time Extract -----------------------------------
            time_cell = row.select_one('td.calendar__time.calendar__cell')
            t_str = time_cell.text.strip()
            try:
                if "all day" in t_str.lower():
                    t_obj = datetime.min.time()
                else:
                    t_obj = datetime.strptime(t_str.upper(),
                                              "%I:%M%p").time()

                dt_local = datetime.combine(curr_date, t_obj)
                dt_utc = dt_local.replace(tzinfo=timezone.utc)

            except:
                continue

            # --- Currency Extract -------------------------------
            curr_cell = row.select_one('td.calendar__currency.calendar__cell')
            if curr_cell:
                curr = curr_cell.text.strip().upper()
                if curr:
                    new_events[curr].append(dt_utc)

        return new_events

    except Exception as e:
        print(f"[NewsThread] SCRAPER ERROR: {e}")
        return None


# ======================================================
# 🧩 SYMBOL MAPPING
# ======================================================
def map_symbol_to_currencies(symbol):
    s = symbol.upper().replace("XAU", "USD")  # Gold = USD pairing assumption

    if len(s) == 6:
        return [s[:3], s[3:]]
    return [s]


# ======================================================
# 🚫 NEWS BLACKOUT CHECK (Instant lookup)
# ======================================================
def check_upcoming_high_impact(symbol, minutes_ahead=60, minutes_after=10):
    """
    Instantly checks cached high-impact events for a blackout window.
    Returns True = DO NOT TRADE
    """
    with _NEWS_CACHE["lock"]:
        events_data = _NEWS_CACHE["data"]

    if not events_data:
        return False

    currencies = map_symbol_to_currencies(symbol)
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes_after)
    end = now + timedelta(minutes=minutes_ahead)

    for c in currencies:
        if c in events_data:
            for ev in events_data[c]:
                if start <= ev <= end:
                    print(f"[NEWS FILTER] Blackout {symbol}. "
                          f"{c} news @ {ev.isoformat()}")
                    return True

    return False
