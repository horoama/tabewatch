import argparse
import requests
import re
import json
import os
import datetime
import sys
import time

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
        return
    try:
        requests.post(webhook_url, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"Error notifying Discord: {e}", file=sys.stderr)

def print_status_table(current_state):
    print("\n--- Current Reservation Status ---")
    if not current_state:
        print("No availability data found.")
        return

    # Sort dates
    sorted_dates = sorted(current_state.keys())

    # Simple table formatting
    header = f"{'Date':<15} | {'Status'}"
    print(header)
    print("-" * len(header))

    for date in sorted_dates:
        status_code = current_state[date]
        status_str = STATUS_TEXT_MAP.get(status_code, str(status_code))
        print(f"{date:<15} | {status_str}")
    print("----------------------------------\n")

def check_and_notify(url, webhook_url, rst_id, session):
    print(f"Checking status for {url} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    vacancy_data = fetch_vacancy(rst_id, session)

    current_state = {}
    if vacancy_data and 'list' in vacancy_data:
        for item in vacancy_data['list']:
            date_str = f"{item['year']}-{item['month']:02d}-{item['day']:02d}"
            current_state[date_str] = item['available']

    print_status_table(current_state)

    state_file = f"state_{rst_id}.json"
    previous_state = load_state(state_file)

    changes = []

    if previous_state is None:
        # First run
        print("First run. Saving current state.")
        save_state(state_file, current_state)
        msg = f"**Started monitoring** {url}\nFound {len(current_state)} dates."
        if webhook_url:
            notify_discord(webhook_url, msg)
        else:
            print(msg)
        return

    # Compare
    all_dates = set(current_state.keys()) | set(previous_state.keys())
    sorted_dates = sorted(list(all_dates))

    for date in sorted_dates:
        prev = previous_state.get(date)
        curr = current_state.get(date)

        if prev is None and curr is not None:
             # New date appeared
             # Notify if it's Available(4), Few(2), or Call(1)
             if curr in [1, 2, 4]:
                 changes.append(f"🆕 {date}: {STATUS_MAP.get(curr)}")
        elif prev is not None and curr is None:
            # Date disappeared (past?)
            pass
        elif prev != curr:
            changes.append(f"📅 {date}: {STATUS_MAP.get(prev, prev)} ➡ {STATUS_MAP.get(curr, curr)}")

    if changes:
        print(f"Changes detected: {len(changes)}")
        # Construct visual message
        message = f"**🔄 Status Changed!**\n{url}\n\n"
        message += "\n".join(changes[:20])
        if len(changes) > 20:
            message += f"\n...and {len(changes)-20} more."

        print(message) # Always print diff to console
        notify_discord(webhook_url, message)
    else:
        print("No changes detected.")

    # Always save the latest state
    save_state(state_file, current_state)

def main():
    parser = argparse.ArgumentParser(description="Monitor Tabelog reservation calendar changes.")
    parser.add_argument("tabelog_url", help="URL of the Tabelog restaurant page")
    parser.add_argument("discord_webhook_url", help="Discord Webhook URL", nargs='?')
    parser.add_argument("--interval", type=int, help="Interval in seconds for periodic checks. If not set, runs once.", default=0)
    parser.add_argument("--proxy", help="Proxy URL (e.g., http://user:pass@host:port)")

    args = parser.parse_args()

    session = requests.Session()
    if args.proxy:
        session.proxies.update({"http": args.proxy, "https": args.proxy})

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

    if args.interval > 0:
        print(f"Starting periodic monitoring every {args.interval} seconds.")
        try:
            while True:
                try:
                    check_and_notify(args.tabelog_url, args.discord_webhook_url, rst_id, session)
                except Exception as e:
                    print(f"Error during check: {e}", file=sys.stderr)

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped monitoring.")
    else:
        check_and_notify(args.tabelog_url, args.discord_webhook_url, rst_id, session)

if __name__ == "__main__":
    main()
