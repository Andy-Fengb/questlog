import csv, io, json
import datetime
from flask import Blueprint, request, jsonify, make_response

from db import get_db
from config import get_level, today
from utils import login_required
from services.xp_service import get_total_xp
from services.streak_service import get_streak

bp = Blueprint('status', __name__)


@bp.route('/health')
def health():
    """Health check endpoint for Docker / monitoring."""
    try:
        db = get_db()
        db.execute('SELECT 1').fetchone()
        return jsonify({'status': 'ok', 'db': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 500


@bp.route('/api/state')
@login_required
def api_state(user_id):
    db = get_db()
    xp = get_total_xp(user_id)
    level = get_level(xp)
    date_str = today()

    # Load habits
    habits = db.execute(
        'SELECT * FROM habits WHERE user_id=? AND is_active=1 ORDER BY sort_order',
        (user_id,)
    ).fetchall()

    # Today's logs
    today_log = {
        r['habit_id']: dict(r) for r in db.execute(
            'SELECT * FROM habit_log WHERE user_id=? AND date=?',
            (user_id, date_str)
        ).fetchall()
    }

    tasks = []
    for h in habits:
        entry = {
            'id': h['id'],
            'name': h['name'],
            'icon': h['icon'],
            'type': h['type'],
            'xp': h['base_xp'],
            'target': h['target_value'],
            'schedule_type': h['schedule_type'],
            'schedule_value': h['schedule_value'],
        }
        log = today_log.get(h['id'])
        if h['type'] == 'yesno':
            entry['done'] = log is not None
            entry['value'] = 1 if log else 0
        else:
            val = log['value'] if log else 0
            entry['value'] = val
            entry['done'] = val >= h['target_value']
        tasks.append(entry)

    done_ids = [t['id'] for t in tasks if t.get('done')]
    streak = get_streak(user_id)

    return jsonify({
        'total_xp': xp,
        'level': level['level'],
        'streak': streak,
        'done_today': done_ids,
        'date': date_str,
        'tasks': tasks
    })


@bp.route('/api/day')
@login_required
def api_day(user_id):
    date_str = request.args.get('date', today())
    db = get_db()

    rows = db.execute(
        'SELECT hl.*, h.name, h.icon FROM habit_log hl '
        'JOIN habits h ON hl.habit_id=h.id '
        'WHERE hl.user_id=? AND hl.date=? ORDER BY hl.created_at',
        (user_id, date_str)
    ).fetchall()

    results = []
    for r in rows:
        results.append({
            'habit_id': r['habit_id'],
            'icon': r['icon'],
            'name': r['name'],
            'value': r['value'],
            'xp': r['xp'],
        })

    total_xp = sum(r['xp'] for r in rows)
    return jsonify({'date': date_str, 'tasks': results, 'total_xp': total_xp, 'count': len(results)})


@bp.route('/api/export')
@login_required
def export_data(user_id):
    """Export all user data as JSON or CSV."""
    fmt = request.args.get('format', 'json')
    db = get_db()

    # User info
    user = db.execute(
        'SELECT id, username, avatar_emoji, created_at FROM users WHERE id=?',
        (user_id,)
    ).fetchone()

    # All habits
    habits = [dict(r) for r in db.execute(
        'SELECT * FROM habits WHERE user_id=? ORDER BY sort_order',
        (user_id,)
    ).fetchall()]

    # All logs
    logs = [dict(r) for r in db.execute(
        'SELECT hl.*, h.name as habit_name FROM habit_log hl '
        'JOIN habits h ON hl.habit_id=h.id '
        'WHERE hl.user_id=? ORDER BY hl.date DESC',
        (user_id,)
    ).fetchall()]

    # XP & achievements
    xp = get_total_xp(user_id)
    level = get_level(xp)
    achievements = [dict(r) for r in db.execute(
        'SELECT * FROM user_achievements WHERE user_id=?',
        (user_id,)
    ).fetchall()]

    data = {
        'user': dict(user) if user else {},
        'xp': xp,
        'level': level['level'],
        'habits': habits,
        'logs': logs,
        'achievements': achievements,
        'exported_at': datetime.datetime.now().isoformat(),
    }

    if fmt == 'csv':
        # CSV: flatten logs
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['date', 'habit_name', 'icon', 'value', 'xp'])
        for log in logs:
            writer.writerow([
                log['date'], log['habit_name'], log.get('icon', ''),
                log['value'], log['xp']
            ])
        resp = make_response(output.getvalue())
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename=questlog_{today()}.csv'
        return resp

    # JSON (default)
    resp = make_response(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=questlog_{today()}.json'
    return resp
