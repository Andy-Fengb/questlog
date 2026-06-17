from flask import Blueprint, request, jsonify

from db import get_db
from utils import login_required

bp = Blueprint('habits', __name__)


@bp.route('/api/habits', methods=['GET'])
@login_required
def list_habits(user_id):
    category = request.args.get('category')
    db = get_db()

    if category:
        rows = db.execute(
            'SELECT * FROM habits WHERE user_id=? AND category=? AND is_active=1 ORDER BY sort_order',
            (user_id, category)
        ).fetchall()
    else:
        rows = db.execute(
            'SELECT * FROM habits WHERE user_id=? AND is_active=1 ORDER BY sort_order',
            (user_id,)
        ).fetchall()

    return jsonify({'habits': [dict(r) for r in rows]})


@bp.route('/api/habits', methods=['POST'])
@login_required
def create_habit(user_id):
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '習慣名稱不能為空'}), 400

    valid_types = ('yesno', 'number', 'timer')
    valid_schedules = ('daily', 'weekly_x', 'weekdays', 'weekends')
    valid_categories = ('daily', 'bonus')

    htype = data.get('type', 'yesno')
    if htype not in valid_types:
        return jsonify({'error': f'類型須為 {valid_types}'}), 400

    sched = data.get('schedule_type', 'daily')
    if sched not in valid_schedules:
        return jsonify({'error': f'頻率須為 {valid_schedules}'}), 400

    cat = data.get('category', 'daily')
    if cat not in valid_categories:
        return jsonify({'error': f'分類須為 {valid_categories}'}), 400

    db = get_db()

    # Determine next sort_order
    last = db.execute(
        'SELECT COALESCE(MAX(sort_order), 0) as mx FROM habits WHERE user_id=?',
        (user_id,)
    ).fetchone()

    db.execute(
        '''INSERT INTO habits (user_id, name, icon, type, schedule_type,
           schedule_value, target_value, base_xp, category, sort_order,
           "group", deadline, "scope")
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (user_id,
         name,
         data.get('icon', '📌'),
         htype,
         sched,
         data.get('schedule_value', 1),
         data.get('target_value', 1),
         data.get('base_xp', 10),
         cat,
         (last['mx'] if last else 0) + 1,
         data.get('group', 'daily'),
         data.get('deadline'),
         data.get('scope'))
    )
    db.commit()

    habit_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    habit = db.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()

    return jsonify({'success': True, 'habit': dict(habit)}), 201


@bp.route('/api/habits/<int:habit_id>', methods=['PUT'])
@login_required
def update_habit(user_id, habit_id):
    data = request.get_json()
    db = get_db()

    # Verify ownership
    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=?', (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'habit not found'}), 404

    updates = []
    params = []
    for field in ('name', 'icon', 'type', 'schedule_type', 'category', 'deadline', 'scope'):
        if field in data:
            updates.append(f'"{field}"=?')
            params.append(data[field])
    if 'group' in data:
        updates.append('"group"=?')
        params.append(data['group'])
    for field in ('schedule_value', 'target_value', 'base_xp', 'sort_order'):
        if field in data:
            updates.append(f"{field}=?")
            params.append(int(data[field]))

    if updates:
        params.append(habit_id)
        params.append(user_id)
        db.execute(
            f"UPDATE habits SET {', '.join(updates)} WHERE id=? AND user_id=?",
            params
        )
        db.commit()

    habit = db.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
    return jsonify({'success': True, 'habit': dict(habit)})


@bp.route('/api/habits/<int:habit_id>', methods=['DELETE'])
@login_required
def delete_habit(user_id, habit_id):
    db = get_db()
    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=?', (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'habit not found'}), 404

    # Soft delete (keep history for stats)
    db.execute("UPDATE habits SET is_active=0 WHERE id=?", (habit_id,))
    db.commit()
    return jsonify({'success': True})
