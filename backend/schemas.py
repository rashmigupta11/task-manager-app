from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    admin  = "admin"
    member = "member"


class StatusEnum(str, Enum):
    todo        = "todo"
    in_progress = "in_progress"
    done        = "done"


class PriorityEnum(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    username:  str = Field(min_length=3, max_length=50)
    email:     str = Field(min_length=5, max_length=150)
    password:  str = Field(min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id:         int
    full_name:  str
    username:   str
    email:      str
    role:       RoleEnum
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserShort(BaseModel):
    id:        int
    full_name: str
    username:  str
    role:      RoleEnum

    class Config:
        from_attributes = True


# ── Projects ──────────────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name:        str  = Field(min_length=2, max_length=150)
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    owner_id:    int
    created_at:  datetime

    class Config:
        from_attributes = True


# ── Project Members ───────────────────────────────────────────────────────────
class MemberAdd(BaseModel):
    username: str
    role:     RoleEnum = RoleEnum.member

class MemberOut(BaseModel):
    id:        int
    user_id:   int
    full_name: str
    username:  str
    role:      RoleEnum
    joined_at: datetime

    class Config:
        from_attributes = True


# ── Tasks ─────────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title:       str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    status:      StatusEnum   = StatusEnum.todo
    priority:    PriorityEnum = PriorityEnum.medium
    due_date:    Optional[datetime] = None

class TaskUpdate(BaseModel):
    title:       Optional[str]          = None
    description: Optional[str]          = None
    assignee_id: Optional[int]          = None
    status:      Optional[StatusEnum]   = None
    priority:    Optional[PriorityEnum] = None
    due_date:    Optional[datetime]     = None

class TaskOut(BaseModel):
    id:            int
    title:         str
    description:   Optional[str]
    project_id:    int
    assignee_id:   Optional[int]
    assignee_name: Optional[str]
    created_by:    int
    creator_name:  str
    status:        StatusEnum
    priority:      PriorityEnum
    due_date:      Optional[datetime]
    created_at:    datetime
    updated_at:    datetime

    class Config:
        from_attributes = True


# ── Comments ──────────────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

class CommentOut(BaseModel):
    id:          int
    task_id:     int
    author_id:   int
    author_name: str
    content:     str
    created_at:  datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardSummary(BaseModel):
    total_projects:  int
    total_tasks:     int
    todo_count:      int
    inprogress_count:int
    done_count:      int
    overdue_count:   int
    my_tasks:        int
