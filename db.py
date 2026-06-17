import sqlite3
import hashlib
from flask import g
from config import DB_PATH

# ── Default habits template for new users ──
DEFAULT_HABITS = [
    # 🔴 Milestones (有截止日 + 子任務進度)
    {'name': 'CCNP 考試準備', 'icon': '🎯', 'type': 'number',  'schedule_type': 'daily',    'schedule_value': 1, 'target_value': 10, 'base_xp': 15, 'category': 'daily', 'sort_order': 1,
     'group': 'milestone', 'deadline': '2026-10-01'},
    {'name': 'IELTS 目標 7.5', 'icon': '🎧', 'type': 'number', 'schedule_type': 'daily',    'schedule_value': 1, 'target_value': 20, 'base_xp': 10, 'category': 'daily', 'sort_order': 2,
     'group': 'milestone', 'deadline': '2026-09-15'},

    # 🔵 累積目標 (週/月累積量)
    {'name': '游泳', 'icon': '🏊', 'type': 'timer',   'schedule_type': 'weekly_x', 'schedule_value': 3, 'target_value': 150, 'base_xp': 10, 'category': 'daily', 'sort_order': 3,
     'group': 'target', 'scope': 'weekly'},
    {'name': '額外閱讀',   'icon': '📖', 'type': 'timer',   'schedule_type': 'daily',    'schedule_value': 1, 'target_value': 600, 'base_xp': 5,  'category': 'bonus', 'sort_order': 8,
     'group': 'target', 'scope': 'monthly'},

    # 🟢 日常習慣 (每日進度 + 連續天數)
    {'name': '閱讀', 'icon': '📖', 'type': 'timer',   'schedule_type': 'daily',    'schedule_value': 1, 'target_value': 30, 'base_xp': 10, 'category': 'daily', 'sort_order': 4,
     'group': 'daily'},
    {'name': 'CCNP 練習', 'icon': '🎯', 'type': 'number',  'schedule_type': 'daily',    'schedule_value': 1, 'target_value': 10, 'base_xp': 15, 'category': 'daily', 'sort_order': 5,
     'group': 'daily'},
    {'name': 'IELTS 聽力', 'icon': '🎧', 'type': 'yesno',   'schedule_type': 'weekly_x', 'schedule_value': 4, 'target_value': 1,  'base_xp': 10, 'category': 'daily', 'sort_order': 6,
     'group': 'daily'},
    {'name': 'IELTS 閱讀', 'icon': '📝', 'type': 'yesno',   'schedule_type': 'weekly_x', 'schedule_value': 4, 'target_value': 1,  'base_xp': 10, 'category': 'daily', 'sort_order': 7,
     'group': 'daily'},
    {'name': '背單字',     'icon': '📚', 'type': 'number',  'schedule_type': 'daily',    'schedule_value': 1, 'target_value': 20, 'base_xp': 5,  'category': 'daily', 'sort_order': 9,
     'group': 'daily'},
    {'name': '寫作練習',   'icon': '✍️', 'type': 'yesno',   'schedule_type': 'weekly_x', 'schedule_value': 2, 'target_value': 1,  'base_xp': 10, 'category': 'bonus', 'sort_order': 10,
     'group': 'daily'},
    {'name': '週日複習',   'icon': '🔄', 'type': 'yesno',   'schedule_type': 'weekends', 'schedule_value': 1, 'target_value': 1,  'base_xp': 10, 'category': 'bonus', 'sort_order': 11,
     'group': 'daily'},
]

# Legacy task_id → habit name mapping (for data migration)
TASK_ID_TO_HABIT = {
    'read': '閱讀', 'swim': '游泳', 'ccnp': 'CCNP',
    'ielts_listen': 'IELTS 聽力', 'ielts_read': 'IELTS 閱讀',
    'vocab': '背單字', 'extra_read': '額外閱讀',
    'writing': '寫作練習', 'review': '週日複習', 'all_done': '全每日任務完成',
}


