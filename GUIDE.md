# TeamTask — Complete Step-by-Step Execution & Deployment Guide

---

## PROJECT STRUCTURE

```
teamtask/
├── backend/
│   ├── main.py          ← FastAPI — all API routes
│   ├── models.py        ← SQLAlchemy ORM tables
│   ├── schemas.py       ← Pydantic request/response shapes
│   ├── database.py      ← DB engine + session
│   └── auth.py          ← bcrypt password hashing
├── frontend/
│   └── app.py           ← Streamlit UI — all pages
├── requirements.txt
├── .env                 ← your secrets (never commit)
├── .env.example
├── .gitignore
├── railway.toml         ← Railway backend config
├── nixpacks.toml        ← Railway build config
├── Procfile             ← fallback start command
└── runtime.txt          ← Python version pin
```

---

## PART 1 — LOCAL SETUP

### Step 1 — PostgreSQL Database

Open pgAdmin Query Tool and run:

```sql
CREATE DATABASE teamtask;
CREATE USER taskuser WITH PASSWORD 'taskpass123';
GRANT ALL PRIVILEGES ON DATABASE teamtask TO taskuser;
GRANT ALL ON SCHEMA public TO taskuser;
ALTER SCHEMA public OWNER TO taskuser;
```

### Step 2 — Create Virtual Environment

```powershell
cd E:\PythonFullStackProjects\teamtask
python -m venv venv
venv\Scripts\activate
```

### Step 3 — Create .env file

Create `teamtask/.env`:

```
DATABASE_URL=postgresql://taskuser:taskpass123@localhost:5432/teamtask
API_URL=http://localhost:8000
```

### Step 4 — Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 5 — Run Backend (Terminal 1)

```powershell
cd E:\PythonFullStackProjects\teamtask\backend
..\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Test at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Step 6 — Run Frontend (Terminal 2)

```powershell
cd E:\PythonFullStackProjects\teamtask\frontend
..\venv\Scripts\activate
streamlit run app.py
```

Opens at: http://localhost:8501

### Step 7 — First Use

1. Go to http://localhost:8501
2. Click "Create Account" tab
3. Fill in Full Name, Username, Email, Password
4. ✅ First account = auto Admin
5. Login and start creating projects

---

## PART 2 — DEPLOY TO RAILWAY

### Step 1 — Push to GitHub

```powershell
cd E:\PythonFullStackProjects\teamtask
git init
git add .
git commit -m "Initial commit - TeamTask"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/teamtask.git
git push -u origin main
```

---

### Step 2 — Deploy Backend on Railway

1. Go to https://railway.app → Sign up / Login with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `teamtask` repo
4. Railway auto-detects Python — click **Deploy**

**Add PostgreSQL:**
5. In your project dashboard → click **"New"** → **"Database"** → **"Add PostgreSQL"**
6. Railway creates the DB and gives you a `DATABASE_URL` automatically

**Set Environment Variables:**
7. Click your web service → **"Variables"** tab
8. Click **"Add Variable"**:
   - Click **"Add Reference"** → select `DATABASE_URL` from the PostgreSQL service (auto-links)
9. Done — Railway injects it automatically

10. Go to **"Settings"** tab → copy your public URL  
    e.g. `https://teamtask-production.up.railway.app`

11. Test it: open `https://YOUR-BACKEND-URL.up.railway.app/docs`

---

### Step 3 — Deploy Streamlit Frontend on Railway

1. In the same Railway project → click **"New"** → **"GitHub Repo"** → same repo
2. Click the new service → **"Settings"**
3. Set **Start Command**:
   ```
   cd frontend && streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```
4. Go to **"Variables"** tab → Add:
   - `API_URL` = `https://YOUR-BACKEND-URL.up.railway.app`
     (the URL from Step 2 above — no trailing slash)
5. Click **"Generate Domain"** in Settings to get your frontend URL
6. Open the frontend URL — app is live!

---

## QUICK REFERENCE

### Local commands
```powershell
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && streamlit run app.py
```

### URLs
| Service  | Local                   | Description          |
|----------|-------------------------|----------------------|
| Frontend | http://localhost:8501   | Streamlit app        |
| Backend  | http://localhost:8000   | FastAPI              |
| API Docs | http://localhost:8000/docs | Swagger UI        |

---

## FEATURES SUMMARY

| Feature                        | Where                              |
|--------------------------------|------------------------------------|
| Signup / Login                 | Auth page (first user = Admin)     |
| Create / Edit / Delete Project | My Projects page                   |
| Add / Remove Team Members      | Project → Members tab              |
| Role-based access (Admin/Member)| Per-project + global role         |
| Create / Edit / Delete Tasks   | Project → Tasks tab                |
| Task assignment                | Assign to any project member       |
| Status tracking (Todo/In Progress/Done) | Task cards + My Tasks page |
| Priority levels (Low/Medium/High) | Task creation + filtering       |
| Due dates + Overdue detection  | Dashboard + task cards             |
| Comments on tasks              | Expandable comment thread per task |
| Dashboard with metrics         | Dashboard page                     |
| Overdue task alerts            | Dashboard + My Tasks               |
| User management                | All Users page (admin only)        |

---

## TROUBLESHOOTING

**`InsufficientPrivilege` on startup**
```sql
GRANT ALL ON SCHEMA public TO taskuser;
ALTER SCHEMA public OWNER TO taskuser;
```

**`psql` not recognized on Windows**
Add `C:\Program Files\PostgreSQL\17\bin` to Windows PATH (System Environment Variables)

**`bcrypt __about__` error**
```powershell
pip install bcrypt==4.0.1
```

**`ModuleNotFoundError: No module named 'database'`**
You must run uvicorn from INSIDE the backend/ folder:
```powershell
cd teamtask/backend
uvicorn main:app --reload --port 8000
```

**Railway deployment fails**
- Check the Deploy Logs in Railway dashboard
- Make sure `DATABASE_URL` env var is set and linked to the PostgreSQL service
- Ensure `requirements.txt` is in the root folder (not inside backend/)
