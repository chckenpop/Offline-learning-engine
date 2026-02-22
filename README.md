# Bright Study — Offline-First Learning Engine

An educational platform that works fully offline while offering premium cloud features when connected. Built for low-bandwidth environments with a modern, premium UI.

---

## 🏗️ Architecture Overview

```
Browser (Vanilla JS + CSS)
       ↕ HTTP (localhost:8000)
Local Python Engine  ←→  SQLite DB (offline persistence)
       ↕ HTTPS (when online)
Supabase (cloud sync)  +  OpenRouter AI (AI Tutor)
```

The **Local Python Engine** (`engine/web_ui.py`) is the single gateway — it serves the frontend, proxies AI requests, and manages all persistence (both local SQLite and Supabase).

---

## 📁 Project Structure

```
Offline-learning-engine/
│
├── UI/                         # Frontend (served by local engine)
│   ├── index.html              # Single-page app shell + all views
│   ├── main.js                 # All JS logic (~2200 lines, app object)
│   └── styles.css              # CSS with design tokens + dark theme
│
├── engine/                     # Local intelligence engine
│   ├── web_ui.py               # HTTP server + ALL API routes
│   ├── ai_tutor.py             # AI Tutor service (OpenRouter)
│   ├── adaptive.py             # Adaptive learning / mastery scoring
│   ├── ai_gen.py               # AI lesson generation service
│   └── updater.py              # Supabase content sync
│
├── backend/                    # FastAPI microservice (auth + admin)
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── api/                # Route handlers (auth, concepts, panels)
│   │   ├── domain/             # Business entities
│   │   ├── persistence/        # DB access layer
│   │   └── core/               # Config, security, JWT
│   ├── .env                    # Backend secrets (not committed)
│   └── requirements.txt        # FastAPI, uvicorn, jose, passlib...
│
├── pune_content/               # Local content store
│   ├── lessons/                # JSON lesson files
│   ├── concepts/               # JSON concept files
│   └── assets/videos/          # Downloaded video metadata
│
├── database/                   # SQLite databases
│   └── metadata.db             # Progress, schedules, cache
│
├── tests/                      # Jest UI tests + Python tests
├── .env                        # Root secrets (used by web_ui.py)
└── package.json                # Node dev deps (Jest only)
```

---

## 🌟 Features

### 🎓 Adaptive Learning Engine
- Keyword-based answer validation with mastery scoring
- Local progress tracking per concept (SQLite)
- AI-generated "Beginner" module when student struggles
- Dashboard with lesson/concept cards

### 🤖 AI Tutor (Chat)
- Context-aware chat linked to current lesson
- Upload `.txt` / `.md` / `.csv` study documents
- OpenRouter integration (GPT-3.5/4, Gemini, Claude)
- Chat history persisted locally

### 📅 Exam Study Planner (Scheduler)
- 5-step interactive wizard (subjects, dates, hours, priorities, breaks)
- **Priority-weighted hour allocation** — High gets 3×, Med 2×, Low 1×
- **Excel-style table** output with columns: #, Subject, Priority, Exam Date, Days Left, Study hrs/day, Break, Recommendation
- **Per-subject dynamic recommendations** based on urgency + priority
- **Persistent across sessions** — saved to `localStorage` + synced to cloud
- **Delete schedule** option to clear and restart

### 📂 Course Builder
- Create courses with subjects, lessons, and concepts from the UI
- Content saved to Supabase; searchable from "Add More Lessons"

### 🔍 Search Videos & Add More Lessons
- Search cloud-hosted lessons and download to local store
- Video search with thumbnail previews

### 🌙 Theme Toggle
- Dark / Light mode with full CSS variable theming

---

## ⚙️ Setup & Running

### Prerequisites
- **Python 3.9+** with `pip`
- **Node.js** (only needed to run tests)

### 1. Configure Environment Variables

Create `Offline-learning-engine/.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
OPENROUTER_API_KEY=sk-or-...
```

### 2. Start the Local Engine (Main App)
```bash
cd engine
pip install requests
python web_ui.py
# App available at: http://localhost:8000
```

### 3. (Optional) Start the Backend Microservice
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

---

## 🔌 API Routes (Local Engine — `web_ui.py`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves `index.html` |
| `GET` | `/api/lessons` | Local lesson list |
| `GET` | `/api/videos` | Local video list |
| `GET` | `/api/search_cloud?q=` | Search Supabase lessons |
| `GET` | `/api/search_videos?q=` | Search Supabase videos |
| `GET` | `/api/courses` | Search courses |
| `GET` | `/api/courses/:id/curriculum` | Course curriculum |
| `GET` | `/api/ai_tutor/history/:uid` | Chat history |
| `POST` | `/api/login` | Auth via Supabase |
| `POST` | `/api/signup` | Register via Supabase |
| `POST` | `/api/progress` | Save lesson progress |
| `POST` | `/api/ai_tutor/chat` | Send chat message to AI |
| `POST` | `/api/scheduler/save` | Save study schedule (cloud + SQLite fallback) |
| `POST` | `/api/generate_adaptive_lesson` | Generate AI lesson |
| `POST` | `/api/download` | Download lesson/video locally |
| `POST` | `/api/add_course` | Save a new course |

---

## 🗄️ Supabase Tables Required

Run this SQL in your **Supabase SQL Editor** once:

```sql
-- Study schedules (for Exam Planner)
CREATE TABLE IF NOT EXISTS public.study_schedules (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         TEXT,
  subjects        TEXT,
  exam_dates      TEXT,
  daily_hours     INTEGER,
  priority_levels TEXT,
  break_time      INTEGER,
  generated_timetable TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.study_schedules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow insert" ON public.study_schedules FOR INSERT WITH CHECK (true);
```

> Other tables (`delivery_subjects`, `added_courses`, `delivery_concepts`, `delivery_lessons`) should already exist from the original schema.

---

## 🧩 Integration Notes for Team Members

### Adding New Subjects / Lessons
1. Place a `lesson.json` in `pune_content/lessons/`
2. Place related `concept.json` files in `pune_content/concepts/`
3. The engine auto-discovers them on the next dashboard load — no code changes needed

### Modifying the UI
- All navigation is in `app.showSection(id)` in `main.js`
- Each view has a `<div id="..." class="view">` in `index.html`
- CSS design tokens are in the `:root` block in `styles.css`

### Modifying AI Tutor Behaviour
- System prompt and model selection are in `engine/ai_tutor.py`
- Change `self.model` for a different OpenRouter model

### Scheduler Persistence
- On save: `localStorage.setItem('brightstudy_schedule', ...)` + POST to `/api/scheduler/save`
- On section load: `loadSavedSchedule()` reads from `localStorage` first
- Fallback: if Supabase is unavailable, saves to local `study_schedules` SQLite table

---

## 🧪 Running Tests

```bash
# UI (Jest)
npm test

# Python
cd engine
python test_imports.py
```

---

## 📌 Development Status

| Feature | Status |
|---------|--------|
| Offline lesson engine | ✅ Complete |
| AI Tutor (OpenRouter) | ✅ Complete |
| Exam Study Planner | ✅ Complete |
| Course Builder | ✅ Complete |
| Cloud Sync (Supabase) | ✅ Complete |
| Theme Toggle | ✅ Complete |
| Scheduler Persistence | ✅ Complete |
| Backend Microservice (FastAPI) | 🟡 Partial (auth + concepts) |
| Spaced Repetition Algorithm | 📋 Planned |

---

*Built for educational excellence — offline-first, cloud-enhanced.*