# ── Auth helpers ──
# Legacy hash (pre-migration, kept for verify only)
def _legacy_hash_pin(pin):
    return hashlib.sha256(f"qsalt_{pin}".encode()).hexdigest()

def hash_pin(pin):
    """Hash PIN with werkzeug (pbkdf2:sha256, random salt)."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(pin, method='pbkdf2:sha256', salt_length=16)

def verify_pin(pin, pin_hash):
    """Verify PIN against hash. Supports both legacy SHA256 and werkzeug."""
    from werkzeug.security import check_password_hash
    # New format (werkzeug): starts with 'pbkdf2:' or 'scrypt:'
    if pin_hash.startswith('pbkdf2:') or pin_hash.startswith('scrypt:'):
        return check_password_hash(pin_hash, pin)
    # Legacy format: plain SHA256 hex
    return _legacy_hash_pin(pin) == pin_hash


# ── DB connection ──
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


# ── Init + Migration ──
def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")

    # ── New schema ──
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pin_hash TEXT NOT NULL,
            avatar_emoji TEXT DEFAULT '🧑',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📌',
            type TEXT NOT NULL DEFAULT 'yesno',
            schedule_type TEXT NOT NULL DEFAULT 'daily',
            schedule_value INTEGER DEFAULT 1,
            target_value INTEGER DEFAULT 1,
            base_xp INTEGER DEFAULT 10,
            category TEXT DEFAULT 'daily',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS habit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            value INTEGER DEFAULT 1,
            xp INTEGER NOT NULL,
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
    ''')

    # ── Legacy tables: only needed for migration (created temporarily) ──
    # These are dropped after migration in _migrate_legacy_data cleanup below.
    db.executescript('''
        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            task_id TEXT NOT NULL,
            xp INTEGER NOT NULL,
            duration INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS xp_total (
            id INTEGER PRIMARY KEY CHECK (id=1),
            total_xp INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO xp_total (id, total_xp) VALUES (1, 0);
        CREATE TABLE IF NOT EXISTS achievements (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Migration: add duration column if missing
    try:
        db.execute('ALTER TABLE daily_log ADD COLUMN duration INTEGER DEFAULT NULL')
    except sqlite3.OperationalError:
        pass

    # site_config table (used for site title etc.)
    db.execute('''
        CREATE TABLE IF NOT EXISTS site_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    db.execute("INSERT OR IGNORE INTO site_config (key, value) VALUES ('title', 'Quest Log')")
    db.commit()

    # ── Migration: add group / deadline / scope columns to habits ──
    for col in ('"group"', 'deadline', '"scope"', 'best_streak'):
        try:
            db.execute(f'ALTER TABLE habits ADD COLUMN {col} TEXT DEFAULT NULL')
        except sqlite3.OperationalError:
            pass
    try:
        db.execute('ALTER TABLE habits ADD COLUMN best_streak INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    # Set default group for existing habits
    db.execute("UPDATE habits SET \"group\"='daily' WHERE \"group\" IS NULL")
    db.commit()

    # ── Migrate old data to new schema ──
    _migrate_legacy_data(db)

    # ── Clean up legacy tables (migration complete) ──
    for tbl in ('daily_log', 'xp_total', 'achievements'):
        try:
            db.execute(f'DROP TABLE IF EXISTS {tbl}')
        except sqlite3.OperationalError:
            pass
    db.commit()

    db.close()


def _migrate_legacy_data(db):
    """Migrate data from old tables (daily_log, xp_total, achievements) to new schema."""
    # Check if admin user exists
    admin = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if admin:
        admin_id = admin['id']
    else:
        # Create admin user with default PIN '0000'
        db.execute(
            "INSERT INTO users (username, pin_hash) VALUES (?, ?)",
            ('admin', hash_pin('0000'))
        )
        db.commit()
        admin_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Check if admin already has habits
    existing_habits = db.execute(
        "SELECT COUNT(*) FROM habits WHERE user_id=?", (admin_id,)
    ).fetchone()[0]

    if existing_habits == 0:
        # Load default habits for admin
        for h in DEFAULT_HABITS:
            db.execute(
                '''INSERT INTO habits (user_id, name, icon, type, schedule_type,
                   schedule_value, target_value, base_xp, category, sort_order,
                   "group", deadline, "scope")
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (admin_id, h['name'], h['icon'], h['type'],
                 h['schedule_type'], h['schedule_value'], h['target_value'],
                 h['base_xp'], h['category'], h['sort_order'],
                 h.get('group', 'daily'), h.get('deadline'), h.get('scope'))
            )
        db.commit()

    # Migrate daily_log → habit_log (only if habit_log is empty)
    log_count = db.execute(
        "SELECT COUNT(*) FROM habit_log WHERE user_id=?", (admin_id,)
    ).fetchone()[0]

    if log_count == 0:
        daily_rows = db.execute(
            "SELECT date, task_id, xp, duration, created_at FROM daily_log ORDER BY created_at"
        ).fetchall()

        if daily_rows:
            for row in daily_rows:
                habit_name = TASK_ID_TO_HABIT.get(row['task_id'])
                if not habit_name:
                    continue  # skip unknown task_ids

                habit = db.execute(
                    "SELECT id FROM habits WHERE user_id=? AND name=?",
                    (admin_id, habit_name)
                ).fetchone()
                if not habit:
                    continue

                value = row['duration'] if row['duration'] else (
                    row['xp'] // 10 + 1 if row['task_id'] in ('ccnp', 'vocab') else 1
                )

                db.execute(
                    '''INSERT INTO habit_log (user_id, habit_id, date, value, xp, created_at)
                       VALUES (?,?,?,?,?,?)''',
                    (admin_id, habit['id'], row['date'], value, row['xp'], row['created_at'])
                )

            db.commit()

    # Migrate xp_total → user_xp
    xp_row = db.execute("SELECT total_xp FROM xp_total WHERE id=1").fetchone()
    if xp_row and xp_row['total_xp'] > 0:
        db.execute(
            "INSERT OR IGNORE INTO user_xp (user_id, total_xp) VALUES (?, ?)",
            (admin_id, xp_row['total_xp'])
        )
        db.commit()

    # Migrate achievements → user_achievements
    old_achs = db.execute("SELECT id, name, unlocked_at FROM achievements").fetchall()
    if old_achs:
        for a in old_achs:
            db.execute(
                "INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?,?,?)",
                (admin_id, a['id'], a['unlocked_at'])
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
    """Login: return (user_dict, is_new)."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if user:
        if verify_pin(pin, user['pin_hash']):
            # Auto-upgrade legacy hash to werkzeug on successful login
            if not user['pin_hash'].startswith('pbkdf2:'):
                db.execute(
                    "UPDATE users SET pin_hash=? WHERE id=?",
                    (hash_pin(pin), user['id'])
                )
                db.commit()
            return dict(user), False
        return None, False  # wrong pin

    # Create new user
    db.execute(
        "INSERT INTO users (username, pin_hash) VALUES (?, ?)",
        (username, hash_pin(pin))
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Load default habits for new user
    for h in DEFAULT_HABITS:
        db.execute(
            '''INSERT INTO habits (user_id, name, icon, type, schedule_type,
               schedule_value, target_value, base_xp, category, sort_order,
               "group", deadline, "scope")
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (user_id, h['name'], h['icon'], h['type'],
             h['schedule_type'], h['schedule_value'], h['target_value'],
             h['base_xp'], h['category'], h['sort_order'],
             h.get('group', 'daily'), h.get('deadline'), h.get('scope'))
        )
    db.commit()

    # Init XP
    db.execute("INSERT OR IGNORE INTO user_xp (user_id, total_xp) VALUES (?, 0)", (user_id,))
    db.commit()

    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(user), True


def get_user(user_id):
    db = get_db()
    user = db.execute("SELECT id, username, avatar_emoji, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(user) if user else None


init_db()