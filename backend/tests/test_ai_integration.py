"""Live checks that the AI routes use Rohan's app.ai functions (skipped until that package exports them)."""
from datetime import date

import pytest

import app.main as main

pytestmark = pytest.mark.skipif(not (hasattr(main.ai, 'analyze_complaint') and hasattr(main.ai, 'generate_admin_report')),
                                reason="Rohan's app.ai functions are not present on this branch")

TODAY = date.today().isoformat()


def config(client, h):
    cats = {c['name']: c['id'] for c in client.get('/api/v1/categories', headers=h['admin']).json()}
    depts = {d['name']: d['id'] for d in client.get('/api/v1/departments', headers=h['admin']).json()}
    return cats, depts


def report(client, h, title, description, location='Block B / Lab 204'):
    r = client.post('/api/v1/complaints', json={'title': title, 'description': description, 'location': location}, headers=h['student'])
    assert r.status_code == 201, r.text
    return r.json()


def analyze(client, h, cid):
    r = client.post(f'/api/v1/complaints/{cid}/analyze', headers=h['admin'])
    assert r.status_code == 200, r.text
    return r.json()


def test_wifi_gets_configured_category_and_department(client, h):
    cats, depts = config(client, h)
    a = analyze(client, h, report(client, h, 'Wi-Fi down in lab', 'The internet disconnects every few minutes.')['id'])
    assert (a['category_id'], a['suggested_department_id']) == (cats['Wi-Fi / Network'], depts['IT'])
    assert a['source'] == 'rules' and not a['needs_review']
    assert a['reason'] != main.MANUAL_REVIEW['reason']  # Rohan's function ran, not the generic fallback


def test_transport_is_configured_and_suggested(client, h):
    cats, depts = config(client, h)
    a = analyze(client, h, report(client, h, 'Shuttle bus late', 'The morning shuttle skipped the stop.', 'Main Gate / Bus Stop')['id'])
    assert (a['category_id'], a['suggested_department_id']) == (cats['Transport'], depts['Transport'])


@pytest.mark.parametrize('title,description', [
    ('Something odd', 'Not sure who to tell about this.'),
    ('Two problems', 'The wifi is down and there is a water leak from the tap.'),
])
def test_unknown_or_mixed_needs_human_review(client, h, title, description):
    a = analyze(client, h, report(client, h, title, description)['id'])
    assert a['needs_review'] and a['category_id'] is None and a['suggested_department_id'] is None


def test_analysis_does_not_change_ticket(client, h):
    t = report(client, h, 'Wi-Fi down', 'Internet keeps dropping.')
    before_history = client.get(f"/api/v1/complaints/{t['id']}/history", headers=h['admin']).json()
    analyze(client, h, t['id'])
    assert client.get(f"/api/v1/complaints/{t['id']}", headers=h['admin']).json() == t
    assert client.get(f"/api/v1/complaints/{t['id']}/history", headers=h['admin']).json() == before_history


def test_report_uses_actual_counts_and_locations(client, h):
    for _ in range(3):
        report(client, h, 'Bin overflowing', 'Garbage everywhere.', 'Cafeteria')
    ins = client.get(f'/api/v1/dashboard/insights?from={TODAY}&to={TODAY}', headers=h['admin']).json()
    rep = client.post('/api/v1/dashboard/insights/report', json={'from': TODAY, 'to': TODAY}, headers=h['admin']).json()
    n = ins['sample_size']
    totals = {}
    for row in ins['by_location']:
        totals[row['location']] = totals.get(row['location'], 0) + row['count']
    hotspot, count = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    assert rep['source'] == 'rules' and rep['sample_size'] == n
    assert rep['summary'].startswith(f'{n} reported tickets')  # Rohan's wording; the backend fallback says "tickets reported"
    assert any(f'{count} of {n}' in r['evidence'] and hotspot in r['evidence'] for r in rep['recommendations'])


def test_empty_period_report(client, h):
    rep = client.post('/api/v1/dashboard/insights/report', json={'from': '2020-01-01', 'to': '2020-01-31'}, headers=h['admin']).json()
    assert rep['sample_size'] == 0 and rep['recommendations'] == [] and rep['source'] == 'rules'


def test_function_failures_fall_back(client, h, monkeypatch):
    def boom(*_):
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(main.ai, 'analyze_complaint', boom)
    monkeypatch.setattr(main.ai, 'generate_admin_report', boom)
    t = report(client, h, 'Wi-Fi down', 'Internet keeps dropping.')
    assert analyze(client, h, t['id']) == main.MANUAL_REVIEW
    r = client.post('/api/v1/dashboard/insights/report', json={'from': TODAY, 'to': TODAY}, headers=h['admin'])
    assert r.status_code == 200 and r.json()['source'] == 'rules' and r.json()['summary'].split()[1] == 'tickets'


def test_students_blocked_from_admin_ai(client, h):
    t = report(client, h, 'Wi-Fi down', 'Internet keeps dropping.')
    assert client.post(f"/api/v1/complaints/{t['id']}/analyze", headers=h['student']).status_code == 403
    assert client.get(f'/api/v1/dashboard/insights?from={TODAY}&to={TODAY}', headers=h['student']).status_code == 403
    assert client.post('/api/v1/dashboard/insights/report', json={'from': TODAY, 'to': TODAY}, headers=h['student']).status_code == 403
