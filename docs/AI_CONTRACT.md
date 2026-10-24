# In-process assistance contract — NLTK keyword implementation

Owner: Rohan. Backend routes: Atif. No external requests or paid inference. v0.3 matching uses NLTK (Snowball stemming, regexp tokenizing, n-grams, edit distance) with no downloaded corpora, labelled `source: nlp`; it is keyword analysis, not trained AI. A future local model is optional, not required to run.

## Ticket function

`analyze_complaint(title, description, allowed_categories, departments) -> dict`

allowed_categories is a list of {id, name, default_department_id}; departments is a list of {id, name}. Both are authorized, active institution configuration supplied by the backend. Input length limits follow the API contract.

Return exactly these fields:

```json
{
  "category_id": null,
  "suggested_department_id": null,
  "priority": "NORMAL",
  "summary": "A campus issue needs review.",
  "reason": "The report does not clearly match a configured category.",
  "suggested_actions": ["Ask the reporter for the exact location and impact."],
  "source": "rules",
  "needs_review": true
}
```

Priority: LOW/NORMAL/HIGH. source: nlp (v0.3), rules or local_model. IDs may be null and must otherwise exist in the input configuration. Return mapped departments only. AI advises and never writes ticket state. Text must not trigger link fetching, filesystem access, or secret requests. Unexpected function errors are handled by the route with manual-review fallback. Never block submission on analysis.

## Admin report function

`generate_admin_report(aggregates, texts=()) -> dict`

v0.3: `texts` are the cohort's own complaint titles/descriptions (backend-selected, at most sample_size). When present, the summary adds NLTK most-mentioned terms, a "recurring mention" recommendation may cite how many tickets use a term, and source is `nlp`. Text is analysed, never quoted.

Input follows the Insights schema in docs/openapi.json. The backend computes it; browser-supplied figures are never trusted. Output follows AdminReport: period, sample_size, generated_at, source, summary, recommendations. Each recommendation contains title, evidence (plain text citing supplied figures), department_id or null, next_step, and horizon IMMEDIATE/ASSESSMENT. Interpret counts as reported tickets, not affected-student population.

No complaints means sample_size 0 and an explicit insufficient-data summary with an empty recommendations list. Distinguish frequency from urgency. Do not invent trends unless previous-period metrics exist. Do not include names, email addresses, raw private reports, fabricated causes/costs, or claims of completed repairs.

## Admin chatbox and common issues (v0.3)

`parse_query(text, categories, departments, locations, today=None) -> {"plan", "warnings"}` turns an English question into the allow-listed QueryPlan in docs/openapi.json. Configuration comes from the backend; text only selects among configured IDs/names and fixed enums.

`describe_result(plan, totals, rows, texts, filter_labels) -> (summary, suggestions)` restates the backend's computed totals and rows, and adds at most 4 suggestions ({title, evidence, next_step}) grounded in those numbers or in NLTK term counts.

`find_common_issues(tickets, locations) -> list` groups tickets by the stemmed word or order-free two-word phrase shared by the most tickets, repeating on the rest (max 5, each ≥2 tickets). Reporter counts are distinct accounts; staff reporters are counted separately from students. No quotes, names or emails are returned.

## Integration

The feature/ai implementation exports both functions from app.ai with these exact signatures. Atif's frozen v0.2 backend already discovers them and validates their output before returning it. If either function fails or its output is invalid, his route retains the existing labelled fallback. No API path, wire model, permission, or ticket workflow change is required.

The report input has no authorized department mapping, so report recommendations intentionally return department_id=null. The report can suggest the type of team/action in prose, but must not invent an institution department ID. Ticket suggestions do use the supplied category routing map.

Rules match configured labels and explicit issue phrases. Multiple issue types, unavailable categories, inactive configuration, and missing department maps require review. Infrastructure can cover equipment/electrical/plumbing only when the more specific category is absent. Priority is a literal triage signal, not a safety determination. Staff always confirms handling and actual resolution. No confidence/accuracy percentage is claimed.

Run dependency-free synthetic checks with `python -m unittest discover -s tests/ai -v`. For exact implemented behavior, limitations, and optional backend adapter verification, see backend/app/ai/README.md. This is a tested deterministic assistance baseline, not a trained or local language model.

AI callable proposals/review go in docs/coordination/ai.md. Wire changes are reflected in the canonical API contract and reviewed by Sonia. Use synthetic examples for meaningful checks of unknown inputs, inactive/unmapped categories, no data, missing comparison periods, and invalid model output.
