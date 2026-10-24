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
    assert a['source'] == 'nlp' and not a['needs_review']
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
    assert rep['source'] == 'nlp' and rep['sample_size'] == n
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


def ask(client, h, body, who='admin'):
    return client.post('/api/v1/dashboard/query', json=body, headers=h[who])


def test_new_categories_are_seeded_and_suggested(client, h):
    cats, depts = config(client, h)
    for name in ('Infrastructure', 'Food / Canteen', 'Hostel', 'Safety / Security', 'Housekeeping', 'Library', 'Academics', 'Sports'):
        assert name in cats
    a = analyze(client, h, report(client, h, 'Stale food at lunch', 'The rice was stale and cold.', 'Cafeteria')['id'])
    assert (a['category_id'], a['suggested_department_id'], a['source']) == (cats['Food / Canteen'], depts['Food Services'], 'nlp')


def test_chatbox_question_returns_table_summary_and_suggestions(client, h):
    cats, _ = config(client, h)
    for desc in ('Food was stale today.', 'Stale bread again.', 'Stale food and cold tea.'):
        r = client.post('/api/v1/complaints', json={'title': 'Canteen food', 'description': desc, 'location': 'Cafeteria',
                                                     'category_id': cats['Food / Canteen']}, headers=h['student'])
        assert r.status_code == 201, r.text
    res = ask(client, h, {'text': 'how many food complaints in the cafeteria by status today'})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body['plan']['category_ids'] == [cats['Food / Canteen']] and body['plan']['locations'] == ['Cafeteria']
    assert body['plan']['group_by'] == 'status' and body['source'] == 'nlp'
    assert body['rows'] == [{'label': 'SUBMITTED', 'tickets': 3, 'unresolved': 3, 'resolved': 0, 'avg_resolution_hours': None}]
    assert body['summary'].startswith('3 tickets (Food / Canteen, Cafeteria) from')
    assert 'stale (3)' in body['summary'] and any(s['title'].startswith('Recurring mention') for s in body['suggestions'])

    # editing the plan (removing a chip) re-runs without re-parsing
    edited = {**body['plan'], 'locations': [], 'metric': 'list', 'group_by': None}
    listed = ask(client, h, {'plan': edited}).json()
    assert listed['query'] is None and [c['key'] for c in listed['columns']][0] == 'ticket_number'
    assert len(listed['rows']) == 3 and all(r['category'] == 'Food / Canteen' for r in listed['rows'])


def test_chatbox_validation_and_permissions(client, h):
    assert ask(client, h, {'text': 'wifi tickets'}, 'student').status_code == 403
    assert ask(client, h, {'text': 'wifi tickets'}, 'it.staff').status_code == 403
    assert ask(client, h, {'text': 'wifi tickets'}, 'coordinator').status_code == 200
    assert ask(client, h, {}).status_code == 422
    assert ask(client, h, {'text': 'x', 'plan': {'from': TODAY, 'to': TODAY}}).status_code == 422
    assert ask(client, h, {'plan': {'from': TODAY, 'to': TODAY, 'group_by': 'c.title; DROP TABLE complaints'}}).status_code == 422
    assert ask(client, h, {'plan': {'from': '2024-01-01', 'to': TODAY}}).status_code == 422


def test_chatbox_parser_failure_falls_back(client, h, monkeypatch):
    def boom(*_):
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(main.ai, 'parse_query', boom)
    monkeypatch.setattr(main.ai, 'describe_result', boom)
    body = ask(client, h, {'text': 'anything'}).json()
    assert body['source'] == 'rules' and body['warnings'] and body['suggestions'] == []


def test_common_issues_on_dashboard_report_and_chat(client, h):
    cats, _ = config(client, h)
    for who, desc in (('student', 'Water leak near the stairs.'), ('student2', 'Big water leak in the washroom.'),
                      ('student', 'The water leak is back again.')):
        r = client.post('/api/v1/complaints', json={'title': 'Water leak in hostel', 'description': desc, 'location': 'Hostel 1',
                                                     'category_id': cats['Plumbing']}, headers=h[who])
        assert r.status_code == 201, r.text
    dash = client.get(f'/api/v1/dashboard/common-issues?from={TODAY}&to={TODAY}', headers=h['admin'])
    assert dash.status_code == 200, dash.text
    leak = next(i for i in dash.json()['issues'] if i['issue'] == 'water leak')
    # an earlier test in this run also reports a water leak, so counts are at least this test's three
    assert leak['times_reported'] >= 3 and leak['student_reporters'] >= 2 and leak['open'] >= 3
    assert leak['locations'][0] == {'location': 'Hostel 1', 'count': 3} and leak['suggestions']

    rep = client.post('/api/v1/dashboard/insights/report', json={'from': TODAY, 'to': TODAY}, headers=h['admin']).json()
    assert any(i['issue'] == 'water leak' for i in rep['common_issues'])
    chat = ask(client, h, {'text': 'plumbing complaints in hostel 1 today'}).json()
    assert [i['issue'] for i in chat['common_issues']][:1] == ['water leak']

    assert client.get(f'/api/v1/dashboard/common-issues?from={TODAY}&to={TODAY}', headers=h['student']).status_code == 403
    assert client.get(f'/api/v1/dashboard/common-issues?from=2024-01-01&to={TODAY}', headers=h['admin']).status_code == 422
