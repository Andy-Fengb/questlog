from flask import Blueprint, request, jsonify, session, render_template, redirect

from db import get_or_create_user, get_user

bp = Blueprint('auth', __name__)

# ── Login rate limiting (in-memory, per IP) ──
_login_attempts = {}  # ip -> {'count': int, 'first_at': float}
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes

def _check_rate_limit(ip):
    """Return (allowed, remaining_seconds)."""
    import time
    now = time.time()
    entry = _login_attempts.get(ip)
    if not entry:
        return True, 0
    # Reset window if expired
    if now - entry['first_at'] > LOCKOUT_SECONDS:
        del _login_attempts[ip]
        return True, 0
    if entry['count'] >= MAX_ATTEMPTS:
        remaining = int(LOCKOUT_SECONDS - (now - entry['first_at']))
        return False, remaining
    return True, 0

def _record_attempt(ip):
    """Record a failed login attempt."""
    import time
    now = time.time()
    entry = _login_attempts.get(ip)
    if not entry or now - entry['first_at'] > LOCKOUT_SECONDS:
        _login_attempts[ip] = {'count': 1, 'first_at': now}
    else:
        entry['count'] += 1

def _clear_attempts(ip):
    """Clear attempts on successful login."""
    _login_attempts.pop(ip, None)


@bp.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect('/')
    return render_template('login.html')


@bp.route('/api/login', methods=['POST'])
def api_login():
    ip = request.remote_addr or 'unknown'

    # Rate limit check
    allowed, remaining = _check_rate_limit(ip)
    if not allowed:
        return jsonify({'error': f'登入嘗試過多，請 {remaining} 秒後再試'}), 429

    data = request.get_json()
    username = data.get('username', '').strip()
    pin = data.get('pin', '')

    if not username or not pin:
        return jsonify({'error': '請輸入名稱和 PIN 碼'}), 400
    if len(pin) != 4 or not pin.isdigit():
        return jsonify({'error': 'PIN 碼需為 4 位數字'}), 400

    result, is_new = get_or_create_user(username, pin)
    if result is None:
        _record_attempt(ip)
        return jsonify({'error': 'PIN 碼錯誤'}), 401

    # Success — clear rate limit
    _clear_attempts(ip)
    session['user_id'] = result['id']
    session['username'] = result['username']

    return jsonify({
        'success': True,
        'user': {'id': result['id'], 'username': result['username']},
        'is_new': is_new
    })


@bp.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


@bp.route('/api/me')
def api_me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'logged_in': False}), 401
    user = get_user(user_id)
    if not user:
        session.clear()
        return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'user': user})