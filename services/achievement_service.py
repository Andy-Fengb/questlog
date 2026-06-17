"""Quest Log v2 — Achievement checking service."""
from db import get_db
from config import CN_ACHIEVEMENTS


def check_achievements(habit_name, date_str, user_id):
    """Check and unlock achievements. Returns list of newly unlocked achievement dicts."""
    db = get_db()
    unlocked = {
        a['achievement_id'] for a in db.execute(
            'SELECT achievement_id FROM user_achievements WHERE user_id=?', (user_id,)
        ).fetchall()
    }

    newly_unlocked = []

    for ach in CN_ACHIEVEMENTS:
        if ach['id'] in unlocked:
            continue
        if _check_trigger(ach, user_id, date_str, db):
            db.execute(
                'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
                (user_id, ach['id'])
            )
            if ach['xp_reward'] > 0:
                db.execute(
                    'UPDATE user_xp SET total_xp = total_xp + ? WHERE user_id=?',
                    (ach['xp_reward'], user_id)
                )
            newly_unlocked.append({
                'id': ach['id'],
                'name': ach['name'],
                'desc': ach['desc'],
                'rarity': ach['rarity'],
                'xp_reward': ach['xp_reward'],
            })

    if newly_unlocked:
        db.commit()

    return newly_unlocked


def _check_trigger(ach, user_id, date_str, db):
    """Check if an achievement trigger condition is met."""
    trigger = ach.get('trigger')

    if trigger == 'level':
        row = db.execute('SELECT total_xp FROM user_xp WHERE user_id=?', (user_id,)).fetchone()
        if not row:
            return False
        from config import get_level
        level = get_level(row['total_xp'])
        return level['level'] >= ach.get('value', 999)

    elif trigger == 'streak':
        from services.streak_service import get_streak
        streak = get_streak(user_id)
        return streak >= ach.get('value', 999)

    elif trigger == 'total_tasks':
        count = db.execute(
            'SELECT COUNT(*) as cnt FROM habit_log WHERE user_id=?', (user_id,)
        ).fetchone()['cnt']
        return count >= ach.get('value', 999)

    elif trigger == 'task_count_any':
        tasks = ach.get('tasks', [])
        total = 0
        for t in tasks:
            # Map task_id to habit names
            from db import get_db as _gdb
            count = db.execute(
                'SELECT COUNT(*) as cnt FROM habit_log hl JOIN habits h ON hl.habit_id=h.id WHERE hl.user_id=? AND h.name LIKE ?',
                (user_id, f'%{t}%')
            ).fetchone()['cnt']
            total += count
        return total >= ach.get('value', 999)

    elif trigger == 'date_check':
        import datetime
        try:
            d = datetime.date.fromisoformat(date_str)
            return d.month == ach.get('month') and d.day == ach.get('day')
        except:
            return False

    return False
