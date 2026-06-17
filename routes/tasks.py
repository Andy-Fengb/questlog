"""Quest Log v2 — Task completion API (binary + SOP)."""
import datetime
from flask import Blueprint, request, jsonify

from db import get_db
from config import get_level, today
from utils import login_required
from services.xp_service import add_xp, get_total_xp
from services.achievement_service import check_achievements

bp = Blueprint('tasks', __name__)


@bp.route('/api/binary/complete', methods=['POST'])
@login_required
def complete_binary(user_id):
    """Complete a binary habit (yes/no)."""
    data = request.get_json()
    habit_id = data.get('habit_id')
    date_str = data.get('date', today())

    if not habit_id:
        return jsonify({'error': 'habit_id required'}), 400

    db = get_db()
    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=? AND is_active=1 AND task_type="binary"',
        (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'habit not found'}), 404

    # Check if already done today
    existing = db.execute(
        'SELECT id FROM habit_log WHERE user_id=? AND habit_id=? AND date=? AND step_order IS NULL',
        (user_id, habit_id, date_str)
    ).fetchone()
    if existing:
        return jsonify({'error': 'already completed today'}), 409

    now = datetime.datetime.now().strftime('%H:%M')
    xp_val = habit['base_xp']

    db.execute(
        'INSERT INTO habit_log (user_id, habit_id, date, completed_at, step_order, xp) VALUES (?,?,?,?,NULL,?)',
        (user_id, habit_id, date_str, now, xp_val)
    )
    add_xp(xp_val, user_id)
    db.commit()

    # Check achievements
    achievements = check_achievements(habit['name'], date_str, user_id)

    total_xp = get_total_xp(user_id)
    return jsonify({
        'success': True,
        'xp_earned': xp_val,
        'total_xp': total_xp,
        'level': get_level(total_xp)['level'],
        'completed_at': now,
        'achievements': achievements,
    })


@bp.route('/api/binary/uncomplete', methods=['POST'])
@login_required
def uncomplete_binary(user_id):
    """Undo a binary habit completion (today only)."""
    data = request.get_json()
    habit_id = data.get('habit_id')
    date_str = data.get('date', today())

    db = get_db()
    existing = db.execute(
        'SELECT id, xp FROM habit_log WHERE user_id=? AND habit_id=? AND date=? AND step_order IS NULL',
        (user_id, habit_id, date_str)
    ).fetchone()

    if not existing:
        return jsonify({'error': 'not completed today'}), 404

    db.execute('DELETE FROM habit_log WHERE id=?', (existing['id'],))
    db.execute(
        'UPDATE user_xp SET total_xp = MAX(0, total_xp - ?) WHERE user_id=?',
        (existing['xp'], user_id)
    )
    db.commit()

    total_xp = get_total_xp(user_id)
    return jsonify({
        'success': True,
        'xp_refunded': existing['xp'],
        'total_xp': total_xp,
        'level': get_level(total_xp)['level'],
    })


@bp.route('/api/sop/complete_step', methods=['POST'])
@login_required
def complete_sop_step(user_id):
    """Complete a specific SOP step (must follow order)."""
    data = request.get_json()
    habit_id = data.get('habit_id')
    step_order = data.get('step_order')
    date_str = data.get('date', today())

    if not habit_id or step_order is None:
        return jsonify({'error': 'habit_id and step_order required'}), 400

    step_order = int(step_order)

    db = get_db()

    # Verify SOP habit
    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=? AND is_active=1 AND task_type="sop"',
        (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'SOP habit not found'}), 404

    # Get the step definition
    step = db.execute(
        'SELECT * FROM sop_steps WHERE habit_id=? AND step_order=?',
        (habit_id, step_order)
    ).fetchone()
    if not step:
        return jsonify({'error': 'step not found'}), 404

    # Check if this step already completed today
    existing = db.execute(
        'SELECT id FROM habit_log WHERE user_id=? AND habit_id=? AND date=? AND step_order=?',
        (user_id, habit_id, date_str, step_order)
    ).fetchone()
    if existing:
        return jsonify({'error': 'step already completed today'}), 409

    # Enforce order: previous step must be completed (except step 1)
    if step_order > 1:
        prev = db.execute(
            'SELECT id FROM habit_log WHERE user_id=? AND habit_id=? AND date=? AND step_order=?',
            (user_id, habit_id, date_str, step_order - 1)
        ).fetchone()
        if not prev:
            return jsonify({'error': f'必须先完成第 {step_order - 1} 步'}), 409

    now = datetime.datetime.now().strftime('%H:%M')
    xp_val = step['xp']

    db.execute(
        'INSERT INTO habit_log (user_id, habit_id, date, completed_at, step_order, xp) VALUES (?,?,?,?,?,?)',
        (user_id, habit_id, date_str, now, step_order, xp_val)
    )
    add_xp(xp_val, user_id)
    db.commit()

    # Check if all steps done
    total_steps = db.execute(
        'SELECT COUNT(*) as cnt FROM sop_steps WHERE habit_id=?', (habit_id,)
    ).fetchone()['cnt']
    completed_steps = db.execute(
        'SELECT COUNT(DISTINCT step_order) as cnt FROM habit_log WHERE user_id=? AND habit_id=? AND date=? AND step_order IS NOT NULL',
        (user_id, habit_id, date_str)
    ).fetchone()['cnt']
    all_done = completed_steps >= total_steps

    total_xp = get_total_xp(user_id)
    return jsonify({
        'success': True,
        'xp_earned': xp_val,
        'total_xp': total_xp,
        'level': get_level(total_xp)['level'],
        'completed_at': now,
        'completed_steps': completed_steps,
        'total_steps': total_steps,
        'all_done': all_done,
    })
