import hashlib
import hmac
import os
import secrets
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]

# Minimal .env reader so the run command needs no extra tooling; real env vars win.
_env = ROOT / '.env'
if _env.exists():
    for line in _env.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://campusresolve:campusresolve_local@localhost:5432/campusresolve')
UPLOAD_DIR = (ROOT / os.environ.get('UPLOAD_DIR', 'uploads')).resolve()
MAX_UPLOAD_BYTES = int(os.environ.get('MAX_UPLOAD_BYTES', 5 * 1024 * 1024))


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, options='-c timezone=UTC')


def get_conn():
    # shortcut: one connection per request, add psycopg_pool if load ever matters.
    with connect() as conn:
        yield conn


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200_000).hex()
    return f'pbkdf2$200000${salt}${digest}'


def verify_password(password: str, stored: str) -> bool:
    _, rounds, salt, digest = stored.split('$')
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(rounds)).hex()
    return hmac.compare_digest(candidate, digest)


DEPARTMENTS = ['IT', 'Facilities', 'Housekeeping', 'Academics', 'Transport']
CATEGORIES = [('Wi-Fi / Network', 'IT'), ('Classroom Equipment', 'IT'), ('Electrical', 'Facilities'),
              ('Plumbing', 'Facilities'), ('Cleanliness', 'Housekeeping'), ('Transport', 'Transport'), ('Other', None)]
LOCATIONS = ['Block A / Classrooms', 'Block B / Lab 204', 'Library', 'Hostel 1', 'Cafeteria', 'Sports Complex', 'Admin Block',
             'Main Gate / Bus Stop']
USERS = [('student@demo.edu', 'Demo Student', 'STUDENT', None), ('student2@demo.edu', 'Second Student', 'STUDENT', None),
         ('it.staff@demo.edu', 'IT Staff', 'STAFF', 'IT'), ('facilities.staff@demo.edu', 'Facilities Staff', 'STAFF', 'Facilities'),
         ('coordinator@demo.edu', 'Demo Coordinator', 'COORDINATOR', None), ('admin@demo.edu', 'Demo Admin', 'ADMIN', None)]
DEMO_PASSWORD = 'demo1234'  # fictional local-only seed accounts, documented in docs/API_CONTRACT.md


def init_db():
    with connect() as conn:
        conn.execute((Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8'))
        created = conn.execute("""INSERT INTO institutions (code, name) VALUES ('DEMO', 'Demo Institute of Technology (fictional)')
                                  ON CONFLICT (code) DO NOTHING RETURNING id""").fetchone()
        inst = conn.execute("SELECT id FROM institutions WHERE code = 'DEMO'").fetchone()['id']
        # Config is ensured on every start so seed additions (e.g. Transport) reach existing demo DBs; tickets are never touched.
        for name in DEPARTMENTS:
            conn.execute('INSERT INTO departments (institution_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING', (inst, name))
        dept = {r['name']: r['id'] for r in conn.execute('SELECT id, name FROM departments WHERE institution_id = %s', (inst,))}
        for name, d in CATEGORIES:
            conn.execute('INSERT INTO categories (institution_id, name, default_department_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                         (inst, name, dept.get(d)))
        for name in LOCATIONS:
            conn.execute('INSERT INTO locations (institution_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING', (inst, name))
        if not created:
            return
        for email, name, role, d in USERS:
            uid = conn.execute('INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) RETURNING id',
                               (email, name, hash_password(DEMO_PASSWORD))).fetchone()['id']
            conn.execute('INSERT INTO memberships (user_id, institution_id, role, department_id) VALUES (%s, %s, %s, %s)',
                         (uid, inst, role, dept.get(d)))
