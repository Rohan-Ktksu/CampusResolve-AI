"""Dependency-free contract sanity check; optionally compare a saved runtime /openapi.json.

Usage: python scripts/check_contract.py [work/runtime-openapi.json]
This checks structure and presence, not full OpenAPI validity or runtime behavior.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / 'docs/openapi.json').read_text(encoding='utf-8'))
assert spec['openapi'].startswith('3.1.'), 'Expected OpenAPI 3.1'
operations = set()
ids = set()

def walk(value):
    if isinstance(value, dict):
        if '$ref' in value:
            target = spec
            assert value['$ref'].startswith('#/'), 'Only local references in seed contract'
            for part in value['$ref'][2:].split('/'):
                target = target[part.replace('~1', '/').replace('~0', '~')]
        for item in value.values():
            walk(item)
    elif isinstance(value, list):
        for item in value:
            walk(item)

walk(spec)
for path, methods in spec['paths'].items():
    assert path.startswith('/api/v1/'), path
    for method, operation in methods.items():
        if method not in {'get','post','patch','delete','put','options','head'}:
            continue
        assert operation['operationId'] not in ids, 'Duplicate operationId'
        ids.add(operation['operationId'])
        operations.add((path, method))
        assert any(key.startswith('2') for key in operation['responses']), 'Missing success response'
        defined = {p['name'] for p in operation.get('parameters',[]) if p['in']=='path' and p.get('required')}
        assert set(re.findall(r'\{([^}]+)\}',path)) <= defined, 'Missing required path parameter'
        for response in operation['responses'].values():
            for content in response.get('content',{}).values():
                assert 'schema' in content, 'Response missing schema'

assert spec['components']['schemas']['Complaint']['properties']['status']['enum'] == ['SUBMITTED','IN_PROGRESS','RESOLVED','REJECTED']
# 'nlp' (v0.3) is local NLTK code, agreed by Rohan; any other source needs the same explicit agreement.
LOCAL_SOURCES = ['rules','nlp','local_model']
for schema in ('AIAnalysis', 'AdminReport', 'QueryResult', 'CommonIssues'):
    assert spec['components']['schemas'][schema]['properties']['source']['enum'] == LOCAL_SOURCES, 'Paid provider source added without agreement'
if len(sys.argv) > 1:
    runtime = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    actual = {(p,m) for p,ms in runtime['paths'].items() for m in ms}
    missing = sorted(operations - actual)
    assert not missing, f'Runtime missing operations: {missing}'
    print('Runtime exposes every seed operation. Compare schemas and test permissions separately.')
print(f'Contract sanity check passed: {len(operations)} operations; local references and path parameters resolved.')
