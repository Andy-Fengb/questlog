import json, datetime
from flask import Blueprint, render_template, session, redirect

from db import get_db
from config import CN_ACHIEVEMENTS, get_level, today, LEVELS
from services.xp_service import get_total_xp
from services.streak_service import get_streak, get_habit_streak

bp = Blueprint('dashboard', __name__)


def _get_weekly_compliance(user_id, habits):
    """Calculate this week's compliance for each habit and return summary stats."""
    db = get_db()
    today_date = datetime.date.today()
    # Monday of this week
    monday = today_date - datetime.timedelta(days=today_date.weekday())
    dates = [(monday + datetime.timedelta(days=i)).isoformat() for i in range(7)]

    habit_compliance = {}
    for h in habits:
        done_days = set()
        rows = db.execute(
            'SELECT date FROM habit_log WHERE user_id=? AND habit_id=? AND date>=?',
            (user_id, h['id'], dates[0])
        ).fetchall()
        for r in rows:
            done_days.add(r['date'])

        # Check schedule compliance
        if h['schedule_type'] == 'daily':
            scheduled_days = 7
        elif h['schedule_type'] == 'weekly_x':
            scheduled_days = h['schedule_value']
        elif h['schedule_type'] == 'weekdays':
            scheduled_days = 5
        elif h['schedule_type'] == 'weekends':
            scheduled_days = 2
        else:
            scheduled_days = 7

        done_count = len(done_days)
        compliance = min(100, int(done_count / max(scheduled_days, 1) * 100)) if scheduled_days > 0 else 0

        habit_compliance[h['id']] = {
            'done': done_count,
            'scheduled': scheduled_days,
            'compliance': compliance,
            'done_dates': [d for d in dates if d in done_days]
        }

    return habit_compliance


