import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import errors, sql

from . import ai
from .db import MAX_UPLOAD_BYTES, UPLOAD_DIR, get_conn, init_db, verify_password
from .models import (AdminReport, AIAnalysis, AssignmentInput, Category, CategoryInput, CommonIssue, CommonIssues, Complaint,
                     ComplaintCreate,
                     ComplaintPatch, Department, DepartmentInput, Feedback, FeedbackInput, HistoryEntry, Insights,
                     Institution, Location, LoginInput, LoginResult, QueryInput, QueryPlan, QueryResult, ReportInput, Staff,
                     Stats, StatusInput, User)

_secret = os.environ.get('AUTH_SECRET', '')
# Without a configured secret, tokens are only valid until the server restarts.
AUTH_SECRET = _secret if _secret and not _secret.startswith('REPLACE_') else secrets.token_urlsafe(32)
TOKEN_HOURS = 8
OPS = ('ADMIN', 'COORDINATOR')
TERMINAL = ('RESOLVED', 'REJECTED')
TRANSITIONS = {'SUBMITTED': {'IN_PROGRESS', 'REJECTED'}, 'IN_PROGRESS': {'RESOLVED', 'REJECTED'}}


@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title='CampusResolve AI API', version='0.2.0', lifespan=lifespan)
api = APIRouter(prefix='/api/v1')
bearer = HTTPBearer(auto_error=False)


def fail(code: int, detail: str):
    raise HTTPException(code, detail)


# ---------- auth ----------

def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), conn=Depends(get_conn)) -> dict:
    if not cred:
        fail(401, 'Not authenticated')
    try:
        claims = jwt.decode(cred.credentials, AUTH_SECRET, algorithms=['HS256'])
    except jwt.PyJWTError:
        fail(401, 'Invalid or expired token')
    me = conn.execute(
        '''SELECT u.id, u.name, m.role, m.institution_id, m.department_id FROM users u
           JOIN memberships m ON m.user_id = u.id AND m.is_active
           WHERE u.id = %s AND m.institution_id = %s''', (int(claims['sub']), claims['ins'])).fetchone()
    if not me:
        fail(401, 'Membership is no longer active')
    return me


def need(me: dict, *roles: str):
    if me['role'] not in roles:
        fail(403, 'Your role cannot perform this action')


@api.post('/auth/login', response_model=LoginResult)
def login(body: LoginInput, conn=Depends(get_conn)):
    row = conn.execute(
        '''SELECT u.id, u.name, u.password_hash, m.role, m.institution_id, m.department_id FROM users u
           JOIN memberships m ON m.user_id = u.id AND m.is_active WHERE lower(u.email) = lower(%s)
           ORDER BY m.id LIMIT 1''', (body.email.strip(),)).fetchone()
    if not row or not verify_password(body.password, row.pop('password_hash')):
        fail(401, 'Invalid email or password')
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    token = jwt.encode({'sub': str(row['id']), 'ins': row['institution_id'], 'exp': exp}, AUTH_SECRET, algorithm='HS256')
    return {'access_token': token, 'token_type': 'bearer', 'user': row}


@api.get('/auth/me', response_model=User)
def me_route(me=Depends(current_user)):
    return me


@api.get('/institutions/current', response_model=Institution)
def current_institution(me=Depends(current_user), conn=Depends(get_conn)):
    return conn.execute('SELECT id, code, name FROM institutions WHERE id = %s', (me['institution_id'],)).fetchone()


@api.get('/locations', response_model=list[Location])
def list_locations(me=Depends(current_user), conn=Depends(get_conn)):
    return conn.execute('SELECT id, name FROM locations WHERE institution_id = %s ORDER BY name', (me['institution_id'],)).fetchall()


# ---------- configuration ----------

def active_department(conn, me, dept_id: int, code=422):
    row = conn.execute('SELECT id FROM departments WHERE id = %s AND institution_id = %s AND is_active',
                       (dept_id, me['institution_id'])).fetchone()
    if not row:
        fail(code, 'Department is not an active department of your institution')


@api.get('/departments', response_model=list[Department])
def list_departments(me=Depends(current_user), conn=Depends(get_conn)):
    return conn.execute('SELECT id, name, is_active FROM departments WHERE institution_id = %s AND is_active ORDER BY name',
                        (me['institution_id'],)).fetchall()


