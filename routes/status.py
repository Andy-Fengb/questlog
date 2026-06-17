"""Quest Log v2 — Status & utility API endpoints."""
import json, datetime
from flask import Blueprint, request, jsonify, make_response

from db import get_db
from config import get_level, today, LEVELS
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
    """Quick JSON snapshot of today's state (for polling / external tools)."""
    db = get_db()
    xp = get_total_xp(user_id)
    level = get_level(xp)
    date_str = today()
    streak = get_streak(user_id)

    # Today's logs
    logs = db.execute(
        'SELECT * FROM habit_log WHERE user_id=? AND date=?',
        (user_id, date_str)
    ).fetchall()

    binary_done = set()
    sop_steps_done = {}
    total_xp_today = 0

    for log in logs:
        total_xp_today += log['xp']
        if log['step_order'] is None:
            binary_done.add(log['habit_id'])
        else:
            if log['habit_id'] not in sop_steps_done:
                sop_steps_done[log['habit_id']] = []
            sop_steps_done[log['habit_id']].append(log['step_order'])

    return jsonify({
        'total_xp': xp,
        'level': level['level'],
        'streak': streak,
        'date': date_str,
        'binary_done': list(binary_done),
        'sop_progress': {str(k): v for k, v in sop_steps_done.items()},
        'today_xp': total_xp_today,
        'level': LEVELS,
    })


@bp.route('/api/day')
@login_required
def api_day(user_id):
    """Get a specific day's activity log."""
    date_str = request.args.get('date', today())
    db = get_db()

    rows = db.execute(
        'SELECT hl.*, h.name, h.icon, h.task_type FROM habit_log hl '
        'JOIN habits h ON hl.habit_id=h.id '
        'WHERE hl.user_id=? AND hl.date=? ORDER BY hl.completed_at',
        (user_id, date_str)
    ).fetchall()

    results = []
    for r in rows:
        entry = {
            'habit_id': r['habit_id'],
            'icon': r['icon'],
            'name': r['name'],
            'task_type': r['task_type'],
            'step_order': r['step_order'],
            'xp': r['xp'],
            'completed_at': r['completed_at'],
            'is_makeup': r['is_makeup'],
        }
        results.append(entry)

    total_xp = sum(r['xp'] for r in rows)
    return jsonify({'date': date_str, 'tasks': results, 'total_xp': total_xp, 'count': len(results)})


@bp.route('/api/export')
@login_required
def export_data(user_id):
    """Export all user data as JSON or CSV."""
    fmt = request.args.get('format', 'json')
    db = get_db()

    user = db.execute(
        'SELECT id, username, avatar_emoji, created_at FROM users WHERE id=?', (user_id,)
    ).fetchone()

    habits = [dict(r) for r in db.execute(
        'SELECT * FROM habits WHERE user_id=? ORDER BY sort_order', (user_id,)
    ).fetchall()]

    # Attach SOP steps
    for h in habits:
        if h['task_type'] == 'sop':
            steps = db.execute(
                'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order', (h['id'],)
            ).fetchall()
            h['steps'] = [dict(s) for s in steps]

    logs = [dict(r) for r in db.execute(
        'SELECT hl.*, h.name as habit_name, h.task_type FROM habit_log hl '
        'JOIN habits h ON hl.habit_id=h.id '
        'WHERE hl.user_id=? ORDER BY hl.date DESC', (user_id,)
    ).fetchall()]

    xp = get_total_xp(user_id)
    achievements = [dict(r) for r in db.execute(
        'SELECT * FROM user_achievements WHERE user_id=?', (user_id,)
    ).fetchall()]

    data = {
        'user': dict(user) if user else {},
        'xp': xp,
        'level': get_level(xp)['level'],
        'habits': habits,
        'logs': logs,
        'achievements': achievements,
        'exported_at': datetime.datetime.now().isoformat(),
    }

    if fmt == 'csv':
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['date', 'habit_name', 'task_type', 'step_order', 'xp', 'completed_at', 'is_makeup'])
        for log in logs:
            writer.writerow([
                log['date'], log['habit_name'], log.get('task_type', ''),
                log.get('step_order', ''), log['xp'], log.get('completed_at', ''),
                log.get('is_makeup', 0)
            ])
        resp = make_response(output.getvalue())
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename=questlog_{today()}.csv'
        return resp

    resp = make_response(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=questlog_{today()}.json'
    return resp
