import requests
import re
import datetime
import logging

# Mapping of availability codes with visual emojis
STATUS_MAP = {
    0: "❌",       # Not Available
    1: "📞",       # Call
    2: "⚠️",       # Few Left
    3: "❓",       # Unknown
    4: "⭕"        # Available
}

STATUS_TEXT_MAP = {
    0: "❌ (Full)",
    1: "📞 (Call)",
    2: "⚠️ (Few)",
    3: "❓ (Unknown)",
    4: "⭕ (Open)"
}

def get_session(proxy=None):
    session = requests.Session()
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    })
    return session

def get_rst_id(url, session):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        match = re.search(r'data-rst-id="(\d+)"', response.text)
        if match:
            return match.group(1)
    except Exception as e:
        logging.error(f"Error fetching page {url}: {e}")
    return None

def fetch_vacancy(rst_id, session):
    url = "https://tabelog.com/booking/calendar/find_vacancy_date_with_status/"
    now = datetime.datetime.now()
    svd = now.strftime("%Y%m%d")
    params = {
        "rst_id": rst_id,
        "svd": svd,
        "svt": "1900", # Default to 19:00
        "svps": "2"    # Default to 2 people
    }
    try:
        response = session.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Normalize to simple state dict
            current_state = {}
            if data and 'list' in data:
                for item in data['list']:
                    date_str = f"{item['year']}-{item['month']:02d}-{item['day']:02d}"
                    current_state[date_str] = item['available']
            return current_state
    except Exception as e:
        logging.error(f"Error fetching vacancy for {rst_id}: {e}")
    return None

def compare_states(previous_state, current_state):
    changes = []

    if previous_state is None:
        return changes # First run, no changes to report essentially (or handle outside)

    all_dates = set(current_state.keys()) | set(previous_state.keys())
    sorted_dates = sorted(list(all_dates))

    for date in sorted_dates:
        prev = previous_state.get(date)
        curr = current_state.get(date)

        if prev is None and curr is not None:
             # New date appeared
             if curr in [1, 2, 4]:
                 changes.append(f"🆕 {date}: {STATUS_MAP.get(curr)}")
        elif prev is not None and curr is None:
            # Date disappeared
            pass
        elif prev != curr:
            changes.append(f"📅 {date}: {STATUS_MAP.get(prev, prev)} ➡ {STATUS_MAP.get(curr, curr)}")

    return changes

def notify_discord(webhook_url, message):
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"content": message}, timeout=10)
    except Exception as e:
        logging.error(f"Error notifying Discord: {e}")
