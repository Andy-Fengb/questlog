"""Quest Log v2 — Database schema & helpers."""
import sqlite3
import hashlib
from flask import g
from config import DB_PATH

# ── Default habits for new users ──
DEFAULT_HABITS = [
    # Binary habits (🟢 日常习惯)
    {'name': '游泳锻炼', 'icon': '🏊', 'task_type': 'binary', 'base_xp': 10, 'sort_order': 1},
    {'name': '按时吃药', 'icon': '💊', 'task_type': 'binary', 'base_xp': 5,  'sort_order': 2},
    {'name': '交易复盘', 'icon': '📊', 'task_type': 'binary', 'base_xp': 10, 'sort_order': 3},
    {'name': '冥想 10 分钟', 'icon': '🧘', 'task_type': 'binary', 'base_xp': 5,  'sort_order': 4},
    {'name': '英文阅读 30 分钟', 'icon': '📖', 'task_type': 'binary', 'base_xp': 15, 'sort_order': 5},
]

DEFAULT_SOP_STEPS = {
    'BBC 6 Min English': [
        {'step_order': 1, 'label': '盲听抓取', 'description': '纯听1-2遍，脑内回答 Quiz 题', 'xp': 5},
        {'step_order': 2, 'label': '断点盲写', 'description': '听写遇阻做记号，暴露听力弱点', 'xp': 10},
        {'step_order': 3, 'label': '文本对账', 'description': '对照 Transcript，核心词汇归档至 Trilium', 'xp': 10},
        {'step_order': 4, 'label': '影子跟读', 'description': '滞后1秒模仿发音语调，口腔肌肉记忆', 'xp': 15},
    ],
}


# ── Auth helpers ──
def _legacy_hash_pin(pin):
    return hashlib.sha256(f"qsalt_{pin}".encode()).hexdigest()

def hash_pin(pin):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(pin, method='pbkdf2:sha256', salt_length=16)

def verify_pin(pin, pin_hash):
    from werkzeug.security import check_password_hash
    if pin_hash.startswith('pbkdf2:') or pin_hash.startswith('scrypt:'):
        return check_password_hash(pin_hash, pin)
    return _legacy_hash_pin(pin) == pin_hash


# ── DB connection ──
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


# ── Init DB ──
def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")

    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pin_hash TEXT NOT NULL,
            avatar_emoji TEXT DEFAULT '🧑',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- v2: habits can be 'binary' or 'sop'
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📋',
            task_type TEXT NOT NULL DEFAULT 'binary',  -- 'binary' | 'sop'
            base_xp INTEGER DEFAULT 10,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- v2: SOP step definitions (only for task_type='sop')
        CREATE TABLE IF NOT EXISTS sop_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL,
            label TEXT NOT NULL,
            description TEXT,
            xp INTEGER DEFAULT 10,
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        );

        -- v2: unified log (binary completion + sop step completion)
        CREATE TABLE IF NOT EXISTS habit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            date TEXT NOT NULL,                        -- 'YYYY-MM-DD'
            completed_at TEXT,                         -- 'HH:MM' or full timestamp
            step_order INTEGER,                        -- SOP: which step; binary: NULL
            xp INTEGER DEFAULT 0,
            is_makeup INTEGER DEFAULT 0,               -- 0=normal, 1=makeup
            makeup_note TEXT,                          -- makeup metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        );

        CREATE TABLE IF NOT EXISTS user_xp (
            user_id INTEGER PRIMARY KEY,
            total_xp INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER NOT NULL,
            achievement_id TEXT NOT NULL,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, achievement_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_habit_log_date ON habit_log(date);
        CREATE INDEX IF NOT EXISTS idx_habit_log_user ON habit_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_habit_log_user_date ON habit_log(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
        CREATE INDEX IF NOT EXISTS idx_sop_steps_habit ON sop_steps(habit_id);
    ''')

    # site_config
    db.execute('''
        CREATE TABLE IF NOT EXISTS site_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    db.execute("INSERT OR IGNORE INTO site_config (key, value) VALUES ('title', 'Quest Log')")
    db.commit()
    db.close()


def _seed_default_data(db, user_id):
    """Load default habits + SOP steps for a new user."""
    existing = db.execute("SELECT COUNT(*) FROM habits WHERE user_id=?", (user_id,)).fetchone()[0]
    if existing > 0:
        return

    for h in DEFAULT_HABITS:
        db.execute(
            '''INSERT INTO habits (user_id, name, icon, task_type, base_xp, sort_order)
               VALUES (?,?,?,?,?,?)''',
            (user_id, h['name'], h['icon'], h['task_type'], h['base_xp'], h['sort_order'])
        )
    db.commit()

    # SOP habits
    sop_habits = [
        ('BBC 6 Min English', '🎧', 'sop', 40, 10),
    ]
    for name, icon, task_type, base_xp, sort_order in sop_habits:
        db.execute(
            '''INSERT INTO habits (user_id, name, icon, task_type, base_xp, sort_order)
               VALUES (?,?,?,?,?,?)''',
            (user_id, name, icon, task_type, base_xp, sort_order)
        )
        habit_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for step in DEFAULT_SOP_STEPS.get(name, []):
            db.execute(
                '''INSERT INTO sop_steps (habit_id, step_order, label, description, xp)
                   VALUES (?,?,?,?,?)''',
                (habit_id, step['step_order'], step['label'], step['description'], step['xp'])
            )
    db.commit()


# ── Site config helpers ──
def get_config(key, default=''):
    db = get_db()
    row = db.execute('SELECT value FROM site_config WHERE key=?', (key,)).fetchone()
    return row['value'] if row else default

def set_config(key, value):
    db = get_db()
    db.execute('INSERT OR REPLACE INTO site_config (key, value) VALUES (?,?)', (key, value))
    db.commit()


# ── User helpers ──
def get_or_create_user(username, pin):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if user:
        if verify_pin(pin, user['pin_hash']):
            if not user['pin_hash'].startswith('pbkdf2:'):
                db.execute("UPDATE users SET pin_hash=? WHERE id=?", (hash_pin(pin), user['id']))
                db.commit()
            return dict(user), False
        return None, False

    db.execute("INSERT INTO users (username, pin_hash) VALUES (?, ?)", (username, hash_pin(pin)))
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    _seed_default_data(db, user_id)
    db.execute("INSERT OR IGNORE INTO user_xp (user_id, total_xp) VALUES (?, 0)", (user_id,))
    db.commit()

    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(user), True


def get_user(user_id):
    db = get_db()
    user = db.execute("SELECT id, username, avatar_emoji, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(user) if user else None


init_db()
