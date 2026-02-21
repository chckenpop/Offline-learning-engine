# Pune-V2 — Full-Stack Integration Context

> **Purpose of this document**: This README is written for an LLM that will be working on this codebase. It explains _everything_ that exists, _what works_, _what is broken or missing_, and _exactly what needs to be done_ to fully wire the React frontend to the Python/FastAPI backend.

---

## 1. Project Overview

**Pune-V2** is a concept authoring, review, and educational content management platform. It has two independently runnable applications:

| App | Tech | Entry Point | Dev URL |
|---|---|---|---|
| Backend | Python + FastAPI + SQLite | `uvicorn app.main:app --reload --port 8000` | `http://localhost:8000` |
| Frontend | React + Vite | `npm run dev` (from `frontend-app/`) | `http://localhost:5173` |

The backend is **fully implemented** and running. The frontend has its own local state management and **partially** calls the backend. The main task is completing that wiring.

---

## 2. Repository Layout

```
pune-V2/
├── backend/                         # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point, CORS config
│   │   ├── container.py             # Dependency injection / wiring
│   │   ├── api/
│   │   │   ├── concepts.py          # Concept CRUD + lifecycle status endpoints
│   │   │   ├── auth.py              # Login, logout, profile endpoints
│   │   │   ├── panels.py            # Comments, diff, warnings panels
│   │   │   ├── huggingface.py       # HuggingFace AI integration
│   │   │   └── openrouter.py        # OpenRouter AI model integration
│   │   ├── application/
│   │   │   └── concept_app_service.py  # Orchestrates domain operations
│   │   ├── domain/concept/
│   │   │   ├── models.py            # Concept domain model
│   │   │   ├── rules.py             # Business rules / constraints
│   │   │   └── service.py           # Domain service (versioning, lifecycle)
│   │   ├── domain/common/
│   │   │   └── result.py            # Result<T> pattern (success/failure)
│   │   ├── validation/
│   │   │   └── concept_validation.py
│   │   ├── persistence/
│   │   │   ├── db.py
│   │   │   ├── interfaces/
│   │   │   │   └── concept_repository.py        # Abstract repo interface
│   │   │   └── repositories/
│   │   │       ├── sqlite/
│   │   │       │   └── sqlite_concept_repository.py   # ACTIVE repo (SQLite)
│   │   │       └── in_memory/
│   │   │           └── in_memory_concept_repository.py # Used in tests
│   │   └── core/
│   │       └── config.py            # App configuration (SECRET_KEY, DB path, etc.)
│   ├── migrations/
│   │   └── 001_init.sql             # SQLite schema: concepts + concept_versions tables
│   ├── tests/
│   │   ├── domain/test_concept_service.py
│   │   └── application/test_concept_app_service.py
│   ├── requirements.txt
│   └── smoke_test.py
│
├── frontend-app/
│   └── src/
│       ├── App.jsx                  # Root component, router, global state
│       ├── main.jsx                 # React entrypoint
│       ├── index.css
│       ├── api/
│       │   ├── api.js               # Base axios instance (unauthenticated)
│       │   ├── conceptApi.js        # All concept-related API calls (WIRED)
│       │   └── lessonApi.js         # Lesson API calls (PARTIALLY WIRED)
│       ├── components/
│       │   ├── LoginPage.jsx        # Auth UI
│       │   ├── ValidatorHome.jsx    # Home / dashboard after login
│       │   ├── TopBar.jsx           # Navigation bar with auth state
│       │   ├── ConceptEditor.jsx    # Main concept editing interface
│       │   ├── DocumentEditor.jsx   # Rich-text doc editor (legacy)
│       │   ├── DocumentEditorV2.jsx # Rich-text doc editor (current, bugfixed)
│       │   ├── EditorWorkspace.jsx  # Workspace layout wrapper
│       │   ├── ReviewCenter.jsx     # Review queue UI (wired to backend)
│       │   ├── BottomPanel.jsx      # Comments, diffs, warnings panels
│       │   ├── AIAssistant.jsx      # AI assistant sidebar
│       │   ├── LessonManifestation.jsx  # Lesson content viewer
│       │   ├── VideoManifestation.jsx   # Video upload/display component
│       │   ├── MetaInfoPanel.jsx    # Metadata editing panel
│       │   ├── SourceTextPanel.jsx  # Source text panel
│       │   ├── ResizablePanel.jsx   # Layout utility
│       │   ├── ConfirmModal.jsx     # Generic confirm dialog
│       │   └── ConnectionStatus.jsx # Backend health-check indicator
│       ├── context/                 # React context providers
│       ├── services/                # Business logic services (frontend)
│       └── store/                   # State management (Zustand/custom)
│
├── README.md                        # Quick start (setup instructions)
├── DEV_README.md                    # Developer changelog / recent changes
├── ARCHITECTURE_COMPLETE.md         # Full architecture description
├── BUSINESS_README.md               # Business/product context
└── app.db                           # SQLite DB (auto-created, do not commit)
```

