from flask import Flask, render_template, request, redirect, url_for
from db import db
from models import Watch
import logic
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tabelog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    watches = Watch.query.order_by(Watch.created_at.desc()).all()
    return render_template('index.html', watches=watches)

@app.route('/add', methods=['POST'])
def add_watch():
    tabelog_url = request.form.get('tabelog_url')
    webhook_url = request.form.get('webhook_url')

    if tabelog_url and webhook_url:
        # Try to resolve rst_id immediately to validate URL (optional, but good UX)
        # Note: In a real app, this might be async, but for now we do it synchronously
        session = logic.get_session()
        rst_id = logic.get_rst_id(tabelog_url, session)

        watch = Watch(
            tabelog_url=tabelog_url,
            webhook_url=webhook_url,
            rst_id=rst_id
        )
        db.session.add(watch)
        db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
