import io
import json
import os
import sqlite3
import sys
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import requests

from app.api.auth import get_current_user, optional_current_user
from app.core.config import LESSONS_DIR, CONCEPTS_DIR, PROGRESS_DB_PATH, SUPABASE_URL, SUPABASE_KEY
from app.persistence.db import get_connection

router = APIRouter(tags=["panels"])

# Headers for Supabase Proxy
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ------------------------------------------------------------------
# Cloud Search (Supabase Proxy)
# ------------------------------------------------------------------
@router.get("/api/search")
def search_supabase(q: str = Query(..., min_length=1)):
    """Search lessons and concepts directly from Supabase delivery tables."""
    try:
        # Search Lessons
        lessons_res = requests.get(
            f"{SUPABASE_URL}/rest/v1/delivery_lessons?select=lesson_id,version,json_data&json_data->>title=ilike.*{q}*",
            headers=HEADERS
        )
        lessons_res.raise_for_status()
        lessons = lessons_res.json()

        # Search Concepts
        concepts_res = requests.get(
            f"{SUPABASE_URL}/rest/v1/delivery_concepts?select=id,version,json_data&json_data->>name=ilike.*{q}*",
            headers=HEADERS
        )
        concepts_res.raise_for_status()
        concepts = concepts_res.json()

        results = []
        for l in lessons:
            results.append({
                "id": l["lesson_id"],
                "title": l["json_data"].get("title", "Untitled Lesson"),
                "type": "Lesson",
                "version": l["version"]
            })
        
        for c in concepts:
            results.append({
                "id": c["id"],
                "title": c["json_data"].get("name", "Untitled Concept"),
                "type": "Concept",
                "version": c["version"]
            })

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase search failed: {str(e)}")


# ------------------------------------------------------------------
# Comments
# ------------------------------------------------------------------
class CommentBody(BaseModel):
    body: str


