# PulseOps — Setup Guide

## Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL with pgvector extension (Supabase recommended)
- OpenRouter API key (https://openrouter.ai/keys)
- HuggingFace token (optional — free tier works without one)

---

## 1. Database Setup

### Create a Supabase project
1. Go to https://supabase.com and create a new project
2. In the project dashboard, go to **Settings → Database → Connection string → URI**
3. Copy the connection string — you'll need it for `DATABASE_URL`

### Run the SQL schema
In the Supabase **SQL Editor**, run these files in order:

```sql
-- Paste contents of database/pgvector_setup.sql  (enables pgvector + creates embeddings table)
-- Paste contents of database/schema.sql           (all application tables)
-- Paste contents of database/seed.sql             (optional: sample data for dev)
```

---

## 2. Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux

# Edit .env — fill in DATABASE_URL, OPENROUTER_API_KEY, SECRET_KEY
# See section 4 below for details

# Run the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

API docs available at: http://localhost:8001/docs

---

## 3. Frontend (Next.js)

```bash
cd frontend

# Install dependencies
# IMPORTANT: If you're on Windows and your project path contains & (e.g. "AI-Task-Management-&-Workflow"),
# npm postinstall scripts will fail. Use --ignore-scripts to bypass:
npm install --ignore-scripts

# Configure environment
# Create frontend/.env.local with:
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
echo NEXT_PUBLIC_APP_URL=http://localhost:3000 >> .env.local

# Run the dev server
npm run dev
```

App available at: http://localhost:3000

---

## 4. Environment Variables

### backend/.env (copy from .env.example and fill in your values)
```env
# Supabase connection string (Settings → Database → URI)
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.yourproject.supabase.co:5432/postgres

# OpenRouter — LLM inference (https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-4o

# HuggingFace embeddings (optional — anonymous free tier works without this)
# Get a free token at https://huggingface.co/settings/tokens
HF_API_KEY=hf_...
HF_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Auth — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-super-secret-jwt-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

ALLOWED_ORIGINS=http://localhost:3000
```

### frontend/.env.local
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## Architecture

```
PulseOps
├── frontend/         Next.js 14+ (App Router, TypeScript, Tailwind, dnd-kit)
├── backend/          FastAPI (Python, SQLAlchemy, pgvector, OpenRouter)
└── database/         PostgreSQL schema + pgvector setup (384-dim embeddings)
```

## AI Stack
| Component | Service | Details |
|-----------|---------|---------|
| LLM | OpenRouter → GPT-4o | Structured JSON outputs |
| Embeddings | HuggingFace free API | `all-MiniLM-L6-v2`, 384 dims |
| Vector DB | pgvector (Supabase) | Cosine similarity search |

## Key Features
- **Kanban Board** — drag-and-drop (dnd-kit), 7 columns, real-time updates
- **AI Intake** — raw text → structured project card, human-confirmed priority
- **Meeting Intelligence** — transcript → action items, decisions, tasks
- **Email Intelligence** — email → extracted tasks, people, deadlines
- **Semantic Search** — pgvector-powered natural language search
- **AI Assistant** — context-aware GPT-4o chat panel
- **Command Palette** — Cmd+K global navigation
- **Dashboard** — stats, activity, AI insights, workload

## API Endpoints
See full documentation at http://localhost:8000/docs after starting the backend.