@api.post('/departments', response_model=Department, status_code=201)
def create_department(body: DepartmentInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    try:
        row = conn.execute('INSERT INTO departments (institution_id, name) VALUES (%s, %s) RETURNING id, name, is_active',
                           (me['institution_id'], body.name.strip())).fetchone()
    except errors.UniqueViolation:
        fail(409, 'A department with this name already exists')
    conn.commit()
    return row


@api.patch('/departments/{id}', response_model=Department)
def update_department(id: int, body: DepartmentInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    try:
        row = conn.execute('UPDATE departments SET name = %s WHERE id = %s AND institution_id = %s RETURNING id, name, is_active',
                           (body.name.strip(), id, me['institution_id'])).fetchone()
    except errors.UniqueViolation:
        fail(409, 'A department with this name already exists')
    if not row:
        fail(404, 'Department not found')
    conn.commit()
    return row


@api.delete('/departments/{id}', status_code=204)
def deactivate_department(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    if conn.execute('UPDATE departments SET is_active = false WHERE id = %s AND institution_id = %s',
                    (id, me['institution_id'])).rowcount == 0:
        fail(404, 'Department not found')
    conn.commit()
    return Response(status_code=204)


CATEGORY_COLS = 'id, name, default_department_id, is_active'


@api.get('/categories', response_model=list[Category])
def list_categories(me=Depends(current_user), conn=Depends(get_conn)):
    return conn.execute(f'SELECT {CATEGORY_COLS} FROM categories WHERE institution_id = %s AND is_active ORDER BY name',
                        (me['institution_id'],)).fetchall()


@api.post('/categories', response_model=Category, status_code=201)
def create_category(body: CategoryInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    if body.default_department_id is not None:
        active_department(conn, me, body.default_department_id)
    try:
        row = conn.execute(f'INSERT INTO categories (institution_id, name, default_department_id) VALUES (%s, %s, %s) RETURNING {CATEGORY_COLS}',
                           (me['institution_id'], body.name.strip(), body.default_department_id)).fetchone()
    except errors.UniqueViolation:
        fail(409, 'A category with this name already exists')
    conn.commit()
    return row


@api.patch('/categories/{id}', response_model=Category)
def update_category(id: int, body: CategoryInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    if body.default_department_id is not None:
        active_department(conn, me, body.default_department_id)
    try:
        row = conn.execute(f'''UPDATE categories SET name = %s, default_department_id = %s
                               WHERE id = %s AND institution_id = %s RETURNING {CATEGORY_COLS}''',
                           (body.name.strip(), body.default_department_id, id, me['institution_id'])).fetchone()
    except errors.UniqueViolation:
        fail(409, 'A category with this name already exists')
    if not row:
        fail(404, 'Category not found')
    conn.commit()
    return row


@api.delete('/categories/{id}', status_code=204)
def deactivate_category(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    if conn.execute('UPDATE categories SET is_active = false WHERE id = %s AND institution_id = %s',
                    (id, me['institution_id'])).rowcount == 0:
        fail(404, 'Category not found')
    conn.commit()
    return Response(status_code=204)


@api.get('/staff', response_model=list[Staff])
def list_staff(department_id: int = Query(ge=1), me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    active_department(conn, me, department_id, code=404)
    return conn.execute(
        '''SELECT u.id, u.name, m.department_id FROM memberships m JOIN users u ON u.id = m.user_id
           WHERE m.institution_id = %s AND m.department_id = %s AND m.role = 'STAFF' AND m.is_active ORDER BY u.name''',
        (me['institution_id'], department_id)).fetchall()


# ---------- complaints ----------

VISIBLE = '''c.institution_id = %(ins)s AND NOT c.archived AND (
  c.reporter_user_id = %(uid)s OR %(role)s IN ('ADMIN', 'COORDINATOR')
  OR (%(role)s = 'STAFF' AND c.assigned_department_id = %(dept)s
      AND (c.assigned_user_id IS NULL OR c.assigned_user_id = %(uid)s)))'''


def scope(me: dict) -> dict:
    return {'ins': me['institution_id'], 'uid': me['id'], 'role': me['role'], 'dept': me['department_id']}


def out(c: dict) -> dict:
    return {**c, 'image_url': f"/api/v1/complaints/{c['id']}/image" if c['image_path'] else None}


def load(conn, me, cid: int, lock=False) -> dict:
    c = conn.execute(f"SELECT * FROM complaints c WHERE c.id = %(cid)s AND {VISIBLE}{' FOR UPDATE' if lock else ''}",
                     {**scope(me), 'cid': cid}).fetchone()
    if not c:
        fail(404, 'Complaint not found')
    return c


def can_work(me: dict, c: dict) -> bool:
    return me['role'] in OPS or (me['role'] == 'STAFF' and c['assigned_department_id'] == me['department_id']
                                 and c['assigned_user_id'] in (None, me['id']))


def check_location(conn, me, name: str):
    if not conn.execute('SELECT 1 FROM locations WHERE institution_id = %s AND name = %s', (me['institution_id'], name)).fetchone():
        fail(422, 'location must be one of the names from GET /api/v1/locations')


def check_category(conn, me, category_id: int):
    if not conn.execute('SELECT 1 FROM categories WHERE id = %s AND institution_id = %s AND is_active',
                        (category_id, me['institution_id'])).fetchone():
        fail(422, 'category_id is not an active category of your institution')


def rule_department(conn, category_id: int | None) -> int | None:
    if category_id is None:
        return None
    row = conn.execute('''SELECT d.id FROM categories c JOIN departments d ON d.id = c.default_department_id AND d.is_active
                          WHERE c.id = %s''', (category_id,)).fetchone()
    return row['id'] if row else None


def record_assignment(conn, cid, actor, dept, user, note):
    conn.execute('INSERT INTO assignments (complaint_id, actor_user_id, department_id, assigned_user_id, note) VALUES (%s, %s, %s, %s, %s)',
                 (cid, actor, dept, user, note))


def record_status(conn, cid, actor, old, new, note):
    conn.execute('INSERT INTO complaint_status_history (complaint_id, actor_user_id, old_status, new_status, note) VALUES (%s, %s, %s, %s, %s)',
                 (cid, actor, old, new, note))


@api.post('/complaints', response_model=Complaint, status_code=201)
def create_complaint(body: ComplaintCreate, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'STUDENT', 'STAFF')
    check_location(conn, me, body.location)
    if body.category_id is not None:
        check_category(conn, me, body.category_id)
    dept = rule_department(conn, body.category_id)
    c = conn.execute('''INSERT INTO complaints (institution_id, reporter_user_id, title, description, location, category_id, assigned_department_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *''',
                     (me['institution_id'], me['id'], body.title.strip(), body.description.strip(), body.location,
                      body.category_id, dept)).fetchone()
    record_status(conn, c['id'], me['id'], None, 'SUBMITTED', None)
    if dept:
        record_assignment(conn, c['id'], me['id'], dept, None, 'Rule-based routing from category')
    conn.commit()
    return out(c)


@api.get('/complaints', response_model=list[Complaint])
def list_complaints(status: str | None = Query(None, pattern='^(SUBMITTED|IN_PROGRESS|RESOLVED|REJECTED)$'),
                    category_id: int | None = Query(None, ge=1), mine: bool = False,
                    me=Depends(current_user), conn=Depends(get_conn)):
    # Filters only narrow VISIBLE; they never widen access.
    where = [VISIBLE]
    params = {**scope(me), 'status': status, 'category_id': category_id}
    if status:
        where.append('c.status = %(status)s')
    if category_id:
        where.append('c.category_id = %(category_id)s')
    if mine:
        where.append('c.reporter_user_id = %(uid)s')
    rows = conn.execute(f"SELECT * FROM complaints c WHERE {' AND '.join(where)} ORDER BY c.created_at DESC, c.id DESC", params).fetchall()
    return [out(c) for c in rows]


@api.get('/complaints/{id}', response_model=Complaint)
def get_complaint(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    return out(load(conn, me, id))


@api.patch('/complaints/{id}', response_model=Complaint)
def update_complaint(id: int, body: ComplaintPatch, me=Depends(current_user), conn=Depends(get_conn)):
    fields = body.model_fields_set
    if not fields:
        fail(422, 'Provide at least one field to update')
    for f in fields & {'title', 'description', 'location', 'priority'}:
        if getattr(body, f) is None:
            fail(422, f'{f} cannot be null')
    c = load(conn, me, id, lock=True)
    if c['reporter_user_id'] == me['id'] and fields <= {'title', 'description', 'location', 'category_id'}:
        if c['status'] != 'SUBMITTED':
            fail(409, 'Reports can only be edited while SUBMITTED')
    elif me['role'] in OPS and fields <= {'category_id', 'priority'}:
        if c['status'] in TERMINAL:
            fail(409, 'Closed tickets cannot be edited')
    else:
        fail(403, 'You cannot change these fields')
    if 'location' in fields:
        check_location(conn, me, body.location)
    updates = {f: getattr(body, f).strip() if f in ('title', 'description') else getattr(body, f) for f in fields}
    if 'category_id' in fields and body.category_id != c['category_id']:
        if body.category_id is not None:
            check_category(conn, me, body.category_id)
        dept = rule_department(conn, body.category_id)
        if dept is None and c['status'] == 'IN_PROGRESS':
            dept = c['assigned_department_id']  # IN_PROGRESS requires a department; keep the current one
        if dept != c['assigned_department_id']:
            updates.update(assigned_department_id=dept, assigned_user_id=None)
            record_assignment(conn, id, me['id'], dept, None,
                              'Category changed; routing reapplied' if dept else 'Category changed; routed to admin review')
    assignments = sql.SQL(', ').join(sql.SQL('{} = {}').format(sql.Identifier(k), sql.Placeholder(k)) for k in updates)
    c = conn.execute(sql.SQL('UPDATE complaints SET {}, updated_at = now() WHERE id = %(id)s RETURNING *').format(assignments),
                     {**updates, 'id': id}).fetchone()
    conn.commit()
    return out(c)


@api.delete('/complaints/{id}', status_code=204)
def archive_complaint(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, 'ADMIN')
    load(conn, me, id, lock=True)
    conn.execute('UPDATE complaints SET archived = true, updated_at = now() WHERE id = %s', (id,))
    conn.commit()
    return Response(status_code=204)


@api.post('/complaints/{id}/image', response_model=Complaint)
def upload_image(id: int, file: UploadFile = File(...), me=Depends(current_user), conn=Depends(get_conn)):
    c = load(conn, me, id, lock=True)
    if c['reporter_user_id'] != me['id']:
        fail(403, 'Only the reporter can attach an image')
    if c['status'] != 'SUBMITTED':
        fail(409, 'Images can only be attached while SUBMITTED')
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        fail(422, f'Image must be at most {MAX_UPLOAD_BYTES / 1048576:g} MiB')
    # Trust the file signature, not the client-declared content type.
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        ext, mime = 'png', 'image/png'
    elif data.startswith(b'\xff\xd8\xff'):
        ext, mime = 'jpg', 'image/jpeg'
    else:
        fail(422, 'Image must be a JPEG or PNG file')
    name = f'{id}-{secrets.token_hex(8)}.{ext}'
    # Stored in PostgreSQL, not on disk: serverless hosts (Vercel) keep no files between requests.
    conn.execute('''INSERT INTO complaint_images (complaint_id, data) VALUES (%s, %s)
                    ON CONFLICT (complaint_id) DO UPDATE SET data = EXCLUDED.data''', (id, data))
    old = c['image_path']
    c = conn.execute('UPDATE complaints SET image_path = %s, image_type = %s, updated_at = now() WHERE id = %s RETURNING *',
                     (name, mime, id)).fetchone()
    conn.commit()
    if old:
        (UPLOAD_DIR / old).unlink(missing_ok=True)
    return out(c)


@api.get('/complaints/{id}/image', response_class=FileResponse,
         responses={200: {'content': {'image/jpeg': {}, 'image/png': {}}}})
def read_image(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    c = load(conn, me, id)
    row = conn.execute('SELECT data FROM complaint_images WHERE complaint_id = %s', (id,)).fetchone()
    if row and c['image_path']:
        return Response(bytes(row['data']), media_type=c['image_type'])
    if c['image_path'] and (UPLOAD_DIR / c['image_path']).is_file():  # uploaded before images moved to the database
        return FileResponse(UPLOAD_DIR / c['image_path'], media_type=c['image_type'])
    fail(404, 'No image attached')


@api.patch('/complaints/{id}/assign', response_model=Complaint)
def assign_complaint(id: int, body: AssignmentInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    c = load(conn, me, id, lock=True)
    if c['status'] in TERMINAL:
        fail(409, 'Closed tickets cannot be reassigned')
    active_department(conn, me, body.department_id)
    if body.assigned_user_id is not None and not conn.execute(
            '''SELECT 1 FROM memberships WHERE user_id = %s AND institution_id = %s AND department_id = %s
               AND role = 'STAFF' AND is_active''', (body.assigned_user_id, me['institution_id'], body.department_id)).fetchone():
        fail(422, 'assigned_user_id must be active staff of that department')
    c = conn.execute('''UPDATE complaints SET assigned_department_id = %s, assigned_user_id = %s, updated_at = now()
                        WHERE id = %s RETURNING *''', (body.department_id, body.assigned_user_id, id)).fetchone()
    record_assignment(conn, id, me['id'], body.department_id, body.assigned_user_id, None)
    conn.commit()
    return out(c)


@api.patch('/complaints/{id}/status', response_model=Complaint)
def change_status(id: int, body: StatusInput, me=Depends(current_user), conn=Depends(get_conn)):
    c = load(conn, me, id, lock=True)
    if not can_work(me, c):
        fail(403, 'Only admins, coordinators, or assigned department staff can change status')
    if body.status not in TRANSITIONS.get(c['status'], ()):
        fail(409, f"Cannot move from {c['status']} to {body.status}")
    if body.status == 'IN_PROGRESS' and c['assigned_department_id'] is None:
        fail(409, 'Assign a department before starting work')
    note = (body.note or '').strip() or None
    if body.status in TERMINAL and not note:
        fail(422, 'An outcome note is required to resolve or reject')
    old = c['status']
    c = conn.execute('''UPDATE complaints SET status = %s, updated_at = now(),
                        resolved_at = CASE WHEN %s = 'RESOLVED' THEN now() ELSE resolved_at END
                        WHERE id = %s RETURNING *''', (body.status, body.status, id)).fetchone()
    record_status(conn, id, me['id'], old, body.status, note)
    conn.commit()
    return out(c)


@api.get('/complaints/{id}/history', response_model=list[HistoryEntry])
def get_history(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    load(conn, me, id)
    return conn.execute(
        '''SELECT id, 'STATUS' AS kind, actor_user_id, old_status, new_status, NULL::int AS department_id,
                  NULL::int AS assigned_user_id, note, created_at FROM complaint_status_history WHERE complaint_id = %(id)s
           UNION ALL
           SELECT id, 'ASSIGNMENT', actor_user_id, NULL, NULL, department_id, assigned_user_id, note, created_at
           FROM assignments WHERE complaint_id = %(id)s
           ORDER BY created_at, kind DESC''', {'id': id}).fetchall()


# ---------- feedback ----------

FEEDBACK_COLS = 'id, complaint_id, author_user_id, rating, comment, created_at'


def feedback_target(conn, me, cid: int):
    c = load(conn, me, cid, lock=True)
    if c['reporter_user_id'] != me['id']:
        fail(403, 'Only the original reporter manages feedback')
    if c['status'] != 'RESOLVED':
        fail(409, 'Feedback is only available on RESOLVED tickets')


@api.get('/complaints/{id}/feedback', response_model=Feedback)
def get_feedback(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    feedback_target(conn, me, id)
    row = conn.execute(f'SELECT {FEEDBACK_COLS} FROM feedback WHERE complaint_id = %s', (id,)).fetchone()
    if not row:
        fail(404, 'No feedback yet')
    return row


@api.post('/complaints/{id}/feedback', response_model=Feedback, status_code=201)
def post_feedback(id: int, body: FeedbackInput, me=Depends(current_user), conn=Depends(get_conn)):
    feedback_target(conn, me, id)
    row = conn.execute(f'''INSERT INTO feedback (complaint_id, author_user_id, rating, comment) VALUES (%s, %s, %s, %s)
                           ON CONFLICT (complaint_id) DO NOTHING RETURNING {FEEDBACK_COLS}''',
                       (id, me['id'], body.rating, body.comment)).fetchone()
    if not row:
        fail(409, 'Feedback already exists; use PATCH')
    conn.commit()
    return row


@api.patch('/complaints/{id}/feedback', response_model=Feedback)
def patch_feedback(id: int, body: FeedbackInput, me=Depends(current_user), conn=Depends(get_conn)):
    feedback_target(conn, me, id)
    row = conn.execute(f'UPDATE feedback SET rating = %s, comment = %s WHERE complaint_id = %s RETURNING {FEEDBACK_COLS}',
                       (body.rating, body.comment, id)).fetchone()
    if not row:
        fail(404, 'No feedback yet')
    conn.commit()
    return row


@api.delete('/complaints/{id}/feedback', status_code=204)
def delete_feedback(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    feedback_target(conn, me, id)
    if conn.execute('DELETE FROM feedback WHERE complaint_id = %s', (id,)).rowcount == 0:
        fail(404, 'No feedback yet')
    conn.commit()
    return Response(status_code=204)


# ---------- analytics ----------

def hours(value) -> float | None:
    return None if value is None else round(float(value), 2)


def by_category(conn, where: str, params) -> list[dict]:
    return conn.execute(f'''SELECT c.category_id, coalesce(cat.name, 'Uncategorized') AS category, count(*) AS count
                            FROM complaints c LEFT JOIN categories cat ON cat.id = c.category_id WHERE {where}
                            GROUP BY 1, 2 ORDER BY 3 DESC, 2''', params).fetchall()


RESOLUTION_AVG = "avg(extract(epoch FROM c.resolved_at - c.created_at) / 3600) FILTER (WHERE c.status = 'RESOLVED')"


@api.get('/dashboard/stats', response_model=Stats)
def dashboard_stats(me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    where, params = 'c.institution_id = %(ins)s AND NOT c.archived', {'ins': me['institution_id']}
    row = conn.execute(f'''SELECT count(*) AS total,
                             count(*) FILTER (WHERE c.status = 'SUBMITTED') AS submitted,
                             count(*) FILTER (WHERE c.status = 'IN_PROGRESS') AS in_progress,
                             count(*) FILTER (WHERE c.status = 'RESOLVED') AS resolved,
                             count(*) FILTER (WHERE c.status = 'REJECTED') AS rejected,
                             {RESOLUTION_AVG} AS avg FROM complaints c WHERE {where}''', params).fetchone()
    return {**row, 'resolved_count': row['resolved'], 'avg_resolution_hours': hours(row.pop('avg')),
            'by_category': by_category(conn, where, params)}


def compute_insights(conn, me, start, end) -> dict:
    if start > end:
        fail(422, 'from must be on or before to')
    if (end - start).days + 1 > 366:
        fail(422, 'Date range is limited to 366 days')
    # Cohort: created in [from 00:00, day after to 00:00) UTC; counts reflect current status.
    where = 'c.institution_id = %(ins)s AND NOT c.archived AND c.created_at >= %(start)s AND c.created_at < %(end)s'
    params = {'ins': me['institution_id'], 'start': start, 'end': end + timedelta(days=1)}
    row = conn.execute(f'''SELECT count(*) AS sample_size,
                             count(*) FILTER (WHERE c.status IN ('SUBMITTED', 'IN_PROGRESS')) AS unresolved,
                             count(*) FILTER (WHERE c.status IN ('SUBMITTED', 'IN_PROGRESS') AND c.priority = 'HIGH') AS high_priority_unresolved,
                             count(*) FILTER (WHERE c.status = 'RESOLVED') AS resolved_count,
                             {RESOLUTION_AVG} AS avg, now() AS generated_at FROM complaints c WHERE {where}''', params).fetchone()
    by_location = conn.execute(f'''SELECT c.category_id, coalesce(cat.name, 'Uncategorized') AS category, c.location, count(*) AS count
                                   FROM complaints c LEFT JOIN categories cat ON cat.id = c.category_id WHERE {where}
                                   GROUP BY 1, 2, 3 ORDER BY 4 DESC, 3, 2''', params).fetchall()
    oldest = conn.execute(f'''SELECT c.id AS complaint_id, c.ticket_number, c.location, c.priority,
                                     round((extract(epoch FROM now() - c.created_at) / 3600)::numeric, 2)::float AS age_hours
                              FROM complaints c WHERE {where} AND c.status IN ('SUBMITTED', 'IN_PROGRESS')
                              ORDER BY c.created_at LIMIT 5''', params).fetchall()
    return {**row, 'period': {'from': start, 'to': end}, 'avg_resolution_hours': hours(row.pop('avg')),
            'by_category': by_category(conn, where, params), 'by_location': by_location, 'oldest_unresolved': oldest}


@api.get('/dashboard/insights', response_model=Insights)
def dashboard_insights(from_: date = Query(alias='from'), to: date = Query(),
                       me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    return compute_insights(conn, me, from_, to)


def rules_report(insights: dict, departments: dict[int, int | None]) -> dict:
    """Labelled rules fallback: restates computed figures, never causes, costs or trends."""
    period, n = insights['period'], insights['sample_size']
    base = {'period': period, 'sample_size': n, 'generated_at': insights['generated_at'], 'source': 'rules'}
    if n == 0:
        return {**base, 'summary': f"No tickets were reported from {period['from']} to {period['to']}; there is insufficient data for recommendations.",
                'recommendations': []}
    avg = insights['avg_resolution_hours']
    summary = (f"{n} tickets reported from {period['from']} to {period['to']}: {insights['unresolved']} unresolved "
               f"({insights['high_priority_unresolved']} high priority), {insights['resolved_count']} resolved"
               + (f', average resolution {avg} hours.' if avg is not None else '.'))
    recs = []
    if insights['high_priority_unresolved']:
        recs.append({'title': 'Review high-priority unresolved tickets',
                     'evidence': f"{insights['high_priority_unresolved']} high-priority tickets are still unresolved.",
                     'department_id': None, 'next_step': 'Confirm each priority with staff and assign an owner.', 'horizon': 'IMMEDIATE'})
    for top in insights['by_category'][:2]:
        recs.append({'title': f"Assess recurring {top['category']} reports",
                     'evidence': f"{top['count']} of {n} tickets in this period are {top['category']}.",
                     'department_id': departments.get(top['category_id']),
                     'next_step': 'Inspect the most-reported locations before deciding on repairs.', 'horizon': 'ASSESSMENT'})
    return {**base, 'summary': summary, 'recommendations': recs[:3]}


@api.post('/dashboard/insights/report', response_model=AdminReport)
def generate_report(body: ReportInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    insights = compute_insights(conn, me, body.from_, body.to)
    departments = {r['id']: r['department_id'] for r in conn.execute(
        '''SELECT c.id, d.id AS department_id FROM categories c LEFT JOIN departments d ON d.id = c.default_department_id AND d.is_active
           WHERE c.institution_id = %s''', (me['institution_id'],)).fetchall()}
    tickets = issue_tickets(conn, *cohort(me, body.from_, body.to))
    report = None
    fn = getattr(ai, 'generate_admin_report', None)
    if fn:
        try:
            candidate = AdminReport.model_validate(fn(Insights.model_validate(insights).model_dump(mode='json', by_alias=True),
                                                      [t['text'] for t in tickets][:insights['sample_size']]))
            if all(r.department_id in (None, *departments.values()) for r in candidate.recommendations):
                report = candidate.model_dump(mode='json', by_alias=True)
        except Exception:
            pass  # invalid or failing AI output falls back to the labelled rules report
    return {**(report or rules_report(insights, departments)), 'common_issues': common_issues(conn, me, tickets)}


MANUAL_REVIEW = {'category_id': None, 'suggested_department_id': None, 'priority': 'NORMAL',
                 'summary': 'A campus issue needs review.', 'reason': 'Automatic suggestions are unavailable; review manually.',
                 'suggested_actions': ['Ask the reporter for the exact location and impact.'], 'source': 'rules', 'needs_review': True}


@api.post('/complaints/{id}/analyze', response_model=AIAnalysis)
def analyze_complaint(id: int, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    c = load(conn, me, id)
    categories = conn.execute('SELECT id, name, default_department_id FROM categories WHERE institution_id = %s AND is_active',
                              (me['institution_id'],)).fetchall()
    departments = conn.execute('SELECT id, name FROM departments WHERE institution_id = %s AND is_active',
                               (me['institution_id'],)).fetchall()
    fn = getattr(ai, 'analyze_complaint', None)
    if fn:
        try:
            result = AIAnalysis.model_validate(fn(c['title'], c['description'], categories, departments))
            if result.category_id in (None, *(x['id'] for x in categories)) and \
                    result.suggested_department_id in (None, *(x['id'] for x in departments)):
                return result  # suggestions only; the ticket is not modified
        except Exception:
            pass  # never break the workflow on AI errors
    return MANUAL_REVIEW


# ---------- admin chatbox queries ----------

GROUP_EXPR = {
    'category': "coalesce(cat.name, 'Uncategorized')", 'location': 'c.location', 'department': "coalesce(d.name, 'Unassigned')",
    'status': 'c.status', 'priority': 'c.priority', 'day': "to_char(c.created_at, 'YYYY-MM-DD')",
    'week': "to_char(date_trunc('week', c.created_at), 'YYYY-MM-DD')", 'month': "to_char(c.created_at, 'YYYY-MM')",
}
QUERY_FROM = '''FROM complaints c LEFT JOIN categories cat ON cat.id = c.category_id
                LEFT JOIN departments d ON d.id = c.assigned_department_id'''
OPEN_SQL = "c.status IN ('SUBMITTED', 'IN_PROGRESS')"
GROUP_COLUMNS = [('label', None), ('tickets', 'Tickets'), ('unresolved', 'Unresolved'), ('resolved', 'Resolved'),
                 ('avg_resolution_hours', 'Avg resolution (h)')]
LIST_COLUMNS = [('ticket_number', 'Ticket'), ('title', 'Title'), ('category', 'Category'), ('location', 'Location'),
                ('department', 'Department'), ('status', 'Status'), ('priority', 'Priority'), ('created_at', 'Created'),
                ('age_hours', 'Age (h)')]


def config_for_query(conn, me):
    ins = me['institution_id']
    cats = conn.execute('SELECT id, name FROM categories WHERE institution_id = %s AND is_active ORDER BY id', (ins,)).fetchall()
    depts = conn.execute('SELECT id, name FROM departments WHERE institution_id = %s AND is_active ORDER BY id', (ins,)).fetchall()
    locs = [r['name'] for r in conn.execute('SELECT name FROM locations WHERE institution_id = %s ORDER BY id', (ins,))]
    return cats, depts, locs


def run_query(conn, me, plan: QueryPlan) -> tuple[list[dict], dict, list[dict]]:
    if plan.from_ > plan.to or (plan.to - plan.from_).days + 1 > 366:
        fail(422, 'Date range must run forwards and cover at most 366 days')
    where = ['c.institution_id = %(ins)s', 'NOT c.archived', 'c.created_at >= %(start)s', 'c.created_at < %(end)s']
    params = {'ins': me['institution_id'], 'start': plan.from_, 'end': plan.to + timedelta(days=1), 'limit': plan.limit}
    for field, column in (('category_ids', 'c.category_id'), ('department_ids', 'c.assigned_department_id'),
                          ('locations', 'c.location'), ('statuses', 'c.status'), ('priorities', 'c.priority')):
        if getattr(plan, field):
            where.append(f'{column} = ANY(%({field})s)')
            params[field] = getattr(plan, field)
    where = ' AND '.join(where)
    totals = conn.execute(f'''SELECT count(*) AS tickets, count(*) FILTER (WHERE {OPEN_SQL}) AS unresolved,
                                count(*) FILTER (WHERE c.status = 'RESOLVED') AS resolved,
                                count(*) FILTER (WHERE {OPEN_SQL} AND c.priority = 'HIGH') AS high_open,
                                {RESOLUTION_AVG} AS avg {QUERY_FROM} WHERE {where}''', params).fetchone()
    totals['avg_resolution_hours'] = hours(totals.pop('avg'))
    if plan.metric == 'list':
        rows = conn.execute(f'''SELECT c.id, c.ticket_number, c.title, coalesce(cat.name, 'Uncategorized') AS category, c.location,
                                     coalesce(d.name, 'Unassigned') AS department, c.status, c.priority, c.created_at,
                                     round((extract(epoch FROM now() - c.created_at) / 3600)::numeric, 1)::float AS age_hours
                              {QUERY_FROM} WHERE {where}
                              ORDER BY c.created_at {'ASC' if plan.oldest_first else 'DESC'}, c.id LIMIT %(limit)s''', params).fetchall()
    elif totals['tickets']:
        group = GROUP_EXPR[plan.group_by] if plan.group_by else "'All matching tickets'"
        order = '1' if plan.group_by in ('day', 'week', 'month') else \
            'avg_resolution_hours DESC NULLS LAST, 1' if plan.metric == 'avg_resolution' else 'tickets DESC, 1'
        rows = conn.execute(f'''SELECT {group} AS label, count(*) AS tickets, count(*) FILTER (WHERE {OPEN_SQL}) AS unresolved,
                                     count(*) FILTER (WHERE c.status = 'RESOLVED') AS resolved,
                                     round(({RESOLUTION_AVG})::numeric, 2)::float AS avg_resolution_hours
                              {QUERY_FROM} WHERE {where} GROUP BY 1 ORDER BY {order} LIMIT %(limit)s''', params).fetchall()
    else:
        rows = []
    return rows, totals, issue_tickets(conn, where, params)


def cohort(me, start: date, end: date) -> tuple[str, dict]:
    return ('c.institution_id = %(ins)s AND NOT c.archived AND c.created_at >= %(start)s AND c.created_at < %(end)s',
            {'ins': me['institution_id'], 'start': start, 'end': end + timedelta(days=1)})


def issue_tickets(conn, where: str, params: dict) -> list[dict]:
    """Matching tickets' text and reporter roles, for NLTK text analysis."""
    return conn.execute(f'''SELECT c.ticket_number, c.title || '. ' || c.description AS text, c.reporter_user_id AS reporter_id,
                                   m.role AS reporter_role, c.location, coalesce(cat.name, 'Uncategorized') AS category,
                                   c.status, c.created_at
                            {QUERY_FROM} LEFT JOIN memberships m ON m.user_id = c.reporter_user_id AND m.institution_id = c.institution_id
                            WHERE {where} ORDER BY c.id LIMIT 2000''', params).fetchall()


def common_issues(conn, me, tickets: list[dict]) -> list[dict]:
    fn = getattr(ai, 'find_common_issues', None)
    if not fn or not tickets:
        return []
    locations = [r['name'] for r in conn.execute('SELECT name FROM locations WHERE institution_id = %s', (me['institution_id'],))]
    try:
        return [CommonIssue.model_validate(i).model_dump(mode='json') for i in fn(tickets, locations)]
    except Exception:
        return []  # common issues are optional; never break the report or chat on them


@api.get('/dashboard/common-issues', response_model=CommonIssues)
def dashboard_common_issues(from_: date = Query(alias='from'), to: date = Query(),
                            me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    if from_ > to or (to - from_).days + 1 > 366:
        fail(422, 'Date range must run forwards and cover at most 366 days')
    tickets = issue_tickets(conn, *cohort(me, from_, to))
    return {'period': {'from': from_, 'to': to}, 'sample_size': len(tickets),
            'issues': common_issues(conn, me, tickets), 'source': 'nlp'}


def filter_labels(plan: QueryPlan, cats, depts) -> list[str]:
    cat_names, dept_names = {r['id']: r['name'] for r in cats}, {r['id']: r['name'] for r in depts}
    return ([cat_names.get(i, f'Category #{i}') for i in plan.category_ids]
            + [dept_names.get(i, f'Department #{i}') + ' dept' for i in plan.department_ids]
            + plan.locations + [s.replace('_', ' ').lower() for s in plan.statuses]
            + [f'{p.lower()} priority' for p in plan.priorities])


@api.post('/dashboard/query', response_model=QueryResult)
def dashboard_query(body: QueryInput, me=Depends(current_user), conn=Depends(get_conn)):
    need(me, *OPS)
    cats, depts, locs = config_for_query(conn, me)
    plan, warnings = body.plan, []
    if plan is None:
        try:
            parsed = ai.parse_query(body.text, cats, depts, locs)
            plan, warnings = QueryPlan.model_validate(parsed['plan']), list(parsed['warnings'])
        except Exception:
            # never break the dashboard on parser errors; fall back to recent totals
            today = date.today()
            plan = QueryPlan.model_validate({'from': today - timedelta(days=29), 'to': today})
            warnings = ['Could not interpret the question; showing totals for the last 30 days.']
    rows, totals, tickets = run_query(conn, me, plan)
    try:
        summary, suggestions = ai.describe_result(plan.model_dump(mode='json', by_alias=True), totals, rows,
                                                  [t['text'] for t in tickets], filter_labels(plan, cats, depts))
        source = 'nlp'
    except Exception:
        summary, suggestions, source = f"{totals['tickets']} tickets matched.", [], 'rules'
    columns = LIST_COLUMNS if plan.metric == 'list' else \
        [(k, v or (plan.group_by or 'scope').capitalize()) for k, v in GROUP_COLUMNS]
    return {'query': body.text, 'plan': plan, 'columns': [{'key': k, 'label': v} for k, v in columns], 'rows': rows,
            'summary': summary, 'suggestions': suggestions, 'common_issues': common_issues(conn, me, tickets),
            'warnings': warnings, 'source': source}


app.include_router(api)

