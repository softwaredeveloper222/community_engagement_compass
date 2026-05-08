# Community Engagement Compass — Local Setup Guide (Windows)

A clean, verified walkthrough to get this Django + AI project running on a Windows machine without errors.

The guide assumes:
- OS: **Windows 10/11**
- Shell: **PowerShell**
- Python available: **3.14** (the only version this guide targets — `requirements/windows.txt` is built for it)
- Project root: `e:\Work\Task\community_engagement_compass`

If you are on Linux/Mac, see the original [TECHNICAL_README.md](TECHNICAL_README.md). This file focuses on Windows because that is where the project is currently checked out.

---

## 1. What this project is

- **Name:** Community Engagement Compass / Knowledge Assistant
- **Type:** Django 5.2.5+ web app — AI-powered Q&A over uploaded PDFs
- **Stack:** Django · Bootstrap 5 · PostgreSQL or SQLite · PyTorch · Transformers · sentence-transformers · FAISS · django-allauth · optional Ollama / Phi-3-mini local model · Groq API fallback

Entry points:
- `manage.py` — Django CLI (defaults to `config.settings.local`)
- `config/settings/base.py` — shared settings
- `config/settings/local.py` — development settings, `DEBUG=True`

---

## 2. Known footguns (read this first)

These are real issues in the repo that will cause errors if ignored:

1. **The bundled `venv/` is broken.** It was created on another machine (user `Bingo`); its `python.exe` shim points to a path that does not exist on your box. **Delete it and recreate.**
2. **Only `requirements/windows.txt` works on Python 3.14.** `requirements/local.txt` pins `torch==2.2.2+cu121`, `numpy==1.26.4` etc., for which no 3.14 wheels exist.
3. **Default `DATABASE_URL` in `.env` points to PostgreSQL.** If Postgres is not running with the expected credentials, migrations will fail. The fastest workaround is to switch to SQLite (covered below).
4. **The top-level `requirements.txt` is UTF-16 encoded and looks garbled.** Ignore it; use files inside `requirements/`.
5. **`.python-version` says `3.12`** but only Python 3.14 is installed locally. The Windows requirements file is compatible with 3.14 — keep going.

---

## 3. Prerequisites

| Tool | Version | How to verify |
|---|---|---|
| Python | 3.14.x | `python --version` |
| pip | latest | `python -m pip --version` |
| Git | any recent | `git --version` |
| PostgreSQL *(optional)* | 12+ | `psql --version` |
| Node.js *(optional, for any frontend tooling)* | 18+ | `node --version` |

If Python 3.14 is not on PATH, use the full path:
`C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe`

---

## 4. Setup — step by step

All commands are run from the project root in **PowerShell**.

### Step 1 — Remove the broken venv and create a fresh one

```powershell
cd e:\Work\Task\community_engagement_compass

# Delete the stale venv from another user
Remove-Item -Recurse -Force .\venv

# Create a fresh venv with Python 3.14
& "C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
```

If activation is blocked by execution policy, run once (admin not required):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

You should now see `(venv)` at the start of your prompt.