@router.get("/concepts/{concept_id}/comments")
def get_comments(concept_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM concept_comments WHERE concept_id = ? ORDER BY created_at ASC",
        (concept_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/concepts/{concept_id}/comments", status_code=201)
def post_comment(
    concept_id: str,
    body: CommentBody,
    current_user: dict = Depends(get_current_user),
):
    import uuid
    from datetime import datetime, timezone
    comment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO concept_comments (id, concept_id, author_id, author_name, body, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (comment_id, concept_id, current_user["sub"], current_user.get("username"), body.body, now),
    )
    conn.commit()
    conn.close()
    return {"id": comment_id, "concept_id": concept_id, "body": body.body, "created_at": now}


# ------------------------------------------------------------------
# Diff between two versions
# ------------------------------------------------------------------
@router.get("/concepts/{concept_id}/diff")
def get_diff(concept_id: str, from_version: Optional[int] = None, to_version: Optional[int] = None):
    conn = get_connection()
    if from_version is None or to_version is None:
        # Auto: last two versions
        rows = conn.execute(
            "SELECT * FROM concept_versions WHERE concept_id = ? ORDER BY version_number DESC LIMIT 2",
            (concept_id,),
        ).fetchall()
        conn.close()
        if len(rows) < 2:
            return {"diff": [], "message": "Need at least 2 versions to diff"}
        v_new, v_old = dict(rows[0]), dict(rows[1])
    else:
        r1 = conn.execute(
            "SELECT * FROM concept_versions WHERE concept_id = ? AND version_number = ?",
            (concept_id, from_version),
        ).fetchone()
        r2 = conn.execute(
            "SELECT * FROM concept_versions WHERE concept_id = ? AND version_number = ?",
            (concept_id, to_version),
        ).fetchone()
        conn.close()
        if not r1 or not r2:
            raise HTTPException(status_code=404, detail="One or both versions not found")
        v_old, v_new = dict(r1), dict(r2)

    fields = ["name", "core_definition", "expanded_explanation", "learning_objective", "scope_boundaries"]
    changes = []
    for field in fields:
        old_val = v_old.get(field) or ""
        new_val = v_new.get(field) or ""
        if old_val != new_val:
            changes.append({"field": field, "old": old_val, "new": new_val})

    return {
        "from_version": v_old.get("version_number"),
        "to_version": v_new.get("version_number"),
        "changes": changes,
    }


# ------------------------------------------------------------------
# Validation warnings
# ------------------------------------------------------------------
@router.get("/concepts/{concept_id}/warnings")
def get_warnings(concept_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM concept_versions WHERE concept_id = ? ORDER BY version_number DESC LIMIT 1",
        (concept_id,),
    ).fetchone()
    conn.close()
    if not row:
        return {"warnings": []}

    warnings = []
    v = dict(row)
    if not v.get("core_definition"):
        warnings.append({"field": "core_definition", "message": "Core definition is missing"})
    if not v.get("learning_objective"):
        warnings.append({"field": "learning_objective", "message": "Learning objective is missing"})
    examples = json.loads(v.get("examples") or "[]")
    if not examples:
        warnings.append({"field": "examples", "message": "No examples provided"})
    if not v.get("check_text"):
        warnings.append({"field": "check_text", "message": "No check/quiz question set"})

    return {"warnings": warnings}


# ------------------------------------------------------------------
# Content delivery (lessons + concepts from JSON files)
# ------------------------------------------------------------------
@router.get("/api/lessons")
def get_lessons():
    """Serve lesson index + full lesson+concept data from the content/ JSON files."""
    index_path = os.path.join(LESSONS_DIR, "index.json")
    if not os.path.exists(index_path):
        return {"lessons": []}

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    lessons_out = []
    for entry in index.get("lessons", []):
        lesson_path = os.path.join(LESSONS_DIR, entry.get("path", ""))
        if not os.path.exists(lesson_path):
            continue
        with open(lesson_path, "r", encoding="utf-8") as f:
            lesson = json.load(f)

        concepts_out = []
        for cid in lesson.get("concepts", []):
            concept_path = os.path.join(CONCEPTS_DIR, f"{cid}.json")
            if not os.path.exists(concept_path):
                continue
            with open(concept_path, "r", encoding="utf-8") as f:
                concept = json.load(f)
            concepts_out.append(concept)

        lessons_out.append({
            "lesson_id": lesson.get("lesson_id", entry.get("lesson_id")),
            "title": lesson.get("title", entry.get("title")),
            "intro": lesson.get("intro", ""),
            "outro": lesson.get("outro", ""),
            "concepts": concepts_out,
        })

    return {"lessons": lessons_out}


# ------------------------------------------------------------------
# Progress tracking (for the UI's local learning sessions)
# ------------------------------------------------------------------
class ProgressBody(BaseModel):
    concept_id: Optional[str] = None
    lesson_id: Optional[str] = None
    status: str = "completed"


@router.post("/api/progress")
def save_progress(body: ProgressBody):
    """Save concept/lesson completion from the learner UI."""
    try:
        conn = sqlite3.connect(PROGRESS_DB_PATH)
        if body.concept_id:
            conn.execute(
                "INSERT OR REPLACE INTO progress (concept_id, status) VALUES (?, ?)",
                (body.concept_id, body.status),
            )
        if body.lesson_id:
            conn.execute(
                "INSERT OR REPLACE INTO lessons (lesson_id, status) VALUES (?, ?)",
                (body.lesson_id, body.status),
            )
        conn.commit()
        conn.close()
        return {"saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/progress")
def get_progress():
    """Get all progress records."""
    try:
        conn = sqlite3.connect(PROGRESS_DB_PATH)
        concepts = conn.execute("SELECT concept_id, status FROM progress").fetchall()
        lessons = conn.execute("SELECT lesson_id, status FROM lessons").fetchall()
        conn.close()
        return {
            "concepts": [{"concept_id": r[0], "status": r[1]} for r in concepts],
            "lessons": [{"lesson_id": r[0], "status": r[1]} for r in lessons],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Updater (Supabase sync — forwarded from existing updater.py)
# ------------------------------------------------------------------
@router.post("/api/apply")
def apply_updates():
    """Run the Supabase content sync and return stdout output."""
    # Import from engine directory dynamically
    _engine_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "engine")
    if _engine_dir not in sys.path:
        sys.path.insert(0, _engine_dir)

    try:
        from updater import run_update  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Cannot import updater: {e}")

    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        run_update()
    except Exception as e:
        sys.stdout = old_stdout
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sys.stdout = old_stdout

    return {"output": buf.getvalue()}


@router.get("/api/installed")
def get_installed():
    """List installed content versions from progress.db."""
    try:
        conn = sqlite3.connect(PROGRESS_DB_PATH)
        rows = conn.execute("SELECT content_id, type, version FROM installed_content").fetchall()
        conn.close()
        return [{"content_id": r[0], "type": r[1], "version": r[2]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/preview")
def preview_updates():
    """Preview available Supabase content updates."""
    _engine_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "engine")
    if _engine_dir not in sys.path:
        sys.path.insert(0, _engine_dir)

    try:
        from updater import preview_updates as _preview  # type: ignore
        return _preview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
