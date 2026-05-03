from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey,
    DateTime, Enum, Boolean, func
)
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


class RoleEnum(str, enum.Enum):
    admin  = "admin"
    member = "member"


class StatusEnum(str, enum.Enum):
    todo        = "todo"
    in_progress = "in_progress"
    done        = "done"


class PriorityEnum(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    full_name  = Column(String(100), nullable=False)
    username   = Column(String(50),  unique=True, nullable=False, index=True)
    email      = Column(String(150), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    role       = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.member)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owned_projects = relationship("Project",       back_populates="owner",        foreign_keys="Project.owner_id")
    memberships    = relationship("ProjectMember", back_populates="user")
    assigned_tasks = relationship("Task",          back_populates="assignee",     foreign_keys="Task.assignee_id")
    created_tasks  = relationship("Task",          back_populates="creator",      foreign_keys="Task.created_by")
    comments       = relationship("Comment",       back_populates="author")


# ── Projects ──────────────────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)
    description = Column(Text)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner   = relationship("User",          back_populates="owned_projects", foreign_keys=[owner_id])
    members = relationship("ProjectMember", back_populates="project",        cascade="all, delete-orphan")
    tasks   = relationship("Task",          back_populates="project",        cascade="all, delete-orphan")


# ── Project Members ───────────────────────────────────────────────────────────
class ProjectMember(Base):
    __tablename__ = "project_members"

    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    role       = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.member)
    joined_at  = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="members")
    user    = relationship("User",    back_populates="memberships")


# ── Tasks ─────────────────────────────────────────────────────────────────────
class Task(Base):
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    project_id  = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id",    ondelete="SET NULL"), nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"),   nullable=False)
    status      = Column(Enum(StatusEnum),   nullable=False, default=StatusEnum.todo)
    priority    = Column(Enum(PriorityEnum), nullable=False, default=PriorityEnum.medium)
    due_date    = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project  = relationship("Project", back_populates="tasks")
    assignee = relationship("User",    back_populates="assigned_tasks", foreign_keys=[assignee_id])
    creator  = relationship("User",    back_populates="created_tasks",  foreign_keys=[created_by])
    comments = relationship("Comment", back_populates="task",           cascade="all, delete-orphan")


# ── Comments ──────────────────────────────────────────────────────────────────
class Comment(Base):
    __tablename__ = "comments"

    id         = Column(Integer, primary_key=True, index=True)
    task_id    = Column(Integer, ForeignKey("tasks.id",  ondelete="CASCADE"), nullable=False)
    author_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task   = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
