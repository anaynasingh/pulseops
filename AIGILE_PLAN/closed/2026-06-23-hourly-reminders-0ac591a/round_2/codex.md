**Findings**

1. **High: Railway scheduling acceptance is too weak for the core goal.**
The gate only checks railway.json is present and the endpoint responds. It does not verify the hourly schedule expression, target URL, HTTP method, or how CRON_SECRET is delivered from Railway to the endpoint. The "creates every hour" part is unproven by the gate.

2. **Medium: Internal endpoint auth is under-specified.**
POST /api/v1/internal/run-reminders is "CRON_SECRET gated" but the plan doesn't define the header name, expected status for wrong/missing/empty secrets, or the Railway → endpoint secret delivery mechanism.

3. **Medium: Reassignment clears last_reminded_at? Unspecified.**
last_reminded_at is on Task (not per-assignee). If a task is reminded, then reassigned within the hour, the new assignee is suppressed by the old assignee's timestamp. Probe covers complete/unassign stop, not reassignment semantics.

4. **Medium: Insert + stamp atomicity not in service contract.**
The no-duplicate guarantee depends on the Notification insert and Task.last_reminded_at stamp being atomic. The plan defines the eligibility query but not the transaction boundary in reminder_service.py.

5. **Low: limit=N still unbounded in GET /notifications.**
Default 20 is fixed, but arbitrary ?limit=N has no stated cap.

**Prior Finding Status**
Addressed: R1H1 sequencing regression, R1H3 is_active join, R1H6 polling interval, concurrent overlap (architectural decision).
Partially addressed: enum mismatch improved (name= added), requires builder to match existing import pattern.

[codex] Thread ID: 019e8cd6-dd10-7e51-ab4c-cb8b83d48f00
