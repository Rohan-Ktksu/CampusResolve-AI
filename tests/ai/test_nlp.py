"""NLTK triage for the new categories, report text analysis, and the admin chatbox parser."""

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ai import analyze_complaint, describe_result, find_common_issues, generate_admin_report, parse_query
from test_rules import aggregates

DEPARTMENTS = [{"id": i, "name": n} for i, n in enumerate(
    ["IT", "Facilities", "Housekeeping", "Academics", "Transport", "Food Services", "Hostel Office", "Campus Security"], 1)]
D = {d["name"]: d["id"] for d in DEPARTMENTS}
CATEGORIES = [{"id": i, "name": n, "default_department_id": D.get(dept)} for i, (n, dept) in enumerate([
    ("Wi-Fi / Network", "IT"), ("Classroom Equipment", "IT"), ("Electrical", "Facilities"), ("Plumbing", "Facilities"),
    ("Cleanliness", "Housekeeping"), ("Transport", "Transport"), ("Other", None), ("Infrastructure", "Facilities"),
    ("Food / Canteen", "Food Services"), ("Hostel", "Hostel Office"), ("Safety / Security", "Campus Security"),
    ("Housekeeping", "Housekeeping"), ("Library", "Academics"), ("Academics", "Academics"), ("Sports", "Facilities")], 1)]
C = {c["name"]: c["id"] for c in CATEGORIES}
LOCATIONS = ["Block A / Classrooms", "Block B / Lab 204", "Library", "Hostel 1", "Cafeteria", "Sports Complex",
             "Admin Block", "Main Gate / Bus Stop"]
TODAY = date(2026, 10, 24)


def triage(title, description="Please look into this."):
    return analyze_complaint(title, description, CATEGORIES, DEPARTMENTS)


def plan(text):
    return parse_query(text, CATEGORIES, DEPARTMENTS, LOCATIONS, TODAY)["plan"]


class NewCategoryTriageTests(unittest.TestCase):
    def test_new_categories_route_to_their_departments(self):
        for title, category, dept in [("Stale food served at lunch", "Food / Canteen", "Food Services"),
                                      ("Warden ignores room allotment request", "Hostel", "Hostel Office"),
                                      ("Laptop stolen from the reading room", "Safety / Security", "Campus Security"),
                                      ("No toilet paper or soap in the washroom", "Housekeeping", "Housekeeping"),
                                      ("Timetable clash for third semester", "Academics", "Academics"),
                                      ("Badminton court net is torn", "Sports", "Facilities"),
                                      ("Lift not working since morning", "Infrastructure", "Facilities")]:
            with self.subTest(title=title):
                result = triage(title)
                self.assertEqual((C[category], D[dept]), (result["category_id"], result["suggested_department_id"]))
                self.assertEqual("nlp", result["source"])

    def test_stemming_word_order_and_typos(self):
        self.assertEqual(C["Plumbing"], triage("The taps are leaking")["category_id"])
        self.assertEqual(C["Classroom Equipment"], triage("Projecter broken")["category_id"])

    def test_new_hazards_raise_priority(self):
        for title in ["Food poisoning after dinner", "Harassment near the bus stop"]:
            with self.subTest(title=title):
                result = triage(title)
                self.assertEqual("HIGH", result["priority"])
                self.assertTrue(result["needs_review"])
        self.assertEqual("NORMAL", triage("Mess menu", "No food poisoning, the menu is just repetitive.")["priority"])

    def test_location_words_alone_do_not_pick_a_category(self):
        self.assertIsNone(triage("Something odd in Hostel 1", "Not sure who handles this.")["category_id"])


class ReportTextTests(unittest.TestCase):
    def test_texts_add_terms_sentence_and_recurring_recommendation(self):
        texts = ["Water leak in lab", "Leaking pipe near Block B", "Leak under the sink keeps getting worse",
                 "Wi-Fi drops", "Garbage not collected"]
        report = generate_admin_report(aggregates(), texts)
        self.assertEqual("nlp", report["source"])
        self.assertIn("Most-mentioned terms: leak (3)", report["summary"])
        self.assertNotIn("Leak under the sink", report["summary"])  # complaint text is not quoted
        self.assertTrue(any("'leak' appears in 3 of 20" in r["evidence"] for r in report["recommendations"]))

    def test_without_texts_source_stays_rules(self):
        self.assertEqual("rules", generate_admin_report(aggregates())["source"])

    def test_more_texts_than_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_admin_report(aggregates(), ["x"] * 21)


