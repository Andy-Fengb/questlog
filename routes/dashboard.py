"""Quest Log v1.01 — Dashboard (Today's Kanban)."""
import json, datetime
from flask import Blueprint, render_template, session, redirect

from db import get_db
import config as app_config
from config import get_level, today, LEVELS, get_tip, CN_ACHIEVEMENTS
from services.xp_service import get_total_xp
from services.streak_service import get_streak, get_habit_streak

bp = Blueprint('dashboard', __name__)


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
    streak = get_streak(user_id)

    # Load all active habits
    all_habits = db.execute(
        'SELECT * FROM habits WHERE user_id=? AND is_active=1 ORDER BY sort_order',
        (user_id,)
    ).fetchall()

    # Split binary into daily vs non-daily
    binary_daily = [dict(h) for h in all_habits if h['task_type'] == 'binary' and h['frequency'] == 'daily']
    binary_other = [dict(h) for h in all_habits if h['task_type'] == 'binary' and h['frequency'] != 'daily']
    sop_habits = [dict(h) for h in all_habits if h['task_type'] == 'sop']

    # Load SOP steps for each SOP habit
    for sop in sop_habits:
        steps = db.execute(
            'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order',
            (sop['id'],)
        ).fetchall()
        sop['steps'] = [dict(s) for s in steps]

    # Today's logs
    today_logs = db.execute(
        'SELECT * FROM habit_log WHERE user_id=? AND date=?',
        (user_id, date_str)
    ).fetchall()

    # Build completion maps
    binary_done = {}
    sop_progress_raw = {}

    for log in today_logs:
        hid = log['habit_id']
        if log['step_order'] is None:
            binary_done[hid] = dict(log)
        else:
            if hid not in sop_progress_raw:
                sop_progress_raw[hid] = set()
            sop_progress_raw[hid].add(log['step_order'])

    # Convert to template-friendly format
    sop_progress = {}
    for sop in sop_habits:
        hid = sop['id']
        completed = sop_progress_raw.get(hid, set())
        sop_progress[hid] = {
            'current_step': max(completed) + 1 if completed else 1,
            'completed_steps': sorted(completed),
        }

    # Activity log for today
    activity_log = []
    for log in today_logs:
        habit = next((h for h in all_habits if h['id'] == log['habit_id']), None)
        if not habit:
            continue
        step_label = ''
        if log['step_order'] is not None:
            step = db.execute(
                'SELECT label FROM sop_steps WHERE habit_id=? AND step_order=?',
                (log['habit_id'], log['step_order'])
            ).fetchone()
            if step:
                step_label = f' · {step["label"]}'
        activity_log.append({
            'time': log['completed_at'] or '--:--',
            'icon': habit['icon'],
            'name': habit['name'],
            'step_label': step_label,
            'xp': log['xp'],
            'is_makeup': log['is_makeup'],
        })

    activity_log.sort(key=lambda x: x['time'] if x['time'] != '--:--' else 'zz:zz')

    # Today's total XP
    today_xp = sum(l['xp'] for l in today_logs)
    today_done_count = len(set(l['habit_id'] for l in today_logs if l['step_order'] is None))
    today_total = len(binary_daily) + len(binary_other)

    # Achievement stats
    unlocked_achs = {
        a['achievement_id'] for a in db.execute(
            'SELECT achievement_id FROM user_achievements WHERE user_id=?', (user_id,)
        ).fetchall()
    }
    unlocked_count = len(unlocked_achs)
    total_ach_count = len(CN_ACHIEVEMENTS)

    # Build all_habits JSON for edit modal
    all_habits_json = []
    for h in all_habits:
        hj = dict(h)
        if hj['task_type'] == 'sop':
            steps = db.execute(
                'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order', (hj['id'],)
            ).fetchall()
            hj['steps'] = [dict(s) for s in steps]
        all_habits_json.append(hj)

    return render_template('index.html',
        today=date_str,
        level=level,
        xp=xp,
        streak=streak,
        tip=get_tip(),
        username=user['username'],
        user_avatar=user['avatar_emoji'],
        binary_daily=binary_daily,
        binary_other=binary_other,
        sop_habits=sop_habits,
        binary_done=binary_done,
        sop_progress=sop_progress,
        activity_log=activity_log,
        today_xp=today_xp,
        today_done_count=today_done_count,
        today_total=today_total,
        unlocked_count=unlocked_count,
        total_ach_count=total_ach_count,
        all_habits_json=json.dumps(all_habits_json, ensure_ascii=False),
        LEVELS=LEVELS,
    )