---

## 3. Backend Architecture (Deep Dive)

### 3.1 Layered Architecture

```
HTTP Request
    │
    ▼
┌──────────────────────────┐
│        API LAYER         │  app/api/*.py
│  FastAPI route handlers  │  Parses request, calls app service, returns JSON
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│   APPLICATION LAYER      │  app/application/concept_app_service.py
│  ConceptAppService       │  Orchestrates: validate → domain op → persist
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│      DOMAIN LAYER        │  app/domain/concept/
│  ConceptService          │  Business rules, versioning, lifecycle FSM
│  ConceptDomainModel      │  Pure Python — no DB, no HTTP
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│    PERSISTENCE LAYER     │  app/persistence/
│  ConceptRepository       │  Interface + SQLite impl + InMemory impl
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│        DATABASE          │
│  SQLite (data/app.db)    │
│  Tables: concepts,       │
│          concept_versions│
└──────────────────────────┘
```

### 3.2 Concept Lifecycle State Machine

Concepts move through states in one direction only — **no reversal allowed**:

```
DRAFT → REVIEW → APPROVED → PUBLISHED
```

- **DRAFT**: Created by author, editable. No one else can see it.
- **REVIEW**: Sent to reviewer queue. Read-only for author.
- **APPROVED**: Approved by reviewer. Creates a new `ConceptVersion` attributed to the approver.
- **PUBLISHED**: Final published state. Publicly visible.

Status transitions are made by `POST /concepts/{id}/status` with body `{ "new_status": "REVIEW" }`.

### 3.3 Versioning

Every time a concept is **updated** (`PUT /concepts/{id}`) or **approved**, a new row is inserted into `concept_versions`. The `concepts` table stores the identity and current status; `concept_versions` stores the content history.

### 3.4 Authentication

- Auth is handled by `app/api/auth.py`.
- Login returns a token (currently a simple signed token — see `app/core/config.py` for `SECRET_KEY`).
- All protected endpoints expect `Authorization: Bearer <token>` header.
- The frontend's axios interceptor in `conceptApi.js` automatically attaches this header via `setAuthToken(token)`.
- `owner_id` is extracted from the bearer token inside each API handler and propagated to domain operations.

> **Note**: JWT migration was implemented in a previous session (see `DEV_README.md`). The token is a JWT; `app/core/config.py` should have `SECRET_KEY` configured either by `.env` or directly.

---

## 4. Frontend Architecture (Deep Dive)

### 4.1 Auth Flow

1. `LoginPage.jsx` collects credentials, calls `POST /auth/login`.
2. On success, the token is stored (likely in React state or localStorage).
3. `setAuthToken(token)` from `conceptApi.js` is called, injecting the token into all subsequent axios requests.
4. `TopBar.jsx` manages user display and logout state.

### 4.2 Concept API Client (`frontend-app/src/api/conceptApi.js`)

This file is **the single source of truth** for all concept-related HTTP calls. It is already fully implemented:

| Function | Method | Endpoint | Description |
|---|---|---|---|
| `checkHealth()` | GET | `/health` | Backend health check |
| `listConcepts()` | GET | `/concepts/` | Get all concepts + latest versions |
| `createConcept(data)` | POST | `/concepts/` | Create new concept in DRAFT |
| `getConcept(id)` | GET | `/concepts/{id}` | Get concept + latest version |
| `updateConcept(id, data)` | PUT | `/concepts/{id}` | Update content (creates new version) |
| `changeStatus(id, newStatus)` | POST | `/concepts/{id}/status` | Transition lifecycle status |
| `getVersions(id)` | GET | `/concepts/{id}/versions` | Get all versions |
| `getVersion(id, versionNum)` | GET | `/concepts/{id}/versions/{n}` | Get specific version |
| `setAuthToken(token)` | — | — | Sets Bearer token on axios instance |

### 4.3 Key Components and Their Roles

| Component | File | Backend Integration Status |
|---|---|---|
| `LoginPage` | `LoginPage.jsx` | ✅ Calls `POST /auth/login` |
| `ConnectionStatus` | `ConnectionStatus.jsx` | ✅ Calls `GET /health` |
| `ReviewCenter` | `ReviewCenter.jsx` | ✅ Wired to backend review queue |
| `ConceptEditor` | `ConceptEditor.jsx` | ⚠️ Partially — may still use local state for some saves |
| `ValidatorHome` | `ValidatorHome.jsx` | ⚠️ Partially — loads concept list |
| `TopBar` | `TopBar.jsx` | ⚠️ Has Publish/Send to Review buttons — needs status wiring |
| `DocumentEditorV2` | `DocumentEditorV2.jsx` | ❌ Operates on local state; edits not persisted to backend |
| `BottomPanel` | `BottomPanel.jsx` | ❌ Comments/diffs may not be persisted |
| `VideoManifestation` | `VideoManifestation.jsx` | ❌ Video uploads not fully wired |
| `LessonManifestation` | `LessonManifestation.jsx` | ❌ Lesson data loaded from `lessonApi.js` (partially) |
| `MetaInfoPanel` | `MetaInfoPanel.jsx` | ❌ Metadata changes not sent to backend |

