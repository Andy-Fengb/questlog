"""Quest Log v1.01 — Habit & SOP CRUD API."""
import json
from flask import Blueprint, request, jsonify

from db import get_db
from utils import login_required

bp = Blueprint('habits', __name__)

VALID_FREQUENCIES = ('daily', 'weekly', 'monthly', 'once')


@bp.route('/api/habits', methods=['GET'])
@login_required
def list_habits(user_id):
    db = get_db()
    rows = db.execute(
        'SELECT * FROM habits WHERE user_id=? AND is_active=1 ORDER BY sort_order',
        (user_id,)
    ).fetchall()

    result = []
    for r in rows:
        h = dict(r)
        if h['task_type'] == 'sop':
            steps = db.execute(
                'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order',
                (h['id'],)
            ).fetchall()
            h['steps'] = [dict(s) for s in steps]
        result.append(h)

    return jsonify({'habits': result})


@bp.route('/api/habits', methods=['POST'])
@login_required
def create_habit(user_id):
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '名称不能为空'}), 400

    task_type = data.get('task_type', 'binary')
    if task_type not in ('binary', 'sop'):
        return jsonify({'error': 'task_type 须为 binary 或 sop'}), 400

    frequency = data.get('frequency', 'daily')
    if frequency not in VALID_FREQUENCIES:
        return jsonify({'error': f'frequency 须为 {VALID_FREQUENCIES}'}), 400

    db = get_db()
    last = db.execute(
        'SELECT COALESCE(MAX(sort_order), 0) as mx FROM habits WHERE user_id=?',
        (user_id,)
    ).fetchone()

    db.execute(
        '''INSERT INTO habits (user_id, name, icon, task_type, frequency, base_xp, sort_order)
           VALUES (?,?,?,?,?,?,?)''',
        (user_id, name, data.get('icon', '📋'), task_type, frequency,
         int(data.get('base_xp', 10)), (last['mx'] if last else 0) + 1)
    )
    db.commit()

    habit_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # If SOP, create steps
    if task_type == 'sop':
        steps = data.get('steps', [])
        for i, s in enumerate(steps, 1):
            db.execute(
                '''INSERT INTO sop_steps (habit_id, step_order, label, description, xp)
                   VALUES (?,?,?,?,?)''',
                (habit_id, s.get('step_order', i), s['label'],
                 s.get('description', ''), int(s.get('xp', 10)))
            )
        db.commit()

    habit = db.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
    result = dict(habit)
    if task_type == 'sop':
        steps = db.execute(
            'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order', (habit_id,)
        ).fetchall()
        result['steps'] = [dict(s) for s in steps]

    return jsonify({'success': True, 'habit': result}), 201


@bp.route('/api/habits/<int:habit_id>', methods=['PUT'])
@login_required
def update_habit(user_id, habit_id):
    data = request.get_json()
    db = get_db()

    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=?', (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'habit not found'}), 404

    updates = []
    params = []
    for field in ('name', 'icon', 'task_type', 'frequency'):
        if field in data:
            if field == 'frequency' and data[field] not in VALID_FREQUENCIES:
                return jsonify({'error': f'frequency 须为 {VALID_FREQUENCIES}'}), 400
            updates.append(f'{field}=?')
            params.append(data[field])
    for field in ('base_xp', 'sort_order'):
        if field in data:
            updates.append(f'{field}=?')
            params.append(int(data[field]))

    if updates:
        params.append(habit_id)
        params.append(user_id)
        db.execute(
            f"UPDATE habits SET {', '.join(updates)} WHERE id=? AND user_id=?",
            params
        )
        db.commit()

    # Update SOP steps if provided
    if 'steps' in data and habit['task_type'] == 'sop':
        db.execute('DELETE FROM sop_steps WHERE habit_id=?', (habit_id,))
        for i, s in enumerate(data['steps'], 1):
            db.execute(
                '''INSERT INTO sop_steps (habit_id, step_order, label, description, xp)
                   VALUES (?,?,?,?,?)''',
                (habit_id, s.get('step_order', i), s['label'],
                 s.get('description', ''), int(s.get('xp', 10)))
            )
        db.commit()

    habit = db.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
    result = dict(habit)
    if result['task_type'] == 'sop':
        steps = db.execute(
            'SELECT * FROM sop_steps WHERE habit_id=? ORDER BY step_order', (habit_id,)
        ).fetchall()
        result['steps'] = [dict(s) for s in steps]

    return jsonify({'success': True, 'habit': result})


@bp.route('/api/habits/<int:habit_id>', methods=['DELETE'])
@login_required
def delete_habit(user_id, habit_id):
    db = get_db()
    habit = db.execute(
        'SELECT * FROM habits WHERE id=? AND user_id=?', (habit_id, user_id)
    ).fetchone()
    if not habit:
        return jsonify({'error': 'habit not found'}), 404

    db.execute("UPDATE habits SET is_active=0 WHERE id=?", (habit_id,))
    db.commit()
    return jsonify({'success': True})
