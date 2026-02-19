import json
import sqlite3
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
ENGINE_DIR = BASE_DIR / "engine"
sys.path.insert(0, str(ENGINE_DIR))

import updater  # noqa: E402


def _init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE installed_content (
            content_id TEXT NOT NULL,
            type TEXT NOT NULL,
            version INTEGER,
            PRIMARY KEY (content_id, type)
        )
        """
    )
    conn.commit()
    conn.close()


def test_preview_updates_classifies_new_update_skip(monkeypatch):
    concepts = [
        {"id": "c1", "version": 1, "json_data": {"title": "C1"}},
        {"id": "c2", "version": 2, "json_data": {"title": "C2"}},
        {"id": "c3", "version": 3, "json_data": {"title": "C3"}},
    ]
    lessons = [
        {"lesson_id": "l1", "version": 1, "json_data": {"title": "L1"}},
        {"lesson_id": "l2", "version": 2, "json_data": {"title": "L2"}},
    ]
    installed = {
        ("c1", "concept"): None,
        ("c2", "concept"): 2,
        ("c3", "concept"): 1,
        ("l1", "lesson"): 1,
        ("l2", "lesson"): None,
    }

    monkeypatch.setattr(updater, "fetch_concepts", lambda: concepts)
    monkeypatch.setattr(updater, "fetch_lessons", lambda: lessons)
    monkeypatch.setattr(
        updater,
        "get_installed_version",
        lambda cid, ctype: installed.get((cid, ctype)),
    )

    result = updater.preview_updates()

    assert result["concepts"]["new"] == [{"id": "c1", "version": 1}]
    assert result["concepts"]["skip"] == [{"id": "c2", "version": 2}]
    assert result["concepts"]["update"] == [{"id": "c3", "version": 3, "installed": 1}]

    assert result["lessons"]["new"] == [{"id": "l2", "version": 2}]
    assert result["lessons"]["skip"] == [{"id": "l1", "version": 1}]


def test_run_update_writes_files_and_updates_index(monkeypatch, tmp_path):
    content_dir = tmp_path / "content"
    lessons_dir = content_dir / "lessons"
    concepts_dir = content_dir / "concepts"
    database_dir = tmp_path / "database"
    lessons_dir.mkdir(parents=True)
    concepts_dir.mkdir(parents=True)
    database_dir.mkdir()

    db_path = database_dir / "progress.db"
    _init_db(db_path)

    monkeypatch.setattr(updater, "LESSONS_DIR", str(lessons_dir))
    monkeypatch.setattr(updater, "CONCEPTS_DIR", str(concepts_dir))
    monkeypatch.setattr(updater, "DB_PATH", str(db_path))
    monkeypatch.setattr(updater, "INDEX_FILE", str(lessons_dir / "index.json"))

    lesson_payload = {"lesson_id": "lesson_a", "version": 1, "json_data": {"title": "Lesson A"}}
    concept_payload = {"id": "concept_x", "version": 1, "json_data": {"title": "Concept X"}}

    monkeypatch.setattr(updater, "fetch_lessons", lambda: [lesson_payload])
    monkeypatch.setattr(updater, "fetch_concepts", lambda: [concept_payload])
    monkeypatch.setattr(
        updater,
        "fetch_concept_detail",
        lambda cid, current_version=None: {
            "concept": concept_payload["json_data"],
            "delivery_version": concept_payload["version"],
            "update_available": True,
        },
    )

    updater.run_update()

    lesson_file = lessons_dir / "lesson_a.json"
    concept_file = concepts_dir / "concept_x.json"
    index_file = lessons_dir / "index.json"

    assert lesson_file.exists()
    assert concept_file.exists()
    assert index_file.exists()

    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert index["lessons"][0]["lesson_id"] == "lesson_a"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM installed_content")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 2