### 4.4 State Management

The frontend uses React context (`context/`) and a store (`store/`) for global state. **Key problem**: concepts created or edited in the UI are often only in local component state or the store, and are never sent to `POST /concepts/` or `PUT /concepts/{id}`. This means **data is lost on page refresh**.

---

## 5. Database Schema (SQLite)

Schema is defined in `backend/migrations/001_init.sql` and is auto-applied on first run.

### `concepts` table

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `owner_id` | TEXT | UUID of creating user |
| `status` | TEXT | DRAFT / REVIEW / APPROVED / PUBLISHED |
| `created_at` | TEXT | ISO8601 timestamp |
| `updated_at` | TEXT | ISO8601 timestamp |

### `concept_versions` table

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `concept_id` | TEXT | FK → concepts.id |
| `version_number` | INTEGER | Monotonically increasing |
| `name` | TEXT | Concept name |
| `core_definition` | TEXT | Core definition text |
| `expanded_explanation` | TEXT | Full explanation |
| `learning_objective` | TEXT | Learning objective |
| `examples` | TEXT | JSON array of strings |
| `misconceptions` | TEXT | JSON array of strings |
| `prerequisites` | TEXT | JSON array of strings |
| `scope_boundaries` | TEXT | Scope boundaries |
| `check` | TEXT | Check/quiz text (nullable) |
| `grade` | TEXT | Grade level (nullable) |
| `board` | TEXT | Education board (nullable) |
| `change_note` | TEXT | Notes for this version |
| `created_by` | TEXT | UUID of user who created this version |
| `created_at` | TEXT | ISO8601 timestamp |

---

## 6. API Contract Reference

Base URL: `http://localhost:8000`

Interactive docs at: `http://localhost:8000/docs` (Swagger UI)

### Auth Endpoints (`app/api/auth.py`)

```
POST /auth/login
  Body: { "username": string, "password": string }
  Returns: { "token": string, "user": { ... } }

POST /auth/logout
  Headers: Authorization: Bearer <token>
  Returns: 200 OK

GET  /auth/profile
  Headers: Authorization: Bearer <token>
  Returns: user profile object

PUT  /auth/profile
  Headers: Authorization: Bearer <token>
  Body: { profile fields }
  Returns: updated profile
```

### Concept Endpoints (`app/api/concepts.py`)

```
GET    /concepts/               → List all concepts (with latest version data)
POST   /concepts/               → Create concept (status starts as DRAFT)
GET    /concepts/{id}           → Get concept + latest version
PUT    /concepts/{id}           → Update concept content (creates new version)
DELETE /concepts/{id}           → Delete concept
POST   /concepts/{id}/status    → Transition status { "new_status": "REVIEW" | "APPROVED" | "PUBLISHED" }
GET    /concepts/{id}/versions  → List all versions
GET    /concepts/{id}/versions/{n} → Get specific version

GET    /health                  → Health check { "status": "ok" }
```

### Panel Endpoints (`app/api/panels.py`)

```
GET  /concepts/{id}/comments    → Get comments for a concept
POST /concepts/{id}/comments    → Post a comment
GET  /concepts/{id}/diff        → Get diff between versions
GET  /concepts/{id}/warnings    → Get validation warnings
```

### AI Endpoints

```
POST /huggingface/...     → HuggingFace model calls
POST /openrouter/...      → OpenRouter AI model calls
```

---

## 7. What Is Broken / Missing (Priority Order)

### P0 — Concept Persistence (Data Loss Bug)

**Problem**: When a user creates or edits a concept in `ConceptEditor.jsx` or `DocumentEditorV2.jsx`, the data is only saved to local React state/store. On page refresh, all unsaved concepts are gone.

**Fix Required**:
- In `ConceptEditor.jsx` (or wherever the "Save" action is triggered), call `createConcept(data)` from `conceptApi.js` if the concept has no `id` yet, or `updateConcept(id, data)` if it already exists.
- Store the returned `concept.id` in local/global state so subsequent saves use `updateConcept`.
- On app load (`App.jsx` or `ValidatorHome.jsx`), call `listConcepts()` to hydrate state from the database.

**Files to touch**:
- `frontend-app/src/App.jsx`
- `frontend-app/src/components/ConceptEditor.jsx`
- `frontend-app/src/components/ValidatorHome.jsx`
- `frontend-app/src/store/` (wherever concept state lives)

