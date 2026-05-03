import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

import models, schemas
from backend.database import engine, get_db
from backend.auth import hash_password, verify_password

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Create all tables on startup (idempotent — safe to run every time)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TeamTask API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_user_or_404(user_id: int, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

def get_project_or_404(project_id: int, db: Session) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return p

def get_task_or_404(task_id: int, db: Session) -> models.Task:
    t = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    return t

def is_project_admin(project_id: int, user_id: int, db: Session) -> bool:
    """Returns True if user is project owner OR has admin role in this project."""
    project = get_project_or_404(project_id, db)
    if project.owner_id == user_id:
        return True
    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id    == user_id,
        models.ProjectMember.role       == models.RoleEnum.admin,
    ).first()
    return member is not None

def is_project_member(project_id: int, user_id: int, db: Session) -> bool:
    """Returns True if user is owner or any kind of member."""
    project = get_project_or_404(project_id, db)
    if project.owner_id == user_id:
        return True
    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id    == user_id,
    ).first()
    return member is not None

def build_task_out(task: models.Task) -> dict:
    return {
        "id":            task.id,
        "title":         task.title,
        "description":   task.description,
        "project_id":    task.project_id,
        "assignee_id":   task.assignee_id,
        "assignee_name": task.assignee.full_name if task.assignee else None,
        "created_by":    task.created_by,
        "creator_name":  task.creator.full_name if task.creator else "Unknown",
        "status":        task.status,
        "priority":      task.priority,
        "due_date":      task.due_date,
        "created_at":    task.created_at,
        "updated_at":    task.updated_at,
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "TeamTask API running", "version": "1.0.0"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/signup", response_model=schemas.UserOut)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check username
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(400, "Username already taken")
    # Check email
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    # First user ever → global admin
    count = db.query(func.count(models.User.id)).scalar()
    role  = models.RoleEnum.admin if count == 0 else models.RoleEnum.member

    user = models.User(
        full_name = payload.full_name,
        username  = payload.username,
        email     = payload.email,
        password  = hash_password(payload.password),
        role      = role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.UserOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(401, "Invalid username or password")
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")
    return user


# ── Users ─────────────────────────────────────────────────────────────────────

@app.get("/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.full_name).all()


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_user_or_404(user_id, db)


@app.patch("/users/{user_id}/role")
def change_global_role(
    user_id: int,
    role: str = Query(..., regex="^(admin|member)$"),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(user_id, db)
    user.role = models.RoleEnum(role)
    db.commit()
    return {"detail": f"Role updated to {role}"}


# ── Projects ──────────────────────────────────────────────────────────────────

@app.get("/projects", response_model=List[schemas.ProjectOut])
def list_projects(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Return all projects this user owns or is a member of."""
    user = get_user_or_404(user_id, db)

    # Global admins see all projects
    if user.role == models.RoleEnum.admin:
        return db.query(models.Project).order_by(models.Project.created_at.desc()).all()

    owned = db.query(models.Project).filter(models.Project.owner_id == user_id)
    member_project_ids = [
        m.project_id for m in
        db.query(models.ProjectMember).filter(models.ProjectMember.user_id == user_id).all()
    ]
    member_projects = db.query(models.Project).filter(
        models.Project.id.in_(member_project_ids)
    )
    return owned.union(member_projects).order_by(models.Project.created_at.desc()).all()


@app.post("/projects", response_model=schemas.ProjectOut)
def create_project(
    payload: schemas.ProjectCreate,
    owner_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_user_or_404(owner_id, db)
    project = models.Project(
        name        = payload.name,
        description = payload.description,
        owner_id    = owner_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Auto-add owner as admin member so they show up in member lists
    membership = models.ProjectMember(
        project_id = project.id,
        user_id    = owner_id,
        role       = models.RoleEnum.admin,
    )
    db.add(membership)
    db.commit()
    return project


@app.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return get_project_or_404(project_id, db)


@app.patch("/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if not is_project_admin(project_id, user_id, db):
        raise HTTPException(403, "Only project admins can edit this project")
    project = get_project_or_404(project_id, db)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    project = get_project_or_404(project_id, db)
    user    = get_user_or_404(user_id, db)
    # Only project owner OR global admin can delete
    if project.owner_id != user_id and user.role != models.RoleEnum.admin:
        raise HTTPException(403, "Only the project owner can delete this project")
    db.delete(project)
    db.commit()
    return {"detail": "Project deleted"}


# ── Project Members ───────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/members")
def get_members(project_id: int, db: Session = Depends(get_db)):
    get_project_or_404(project_id, db)
    members = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id
    ).all()
    result = []
    for m in members:
        result.append({
            "id":        m.id,
            "user_id":   m.user_id,
            "full_name": m.user.full_name,
            "username":  m.user.username,
            "role":      m.role,
            "joined_at": m.joined_at,
        })
    return result


@app.post("/projects/{project_id}/members")
def add_member(
    project_id: int,
    payload: schemas.MemberAdd,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if not is_project_admin(project_id, user_id, db):
        raise HTTPException(403, "Only project admins can add members")

    target = db.query(models.User).filter(models.User.username == payload.username).first()
    if not target:
        raise HTTPException(404, f"User '{payload.username}' not found")

    existing = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id    == target.id,
    ).first()
    if existing:
        raise HTTPException(400, "User is already a member of this project")

    member = models.ProjectMember(
        project_id = project_id,
        user_id    = target.id,
        role       = models.RoleEnum(payload.role),
    )
    db.add(member)
    db.commit()
    return {"detail": f"{target.full_name} added as {payload.role}"}


@app.delete("/projects/{project_id}/members/{member_user_id}")
def remove_member(
    project_id: int,
    member_user_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    project = get_project_or_404(project_id, db)
    if project.owner_id == member_user_id:
        raise HTTPException(400, "Cannot remove the project owner")
    if not is_project_admin(project_id, user_id, db):
        raise HTTPException(403, "Only admins can remove members")

    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id    == member_user_id,
    ).first()
    if not member:
        raise HTTPException(404, "Member not found")

    db.delete(member)
    db.commit()
    return {"detail": "Member removed"}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/tasks")
def get_tasks(
    project_id: int,
    status:   Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
):
    get_project_or_404(project_id, db)
    q = db.query(models.Task).filter(models.Task.project_id == project_id)
    if status:
        q = q.filter(models.Task.status == status)
    if priority:
        q = q.filter(models.Task.priority == priority)
    tasks = q.order_by(models.Task.created_at.desc()).all()
    return [build_task_out(t) for t in tasks]


@app.post("/projects/{project_id}/tasks")
def create_task(
    project_id: int,
    payload: schemas.TaskCreate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if not is_project_member(project_id, user_id, db):
        raise HTTPException(403, "You are not a member of this project")

    # Validate assignee is a project member
    if payload.assignee_id:
        if not is_project_member(project_id, payload.assignee_id, db):
            raise HTTPException(400, "Assignee must be a project member")

    task = models.Task(
        title       = payload.title,
        description = payload.description,
        project_id  = project_id,
        assignee_id = payload.assignee_id,
        created_by  = user_id,
        status      = models.StatusEnum(payload.status),
        priority    = models.PriorityEnum(payload.priority),
        due_date    = payload.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return build_task_out(task)


@app.patch("/projects/{project_id}/tasks/{task_id}")
def update_task(
    project_id: int,
    task_id: int,
    payload: schemas.TaskUpdate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if not is_project_member(project_id, user_id, db):
        raise HTTPException(403, "You are not a member of this project")

    task = get_task_or_404(task_id, db)
    if task.project_id != project_id:
        raise HTTPException(404, "Task not found in this project")

    # Members can only update their own tasks unless they're project admin
    if not is_project_admin(project_id, user_id, db) and task.created_by != user_id:
        # But members can update status/assignee of tasks assigned to them
        if task.assignee_id != user_id:
            raise HTTPException(403, "You can only update tasks you created or are assigned to")

    for field, value in payload.dict(exclude_unset=True).items():
        if field == "status" and value:
            setattr(task, field, models.StatusEnum(value))
        elif field == "priority" and value:
            setattr(task, field, models.PriorityEnum(value))
        else:
            setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return build_task_out(task)


@app.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(
    project_id: int,
    task_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    task = get_task_or_404(task_id, db)
    if task.project_id != project_id:
        raise HTTPException(404, "Task not found in this project")
    if not is_project_admin(project_id, user_id, db) and task.created_by != user_id:
        raise HTTPException(403, "Only project admins or task creator can delete tasks")
    db.delete(task)
    db.commit()
    return {"detail": "Task deleted"}


# ── Comments ──────────────────────────────────────────────────────────────────

@app.get("/tasks/{task_id}/comments")
def get_comments(task_id: int, db: Session = Depends(get_db)):
    get_task_or_404(task_id, db)
    comments = db.query(models.Comment).filter(
        models.Comment.task_id == task_id
    ).order_by(models.Comment.created_at.asc()).all()
    return [
        {
            "id":          c.id,
            "task_id":     c.task_id,
            "author_id":   c.author_id,
            "author_name": c.author.full_name if c.author else "Unknown",
            "content":     c.content,
            "created_at":  c.created_at,
        }
        for c in comments
    ]


@app.post("/tasks/{task_id}/comments")
def add_comment(
    task_id: int,
    payload: schemas.CommentCreate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    task = get_task_or_404(task_id, db)
    if not is_project_member(task.project_id, user_id, db):
        raise HTTPException(403, "You are not a member of this project")
    comment = models.Comment(
        task_id   = task_id,
        author_id = user_id,
        content   = payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "id":          comment.id,
        "task_id":     comment.task_id,
        "author_id":   comment.author_id,
        "author_name": comment.author.full_name,
        "content":     comment.content,
        "created_at":  comment.created_at,
    }


@app.delete("/tasks/{task_id}/comments/{comment_id}")
def delete_comment(
    task_id: int,
    comment_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment or comment.task_id != task_id:
        raise HTTPException(404, "Comment not found")
    task = get_task_or_404(task_id, db)
    user = get_user_or_404(user_id, db)
    if comment.author_id != user_id and not is_project_admin(task.project_id, user_id, db) and user.role != models.RoleEnum.admin:
        raise HTTPException(403, "Cannot delete this comment")
    db.delete(comment)
    db.commit()
    return {"detail": "Comment deleted"}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard")
def dashboard(user_id: int = Query(...), db: Session = Depends(get_db)):
    user = get_user_or_404(user_id, db)
    now  = datetime.now(timezone.utc)

    if user.role == models.RoleEnum.admin:
        # Global admin sees everything
        all_tasks    = db.query(models.Task).all()
        all_projects = db.query(models.Project).all()
    else:
        member_project_ids = [
            m.project_id for m in
            db.query(models.ProjectMember).filter(
                models.ProjectMember.user_id == user_id
            ).all()
        ]
        owned_ids = [
            p.id for p in
            db.query(models.Project).filter(
                models.Project.owner_id == user_id
            ).all()
        ]
        visible_ids = list(set(member_project_ids + owned_ids))
        all_tasks    = db.query(models.Task).filter(
            models.Task.project_id.in_(visible_ids)
        ).all()
        all_projects = db.query(models.Project).filter(
            models.Project.id.in_(visible_ids)
        ).all()

    overdue = [
        t for t in all_tasks
        if t.due_date and t.due_date.replace(tzinfo=timezone.utc) < now
        and t.status != models.StatusEnum.done
    ]

    my_tasks = [t for t in all_tasks if t.assignee_id == user_id]

    # Recent activity: last 10 tasks updated
    recent = sorted(all_tasks, key=lambda t: t.updated_at, reverse=True)[:10]

    return {
        "total_projects":   len(all_projects),
        "total_tasks":      len(all_tasks),
        "todo_count":       sum(1 for t in all_tasks if t.status == models.StatusEnum.todo),
        "inprogress_count": sum(1 for t in all_tasks if t.status == models.StatusEnum.in_progress),
        "done_count":       sum(1 for t in all_tasks if t.status == models.StatusEnum.done),
        "overdue_count":    len(overdue),
        "my_tasks_count":   len(my_tasks),
        "overdue_tasks": [
            {
                "id":       t.id,
                "title":    t.title,
                "project":  t.project.name if t.project else "",
                "due_date": t.due_date,
                "priority": t.priority,
            }
            for t in overdue[:5]
        ],
        "recent_tasks": [
            {
                "id":         t.id,
                "title":      t.title,
                "status":     t.status,
                "priority":   t.priority,
                "project":    t.project.name if t.project else "",
                "updated_at": t.updated_at,
            }
            for t in recent
        ],
    }
