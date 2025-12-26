import time
import logging
import os
import datetime
from flask import Flask
from db import db
from models import Watch, WatchHistory
import logic

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tabelog.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def run_check(app):
    with app.app_context():
        # Ideally we would filter in SQL, but for simplicity we iterate and filter in python
        # logic so we can check multiple at once if needed without complex scheduling
        watches = Watch.query.all()

        session = logic.get_session(proxy=os.environ.get('PROXY'))
        now = datetime.datetime.utcnow()

        for watch in watches:
            try:
                # Check if due
                if watch.last_checked_at:
                    delta = (now - watch.last_checked_at).total_seconds()
                    if delta < watch.check_interval:
                        continue

                logger.info(f"Checking watch {watch.id} (Interval: {watch.check_interval}s)")

                # Ensure we have an rst_id
                if not watch.rst_id:
                    rst_id = logic.get_rst_id(watch.tabelog_url, session)
                    if rst_id:
                        watch.rst_id = rst_id
                        db.session.commit()
                    else:
                        logger.warning(f"Could not resolve rst_id for {watch.tabelog_url}")
                        continue

                # Fetch current vacancy
                current_state = logic.fetch_vacancy(watch.rst_id, session)
                if current_state is None:
                    continue # Skip if error

                previous_state = watch.get_state()

                # Compare
                if previous_state is None:
                    # First run for this watch
                    logger.info(f"First run for watch {watch.id}")
                    watch.set_state(current_state)
                    # Don't update last_checked_at yet? No, update it so we don't spam
                    # But actually we want to start counting interval from now
                    msg = f"**Started monitoring** {watch.tabelog_url}\nFound {len(current_state)} dates."
                    logic.notify_discord(watch.webhook_url, msg)
                else:
                    changes = logic.compare_states(previous_state, current_state)
                    if changes:
                        logger.info(f"Changes detected for {watch.id}")

                        # Save History
                        history_entry = WatchHistory(watch_id=watch.id)
                        history_entry.set_details(changes)
                        db.session.add(history_entry)

                        message = f"**🔄 Status Changed!**\n{watch.tabelog_url}\n\n"
                        message += "\n".join(changes[:20])
                        if len(changes) > 20:
                            message += f"\n...and {len(changes)-20} more."

                        logic.notify_discord(watch.webhook_url, message)

                        # Update state only if changed
                        watch.set_state(current_state)
                    else:
                        pass

                # Update last checked time
                watch.last_checked_at = datetime.datetime.utcnow()
                db.session.commit()

            except Exception as e:
                logger.error(f"Error processing watch {watch.id}: {e}")

def main():
    app = create_app()
    # Run loop more frequently to catch individual intervals
    loop_interval = 10

    logger.info(f"Starting worker loop every {loop_interval}s")

    while True:
        try:
            run_check(app)
        except Exception as e:
            logger.error(f"Global worker error: {e}")

        time.sleep(loop_interval)

if __name__ == "__main__":
    main()
