"""Shared fixtures: real local PostgreSQL test database, wiped once per test run."""
import os

import psycopg
import pytest

TEST_DB = os.environ.get('TEST_DATABASE_URL', 'postgresql://campusresolve:campusresolve_local@localhost:5432/campusresolve_test')
os.environ['DATABASE_URL'] = TEST_DB
os.environ['UPLOAD_DIR'] = 'work/test-uploads'

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope='session')
def client():
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        conn.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope='session')
def h(client):
    def login(email):
        r = client.post('/api/v1/auth/login', json={'email': email, 'password': 'demo1234'})
        assert r.status_code == 200, r.text
        return {'Authorization': f"Bearer {r.json()['access_token']}"}
    return {k: login(f'{k}@demo.edu') for k in ('student', 'student2', 'it.staff', 'facilities.staff', 'coordinator', 'admin')}