### P1 — Publish Workflow Buttons

**Problem**: The `TopBar.jsx` has "Send to Review", "Approve", and "Publish" buttons that are either disabled or only update local state. They need to call `changeStatus()`.

**Fix Required**:
- "Send to Review" → `changeStatus(conceptId, 'REVIEW')`
- "Approve" → `changeStatus(conceptId, 'APPROVED')`
- "Publish" → `changeStatus(conceptId, 'PUBLISHED')`
- After each call, refresh the concept from the backend to get the new status and re-render button states.

**Files to touch**:
- `frontend-app/src/components/TopBar.jsx`

### P2 — Document Editor Not Persisting

**Problem**: `DocumentEditorV2.jsx` is a rich-text editor that operates purely on local state. Rich text changes are not being serialized and sent to the backend as `core_definition`, `expanded_explanation`, etc.

**Fix Required**:
- Map the editor's rich-text output to the concept's content fields.
- Call `updateConcept(id, data)` when the user explicitly saves or on auto-save.

**Files to touch**:
- `frontend-app/src/components/DocumentEditorV2.jsx`

### P3 — Lesson API Wiring

**Problem**: `lessonApi.js` exists but lessons are currently hardcoded or partially fetched. The backend `app/api/panels.py` may have lesson-related endpoints.

**Fix Required**:
- Verify what lesson endpoints exist on the backend.
- Wire `LessonManifestation.jsx` to fetch real lesson data.

### P4 — Role-Based Access Control

**Problem**: The lifecycle transitions (REVIEW → APPROVED) should only be available to users with the `reviewer` role; APPROVED → PUBLISHED should require `approver`. Currently, any authenticated user can call any status endpoint.

**Fix Required**:
- Backend: Add role check in `app/api/concepts.py` for the `/status` endpoint.
- Frontend: Hide/disable buttons in `TopBar.jsx` based on the logged-in user's role.

### P5 — Video Upload Persistence

**Problem**: `VideoManifestation.jsx` handles video uploads, but the upload target and storage path need to be confirmed.

**Fix Required**:
- Confirm the backend upload endpoint in `app/api/` (check for a `/upload` or `/videos` route).
- Wire the frontend file picker to `POST` to that endpoint.
- Store the returned file URL back into the concept/lesson data.

---

## 8. How to Run the Full Stack Locally

### Backend

```powershell
cd backend
python -m venv ../.venv
..\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- DB auto-created at `backend/data/app.db` (or `app.db` in root — check `app/core/config.py`)

### Frontend

```powershell
cd frontend-app
npm install
npm run dev
```

- App: `http://localhost:5173`
- The `ConnectionStatus` component in the UI will show green when the backend is reachable.

### Run Tests

```powershell
cd backend
pytest -q
```

---

## 9. Environment Configuration

Create a `backend/.env` file (or set environment variables):

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./data/app.db
```

`app/core/config.py` reads these values. Without `SECRET_KEY`, JWT signing will use a default/insecure fallback.

---

## 10. Key Design Decisions to Preserve

1. **Result pattern**: Domain functions return `Result(success, value, error)` — never raise exceptions for normal flow. Always check `.is_success` before using `.value`.
2. **Repository interface**: Never call SQLite directly from application/domain code. Always go through `ConceptRepository` interface — this makes swapping to Postgres easy later.
3. **Version immutability**: Once a `concept_version` row is written, it is never mutated. Updates create new version rows. Do not attempt to `UPDATE` a version.
4. **Status irreversibility**: The state machine enforces `DRAFT → REVIEW → APPROVED → PUBLISHED` order. Do not attempt to skip or reverse states — the domain rules layer will reject it.
5. **CORS**: Currently set to `allow_origins=["*"]` in `app/main.py`. Keep this for local dev; restrict for production.
6. **Safe schema init**: The SQLite repo uses `CREATE TABLE IF NOT EXISTS` — it will NOT drop and recreate tables on server restart. Data persists across reloads.

---

## 11. Quick Reference — Files Most Likely to Need Editing

| Task | Files |
|---|---|
| Save concept on create/edit | `ConceptEditor.jsx`, `App.jsx`, `store/` |
| Load concepts on startup | `App.jsx`, `ValidatorHome.jsx` |
| Status transition buttons | `TopBar.jsx` |
| Doc editor → backend | `DocumentEditorV2.jsx` |
| Role-based button visibility | `TopBar.jsx`, `App.jsx` |
| Backend role enforcement | `app/api/concepts.py`, `app/api/auth.py` |
| Lesson data wiring | `LessonManifestation.jsx`, `lessonApi.js` |
| Video upload | `VideoManifestation.jsx`, check `app/api/` for upload route |
