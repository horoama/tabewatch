import argparse
import requests
import re
import json
import os
import datetime
import sys

# Mapping of availability codes
STATUS_MAP = {
    0: "× (Not Available)",
    1: "Tel (Call)",
    2: "△ (Few Left)",
    3: "Unknown(3)",
    4: "◎ (Available)"
}

def get_rst_id(url, session):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        match = re.search(r'data-rst-id="(\d+)"', response.text)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
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
            return response.json()
    except Exception as e:
        print(f"Error fetching vacancy: {e}", file=sys.stderr)
    return None

def load_state(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return {}
    return None # None indicates file didn't exist (First run)

def save_state(filepath, state):
    with open(filepath, 'w') as f:
        json.dump(state, f, indent=2)

def notify_discord(webhook_url, message):
    if not webhook_url:
        print("No webhook URL provided. Message:", message)
        return
    try:
        requests.post(webhook_url, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"Error notifying Discord: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Monitor Tabelog reservation calendar changes.")
    parser.add_argument("tabelog_url", help="URL of the Tabelog restaurant page")
    parser.add_argument("discord_webhook_url", help="Discord Webhook URL", nargs='?') # Optional for testing
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": args.tabelog_url
    })

    rst_id = get_rst_id(args.tabelog_url, session)
    if not rst_id:
        print("Could not find restaurant ID (rst_id).", file=sys.stderr)
        return

    print(f"Restaurant ID: {rst_id}")

    vacancy_data = fetch_vacancy(rst_id, session)

    current_state = {}
    if vacancy_data and 'list' in vacancy_data:
        for item in vacancy_data['list']:
            date_str = f"{item['year']}-{item['month']:02d}-{item['day']:02d}"
            current_state[date_str] = item['available']

    state_file = f"state_{rst_id}.json"
    previous_state = load_state(state_file)

    changes = []

    if previous_state is None:
        # First run
        print("First run. Saving current state.")
        save_state(state_file, current_state)
        notify_discord(args.discord_webhook_url, f"Started monitoring {args.tabelog_url}.\nFound {len(current_state)} dates.")
        return

    # Compare
    if not previous_state and current_state:
        changes.append("Calendar appeared (was empty/non-existent, now has dates).")
    elif previous_state and not current_state:
        changes.append("Calendar disappeared (was available, now empty).")
    else:
        for date, status in current_state.items():
            if date in previous_state:
                prev_status = previous_state[date]
                if prev_status != status:
                    changes.append(f"Date {date}: {STATUS_MAP.get(prev_status, prev_status)} -> {STATUS_MAP.get(status, status)}")
            # We ignore new dates appearing due to rolling window

    if changes:
        print(f"Changes detected: {len(changes)}")
        message = f"**Tabelog Calendar Change Detected**\n{args.tabelog_url}\n" + "\n".join(changes[:20]) # Limit msg size
        if len(changes) > 20:
            message += f"\n...and {len(changes)-20} more."

        notify_discord(args.discord_webhook_url, message)
        save_state(state_file, current_state)
    else:
        print("No changes detected.")
        save_state(state_file, current_state)

if __name__ == "__main__":
    main()