### Step 2 — Install dependencies (Windows-friendly set)

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements\windows.txt
```

This file ships CPU-only PyTorch, drops the `nvidia-*` Linux-CUDA packages, and uses `>=` pins so it resolves cleanly on Python 3.14.

> Tip: the install pulls a few hundred MB of ML packages (torch, transformers, sentence-transformers, faiss). Allow ~5–15 min depending on bandwidth.

### Step 3 — Configure the database

The project's `.env` ships with:

```
DATABASE_URL=postgres://postgres:softwaredeveloper@localhost:5432/knowledgeassistant_db
```

Pick **one** of the two paths below.

#### 3A. Easiest: switch to SQLite (recommended for first run)

Open [.env](.env) and replace the `DATABASE_URL` line with:

```
DATABASE_URL=sqlite:///db.sqlite3
```

A `db.sqlite3` file already exists at the project root and will be used automatically.

#### 3B. Use PostgreSQL

Make sure Postgres is running, then in `psql`:

```sql
CREATE DATABASE knowledgeassistant_db;
CREATE USER postgres WITH PASSWORD 'softwaredeveloper';
GRANT ALL PRIVILEGES ON DATABASE knowledgeassistant_db TO postgres;
```

Leave `.env` untouched.

### Step 4 — Apply migrations and create an admin user

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Follow the prompts to set an email and password for the admin account.

### Step 5 — Run the development server

```powershell
python manage.py runserver
```

Open in a browser:

- App: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

You should see the chat UI. Log in via the admin URL using the superuser you just created.

---

## 5. Optional — enable full AI features

The app runs fine without a local LLM; it can use the Groq API key already present in `.env`. Set up a local model only if you want offline inference.

### 5A. Download a local model

Recommended (per [QUICK_START.sh](QUICK_START.sh)): **Phi-3-mini** (~7.5 GB).

```powershell
python utility\download_phi3_mini.py
```

Other available downloaders in [utility/](utility/):
- `download_phi2.py`
- `download_phi3_mini.py`
- `download_llama_3_2_3b.py`
- `download_stablelm_3b.py`

### 5B. Build the FAISS vector index

After uploading PDFs through the UI (or admin):

```powershell
python manage.py rebuild_index_optimized
```

Other useful commands:

```powershell
python manage.py process_pending_docs    # ingest queued docs
python manage.py rebuild_index            # full reindex
python manage.py chat_stats               # usage stats
```

### 5C. GPU acceleration (optional)

`requirements/windows.txt` installs **CPU** torch. To use an NVIDIA GPU, after Step 2 reinstall torch with a CUDA build matching your driver, e.g.:

```powershell
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## 6. Daily workflow

```powershell
cd e:\Work\Task\community_engagement_compass
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

Stop the server with `Ctrl+C`. Deactivate the venv with `deactivate`.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `did not find executable at 'C:\Users\Bingo\...python.exe'` | Stale venv from another user | Step 1 — delete and recreate |
| `Could not find a version that satisfies torch==2.2.2+cu121` | Installed `requirements/local.txt` on Python 3.14 | Use `requirements\windows.txt` |
| `psycopg.OperationalError: connection refused` | Postgres not running | Step 3A — use SQLite, or start Postgres |
| `django.db.utils.OperationalError: FATAL: password authentication failed` | Postgres user/password mismatch | Match `.env` `DATABASE_URL` to your Postgres setup |
| `ImportError: Couldn't import Django` | venv not activated | `.\venv\Scripts\Activate.ps1` |
| `You have N unapplied migration(s)` on startup | First run | `python manage.py migrate` |
| `RuntimeError: CUDA out of memory` | Local LLM larger than VRAM | Stay on CPU torch, or use the Groq API (key in `.env`) |
| `ModuleNotFoundError: No module named 'environ'` | Skipped Step 2, or wrong venv active | Reinstall `requirements\windows.txt` |
| Activation script blocked | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| `UnicodeDecodeError` reading `requirements.txt` | Root file is UTF-16 garbage | Don't use it — use `requirements/windows.txt` |

---

## 8. Project layout (quick reference)

```
community_engagement_compass/
├── manage.py                        # Django CLI entry point
├── .env                             # Local secrets (already populated)
├── .python-version                  # Says 3.12 (ignore — use 3.14 on this box)
├── db.sqlite3                       # SQLite DB (used if DATABASE_URL=sqlite:...)
├── config/
│   ├── settings/
│   │   ├── base.py                  # Shared settings, reads .env
│   │   ├── local.py                 # Dev settings (DEBUG=True)
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   └── wsgi.py
├── chat/                            # Main app: chat, PDF ingest, embeddings
├── knowledgeassistant/              # Project package: users, static, templates
├── requirements/
│   ├── base.txt
│   ├── local.txt                    # ❌ do not use on Python 3.14
│   ├── production.txt
│   ├── mac_os.txt
│   └── windows.txt                  # ✅ use this on Windows
├── utility/                         # Model download scripts
├── docs/                            # Sphinx docs
└── venv/                            # Will be recreated by Step 1
```

---

## 9. TL;DR (copy-paste)

```powershell
cd e:\Work\Task\community_engagement_compass
Remove-Item -Recurse -Force .\venv
& "C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements\windows.txt
# Then edit .env -> DATABASE_URL=sqlite:///db.sqlite3
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ — done.
