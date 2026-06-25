## Burst Plan

**Goal:** Add a CSS-only diverging bar chart to the Analytics page showing overdue vs upcoming tasks per person, broken down by High/Medium/Low priority, backed by a new `/analytics/task-balance` endpoint.

**CHARTER alignment:** "Frontend connected to live backend — no mock data" and "Complete backend API — all routers functional."

**Streams:** Two parallel streams (backend and frontend share only the locked API contract)

---

### Stream A - Backend: task-balance endpoint

- **Scope (files WRITTEN):**
  - `backend/app/api/v1/analytics.py`
  - `backend/app/schemas/schemas.py`
- **Excluded:** All other backend files. `main.py` untouched — analytics router already mounted. No migration, no model changes.
- **Exports:** `GET /api/v1/analytics/task-balance` returning `TaskBalanceResponse`
- **Dependency:** None
- **Builder:** claude

---

### Stream B - Frontend: TaskBalanceChart component + analytics page integration

- **Scope (files WRITTEN):**
  - `frontend/components/dashboard/TaskBalanceChart.tsx` (new)
  - `frontend/app/(dashboard)/analytics/page.tsx`
  - `frontend/lib/api.ts`
  - `frontend/lib/types.ts`
- **Excluded:** `package.json` (no new dependencies), all backend files
- **Exports:** `TaskBalanceChart` component; `analyticsApi.taskBalance()` client method
- **Dependency:** Stream A interface contract (locked — can build in parallel)
- **Builder:** claude

---

**Shared files:** None.

**Integration gate:** Both streams merged; `GET /api/v1/analytics/task-balance` returns valid JSON; TaskBalanceChart renders with real data showing at least one person row.

**Deferred to next Burst:** Row sorting by total count; click-through to filtered task list; individual bar segment interactions.

---

## Implementation Notes

### API contract

`GET /api/v1/analytics/task-balance`

```json
{
  "people": [
    {
      "name": "Alice",
      "overdue": { "high": 2, "medium": 1, "low": 0 },
      "upcoming": { "high": 0, "medium": 3, "low": 1 }
    }
  ],
  "max_count": 5
}
```

### Backend query logic

Two async queries — overdue (`due_date < today`) and upcoming (`due_date >= today OR NULL`) — joined to User, grouped by name and priority. Priority collapse: urgent → high.

### New Pydantic schemas

```python
class TaskPriorityBreakdown(BaseModel):
    high: int = 0; medium: int = 0; low: int = 0

class PersonTaskBalance(BaseModel):
    name: str; overdue: TaskPriorityBreakdown; upcoming: TaskPriorityBreakdown

class TaskBalanceResponse(BaseModel):
    people: List[PersonTaskBalance]; max_count: int
```

### CSS chart approach

Per-person row: `[overdue zone flex-row-reverse] [name label w-28 text-center] [upcoming zone flex-row]`
Bar widths via inline style percentage of max_count.
Colours — Overdue: high=red-600, medium=orange-500, low=amber-400. Upcoming: high=indigo-600, medium=purple-500, low=slate-500.
