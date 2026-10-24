# In-process assistance contract — proposed

Owner: Rohan. Backend routes: Atif. Default AI_MODE=rules, no external requests or paid inference. Rules are not represented as trained AI. A future local model is optional, not required to run.

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

Priority: LOW/NORMAL/HIGH. source: rules or local_model. IDs may be null and must otherwise exist in the input configuration. Return mapped departments only. AI advises and never writes ticket state. Text must not trigger link fetching, filesystem access, or secret requests. Unexpected function errors are handled by the route with manual-review fallback. Never block submission on analysis.

## Admin report function

`generate_admin_report(aggregates) -> dict`

Input follows the Insights schema in docs/openapi.json. The backend computes it; browser-supplied figures are never trusted. Output follows AdminReport: period, sample_size, generated_at, source, summary, recommendations. Each recommendation contains title, evidence (plain text citing supplied figures), department_id or null, next_step, and horizon IMMEDIATE/ASSESSMENT. Interpret counts as reported tickets, not affected-student population.

No complaints means sample_size 0 and an explicit insufficient-data summary with an empty recommendations list. Distinguish frequency from urgency. Do not invent trends unless previous-period metrics exist. Do not include names, email addresses, raw private reports, fabricated causes/costs, or claims of completed repairs.

## Integration

Atif imports these functions from app.ai once implemented. The baseline package exports no functions yet; until Rohan's module exists, Atif keeps optional AI routes behind a local manual-review result rather than breaking application startup. Do not duplicate the classifier in backend routers.

AI callable proposals/review go in docs/coordination/ai.md. Wire changes are reflected in the canonical API contract and reviewed by Sonia. Use synthetic examples for meaningful checks of unknown inputs, inactive/unmapped categories, no data, missing comparison periods, and invalid model output.
