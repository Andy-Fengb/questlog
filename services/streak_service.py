import datetime
from db import get_db

def get_streak(user_id=None):
    """Calculate streak: consecutive days with ANY habit_log entry.
    Optimized: single query, Python-side counting."""
    from flask import session
    if user_id is None:
        user_id = session.get('user_id')
    if not user_id:
        return 0

    db = get_db()
    # Fetch last 90 days of distinct log dates in one query
    cutoff = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    rows = db.execute(
        'SELECT DISTINCT date FROM habit_log WHERE user_id=? AND date>=? ORDER BY date DESC',
        (user_id, cutoff)
    ).fetchall()

    if not rows:
        return 0

    # Build set of logged dates
    logged_dates = {r['date'] for r in rows}

    # Count consecutive days backwards from today
    streak = 0
    d = datetime.date.today()
    while d.isoformat() in logged_dates:
        streak += 1
        d -= datetime.timedelta(days=1)

    return streak


def get_habit_streak(user_id, habit_id):
    """Calculate consecutive days for a specific habit.
    Optimized: single query, Python-side counting."""
    db = get_db()
    cutoff = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    rows = db.execute(
        'SELECT DISTINCT date FROM habit_log WHERE user_id=? AND habit_id=? AND date>=? ORDER BY date DESC',
        (user_id, habit_id, cutoff)
    ).fetchall()

    if not rows:
        return 0

    logged_dates = {r['date'] for r in rows}

    streak = 0
    d = datetime.date.today()
    while d.isoformat() in logged_dates:
        streak += 1
        d -= datetime.timedelta(days=1)

    return streak
