"""End-to-end API checks against a real local PostgreSQL test database (wiped per run).

Run from backend/:  TEST_DATABASE_URL=postgresql://... python -m pytest
"""
import struct
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import psycopg

from conftest import TEST_DB

PNG = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0) + struct.pack('>I', zlib.crc32(b'IHDR'))


def ids(client, h):
    cats = {c['name']: c for c in client.get('/api/v1/categories', headers=h['admin']).json()}
    depts = {d['name']: d['id'] for d in client.get('/api/v1/departments', headers=h['admin']).json()}
    return cats, depts


def new(client, headers, **kw):
    body = {'title': 'Wi-Fi unavailable', 'description': 'Disconnects during lab.', 'location': 'Block B / Lab 204', **kw}
    return client.post('/api/v1/complaints', json=body, headers=headers)


def test_auth(client, h):
    assert client.get('/api/v1/complaints').status_code == 401
    assert client.get('/api/v1/complaints', headers={'Authorization': 'Bearer junk'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'student@demo.edu', 'password': 'wrong'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'a', 'password': 'b', 'extra': 1}).status_code == 422
    me = client.get('/api/v1/auth/me', headers=h['it.staff']).json()
    assert me['role'] == 'STAFF' and me['department_id']


def test_full_lifecycle(client, h):
    cats, depts = ids(client, h)
    r = new(client, h['student'], category_id=cats['Wi-Fi / Network']['id'])
    assert r.status_code == 201, r.text
    t = r.json()
    assert t['ticket_number'] == f"CMP-{t['id']:06d}" and t['status'] == 'SUBMITTED'
    assert t['assigned_department_id'] == depts['IT']  # category rule routing
    tid = t['id']

    # image: invalid, oversized, then valid; served only with auth
    assert client.post(f'/api/v1/complaints/{tid}/image', files={'file': ('x.png', b'not an image', 'image/png')}, headers=h['student']).status_code == 422
    assert client.post(f'/api/v1/complaints/{tid}/image', files={'file': ('x.png', PNG + b'0' * (5 * 1024 * 1024), 'image/png')}, headers=h['student']).status_code == 422
    r = client.post(f'/api/v1/complaints/{tid}/image', files={'file': ('x.png', PNG, 'image/png')}, headers=h['student'])
    assert r.status_code == 200 and r.json()['image_url'] == f'/api/v1/complaints/{tid}/image'
    assert client.get(f'/api/v1/complaints/{tid}/image').status_code == 401
    assert client.get(f'/api/v1/complaints/{tid}/image', headers=h['student2']).status_code == 404
    img = client.get(f'/api/v1/complaints/{tid}/image', headers=h['it.staff'])
    assert img.status_code == 200 and img.headers['content-type'] == 'image/png' and img.content == PNG

    # access boundaries
    assert client.get(f'/api/v1/complaints/{tid}', headers=h['student2']).status_code == 404
    assert client.get(f'/api/v1/complaints/{tid}', headers=h['facilities.staff']).status_code == 404
    assert client.patch(f'/api/v1/complaints/{tid}/status', json={'status': 'IN_PROGRESS'}, headers=h['student']).status_code == 403
    assert client.patch(f'/api/v1/complaints/{tid}', json={'priority': 'HIGH'}, headers=h['student']).status_code == 403

    # assign to named IT staff (must belong to department)
    staff = client.get(f"/api/v1/staff?department_id={depts['IT']}", headers=h['admin']).json()
    it_id = staff[0]['id']
    fac_id = client.get(f"/api/v1/staff?department_id={depts['Facilities']}", headers=h['admin']).json()[0]['id']
    assert client.patch(f'/api/v1/complaints/{tid}/assign', json={'department_id': depts['IT'], 'assigned_user_id': fac_id}, headers=h['admin']).status_code == 422
    r = client.patch(f'/api/v1/complaints/{tid}/assign', json={'department_id': depts['IT'], 'assigned_user_id': it_id}, headers=h['coordinator'])
    assert r.status_code == 200 and r.json()['assigned_user_id'] == it_id

    # status workflow by assigned staff
    assert client.patch(f'/api/v1/complaints/{tid}/status', json={'status': 'RESOLVED', 'note': 'x'}, headers=h['it.staff']).status_code == 409
    assert client.patch(f'/api/v1/complaints/{tid}/status', json={'status': 'IN_PROGRESS'}, headers=h['it.staff']).status_code == 200
    assert client.patch(f'/api/v1/complaints/{tid}', json={'title': 'New'}, headers=h['student']).status_code == 409
    assert client.post(f'/api/v1/complaints/{tid}/feedback', json={'rating': 5}, headers=h['student']).status_code == 409
    assert client.patch(f'/api/v1/complaints/{tid}/status', json={'status': 'RESOLVED', 'note': ' '}, headers=h['it.staff']).status_code == 422
    r = client.patch(f'/api/v1/complaints/{tid}/status', json={'status': 'RESOLVED', 'note': 'Router replaced'}, headers=h['it.staff'])
    assert r.status_code == 200 and r.json()['resolved_at']
    assert client.patch(f'/api/v1/complaints/{tid}/status', json={'status': 'REJECTED', 'note': 'x'}, headers=h['admin']).status_code == 409

    hist = client.get(f'/api/v1/complaints/{tid}/history', headers=h['student']).json()
    assert [e['new_status'] for e in hist if e['kind'] == 'STATUS'] == ['SUBMITTED', 'IN_PROGRESS', 'RESOLVED']
    assert [e['old_status'] for e in hist if e['kind'] == 'STATUS'] == [None, 'SUBMITTED', 'IN_PROGRESS']
    assert sum(e['kind'] == 'ASSIGNMENT' for e in hist) == 2

    # feedback: reporter only, one per ticket
    fb = f'/api/v1/complaints/{tid}/feedback'
    assert client.get(fb, headers=h['student']).status_code == 404
    assert client.post(fb, json={'rating': 6}, headers=h['student']).status_code == 422
    assert client.post(fb, json={'rating': 4}, headers=h['admin']).status_code == 403
    assert client.post(fb, json={'rating': 4, 'comment': 'Quick fix'}, headers=h['student']).status_code == 201
    assert client.post(fb, json={'rating': 4}, headers=h['student']).status_code == 409
    assert client.patch(fb, json={'rating': 5}, headers=h['student']).json()['rating'] == 5
    assert client.delete(fb, headers=h['student']).status_code == 204
    assert client.get(fb, headers=h['student']).status_code == 404

    stats = client.get('/api/v1/dashboard/stats', headers=h['admin']).json()
    assert stats['resolved_count'] >= 1 and stats['avg_resolution_hours'] is not None
    assert client.get('/api/v1/dashboard/stats', headers=h['student']).status_code == 403


