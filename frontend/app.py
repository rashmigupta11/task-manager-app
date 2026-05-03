import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
API = os.getenv("API_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TeamTask",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background: #0d1117; color: #cdd9e5; }

section[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #21262d;
}

/* Sidebar nav */
div[data-testid="stSidebar"] .stRadio label {
    font-size: 14px !important;
    padding: 6px 0 !important;
    color: #8b949e !important;
    transition: color .15s;
}
div[data-testid="stSidebar"] .stRadio label:hover { color: #cdd9e5 !important; }

/* Cards */
.card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    margin-bottom: .6rem;
    transition: border-color .15s;
}
.card:hover { border-color: #388bfd; }

.card-title {
    font-size: 15px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 4px;
}
.card-meta {
    font-size: 12px;
    color: #8b949e;
    font-family: 'DM Mono', monospace;
}

/* Metric boxes */
.metric-box {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.metric-box .num {
    font-size: 32px;
    font-weight: 700;
    font-family: 'DM Mono', monospace;
    line-height: 1.1;
}
.metric-box .lbl {
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-top: 4px;
}
.clr-blue   { color: #388bfd; }
.clr-yellow { color: #d29922; }
.clr-green  { color: #3fb950; }
.clr-red    { color: #f85149; }
.clr-purple { color: #a371f7; }

/* Priority / status badges */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
    font-family: 'DM Mono', monospace;
}
.b-todo        { background: #21262d; color: #8b949e; }
.b-inprogress  { background: #1c2a3a; color: #388bfd; }
.b-done        { background: #1a2f1a; color: #3fb950; }
.b-low         { background: #1a2f1a; color: #3fb950; }
.b-medium      { background: #2d2208; color: #d29922; }
.b-high        { background: #2d1414; color: #f85149; }
.b-admin       { background: #2d1b54; color: #a371f7; }
.b-member      { background: #1c2a3a; color: #388bfd; }
.b-overdue     { background: #2d1414; color: #f85149; }

/* Page title */
.page-title {
    font-size: 24px;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 2px;
}
.page-sub {
    font-size: 13px;
    color: #8b949e;
    margin-bottom: 1.4rem;
}

/* Form inputs */
.stTextInput > div > input,
.stTextArea > div > textarea,
.stNumberInput > div > input,
.stSelectbox > div > div,
.stDateInput > div > input {
    background: #161b22 !important;
    color: #cdd9e5 !important;
    border: 1px solid #21262d !important;
    border-radius: 6px !important;
}
.stTextInput > div > input:focus,
.stTextArea > div > textarea:focus {
    border-color: #388bfd !important;
    box-shadow: none !important;
}

/* Buttons */
.stButton > button {
    background: #238636;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 13px;
    padding: .45rem 1.1rem;
    transition: background .15s;
}
.stButton > button:hover { background: #2ea043; }

/* Tabs */
.stTabs [data-baseweb="tab"] { color: #8b949e !important; }
.stTabs [aria-selected="true"] { color: #e6edf3 !important; border-bottom-color: #388bfd !important; }

hr { border-color: #21262d; margin: .4rem 0; }

.section-head {
    font-size: 13px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: .07em;
    margin: 1.2rem 0 .6rem;
}

.brand-logo {
    font-size: 22px;
    font-weight: 700;
    color: #e6edf3;
    letter-spacing: -.5px;
    padding: 1rem 0 1.4rem;
}
</style>
""", unsafe_allow_html=True)

# ── Session init ───────────────────────────────────────────────────────────────
for key in ["user", "active_project"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ── API helpers ────────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs):
    try:
        r = getattr(requests, method)(f"{API}{path}", timeout=12, **kwargs)
        return r
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the API server. Is the backend running?")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def jget(path, **kw):
    r = api("get", path, **kw)
    return r.json() if r and r.status_code == 200 else None

def jpost(path, data, **kw):
    return api("post", path, json=data, **kw)

def jpatch(path, data, **kw):
    return api("patch", path, json=data, **kw)

def jdelete(path, **kw):
    return api("delete", path, **kw)


# ── Badge helpers ──────────────────────────────────────────────────────────────
STATUS_CLASS   = {"todo": "b-todo", "in_progress": "b-inprogress", "done": "b-done"}
STATUS_LABEL   = {"todo": "To Do",  "in_progress": "In Progress",  "done": "Done"}
PRIORITY_CLASS = {"low": "b-low", "medium": "b-medium", "high": "b-high"}

def sbadge(status):
    return f'<span class="badge {STATUS_CLASS.get(status,"b-todo")}">{STATUS_LABEL.get(status, status)}</span>'

def pbadge(priority):
    return f'<span class="badge {PRIORITY_CLASS.get(priority,"b-medium")}">{priority.capitalize()}</span>'

def rbadge(role):
    cls = "b-admin" if role == "admin" else "b-member"
    return f'<span class="badge {cls}">{role.upper()}</span>'

def is_overdue(due_date_str):
    if not due_date_str:
        return False
    try:
        dt = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except Exception:
        return False

def fmt_date(dt_str):
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return dt_str[:10]


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════
def show_auth():
    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown("""
        <div style='text-align:center;padding:2.5rem 0 2rem'>
            <div style='font-size:42px;margin-bottom:6px'>🗂️</div>
            <div style='font-size:30px;font-weight:700;color:#e6edf3;letter-spacing:-1px'>TeamTask</div>
            <div style='font-size:13px;color:#8b949e;margin-top:4px'>Collaborative project & task management</div>
        </div>
        """, unsafe_allow_html=True)

        tab_l, tab_s = st.tabs(["Login", "Create Account"])

        with tab_l:
            with st.form("login"):
                username  = st.text_input("Username")
                password  = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Fill in all fields.")
                else:
                    r = jpost("/auth/login", {"username": username, "password": password})
                    if r is None:
                        pass
                    elif r.status_code == 200:
                        st.session_state.user = r.json()
                        st.rerun()
                    elif r.status_code == 401:
                        st.error("Invalid username or password.")
                    else:
                        st.error(f"Login failed: {r.json().get('detail','')}")

        with tab_s:
            with st.form("signup"):
                full_name  = st.text_input("Full Name")
                s_user     = st.text_input("Username  (min 3 chars)")
                email      = st.text_input("Email")
                s_pass     = st.text_input("Password  (min 6 chars)", type="password")
                s_confirm  = st.text_input("Confirm Password", type="password")
                submitted2 = st.form_submit_button("Create Account", use_container_width=True)
            if submitted2:
                if not all([full_name, s_user, email, s_pass, s_confirm]):
                    st.error("Fill in all fields.")
                elif s_pass != s_confirm:
                    st.error("Passwords do not match.")
                elif len(s_pass) < 6:
                    st.error("Password must be ≥ 6 characters.")
                elif "@" not in email:
                    st.error("Enter a valid email.")
                else:
                    r = jpost("/auth/signup", {
                        "full_name": full_name,
                        "username":  s_user,
                        "email":     email,
                        "password":  s_pass,
                    })
                    if r is None:
                        pass
                    elif r.status_code == 200:
                        st.success("✅ Account created! Please log in.")
                    elif r.status_code == 400:
                        st.error(r.json().get("detail", "Username or email already exists."))
                    else:
                        st.error("Signup failed. Try again.")


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def show_sidebar():
    u = st.session_state.user
    with st.sidebar:
        st.markdown('<div class="brand-logo">🗂️ TeamTask</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="margin-bottom:1.2rem">
            <div style="font-weight:600;color:#e6edf3">{u['full_name']}</div>
            <div style="font-size:12px;color:#8b949e;margin-top:2px">
                @{u['username']} · {rbadge(u['role'])}
            </div>
        </div>
        """, unsafe_allow_html=True)

        pages = ["Dashboard", "My Projects", "My Tasks", "All Users"]
        page  = st.radio("", pages, label_visibility="collapsed")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            st.session_state.user           = None
            st.session_state.active_project = None
            st.rerun()
    return page


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    u = st.session_state.user
    st.markdown(f'<div class="page-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Welcome back, {u["full_name"]}</div>', unsafe_allow_html=True)

    data = jget("/dashboard", params={"user_id": u["id"]})
    if not data:
        st.info("No data yet. Create a project to get started.")
        return

    # Metric row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    metrics = [
        (c1, data["total_projects"],   "Projects",    "clr-blue"),
        (c2, data["total_tasks"],      "Total Tasks",  "clr-blue"),
        (c3, data["todo_count"],       "To Do",        "clr-yellow"),
        (c4, data["inprogress_count"], "In Progress",  "clr-blue"),
        (c5, data["done_count"],       "Done",         "clr-green"),
        (c6, data["overdue_count"],    "Overdue",      "clr-red"),
    ]
    for col, val, lbl, clr in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-box">
                <div class="num {clr}">{val}</div>
                <div class="lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    left, right = st.columns(2)

    with left:
        st.markdown('<div class="section-head">⚠️ Overdue Tasks</div>', unsafe_allow_html=True)
        overdue = data.get("overdue_tasks", [])
        if not overdue:
            st.markdown('<div class="card"><span style="color:#3fb950">✓ No overdue tasks</span></div>', unsafe_allow_html=True)
        else:
            for t in overdue:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">{t['title']}</div>
                    <div class="card-meta">
                        {t['project']} · Due {fmt_date(str(t['due_date']))} · {pbadge(t['priority'])}
                        <span class="badge b-overdue">OVERDUE</span>
                    </div>
                </div>""", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-head">🕐 Recent Activity</div>', unsafe_allow_html=True)
        recent = data.get("recent_tasks", [])
        if not recent:
            st.markdown('<div class="card" style="color:#8b949e">No recent activity</div>', unsafe_allow_html=True)
        else:
            for t in recent:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">{t['title']}</div>
                    <div class="card-meta">
                        {t['project']} · {sbadge(t['status'])} · Updated {fmt_date(str(t['updated_at']))}
                    </div>
                </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MY PROJECTS
# ══════════════════════════════════════════════════════════════════════════════
def page_projects():
    u = st.session_state.user
    st.markdown('<div class="page-title">My Projects</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Projects you own or belong to</div>', unsafe_allow_html=True)

    if st.session_state.active_project:
        project_detail(st.session_state.active_project)
        return

    # ── Create project ─────────────────────────────────────────────────────
    with st.expander("➕ Create New Project"):
        with st.form("create_project"):
            pname = st.text_input("Project name *")
            pdesc = st.text_area("Description", height=80)
            if st.form_submit_button("Create Project"):
                if not pname.strip():
                    st.error("Project name required.")
                else:
                    r = jpost("/projects", {"name": pname.strip(), "description": pdesc},
                              params={"owner_id": u["id"]})
                    if r and r.status_code == 200:
                        st.success(f"✅ '{pname}' created!")
                        st.rerun()
                    elif r:
                        st.error(r.json().get("detail", "Failed to create project."))

    # ── List projects ──────────────────────────────────────────────────────
    projects = jget("/projects", params={"user_id": u["id"]})
    if not projects:
        st.info("No projects yet. Create one above.")
        return

    for p in projects:
        tasks = jget(f"/projects/{p['id']}/tasks") or []
        done  = sum(1 for t in tasks if t["status"] == "done")
        total = len(tasks)
        pct   = int(done / total * 100) if total > 0 else 0
        is_owner = p["owner_id"] == u["id"]

        col_main, col_btn = st.columns([5, 1])
        with col_main:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">{p['name']}
                    {'<span style="color:#8b949e;font-size:11px;margin-left:8px">(owner)</span>' if is_owner else ''}
                </div>
                <div class="card-meta">{p.get('description') or 'No description'}</div>
                <div style="margin-top:8px;font-size:12px;color:#8b949e">
                    {done}/{total} tasks done &nbsp;·&nbsp;
                    <span style="color:{'#3fb950' if pct==100 else '#388bfd'}">{pct}%</span>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            if st.button("Open →", key=f"open_{p['id']}"):
                st.session_state.active_project = p
                st.rerun()


# ── Project Detail (tasks + members + settings) ────────────────────────────
def project_detail(p):
    u = st.session_state.user
    is_admin = p["owner_id"] == u["id"]

    col_back, col_title = st.columns([1, 8])
    with col_back:
        if st.button("← Back"):
            st.session_state.active_project = None
            st.rerun()
    with col_title:
        st.markdown(f'<div class="page-title">{p["name"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="page-sub">{p.get("description") or ""}</div>', unsafe_allow_html=True)

    tab_tasks, tab_members, tab_settings = st.tabs(["Tasks", "Members", "Settings"])

    # ── TASKS TAB ──────────────────────────────────────────────────────────
    with tab_tasks:
        members_raw = jget(f"/projects/{p['id']}/members") or []
        member_map  = {m["user_id"]: m["full_name"] for m in members_raw}
        member_opts = {m["full_name"]: m["user_id"] for m in members_raw}

        with st.expander("➕ Add Task"):
            with st.form("add_task"):
                t_title = st.text_input("Task title *")
                t_desc  = st.text_area("Description", height=70)
                c1, c2, c3 = st.columns(3)
                with c1:
                    t_assignee_name = st.selectbox("Assign to", ["(unassigned)"] + list(member_opts.keys()))
                with c2:
                    t_status   = st.selectbox("Status",   ["todo", "in_progress", "done"],
                                              format_func=lambda x: STATUS_LABEL[x])
                with c3:
                    t_priority = st.selectbox("Priority", ["low", "medium", "high"],
                                              index=1,
                                              format_func=lambda x: x.capitalize())
                t_due = st.date_input("Due date (optional)", value=None)
                if st.form_submit_button("Add Task"):
                    if not t_title.strip():
                        st.error("Task title required.")
                    else:
                        assignee_id = member_opts.get(t_assignee_name) if t_assignee_name != "(unassigned)" else None
                        due_iso     = datetime(t_due.year, t_due.month, t_due.day).isoformat() if t_due else None
                        r = jpost(f"/projects/{p['id']}/tasks", {
                            "title":       t_title.strip(),
                            "description": t_desc,
                            "assignee_id": assignee_id,
                            "status":      t_status,
                            "priority":    t_priority,
                            "due_date":    due_iso,
                        }, params={"user_id": u["id"]})
                        if r and r.status_code == 200:
                            st.success("✅ Task added!")
                            st.rerun()
                        elif r:
                            st.error(r.json().get("detail", "Failed."))

        # Filters
        cf1, cf2, cf3 = st.columns([2, 2, 4])
        with cf1:
            f_status = st.selectbox("Filter status",
                                    ["all", "todo", "in_progress", "done"],
                                    format_func=lambda x: "All Statuses" if x == "all" else STATUS_LABEL[x])
        with cf2:
            f_priority = st.selectbox("Filter priority",
                                      ["all", "high", "medium", "low"],
                                      format_func=lambda x: "All Priorities" if x == "all" else x.capitalize())

        params = {"user_id": u["id"]}
        if f_status   != "all": params["status"]   = f_status
        if f_priority != "all": params["priority"] = f_priority
        tasks = jget(f"/projects/{p['id']}/tasks", params=params) or []

        if not tasks:
            st.info("No tasks found.")
        else:
            for t in tasks:
                overdue_flag = is_overdue(str(t["due_date"])) if t["due_date"] else False
                can_edit = is_admin or t["created_by"] == u["id"] or t["assignee_id"] == u["id"]

                with st.container():
                    tc1, tc2 = st.columns([7, 1])
                    with tc1:
                        ov_badge = '<span class="badge b-overdue">OVERDUE</span>' if overdue_flag else ""
                        st.markdown(f"""
                        <div class="card">
                            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                                <span class="card-title">{t['title']}</span>
                                {sbadge(t['status'])} {pbadge(t['priority'])} {ov_badge}
                            </div>
                            <div class="card-meta" style="margin-top:5px">
                                Assigned to: {member_map.get(t['assignee_id'], 'Unassigned')} &nbsp;·&nbsp;
                                Due: {fmt_date(str(t['due_date'])) if t['due_date'] else '—'} &nbsp;·&nbsp;
                                By: {t['creator_name']}
                            </div>
                            {f'<div style="font-size:13px;color:#8b949e;margin-top:4px">{t["description"]}</div>' if t.get("description") else ''}
                        </div>""", unsafe_allow_html=True)
                    with tc2:
                        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                        if can_edit and st.button("Edit", key=f"edit_t_{t['id']}"):
                            st.session_state[f"edit_task_{t['id']}"] = True
                        if (is_admin or t["created_by"] == u["id"]) and st.button("Del", key=f"del_t_{t['id']}"):
                            r = jdelete(f"/projects/{p['id']}/tasks/{t['id']}", params={"user_id": u["id"]})
                            if r and r.status_code == 200:
                                st.rerun()

                # Inline edit
                if st.session_state.get(f"edit_task_{t['id']}"):
                    with st.expander(f"Edit: {t['title']}", expanded=True):
                        with st.form(f"eform_{t['id']}"):
                            e_title = st.text_input("Title", value=t["title"])
                            e_desc  = st.text_area("Description", value=t.get("description") or "", height=70)
                            ec1, ec2, ec3 = st.columns(3)
                            with ec1:
                                e_assignee = st.selectbox(
                                    "Assign to",
                                    ["(unassigned)"] + list(member_opts.keys()),
                                    index=(["(unassigned)"] + list(member_opts.keys())).index(
                                        member_map.get(t["assignee_id"], "(unassigned)")
                                    ) if member_map.get(t["assignee_id"]) in (["(unassigned)"] + list(member_opts.keys())) else 0,
                                )
                            with ec2:
                                status_opts = ["todo", "in_progress", "done"]
                                e_status = st.selectbox("Status", status_opts,
                                    index=status_opts.index(t["status"]),
                                    format_func=lambda x: STATUS_LABEL[x])
                            with ec3:
                                pri_opts = ["low", "medium", "high"]
                                e_priority = st.selectbox("Priority", pri_opts,
                                    index=pri_opts.index(t["priority"]),
                                    format_func=lambda x: x.capitalize())
                            if st.form_submit_button("Save"):
                                r = jpatch(f"/projects/{p['id']}/tasks/{t['id']}", {
                                    "title":       e_title,
                                    "description": e_desc,
                                    "assignee_id": member_opts.get(e_assignee) if e_assignee != "(unassigned)" else None,
                                    "status":      e_status,
                                    "priority":    e_priority,
                                }, params={"user_id": u["id"]})
                                if r and r.status_code == 200:
                                    del st.session_state[f"edit_task_{t['id']}"]
                                    st.success("Saved!")
                                    st.rerun()
                                elif r:
                                    st.error(r.json().get("detail", "Update failed."))

                # Comments
                with st.expander(f"💬 Comments — {t['title']}", expanded=False):
                    comments = jget(f"/tasks/{t['id']}/comments") or []
                    for c in comments:
                        col_a, col_b = st.columns([8, 1])
                        with col_a:
                            st.markdown(f"""
                            <div style="border-left:2px solid #21262d;padding:4px 0 4px 10px;margin-bottom:6px">
                                <span style="font-size:12px;font-weight:600;color:#388bfd">@{c['author_name']}</span>
                                <span style="font-size:11px;color:#8b949e;margin-left:8px">{fmt_date(str(c['created_at']))}</span><br>
                                <span style="font-size:13px;color:#cdd9e5">{c['content']}</span>
                            </div>""", unsafe_allow_html=True)
                        with col_b:
                            if c["author_id"] == u["id"] or is_admin:
                                if st.button("🗑", key=f"dc_{c['id']}"):
                                    jdelete(f"/tasks/{t['id']}/comments/{c['id']}", params={"user_id": u["id"]})
                                    st.rerun()

                    with st.form(f"cmt_{t['id']}"):
                        cmt_text = st.text_input("Write a comment…", label_visibility="collapsed")
                        if st.form_submit_button("Post"):
                            if cmt_text.strip():
                                r = jpost(f"/tasks/{t['id']}/comments",
                                          {"content": cmt_text.strip()},
                                          params={"user_id": u["id"]})
                                if r and r.status_code == 200:
                                    st.rerun()

    # ── MEMBERS TAB ────────────────────────────────────────────────────────
    with tab_members:
        members = jget(f"/projects/{p['id']}/members") or []

        st.markdown(f'<div class="section-head">Team Members ({len(members)})</div>', unsafe_allow_html=True)
        for m in members:
            mc1, mc2 = st.columns([6, 1])
            with mc1:
                st.markdown(f"""
                <div class="card">
                    <span style="font-weight:600;color:#e6edf3">{m['full_name']}</span>
                    <span style="color:#8b949e;font-size:12px;margin-left:8px">@{m['username']}</span>
                    &nbsp;{rbadge(m['role'])}
                </div>""", unsafe_allow_html=True)
            with mc2:
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                if is_admin and m["user_id"] != u["id"]:
                    if st.button("Remove", key=f"rm_{m['user_id']}"):
                        r = jdelete(f"/projects/{p['id']}/members/{m['user_id']}",
                                    params={"user_id": u["id"]})
                        if r and r.status_code == 200:
                            st.rerun()
                        elif r:
                            st.error(r.json().get("detail", "Failed."))

        if is_admin:
            st.markdown('<div class="section-head">Add Member</div>', unsafe_allow_html=True)
            with st.form("add_member"):
                m_username = st.text_input("Username to add")
                m_role     = st.selectbox("Role", ["member", "admin"])
                if st.form_submit_button("Add"):
                    if not m_username.strip():
                        st.error("Enter a username.")
                    else:
                        r = jpost(f"/projects/{p['id']}/members",
                                  {"username": m_username.strip(), "role": m_role},
                                  params={"user_id": u["id"]})
                        if r and r.status_code == 200:
                            st.success("✅ Member added!")
                            st.rerun()
                        elif r:
                            st.error(r.json().get("detail", "Failed."))

    # ── SETTINGS TAB ───────────────────────────────────────────────────────
    with tab_settings:
        if is_admin:
            st.markdown('<div class="section-head">Edit Project</div>', unsafe_allow_html=True)
            with st.form("edit_project"):
                ep_name = st.text_input("Project name", value=p["name"])
                ep_desc = st.text_area("Description",   value=p.get("description") or "", height=80)
                if st.form_submit_button("Save Changes"):
                    r = jpatch(f"/projects/{p['id']}",
                               {"name": ep_name, "description": ep_desc},
                               params={"user_id": u["id"]})
                    if r and r.status_code == 200:
                        st.success("✅ Project updated!")
                        st.session_state.active_project = r.json()
                        st.rerun()
                    elif r:
                        st.error(r.json().get("detail", "Failed."))

            st.markdown('<div class="section-head" style="color:#f85149">Danger Zone</div>', unsafe_allow_html=True)
            if st.checkbox("I want to delete this project permanently"):
                if st.button("🗑️ Delete Project", type="primary"):
                    r = jdelete(f"/projects/{p['id']}", params={"user_id": u["id"]})
                    if r and r.status_code == 200:
                        st.session_state.active_project = None
                        st.success("Project deleted.")
                        st.rerun()
                    elif r:
                        st.error(r.json().get("detail", "Failed."))
        else:
            st.info("Only project admins can change settings.")


# ══════════════════════════════════════════════════════════════════════════════
# MY TASKS
# ══════════════════════════════════════════════════════════════════════════════
def page_my_tasks():
    u = st.session_state.user
    st.markdown('<div class="page-title">My Tasks</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">All tasks assigned to you across projects</div>', unsafe_allow_html=True)

    projects = jget("/projects", params={"user_id": u["id"]}) or []
    if not projects:
        st.info("You have no projects yet.")
        return

    all_tasks = []
    for proj in projects:
        tasks = jget(f"/projects/{proj['id']}/tasks") or []
        for t in tasks:
            if t["assignee_id"] == u["id"]:
                t["project_name"] = proj["name"]
                t["project_id_ref"] = proj["id"]
                all_tasks.append(t)

    if not all_tasks:
        st.info("No tasks assigned to you yet.")
        return

    # Summary
    todo_n = sum(1 for t in all_tasks if t["status"] == "todo")
    ip_n   = sum(1 for t in all_tasks if t["status"] == "in_progress")
    dn_n   = sum(1 for t in all_tasks if t["status"] == "done")
    ov_n   = sum(1 for t in all_tasks if is_overdue(str(t["due_date"])) and t["status"] != "done")

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, clr in [
        (c1, todo_n, "To Do",      "clr-yellow"),
        (c2, ip_n,   "In Progress","clr-blue"),
        (c3, dn_n,   "Done",       "clr-green"),
        (c4, ov_n,   "Overdue",    "clr-red"),
    ]:
        with col:
            st.markdown(f'<div class="metric-box"><div class="num {clr}">{val}</div><div class="lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    f_st = st.selectbox("Filter", ["all", "todo", "in_progress", "done", "overdue"],
                        format_func=lambda x: {
                            "all": "All Tasks", "todo": "To Do",
                            "in_progress": "In Progress", "done": "Done", "overdue": "Overdue"
                        }[x])

    filtered = all_tasks
    if f_st == "overdue":
        filtered = [t for t in all_tasks if is_overdue(str(t["due_date"])) and t["status"] != "done"]
    elif f_st != "all":
        filtered = [t for t in all_tasks if t["status"] == f_st]

    for t in filtered:
        overdue_flag = is_overdue(str(t["due_date"])) and t["status"] != "done"
        ov = '<span class="badge b-overdue">OVERDUE</span>' if overdue_flag else ""
        st.markdown(f"""
        <div class="card">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span class="card-title">{t['title']}</span>
                {sbadge(t['status'])} {pbadge(t['priority'])} {ov}
            </div>
            <div class="card-meta" style="margin-top:4px">
                {t['project_name']} · Due: {fmt_date(str(t['due_date'])) if t['due_date'] else '—'}
            </div>
        </div>""", unsafe_allow_html=True)

        # Quick status update
        ns_opts = ["todo", "in_progress", "done"]
        cur_idx = ns_opts.index(t["status"])
        nc1, nc2 = st.columns([3, 5])
        with nc1:
            new_s = st.selectbox("Update status", ns_opts, index=cur_idx,
                                 key=f"myts_{t['id']}",
                                 format_func=lambda x: STATUS_LABEL[x],
                                 label_visibility="collapsed")
        with nc2:
            if new_s != t["status"]:
                if st.button("Apply", key=f"mytb_{t['id']}"):
                    r = jpatch(f"/projects/{t['project_id_ref']}/tasks/{t['id']}",
                               {"status": new_s}, params={"user_id": u["id"]})
                    if r and r.status_code == 200:
                        st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ALL USERS (admin panel)
# ══════════════════════════════════════════════════════════════════════════════
def page_users():
    u = st.session_state.user
    st.markdown('<div class="page-title">All Users</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Every registered account</div>', unsafe_allow_html=True)

    users = jget("/users") or []
    if not users:
        st.info("No users found.")
        return

    st.markdown(f'<div class="card-meta" style="margin-bottom:.8rem">{len(users)} users registered</div>', unsafe_allow_html=True)

    for usr in users:
        uc1, uc2 = st.columns([6, 2])
        with uc1:
            st.markdown(f"""
            <div class="card">
                <span style="font-weight:600;color:#e6edf3">{usr['full_name']}</span>
                <span style="color:#8b949e;font-size:12px;margin-left:8px">@{usr['username']}</span>
                &nbsp;{rbadge(usr['role'])}<br>
                <span class="card-meta">{usr['email']} · Joined {fmt_date(str(usr['created_at']))}</span>
            </div>""", unsafe_allow_html=True)
        with uc2:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            # Only global admin can change global roles
            if u["role"] == "admin" and usr["id"] != u["id"]:
                new_role = st.selectbox(
                    "Role",
                    ["admin", "member"],
                    index=0 if usr["role"] == "admin" else 1,
                    key=f"role_{usr['id']}",
                    label_visibility="collapsed",
                )
                if new_role != usr["role"]:
                    if st.button("Update", key=f"upd_{usr['id']}"):
                        r = api("patch", f"/users/{usr['id']}/role",
                                params={"role": new_role})
                        if r and r.status_code == 200:
                            st.success("Role updated!")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.user is None:
    show_auth()
else:
    page = show_sidebar()
    if page == "Dashboard":
        page_dashboard()
    elif page == "My Projects":
        page_projects()
    elif page == "My Tasks":
        page_my_tasks()
    elif page == "All Users":
        page_users()