@bp.route('/day/<date_str>')
def day_view(date_str):
    """Read-only historical day view."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        session.clear()
        return redirect('/login')

    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return redirect('/')

    prev_date = (d - datetime.timedelta(days=1)).isoformat()
    next_date = (d + datetime.timedelta(days=1)).isoformat()
    is_today = date_str == today()

    all_habits = db.execute(
        'SELECT * FROM habits WHERE user_id=? AND is_active=1 ORDER BY sort_order',
        (user_id,)
    ).fetchall()

    binary_daily = [dict(h) for h in all_habits if h['task_type'] == 'binary' and h['frequency'] == 'daily']
    binary_other = [dict(h) for h in all_habits if h['task_type'] == 'binary' and h['frequency'] != 'daily']
    sop_habits = [dict(h) for h in all_habits if h['task_type'] == 'sop']

    for sop in sop_habits:
        steps = db.execute(
            'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order',
            (sop['id'],)
        ).fetchall()
        sop['steps'] = [dict(s) for s in steps]

    day_logs = db.execute(
        'SELECT * FROM habit_log WHERE user_id=? AND date=?',
        (user_id, date_str)
    ).fetchall()

    binary_done = {}
    sop_progress_raw = {}
    activity_log = []

    for log in day_logs:
        hid = log['habit_id']
        if log['step_order'] is None:
            binary_done[hid] = dict(log)
        else:
            if hid not in sop_progress_raw:
                sop_progress_raw[hid] = set()
            sop_progress_raw[hid].add(log['step_order'])

        habit = next((h for h in all_habits if h['id'] == hid), None)
        if habit:
            step_label = ''
            if log['step_order'] is not None:
                step = db.execute(
                    'SELECT label FROM sop_steps WHERE habit_id=? AND step_order=?',
                    (hid, log['step_order'])
                ).fetchone()
                if step:
                    step_label = f' · {step["label"]}'
            activity_log.append({
                'time': log['completed_at'] or '--:--',
                'icon': habit['icon'],
                'name': habit['name'],
                'step_label': step_label,
                'xp': log['xp'],
                'is_makeup': log['is_makeup'],
            })

    sop_progress = {}
    for sop in sop_habits:
        hid = sop['id']
        completed = sop_progress_raw.get(hid, set())
        sop_progress[hid] = {
            'current_step': max(completed) + 1 if completed else 1,
            'completed_steps': sorted(completed),
        }

    activity_log.sort(key=lambda x: x['time'] if x['time'] != '--:--' else 'zz:zz')

    day_xp = sum(l['xp'] for l in day_logs)
    day_done = len(set(l['habit_id'] for l in day_logs if l['step_order'] is None))

    return render_template('day.html',
        date_str=date_str,
        prev_date=prev_date,
        next_date=next_date,
        is_today=is_today,
        level=get_level(get_total_xp(user_id)),
        xp=get_total_xp(user_id),
        streak=get_streak(user_id),
        username=user['username'],
        user_avatar=user['avatar_emoji'],
        binary_daily=binary_daily,
        binary_other=binary_other,
        sop_habits=sop_habits,
        binary_done=binary_done,
        sop_progress=sop_progress,
        activity_log=activity_log,
        day_xp=day_xp,
        day_done=day_done,
        today=today(),
    )