def test_uncategorized_review_reject_and_staff_reporter(client, h):
    r = new(client, h['facilities.staff'], title='Leaking tap', location='Hostel 1')
    assert r.status_code == 201
    t = r.json()
    assert t['category_id'] is None and t['assigned_department_id'] is None
    assert client.patch(f"/api/v1/complaints/{t['id']}/status", json={'status': 'IN_PROGRESS'}, headers=h['admin']).status_code == 409
    assert client.patch(f"/api/v1/complaints/{t['id']}/status", json={'status': 'REJECTED', 'note': 'Duplicate'}, headers=h['admin']).status_code == 200
    assert new(client, h['admin']).status_code == 403
    assert new(client, h['student'], location='Nowhere').status_code == 422
    assert new(client, h['student'], category_id=9999).status_code == 422


def test_category_change_reroutes_and_archive(client, h):
    cats, depts = ids(client, h)
    t = new(client, h['student'], category_id=cats['Wi-Fi / Network']['id']).json()
    r = client.patch(f"/api/v1/complaints/{t['id']}", json={'category_id': cats['Plumbing']['id']}, headers=h['student'])
    assert r.status_code == 200 and r.json()['assigned_department_id'] == depts['Facilities']
    assert client.patch(f"/api/v1/complaints/{t['id']}", json={}, headers=h['student']).status_code == 422
    assert client.patch(f"/api/v1/complaints/{t['id']}", json={'ticket_number': 'X'}, headers=h['student']).status_code == 422
    assert client.delete(f"/api/v1/complaints/{t['id']}", headers=h['coordinator']).status_code == 403
    assert client.delete(f"/api/v1/complaints/{t['id']}", headers=h['admin']).status_code == 204
    assert client.get(f"/api/v1/complaints/{t['id']}", headers=h['student']).status_code == 404


def test_config_admin_only_and_deactivate(client, h):
    assert client.post('/api/v1/departments', json={'name': 'Security'}, headers=h['coordinator']).status_code == 403
    d = client.post('/api/v1/departments', json={'name': 'Security'}, headers=h['admin'])
    assert d.status_code == 201
    assert client.post('/api/v1/departments', json={'name': 'Security'}, headers=h['admin']).status_code == 409
    c = client.post('/api/v1/categories', json={'name': 'Safety', 'default_department_id': d.json()['id']}, headers=h['admin']).json()
    assert client.delete(f"/api/v1/categories/{c['id']}", headers=h['admin']).status_code == 204
    assert c['id'] not in [x['id'] for x in client.get('/api/v1/categories', headers=h['student']).json()]
    assert new(client, h['student'], category_id=c['id']).status_code == 422


def test_foreign_institution_isolated(client, h):
    with psycopg.connect(TEST_DB) as conn:
        inst = conn.execute("INSERT INTO institutions (code, name) VALUES ('OTHER', 'Other') RETURNING id").fetchone()[0]
        dept = conn.execute("INSERT INTO departments (institution_id, name) VALUES (%s, 'IT') RETURNING id", (inst,)).fetchone()[0]
    assert client.patch('/api/v1/complaints/1/assign', json={'department_id': dept}, headers=h['admin']).status_code in (409, 422)
    assert client.get(f'/api/v1/staff?department_id={dept}', headers=h['admin']).status_code == 404


def test_unique_ticket_numbers_under_concurrency(client, h):
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda _: new(client, h['student2']).json()['ticket_number'], range(16)))
    assert len(set(results)) == 16


def test_analyze_and_insights(client, h):
    r = client.post('/api/v1/complaints/2/analyze', headers=h['admin'])
    assert r.status_code == 200 and r.json()['source'] in ('rules', 'local_model')
    assert client.post('/api/v1/complaints/2/analyze', headers=h['student']).status_code in (403, 404)
    today = date.today().isoformat()
    ins = client.get(f'/api/v1/dashboard/insights?from={today}&to={today}', headers=h['coordinator']).json()
    assert ins['sample_size'] > 0 and ins['period'] == {'from': today, 'to': today}
    assert client.get('/api/v1/dashboard/insights?from=2026-01-02&to=2026-01-01', headers=h['admin']).status_code == 422
    assert client.get('/api/v1/dashboard/insights?from=2024-01-01&to=2026-01-01', headers=h['admin']).status_code == 422
    rep = client.post('/api/v1/dashboard/insights/report', json={'from': today, 'to': today}, headers=h['admin']).json()
    assert rep['source'] == 'rules' and rep['sample_size'] == ins['sample_size']
    empty = client.post('/api/v1/dashboard/insights/report', json={'from': '2020-01-01', 'to': '2020-01-02'}, headers=h['admin']).json()
    assert empty['sample_size'] == 0 and empty['recommendations'] == []
