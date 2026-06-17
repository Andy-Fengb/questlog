"""Shared utilities for Quest Log routes."""
from functools import wraps
from flask import session, jsonify


def login_required(f):
    """Decorator: require logged-in user, pass user_id as first arg."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'not logged in'}), 401
        return f(user_id, *args, **kwargs)
    return decorated
