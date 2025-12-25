from db import db
import datetime
import json

class Watch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tabelog_url = db.Column(db.String(500), nullable=False)
    rst_id = db.Column(db.String(50), nullable=True) # Cached ID
    webhook_url = db.Column(db.String(500), nullable=False)
    last_state = db.Column(db.Text, nullable=True) # Stored as JSON string
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    check_interval = db.Column(db.Integer, default=300) # seconds
    last_checked_at = db.Column(db.DateTime, nullable=True)

    # Relationship
    history = db.relationship('WatchHistory', backref='watch', cascade="all, delete-orphan", lazy=True)

    def set_state(self, state_dict):
        self.last_state = json.dumps(state_dict)

    def get_state(self):
        if self.last_state:
            return json.loads(self.last_state)
        return None

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    watch_id = db.Column(db.Integer, db.ForeignKey('watch.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    details = db.Column(db.Text, nullable=False) # JSON list of change strings

    def set_details(self, changes_list):
        self.details = json.dumps(changes_list)

    def get_details(self):
        if self.details:
            return json.loads(self.details)
        return []
