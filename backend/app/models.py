"""Pydantic models mirroring docs/openapi.json. Inputs reject unknown fields."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Id = Annotated[int, Field(ge=1)]
Status = Literal['SUBMITTED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED']
Priority = Literal['LOW', 'NORMAL', 'HIGH']
Role = Literal['STUDENT', 'STAFF', 'COORDINATOR', 'ADMIN']
Source = Literal['rules', 'local_model']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class LoginInput(Input):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)


class User(BaseModel):
    id: Id
    name: str
    role: Role
    institution_id: Id
    department_id: Id | None


class LoginResult(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    user: User


class Institution(BaseModel):
    id: Id
    code: str
    name: str


class Location(BaseModel):
    id: Id
    name: str


class DepartmentInput(Input):
    name: str = Field(min_length=1, max_length=120)


class Department(BaseModel):
    id: Id
    name: str
    is_active: bool


class CategoryInput(Input):
    name: str = Field(min_length=1, max_length=120)
    default_department_id: Id | None = None


class Category(BaseModel):
    id: Id
    name: str
    default_department_id: Id | None
    is_active: bool


class Staff(BaseModel):
    id: Id
    name: str
    department_id: Id


class ComplaintCreate(Input):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=5000)
    location: str = Field(min_length=1, max_length=160)
    category_id: Id | None = None


class ComplaintPatch(Input):
    title: str | None = Field(None, min_length=1, max_length=160)
    description: str | None = Field(None, min_length=1, max_length=5000)
    location: str | None = Field(None, min_length=1, max_length=160)
    category_id: Id | None = None
    priority: Priority | None = None


class Complaint(BaseModel):
    id: Id
    ticket_number: str
    reporter_user_id: Id
    title: str
    description: str
    location: str
    category_id: Id | None
    status: Status
    priority: Priority
    assigned_department_id: Id | None
    assigned_user_id: Id | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class AssignmentInput(Input):
    department_id: Id
    assigned_user_id: Id | None = None


class StatusInput(Input):
    status: Status
    note: str | None = Field(None, max_length=2000)


class HistoryEntry(BaseModel):
    id: Id
    kind: Literal['STATUS', 'ASSIGNMENT']
    actor_user_id: Id
    old_status: Status | None
    new_status: Status | None
    department_id: Id | None
    assigned_user_id: Id | None
    note: str | None
    created_at: datetime


class FeedbackInput(Input):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class Feedback(BaseModel):
    id: Id
    complaint_id: Id
    author_user_id: Id
    rating: int
    comment: str | None
    created_at: datetime


class CategoryCount(BaseModel):
    category_id: Id | None
    category: str
    count: int


class Stats(BaseModel):
    total: int
    submitted: int
    in_progress: int
    resolved: int
    rejected: int
    resolved_count: int
    avg_resolution_hours: float | None
    by_category: list[CategoryCount]


class AIAnalysis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category_id: Id | None
    suggested_department_id: Id | None
    priority: Priority
    summary: str
    reason: str
    suggested_actions: list[str]
    source: Source
    needs_review: bool


class Period(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: date = Field(alias='from')
    to: date


class LocationCount(BaseModel):
    category_id: Id | None
    category: str
    location: str
    count: int


class BacklogEntry(BaseModel):
    complaint_id: Id
    ticket_number: str
    location: str
    priority: Priority
    age_hours: float


class Insights(BaseModel):
    period: Period
    generated_at: datetime
    sample_size: int
    by_category: list[CategoryCount]
    by_location: list[LocationCount]
    unresolved: int
    high_priority_unresolved: int
    oldest_unresolved: list[BacklogEntry]
    resolved_count: int
    avg_resolution_hours: float | None


class ReportInput(Input):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    from_: date = Field(alias='from')
    to: date


class Recommendation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str
    evidence: str
    department_id: Id | None
    next_step: str
    horizon: Literal['IMMEDIATE', 'ASSESSMENT']


class AdminReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    period: Period
    sample_size: int
    generated_at: datetime
    source: Source
    summary: str
    recommendations: list[Recommendation]
