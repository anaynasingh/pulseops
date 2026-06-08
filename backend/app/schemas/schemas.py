"""
PulseOps — Pydantic v2 Schemas (request/response models)
"""
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from app.models.models import (
    UserRole, ProjectStatus, PriorityLevel,
    HealthStatus, IntakeStatus, SummaryType
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ── Users ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[UserRole] = None


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.intake
    priority: PriorityLevel = PriorityLevel.medium
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    due_date: Optional[date] = None
    tags: List[str] = []
    stakeholders: List[str] = []
    next_action: Optional[str] = None
    risks: Optional[str] = None
    blockers: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[PriorityLevel] = None
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    progress_pct: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[date] = None
    tags: Optional[List[str]] = None
    stakeholders: Optional[List[str]] = None
    next_action: Optional[str] = None
    risks: Optional[str] = None
    blockers: Optional[str] = None
    latest_update: Optional[str] = None
    kanban_order: Optional[int] = None


class ProjectOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: ProjectStatus
    priority: PriorityLevel
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    progress_pct: int
    due_date: Optional[date] = None
    tags: List[str]
    stakeholders: List[str]
    next_action: Optional[str] = None
    risks: Optional[str] = None
    blockers: Optional[str] = None
    health_score: int
    latest_update: Optional[str] = None
    kanban_order: int
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserOut] = None
    tasks: List["TaskOut"] = []
    insights: List["AIInsightOut"] = []
    health_records: List["ProjectHealthOut"] = []

    model_config = {"from_attributes": True}


# ── Kanban Move ───────────────────────────────────────────────────────────────

class KanbanMoveRequest(BaseModel):
    project_id: UUID
    new_status: ProjectStatus
    new_order: Optional[int] = None


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.todo
    priority: PriorityLevel = PriorityLevel.medium
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[PriorityLevel] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    is_completed: Optional[bool] = None


class ProjectMini(BaseModel):
    id: UUID
    title: str
    status: ProjectStatus
    priority: PriorityLevel
    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: ProjectStatus
    priority: PriorityLevel
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    assignee: Optional[UserOut] = None
    project: Optional[ProjectMini] = None

    model_config = {"from_attributes": True}


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    body: str = Field(min_length=1)
    mentions: List[str] = []


class CommentOut(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    user_id: UUID
    body: str
    mentions: List[str]
    created_at: datetime
    updated_at: datetime
    user: Optional[UserOut] = None
    replies: List["CommentOut"] = []

    model_config = {"from_attributes": True}


# ── Activity ──────────────────────────────────────────────────────────────────

class ActivityLogOut(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    user_id: Optional[UUID] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    metadata: dict = Field(default_factory=dict, alias="meta")
    created_at: datetime
    user: Optional[UserOut] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Project Health ────────────────────────────────────────────────────────────

class ProjectHealthOut(BaseModel):
    id: UUID
    project_id: UUID
    health_status: HealthStatus
    health_score: int
    risk_score: int
    delivery_confidence: int
    reasoning: Optional[str] = None
    evaluated_at: datetime

    model_config = {"from_attributes": True}


# ── AI Insights ───────────────────────────────────────────────────────────────

class AIInsightOut(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    insight_type: str
    body: str
    confidence_score: float
    is_dismissed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Intake ─────────────────────────────────────────────────────────────────

class IntakeRequest(BaseModel):
    raw_input: str = Field(min_length=10)
    team_id: Optional[UUID] = None


class IntakeResult(BaseModel):
    """Structured output from OpenAI for a request intake."""
    title: str
    description: str
    project_type: str
    suggested_tags: List[str]
    suggested_subtasks: List[str]
    suggested_next_steps: List[str]
    suggested_due_date: Optional[str] = None   # ISO date string
    suggested_priority: PriorityLevel
    suggested_owners: List[str]
    suggested_stakeholders: List[str]
    ai_reasoning: str


class IntakeConfirmRequest(BaseModel):
    confirmed_priority: PriorityLevel
    # optional overrides
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None


class IntakeOut(BaseModel):
    id: UUID
    raw_input: str
    generated_title: Optional[str] = None
    generated_description: Optional[str] = None
    project_type: Optional[str] = None
    suggested_tags: List[str]
    suggested_subtasks: Any
    suggested_next_steps: List[str]
    suggested_due_date: Optional[date] = None
    suggested_priority: Optional[PriorityLevel] = None
    suggested_owners: List[str]
    ai_reasoning: Optional[str] = None
    user_confirmed_priority: Optional[PriorityLevel] = None
    intake_status: IntakeStatus
    project_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Email Intelligence ────────────────────────────────────────────────────────

class EmailAnalysisRequest(BaseModel):
    subject: Optional[str] = None
    body: str = Field(min_length=20)
    sender: Optional[str] = None
    recipients: List[str] = []


class ExtractedTask(BaseModel):
    title: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.medium
    context: Optional[str] = None


class EmailAnalysisResult(BaseModel):
    summary: str
    extracted_tasks: List[ExtractedTask]
    extracted_people: List[str]
    extracted_deadlines: List[dict]
    extracted_blockers: List[str]


class EmailIngestionOut(BaseModel):
    id: UUID
    subject: Optional[str] = None
    sender: Optional[str] = None
    summary: Optional[str] = None
    extracted_tasks: Any
    extracted_people: List[str]
    tasks_created: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Meeting Transcript ────────────────────────────────────────────────────────

class TranscriptAnalysisRequest(BaseModel):
    title: str
    raw_transcript: str = Field(min_length=50)
    source: str = "manual"
    meeting_date: Optional[date] = None
    project_id: Optional[UUID] = None


class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.medium


class TranscriptAnalysisResult(BaseModel):
    summary: str
    action_items: List[ActionItem]
    decisions: List[str]
    blockers: List[str]
    attendees: List[str]


class TranscriptOut(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    title: str
    source: str
    summary: Optional[str] = None
    action_items: Any
    decisions: List[str]
    blockers: List[str]
    attendees: List[str]
    meeting_date: Optional[date] = None
    tasks_created: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Search ────────────────────────────────────────────────────────────────────

class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=3)
    content_types: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)


class SemanticSearchResult(BaseModel):
    content_id: UUID
    content_type: str
    similarity: float
    metadata: dict


# ── Summary ───────────────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    summary_type: SummaryType
    entity_type: str = "project"
    entity_id: Optional[UUID] = None  # None = entire workspace


class SummaryOut(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    summary_type: SummaryType
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Priority Suggestion ───────────────────────────────────────────────────────

class PrioritySuggestionRequest(BaseModel):
    project_id: UUID


class PrioritySuggestionOut(BaseModel):
    suggested_priority: PriorityLevel
    reasoning: str
    factors: List[str]


# ── Dashboard / Analytics ─────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    blocked_projects: int
    done_this_week: int
    intake_queue: int
    overdue_projects: int
    team_workload: List[dict]
    recent_activity: List[ActivityLogOut]
    high_priority_projects: List[ProjectOut]
    stale_projects: List[ProjectOut]
    ai_insights: List[AIInsightOut]


# Allow forward references
ProjectOut.model_rebuild()
CommentOut.model_rebuild()
