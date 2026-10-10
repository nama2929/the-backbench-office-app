"""SQLite data layer for a private, single-host, small-team Streamlit application.

No accounts or messages leave this machine. Do not point an internet-hosted
Streamlit app at SQLite on an ephemeral filesystem.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

DATA_DIR = Path(os.environ.get('BACKBENCH_DATA_DIR', str(Path(__file__).parent / 'data')))
DB_PATH = DATA_DIR / 'backbenchers.sqlite3'
CATEGORIES = {'Appreciation', 'Team idea', 'Light moment'}
REACTIONS = {'👏', '💡', '😄'}
VOTES = {'Aye', 'No', 'Abstain'}
MOMENTS = {'Applause', 'Quick Poll', 'Tea Break', 'Team Challenge'}


def now() -> int:
    return int(time.time())


@contextmanager
def connect():
    """Open one short-lived connection; commit/rollback transactions and close."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA busy_timeout = 15000')
        conn.execute('PRAGMA foreign_keys=ON')
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
            CREATE TABLE IF NOT EXISTS room (
                id INTEGER PRIMARY KEY CHECK(id=1),
                name TEXT NOT NULL,
                code_salt TEXT NOT NULL, code_hash TEXT NOT NULL,
                admin_salt TEXT NOT NULL, admin_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL COLLATE NOCASE UNIQUE,
                pin_salt TEXT NOT NULL, pin_hash TEXT NOT NULL,
                joined_at INTEGER NOT NULL, last_seen INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, details TEXT NOT NULL,
                author_id TEXT NOT NULL REFERENCES members(id),
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')),
                created_at INTEGER NOT NULL, closed_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS votes (
                bill_id INTEGER NOT NULL REFERENCES bills(id),
                member_id TEXT NOT NULL REFERENCES members(id),
                choice TEXT NOT NULL CHECK(choice IN ('Aye','No','Abstain')),
                created_at INTEGER NOT NULL,
                PRIMARY KEY(bill_id,member_id)
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id TEXT NOT NULL REFERENCES members(id),
                category TEXT NOT NULL, body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reactions (
                post_id INTEGER NOT NULL REFERENCES posts(id),
                member_id TEXT NOT NULL REFERENCES members(id),
                reaction TEXT NOT NULL,
                PRIMARY KEY(post_id,member_id)
            );
            CREATE TABLE IF NOT EXISTS moments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL, title TEXT NOT NULL,
                detail TEXT NOT NULL,
                author_id TEXT NOT NULL REFERENCES members(id),
                created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_members_active ON members(last_seen);
            CREATE INDEX IF NOT EXISTS ix_posts_status ON posts(status, created_at);
            CREATE INDEX IF NOT EXISTS ix_moments_expiry ON moments(expires_at);
        ''')


def _key(secret: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', secret.encode('utf8'), bytes.fromhex(salt), 180_000).hex()


def _hash_secret(secret: str):
    salt = secrets.token_hex(16)
    return salt, _key(secret, salt)


def verify_secret(candidate: str, salt: str, expected: str) -> bool:
    return hmac.compare_digest(_key(candidate, salt), expected)


def room() -> dict | None:
    with connect() as c:
        row = c.execute('SELECT id, name, created_at FROM room WHERE id=1').fetchone()
        return dict(row) if row else None


def create_room(name: str, code: str, admin_pin: str) -> bool:
    name = name.strip()[:65]
    if not name or len(code.strip()) < 6 or len(admin_pin.strip()) < 6:
        raise ValueError('Enter a room name, access code (6+ characters), and host PIN (6+ characters).')
    a_salt, a_hash = _hash_secret(admin_pin.strip())
    c_salt, c_hash = _hash_secret(code.strip())
    with connect() as c:
        try:
            c.execute('INSERT INTO room VALUES (1,?,?,?,?,?,?)', (name, c_salt, c_hash, a_salt, a_hash, now()))
        except sqlite3.IntegrityError:
            return False
    return True


def validate_room_code(code: str) -> bool:
    with connect() as c:
        r = c.execute('SELECT code_salt,code_hash FROM room WHERE id=1').fetchone()
    return bool(r and verify_secret(code.strip(), r['code_salt'], r['code_hash']))


def validate_host_pin(pin: str) -> bool:
    with connect() as c:
        r = c.execute('SELECT admin_salt,admin_hash FROM room WHERE id=1').fetchone()
    return bool(r and verify_secret(pin.strip(), r['admin_salt'], r['admin_hash']))


def register(nickname: str, pin: str) -> dict:
    nickname = re.sub(r'\s+', ' ', nickname.strip())
    if not 2 <= len(nickname) <= 24 or len(pin) < 4 or len(pin) > 32:
        raise ValueError('Nickname must have 2–24 characters; personal PIN must have 4–32 characters.')
    if not re.fullmatch(r'[\w .-]+', nickname, re.UNICODE):
        raise ValueError('Use only letters, numbers, spaces, dots, underscores, or hyphens in nicknames.')
    salt, digest = _hash_secret(pin)
    member_id = secrets.token_hex(12)
    try:
        with connect() as c:
            c.execute('INSERT INTO members VALUES (?,?,?,?,?,?)',
                      (member_id, nickname, salt, digest, now(), now()))
    except sqlite3.IntegrityError as e:
        raise ValueError('Nickname already taken. Use the Returning Player tab if this is yours.') from e
    return {'id': member_id, 'nickname': nickname}


def login(nickname: str, pin: str) -> dict | None:
    with connect() as c:
        r = c.execute('SELECT * FROM members WHERE nickname=? COLLATE NOCASE', (nickname.strip(),)).fetchone()
    if r and verify_secret(pin, r['pin_salt'], r['pin_hash']):
        return {'id': r['id'], 'nickname': r['nickname']}
    return None


def heartbeat(member_id: str) -> None:
    with connect() as c:
        c.execute('UPDATE members SET last_seen=? WHERE id=?', (now(), member_id))


def members() -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT id,nickname,joined_at,last_seen FROM members ORDER BY nickname')]


def new_bill(member_id: str, title: str, details: str) -> int:
    title, details = title.strip(), details.strip()
    if not 5 <= len(title) <= 90 or len(details) > 400:
        raise ValueError('Bill title must be 5–90 characters; description can be up to 400 characters.')
    with connect() as c:
        cur = c.execute('INSERT INTO bills(title,details,author_id,created_at) VALUES(?,?,?,?)',
                        (title, details, member_id, now()))
        return cur.lastrowid


def bills() -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute('''
            SELECT b.*,m.nickname,
                (SELECT COUNT(*) FROM votes v WHERE v.bill_id=b.id AND v.choice='Aye') aye,
                (SELECT COUNT(*) FROM votes v WHERE v.bill_id=b.id AND v.choice='No') no,
                (SELECT COUNT(*) FROM votes v WHERE v.bill_id=b.id AND v.choice='Abstain') abstain
            FROM bills b JOIN members m ON m.id=b.author_id ORDER BY b.created_at DESC, b.id DESC LIMIT 60
        ''')]


def my_vote(bill_id: int, member_id: str) -> str | None:
    with connect() as c:
        r = c.execute('SELECT choice FROM votes WHERE bill_id=? AND member_id=?', (bill_id, member_id)).fetchone()
        return r['choice'] if r else None


def vote(bill_id: int, member_id: str, choice: str) -> None:
    if choice not in VOTES:
        raise ValueError('Invalid vote')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        r = c.execute('SELECT status FROM bills WHERE id=?', (bill_id,)).fetchone()
        if not r or r['status'] != 'open':
            raise ValueError('This vote is already closed.')
        c.execute('''INSERT INTO votes(bill_id,member_id,choice,created_at) VALUES(?,?,?,?)
            ON CONFLICT(bill_id,member_id) DO UPDATE SET choice=excluded.choice,created_at=excluded.created_at''',
                  (bill_id, member_id, choice, now()))
        c.commit()


def close_bill(bill_id: int) -> None:
    with connect() as c:
        c.execute("UPDATE bills SET status='closed',closed_at=? WHERE id=? AND status='open'", (now(), bill_id))


def add_post(member_id: str, category: str, body: str) -> int:
    body = body.strip()
    if category not in CATEGORIES or not 8 <= len(body) <= 350:
        raise ValueError('Choose a category and write 8–350 characters.')
    with connect() as c:
        cur = c.execute('INSERT INTO posts(author_id,category,body,status,created_at) VALUES(?,?,?,?,?)',
                        (member_id, category, body, 'pending', now()))
        return cur.lastrowid


def posts(status: str = 'approved', limit: int = 80) -> list[dict]:
    if status not in {'approved','pending','rejected'}:
        raise ValueError('Invalid post status')
    with connect() as c:
        return [dict(r) for r in c.execute('''
            SELECT p.*,m.nickname FROM posts p JOIN members m ON p.author_id=m.id
            WHERE p.status=? ORDER BY p.created_at DESC,p.id DESC LIMIT ?''', (status,limit))]


def moderate_post(post_id: int, status: str) -> None:
    if status not in {'approved','rejected'}:
        raise ValueError('Invalid moderation')
    with connect() as c:
        c.execute("UPDATE posts SET status=? WHERE id=? AND status='pending'", (status, post_id))


def react(post_id: int, member_id: str, reaction: str) -> None:
    if reaction not in REACTIONS:
        raise ValueError('Invalid reaction')
    with connect() as c:
        if not c.execute("SELECT 1 FROM posts WHERE id=? AND status='approved'",(post_id,)).fetchone():
            raise ValueError('This message is unavailable')
        c.execute('''INSERT INTO reactions(post_id,member_id,reaction) VALUES(?,?,?)
            ON CONFLICT(post_id,member_id) DO UPDATE SET reaction=excluded.reaction''',
                  (post_id,member_id,reaction))


def reactions_for(post_id: int) -> dict[str,int]:
    with connect() as c:
        counts = c.execute('SELECT reaction,COUNT(*) n FROM reactions WHERE post_id=? GROUP BY reaction', (post_id,))
        return {r['reaction']:r['n'] for r in counts}


def add_moment(member_id: str, kind: str, title: str, detail: str, duration: int = 30) -> int:
    title,detail = title.strip(),detail.strip()
    if kind not in MOMENTS or not 3 <= len(title) <= 90 or len(detail) > 240 or not 10 <= duration <= 120:
        raise ValueError('Invalid announcement or duration.')
    t=now()
    with connect() as c:
        cur=c.execute('''INSERT INTO moments(kind,title,detail,author_id,created_at,expires_at)
            VALUES (?,?,?,?,?,?)''',(kind,title,detail,member_id,t,t+duration))
        return cur.lastrowid


def current_moment() -> dict | None:
    with connect() as c:
        r=c.execute('SELECT * FROM moments WHERE expires_at>? ORDER BY id DESC LIMIT 1',(now(),)).fetchone()
        return dict(r) if r else None


def recent_moments() -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM moments ORDER BY id DESC LIMIT 20')]


def stats() -> dict:
    with connect() as c:
        people=c.execute('SELECT COUNT(*) FROM members').fetchone()[0]
        online=c.execute('SELECT COUNT(*) FROM members WHERE last_seen>=?',(now()-25,)).fetchone()[0]
        proposals=c.execute('SELECT COUNT(*) FROM bills').fetchone()[0]
        passed=c.execute("""SELECT COUNT(*) FROM bills b WHERE status='closed' AND
              (SELECT COUNT(*) FROM votes v WHERE v.bill_id=b.id AND choice='Aye') >
              (SELECT COUNT(*) FROM votes v WHERE v.bill_id=b.id AND choice='No')""").fetchone()[0]
        return dict(people=people,online=online,proposals=proposals,passed=passed)