class QueryParserTests(unittest.TestCase):
    def test_category_location_status_and_month(self):
        p = plan("How many food complaints in Hostel 1 were unresolved last month?")
        self.assertEqual(([C["Food / Canteen"]], ["Hostel 1"], ["SUBMITTED", "IN_PROGRESS"]),
                         (p["category_ids"], p["locations"], p["statuses"]))
        self.assertEqual(("2026-09-01", "2026-09-30", "count"), (p["from"], p["to"], p["metric"]))

    def test_grouping_top_n_and_average(self):
        p = plan("top 3 locations with most complaints this week")
        self.assertEqual(("location", 3, "2026-10-19"), (p["group_by"], p["limit"], p["from"]))
        p = plan("average resolution time by category")
        self.assertEqual(("avg_resolution", "category"), (p["metric"], p["group_by"]))
        self.assertEqual("week", plan("weekly trend of safety issues")["group_by"])

    def test_list_department_and_dates(self):
        p = plan("show oldest open high priority tickets assigned to IT department")
        self.assertEqual(("list", True, ["HIGH"], [D["IT"]]), (p["metric"], p["oldest_first"], p["priorities"], p["department_ids"]))
        p = plan("wifi issues in the library since 2026-10-01")
        self.assertEqual(([C["Wi-Fi / Network"]], ["Library"], "2026-10-01"), (p["category_ids"], p["locations"], p["from"]))
        self.assertEqual([C["Library"]], plan("library complaints in september")["category_ids"])

    def test_unknown_question_warns_and_long_ranges_are_capped(self):
        result = parse_query("hello there", CATEGORIES, DEPARTMENTS, LOCATIONS, TODAY)
        self.assertEqual(2, len(result["warnings"]))
        p = plan("tickets from 2024-01-01 to 2026-10-24")
        self.assertEqual("2025-10-24", p["from"])

    def test_untrusted_text_only_fills_the_plan(self):
        p = plan("'; DROP TABLE complaints; -- show wifi tickets")
        self.assertEqual({"metric", "group_by", "category_ids", "department_ids", "locations", "statuses", "priorities",
                          "from", "to", "limit", "oldest_first"}, set(p))
        with self.assertRaises(ValueError):
            plan("x" * 501)


class DescribeResultTests(unittest.TestCase):
    def test_grouped_counts_give_summary_and_focus_suggestion(self):
        p = {**plan("complaints by category"), "from": "2026-10-01", "to": "2026-10-24"}
        totals = {"tickets": 10, "unresolved": 6, "resolved": 4, "high_open": 2, "avg_resolution_hours": 5.0}
        rows = [{"label": "Plumbing", "tickets": 6, "unresolved": 4, "resolved": 2, "avg_resolution_hours": 6.0},
                {"label": "Wi-Fi / Network", "tickets": 4, "unresolved": 2, "resolved": 2, "avg_resolution_hours": 4.0}]
        texts = ["Water leak in lab", "Leaking pipe", "Leak again", "Wi-Fi drops"]
        summary, suggestions = describe_result(p, totals, rows, texts, [])
        self.assertTrue(summary.startswith("10 tickets from 2026-10-01 to 2026-10-24: 6 unresolved, 4 resolved"))
        self.assertIn("Top category: Plumbing with 6 tickets.", summary)
        titles = [s["title"] for s in suggestions]
        self.assertEqual(["Prioritize 2 open high-priority tickets", "Focus on Plumbing", "Reduce the open backlog",
                          "Recurring mention: 'leak'"], titles)

    def test_empty_result_suggests_widening(self):
        totals = {"tickets": 0, "unresolved": 0, "resolved": 0, "high_open": 0, "avg_resolution_hours": None}
        _, suggestions = describe_result(plan("food complaints today"), totals, [], [], ["Food / Canteen"])
        self.assertEqual("No matching tickets", suggestions[0]["title"])


def ticket(n, text, reporter, role="STUDENT", location="Hostel 1", status="SUBMITTED", category="Plumbing"):
    return {"ticket_number": f"CMP-{n:06d}", "text": text, "reporter_id": reporter, "reporter_role": role,
            "location": location, "category": category, "status": status, "created_at": f"2026-10-{n:02d}T09:00:00Z"}


class CommonIssueTests(unittest.TestCase):
    def test_groups_by_shared_phrase_with_reporter_counts(self):
        tickets = [ticket(1, "Water leak in bathroom. Water leak is getting worse.", 1),
                   ticket(2, "Hostel 1 has a water leak near the stairs", 2),
                   ticket(3, "Another water leak, please fix", 1, status="RESOLVED"),
                   ticket(4, "Water leaking from ceiling of lab", 9, role="STAFF", location="Block B / Lab 204"),
                   ticket(5, "Stale food again, food is stale in the mess", 3, category="Food / Canteen", location="Cafeteria"),
                   ticket(6, "Stale food served again at dinner", 4, category="Food / Canteen", location="Cafeteria"),
                   ticket(7, "Projector broken", 5, category="Classroom Equipment")]
        issues = find_common_issues(tickets, LOCATIONS)
        self.assertEqual(["water leak", "stale food"], [i["issue"] for i in issues])
        leak = issues[0]
        self.assertEqual((4, 3, 2, 3), (leak["times_reported"], leak["reporters"], leak["student_reporters"], leak["open"]))
        self.assertEqual({"location": "Hostel 1", "count": 3}, leak["locations"][0])
        self.assertEqual(("2026-10-01", "2026-10-04"), (leak["first_reported"], leak["last_reported"]))
        self.assertTrue(leak["summary"].startswith("'water leak' was reported 4 times by 2 students and 1 staff"))
        self.assertTrue(any("one cause" in s for s in leak["suggestions"]))
        self.assertEqual(2, issues[1]["times_reported"])

    def test_location_and_generic_words_are_not_issues(self):
        tickets = [ticket(1, "Problem in Hostel 1", 1), ticket(2, "Issue at Hostel 1, please help", 2)]
        self.assertEqual([], find_common_issues(tickets, LOCATIONS))

    def test_single_reporter_repeating_gets_contact_suggestion(self):
        tickets = [ticket(1, "Wifi router down", 7), ticket(2, "Wifi router down again", 7)]
        issue = find_common_issues(tickets, LOCATIONS)[0]
        self.assertEqual((2, 1), (issue["times_reported"], issue["reporters"]))
        self.assertTrue(any("one person" in s for s in issue["suggestions"]))


if __name__ == "__main__":
    unittest.main()