@bp.route('/')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        session.clear()
        return redirect('/login')

    xp = get_total_xp(user_id)
    level = get_level(xp)
    date_str = today()
    site_title = 'Quest Log'

    # Load habits from DB — grouped by milestone / target / daily
    all_habits = db.execute(
        'SELECT * FROM habits WHERE user_id=? AND is_active=1 ORDER BY sort_order',
        (user_id,)
    ).fetchall()

    milestone_habits = [h for h in all_habits if h['group'] == 'milestone']
    target_habits = [dict(h) for h in all_habits if h['group'] == 'target']
    daily_habits = [dict(h) for h in all_habits if h['group'] == 'daily']

    # Today's log entries
    today_log = {
        r['habit_id']: dict(r) for r in db.execute(
            'SELECT hl.*, h.name, h.icon, h.type, h.target_value FROM habit_log hl '
            'JOIN habits h ON hl.habit_id=h.id '
            'WHERE hl.user_id=? AND hl.date=?',
            (user_id, date_str)
        ).fetchall()
    }

    # Per-habit progress & streak
    task_progress = {}
    done_ids = set()
    for h in all_habits:
        log = today_log.get(h['id'])
        tid = h['id']

        if h['type'] == 'yesno':
            done = log is not None
            if done:
                done_ids.add(tid)
        elif h['type'] == 'number':
            val = log['value'] if log else 0
            done = val >= h['target_value']
            if done:
                done_ids.add(tid)
        else:  # timer
            val = log['value'] if log else 0
            done = val >= h['target_value']
            if done:
                done_ids.add(tid)
            progress_ring = f"{val}/{h['target_value']}"

        streak = get_habit_streak(user_id, h['id'])

        task_progress[tid] = {
            'current': log['value'] if log else 0,
            'target': h['target_value'],
            'done': done,
            'streak': streak,
        }

    # Weekly compliance
    compliance = _get_weekly_compliance(user_id, all_habits)

    # ── Target cumulative progress (weekly/monthly) ──
    today_date = datetime.date.today()
    for t in target_habits:
        tid = t['id']
        if t.get('scope') == 'weekly':
            start = today_date - datetime.timedelta(days=today_date.weekday())
        else:  # monthly
            start = today_date.replace(day=1)

        rows = db.execute(
            'SELECT COALESCE(SUM(value),0) as total FROM habit_log WHERE user_id=? AND habit_id=? AND date>=?',
            (user_id, tid, start.isoformat())
        ).fetchone()
        cum_val = rows['total'] if rows else 0
        target = t['target_value']

        if tid not in task_progress:
            task_progress[tid] = {'current': 0, 'target': target, 'done': False, 'streak': 0}
        task_progress[tid]['current'] = cum_val
        task_progress[tid]['target'] = target
        task_progress[tid]['done'] = cum_val >= target

        # Calculate average per day
        days_elapsed = max(1, (today_date - start).days + 1)
        task_progress[tid]['avg'] = round(cum_val / days_elapsed, 1)

    # Streak
    streak = get_streak(user_id)

    # Week data (for chart)
    week_data = []
    week_xp_sum = 0
    for i in range(6, -1, -1):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        rows = db.execute(
            'SELECT xp FROM habit_log WHERE user_id=? AND date=?',
            (user_id, d)
        ).fetchall()
        xp_sum = sum(r['xp'] for r in rows)
        week_data.append({'date': d, 'xp': xp_sum, 'count': len(rows)})
        week_xp_sum += xp_sum

    # Achievements
    unlocked_achs = {
        a['achievement_id'] for a in db.execute(
            'SELECT achievement_id FROM user_achievements WHERE user_id=?',
            (user_id,)
        ).fetchall()
    }
    cn_achievements = []
    for ach in CN_ACHIEVEMENTS:
        cn_achievements.append({**ach, 'unlocked': ach['id'] in unlocked_achs})
    unlocked_count = len([a for a in cn_achievements if a['unlocked']])
    total_ach_count = len(cn_achievements)

    # History
    history = db.execute(
        '''SELECT hl.date, hl.xp, hl.value, h.name, h.icon
           FROM habit_log hl JOIN habits h ON hl.habit_id=h.id
           WHERE hl.user_id=? ORDER BY hl.created_at DESC LIMIT 50''',
        (user_id,)
    ).fetchall()

    # ── Heatmap (last 12 weeks, GitHub-style) ──
    today_date = datetime.date.today()
    heatmap_start = today_date - datetime.timedelta(days=today_date.weekday() + 83)  # ~12 weeks back to Monday
    heatmap_rows = db.execute(
        'SELECT date, COUNT(*) as cnt, COALESCE(SUM(xp),0) as xp_sum FROM habit_log '
        'WHERE user_id=? AND date>=? GROUP BY date ORDER BY date',
        (user_id, heatmap_start.isoformat())
    ).fetchall()
    heatmap_by_date = {r['date']: {'cnt': r['cnt'], 'xp': r['xp_sum']} for r in heatmap_rows}

    heatmap_weeks = []
    d = heatmap_start
    max_xp = max((r['xp_sum'] for r in heatmap_rows), default=1)
    while d <= today_date:
        week = []
        for _ in range(7):
            iso = d.isoformat()
            entry = heatmap_by_date.get(iso, {'cnt': 0, 'xp': 0})
            # Intensity: 0-3 based on XP relative to max
            intensity = 0
            if entry['cnt'] > 0:
                ratio = entry['xp'] / max_xp
                if ratio > 0.66:
                    intensity = 3
                elif ratio > 0.33:
                    intensity = 2
                else:
                    intensity = 1
            week.append({'date': iso, 'cnt': entry['cnt'], 'xp': entry['xp'], 'intensity': intensity})
            d += datetime.timedelta(days=1)
        heatmap_weeks.append(week)

    # ── Insight rankings ──
    # Compliance ranking (sorted best → worst)
    insight_compliance = []
    for h in all_habits:
        c = compliance.get(h['id'], {'done': 0, 'scheduled': 7, 'compliance': 0})
        insight_compliance.append({
            'id': h['id'],
            'name': h['name'],
            'icon': h['icon'],
            'done': c['done'],
            'scheduled': c['scheduled'],
            'compliance': c['compliance'],
        })
    insight_compliance.sort(key=lambda x: x['compliance'], reverse=True)

    # Streak ranking (sorted longest → shortest)
    insight_streaks = []
    for h in all_habits:
        s = task_progress.get(h['id'], {}).get('streak', 0)
        insight_streaks.append({
            'id': h['id'],
            'name': h['name'],
            'icon': h['icon'],
            'streak': s,
        })
    insight_streaks.sort(key=lambda x: x['streak'], reverse=True)

    return render_template('index.html',
        today=date_str,
        site_title=site_title,
        milestone_habits=[dict(h) for h in milestone_habits],
        target_habits=[dict(h) for h in target_habits],
        daily_habits=[dict(h) for h in daily_habits],
        done_ids=done_ids,
        task_progress=task_progress,
        task_progress_json=json.dumps({str(k): v for k, v in task_progress.items()}),
        compliance={str(k): v for k, v in compliance.items()},
        level=level,
        xp=xp,
        streak=streak,
        username=user['username'],
        user_avatar=user['avatar_emoji'],
        week_xp_sum=week_xp_sum,
        week_data=json.dumps(week_data),
        cn_achievements=cn_achievements,
        unlocked_count=unlocked_count,
        total_ach_count=total_ach_count,
        history=history,
        heatmap_weeks=heatmap_weeks,
        insight_compliance=insight_compliance,
        insight_streaks=insight_streaks,
        LEVELS=LEVELS,
    )