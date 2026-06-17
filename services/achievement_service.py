import datetime
from db import get_db
from config import CN_ACHIEVEMENTS, get_level, LEVELS
from services.xp_service import add_xp, get_total_xp
from services.streak_service import get_streak


def check_cn_achievement(db, ach, level, streak, total_tasks, ccnp_xp, ielts_count, today_date, user_id):
    aid = ach['id']
    if db.execute(
        'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id=?',
        (user_id, aid)
    ).fetchone():
        return None
    unlock = False
    t = ach['trigger']
    if t == 'level':
        unlock = level >= ach['value']
    elif t == 'streak':
        unlock = streak >= ach['value']
    elif t == 'task_count_any':
        placeholders = ','.join('?' for _ in ach['tasks'])
        # Need to join with habits to resolve name → habit_id
        rows = db.execute(
            f'SELECT COUNT(*) FROM habit_log hl JOIN habits h ON hl.habit_id=h.id '
            f'WHERE hl.user_id=? AND h.name IN ({placeholders})',
            (user_id, *ach['tasks'])
        ).fetchone()
        count = rows[0] if rows else 0
        unlock = count >= ach['value']
    elif t == 'task_sum':
        # Sum XP for habits matching the task name
        rows = db.execute(
            'SELECT COALESCE(SUM(hl.xp),0) FROM habit_log hl JOIN habits h ON hl.habit_id=h.id '
            'WHERE hl.user_id=? AND h.name=?',
            (user_id, ach['task_id'])
        ).fetchone()
        sum_xp = rows[0] if rows else 0
        unlock = sum_xp >= ach['value']
    elif t == 'total_tasks':
        unlock = total_tasks >= ach['value']
    elif t == 'date_check':
        unlock = today_date.month == ach['month'] and today_date.day == ach['day']
    elif t == 'spring_festival':
        unlock = (today_date.month == 1 and today_date.day >= 20) or \
                 (today_date.month == 2 and today_date.day <= 15)
    elif t == 'all_done_30':
        # Days where user completed all daily habits (6+ entries on a single day)
        all_done_count = db.execute(
            'SELECT COUNT(*) FROM (SELECT date, COUNT(DISTINCT habit_id) as cnt FROM habit_log '
            'WHERE user_id=? AND date >= date("now","-1 year") GROUP BY date HAVING cnt >= 6)',
            (user_id,)
        ).fetchone()[0]
        unlock = all_done_count >= ach['value']
    elif t == 'never':
        unlock = False
    if unlock:
        db.execute(
            'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
            (user_id, aid)
        )
        if ach['xp_reward'] > 0:
            add_xp(ach['xp_reward'], user_id)
        return f"{ach['name']} +{ach['xp_reward']}XP"
    return None


def check_achievements(habit_name, date_str, user_id):
    db = get_db()
    unlocked = []
    today_date = datetime.date.today()
    xp = get_total_xp(user_id)
    level = get_level(xp)['level']
    streak = get_streak(user_id)

    # Legacy achievements (now per-user)
    if not db.execute(
        'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id="first_quest"',
        (user_id,)
    ).fetchone():
        db.execute(
            'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
            (user_id, 'first_quest')
        )
        add_xp(10, user_id)
        unlocked.append('🏅 初心者 +10XP')

    # CCNP achievements (match by habit name)
    if habit_name == 'CCNP':
        ccnp_xp = db.execute(
            'SELECT COALESCE(SUM(hl.xp),0) FROM habit_log hl JOIN habits h ON hl.habit_id=h.id '
            'WHERE hl.user_id=? AND h.name="CCNP"',
            (user_id,)
        ).fetchone()[0]
        if ccnp_xp >= 100 and not db.execute(
            'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id="ccnp_100"',
            (user_id,)
        ).fetchone():
            db.execute(
                'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
                (user_id, 'ccnp_100')
            )
            add_xp(50, user_id)
            unlocked.append('🏅 CCNP 百題斬 +50XP')
        if ccnp_xp >= 500 and not db.execute(
            'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id="ccnp_500"',
            (user_id,)
        ).fetchone():
            db.execute(
                'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
                (user_id, 'ccnp_500')
            )
            add_xp(100, user_id)
            unlocked.append('🏅 CCNP 五百題斬 +100XP')

    if streak >= 7 and not db.execute(
        'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id="streak_7"',
        (user_id,)
    ).fetchone():
        db.execute(
            'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
            (user_id, 'streak_7')
        )
        add_xp(50, user_id)
        unlocked.append('🏅 連續 7 天達人 +50XP')
    if streak >= 30 and not db.execute(
        'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id="streak_30"',
        (user_id,)
    ).fetchone():
        db.execute(
            'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
            (user_id, 'streak_30')
        )
        add_xp(200, user_id)
        unlocked.append('🏅 連續 30 天強者 +200XP')

    if habit_name in ('IELTS 聽力', 'IELTS 閱讀'):
        ielts_total = db.execute(
            'SELECT COUNT(*) FROM habit_log hl JOIN habits h ON hl.habit_id=h.id '
            'WHERE hl.user_id=? AND h.name IN ("IELTS 聽力","IELTS 閱讀")',
            (user_id,)
        ).fetchone()[0]
        if ielts_total >= 50 and not db.execute(
            'SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id="ielts_50"',
            (user_id,)
        ).fetchone():
            db.execute(
                'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?,?)',
                (user_id, 'ielts_50')
            )
            add_xp(50, user_id)
            unlocked.append('🏅 IELTS 練習 50 次 +50XP')

    # Stats for CN achievements
    total_tasks = db.execute(
        'SELECT COUNT(*) FROM habit_log WHERE user_id=?', (user_id,)
    ).fetchone()[0]
    ccnp_xp = db.execute(
        'SELECT COALESCE(SUM(hl.xp),0) FROM habit_log hl JOIN habits h ON hl.habit_id=h.id '
        'WHERE hl.user_id=? AND h.name="CCNP"',
        (user_id,)
    ).fetchone()[0]
    ielts_count = db.execute(
        'SELECT COUNT(*) FROM habit_log hl JOIN habits h ON hl.habit_id=h.id '
        'WHERE hl.user_id=? AND h.name IN ("IELTS 聽力","IELTS 閱讀")',
        (user_id,)
    ).fetchone()[0]

    for ach in CN_ACHIEVEMENTS:
        result = check_cn_achievement(
            db, ach, level, streak, total_tasks, ccnp_xp, ielts_count, today_date, user_id
        )
        if result:
            unlocked.append(result)

    db.commit()
    return unlocked