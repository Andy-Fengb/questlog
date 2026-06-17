from flask import Blueprint, request, jsonify

from db import get_db
from config import get_level, today
from utils import login_required
from services.xp_service import add_xp, get_total_xp
from services.achievement_service import check_achievements
from services.xp_calculator import calculate_quest_xp
from services.streak_service import get_streak

bp = Blueprint('tasks', __name__)


def _calc_xp(habit, value):
    """Calculate XP based on habit type and value."""
    base = habit['base_xp']
    if habit['type'] == 'yesno':
        return base
    elif habit['type'] == 'number':
        target = habit['target_value']
        if value >= target:
            return base
        return max(1, int(value / target * base))
    elif habit['type'] == 'timer':
        result = calculate_quest_xp(
            actual_minutes=value,
            base_minutes=habit['target_value'],
            base_xp=base,
            bonus_interval=5,
            bonus_xp=2,
        )
        return result['total_xp']
    return base


@bp.route('/api/complete', methods=['POST'])
@login_required
def complete_habit(user_id):
    data = request.get_json()
    habit_id = data.get('habit_id')
    date_str = data.get('date', today())
    value = data.get('value')

    if not habit_id:
        return jsonify({'error': 'habit_id required'}), 400

    db = get_db()

    # Verify habit ownership
    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=? AND is_active=1',
        (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'habit not found'}), 404

    # Determine value based on habit type
    if value is None:
        if habit['type'] == 'yesno':
            value = 1
        elif habit['type'] in ('number', 'timer'):
            return jsonify({'error': f'請提供 {habit["name"]} 的今日數值'}), 400
    else:
        value = int(value)

    # Check if already logged today
    existing = db.execute(
        'SELECT id, value, xp FROM habit_log WHERE user_id=? AND habit_id=? AND date=?',
        (user_id, habit_id, date_str)
    ).fetchone()

    if existing:
        if habit['type'] == 'yesno':
            return jsonify({'error': 'already completed today'}), 409
        else:
            # Accumulate (number/timer): add to existing value, recalculate XP
            old_value = existing['value']
            old_xp = existing['xp']
            new_value = old_value + value
            new_xp_val = _calc_xp(habit, new_value)
            delta_xp = new_xp_val - old_xp
            db.execute(
                'UPDATE habit_log SET value=?, xp=? WHERE id=?',
                (new_value, new_xp_val, existing['id'])
            )
            if delta_xp > 0:
                add_xp(delta_xp, user_id)
            db.commit()

            target = habit['target_value']
            done = new_value >= target
            total_xp_now = get_total_xp(user_id)
            level = get_level(total_xp_now)

            return jsonify({
                'success': True,
                'xp_earned': delta_xp,
                'total_value': new_value,
                'target': target,
                'done': done,
                'total_xp': total_xp_now,
                'level': level['level'],
            })

    # New log entry
    xp_val = _calc_xp(habit, value)
    db.execute(
        'INSERT INTO habit_log (user_id, habit_id, date, value, xp) VALUES (?,?,?,?,?)',
        (user_id, habit_id, date_str, value, xp_val)
    )
    if xp_val > 0:
        add_xp(xp_val, user_id)
    db.commit()

    # Check achievements
    achievements_unlocked = check_achievements(habit['name'], date_str, user_id)

    total_xp_now = get_total_xp(user_id)
    level = get_level(total_xp_now)
    target = habit['target_value']
    done = value >= target if habit['type'] != 'yesno' else True

    return jsonify({
        'success': True,
        'xp_earned': xp_val,
        'total_value': value,
        'target': target,
        'done': done,
        'total_xp': total_xp_now,
        'level': level['level'],
        'achievements': achievements_unlocked,
    })


@bp.route('/api/uncomplete', methods=['POST'])
@login_required
def uncomplete_habit(user_id):
    data = request.get_json()
    habit_id = data.get('habit_id')
    date_str = data.get('date', today())

    db = get_db()

    existing = db.execute(
        'SELECT id, xp FROM habit_log WHERE user_id=? AND habit_id=? AND date=?',
        (user_id, habit_id, date_str)
    ).fetchone()

    if not existing:
        return jsonify({'error': 'not completed today'}), 404

    total_refund = existing['xp']
    db.execute('DELETE FROM habit_log WHERE id=?', (existing['id'],))
    db.execute(
        'UPDATE user_xp SET total_xp = MAX(0, total_xp - ?) WHERE user_id=?',
        (total_refund, user_id)
    )
    db.commit()

    xp = get_total_xp(user_id)
    level = get_level(xp)

    return jsonify({
        'success': True,
        'xp_refunded': total_refund,
        'total_xp': xp,
        'level': level['level'],
    })


@bp.route('/api/complete_batch', methods=['POST'])
@login_required
def complete_batch(user_id):
    data = request.get_json()
    habit_ids = data.get('habit_ids', [])
    values = data.get('values', {})
    date_str = data.get('date', today())

    results = []
    db = get_db()

    for hid in habit_ids:
        habit = db.execute(
            'SELECT * FROM habits WHERE id=? AND user_id=? AND is_active=1',
            (hid, user_id)
        ).fetchone()
        if not habit:
            results.append({'habit_id': hid, 'status': 'unknown'})
            continue

        val = values.get(str(hid)) if isinstance(values, dict) else None
        if val is not None:
            val = int(val)
        elif habit['type'] == 'yesno':
            val = 1
        else:
            results.append({'habit_id': hid, 'status': 'need_value'})
            continue

        existing = db.execute(
            'SELECT id FROM habit_log WHERE user_id=? AND habit_id=? AND date=?',
            (user_id, hid, date_str)
        ).fetchone()

        if existing:
            results.append({'habit_id': hid, 'status': 'already_done'})
            continue

        xp_val = _calc_xp(habit, val)
        db.execute(
            'INSERT INTO habit_log (user_id, habit_id, date, value, xp) VALUES (?,?,?,?,?)',
            (user_id, hid, date_str, val, xp_val)
        )
        if xp_val > 0:
            add_xp(xp_val, user_id)
        results.append({'habit_id': hid, 'status': 'done', 'xp': xp_val})

    db.commit()

    total_xp = get_total_xp(user_id)
    level = get_level(total_xp)
    return jsonify({'results': results, 'total_xp': total_xp, 'level': level['level']})
