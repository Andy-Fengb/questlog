from flask import Blueprint, request, jsonify

from db import get_config, set_config

bp = Blueprint('config_routes', __name__)


@bp.route('/api/save_config', methods=['POST'])
def api_save_config():
    data = request.get_json()
    key = data.get('key', '')
    value = data.get('value', '')
    if not key:
        return jsonify({'error': 'key is required'}), 400
    set_config(key, value)
    return jsonify({'success': True, 'key': key, 'value': value})


@bp.route('/api/get_config')
def api_get_config():
    key = request.args.get('key', '')
    if not key:
        return jsonify({'error': 'key is required'}), 400
    value = get_config(key)
    return jsonify({'key': key, 'value': value})