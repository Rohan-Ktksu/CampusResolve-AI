"""Check our functions through Atif's actual route adapters, without a database.

Usage: python tests/ai/check_backend_adapter.py <backend-snapshot-directory>
Use a temporary backend snapshot overlaid with backend/app/ai/ and its installed
requirements. Mock database/auth inputs are explicit; this is NOT a live API/DB test.
"""

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_rules import CATEGORIES, DEPARTMENTS, aggregates

# test_rules loads app.ai from our working tree. Extend that package's search path
# with the backend snapshot so its real models and main module can import normally.
import app

snapshot = Path(sys.argv[1]).resolve()
assert (snapshot / "app/main.py").is_file(), "Pass the directory containing Atif's app/"
app.__path__.append(str(snapshot / "app"))
backend = importlib.import_module("app.main")


def run():
    admin = {"id": 90, "institution_id": 1, "role": "ADMIN", "department_id": None}
    conn = MagicMock()
    conn.execute.side_effect = [MagicMock(fetchall=MagicMock(return_value=CATEGORIES)),
                                MagicMock(fetchall=MagicMock(return_value=DEPARTMENTS))]
    with patch.object(backend, "load", return_value={"title": "Wi-Fi down", "description": "Internet disconnects in lab."}):
        result = backend.analyze_complaint(42, me=admin, conn=conn)
    assert result.category_id == 1 and result.suggested_department_id == 10
    assert result.source == "nlp" and not result.needs_review
    assert "NLTK keyword matching" in result.reason, "Backend silently used the manual-review fallback"
    assert conn.execute.call_count == 2, "Triage should read configuration, not write ticket state"

    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [{"id": 1, "department_id": 10},
                                                      {"id": 5, "department_id": 30}]
    body = backend.ReportInput.model_validate({"from": "2026-10-01", "to": "2026-10-24"})
    patch.object(backend, "issue_tickets", return_value=[]).start()  # complaint-text query; covered by live tests
    with patch.object(backend, "compute_insights", return_value=aggregates()):
        report = backend.AdminReport.model_validate(backend.generate_report(body, me=admin, conn=conn))
    assert report.sample_size == 20 and report.source == "rules"
    assert len(report.recommendations) == 3
    assert "13 of 20" in report.recommendations[2].evidence, "Backend did not use Rohan's location aggregation"

    empty = aggregates()
    empty.update(sample_size=0, unresolved=0, high_priority_unresolved=0, resolved_count=0,
                 avg_resolution_hours=None, by_category=[], by_location=[])
    with patch.object(backend, "compute_insights", return_value=empty):
        empty_report = backend.AdminReport.model_validate(backend.generate_report(body, me=admin, conn=conn))
    assert empty_report.sample_size == 0 and empty_report.recommendations == []

    with patch.object(backend, "load", return_value={"title": "Wi-Fi down", "description": "Internet disconnects."}), \
            patch.object(backend.ai, "analyze_complaint", side_effect=ValueError("Synthetic failure")):
        fallback = backend.AIAnalysis.model_validate(backend.analyze_complaint(42, me=admin, conn=MagicMock()))
    assert fallback.needs_review and fallback.category_id is None and fallback.source == "rules"

    with patch.object(backend, "compute_insights", return_value=aggregates()), \
            patch.object(backend.ai, "generate_admin_report", side_effect=ValueError("Synthetic failure")):
        fallback_report = backend.AdminReport.model_validate(backend.generate_report(body, me=admin, conn=conn))
    assert fallback_report.sample_size == 20 and fallback_report.source == "rules"

    print("Backend adapter checks passed: actual Pydantic models accept both functions; no silent fallback; no-data and error fallbacks work.")
    print("Database/auth inputs were mocked. A live PostgreSQL/browser integration run is still required after merging.")
    return {"synthetic_example": True, "ticket_analysis": result.model_dump(mode="json"),
            "admin_report": report.model_dump(mode="json", by_alias=True)}


if __name__ == "__main__":
    output = run()
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
