from db import get_db

def get_total_xp(user_id=None):
    db = get_db()
    # If no user_id, use session default
    if user_id is None:
        from flask import session
        user_id = session.get('user_id')
    if not user_id:
        return 0
    row = db.execute('SELECT total_xp FROM user_xp WHERE user_id=?', (user_id,)).fetchone()
    return row['total_xp'] if row else 0


def add_xp(amount, user_id=None):
    db = get_db()
    if user_id is None:
        from flask import session
        user_id = session.get('user_id')
    if not user_id:
        return
    db.execute(
        'INSERT INTO user_xp (user_id, total_xp) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET total_xp = total_xp + ?',
        (user_id, amount, amount)
    )
    db.commit()