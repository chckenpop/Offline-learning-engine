"""SQLite implementation of ConceptRepository."""
from __future__ import annotations
import json
from typing import List, Optional

from app.domain.concept.models import Concept, ConceptVersion
from app.persistence.interfaces.concept_repository import ConceptRepository
from app.persistence.db import get_connection


def _row_to_version(row) -> ConceptVersion:
    return ConceptVersion(
        id=row["id"],
        concept_id=row["concept_id"],
        version_number=row["version_number"],
        name=row["name"],
        core_definition=row["core_definition"],
        expanded_explanation=row["expanded_explanation"],
        learning_objective=row["learning_objective"],
        examples=json.loads(row["examples"] or "[]"),
        misconceptions=json.loads(row["misconceptions"] or "[]"),
        prerequisites=json.loads(row["prerequisites"] or "[]"),
        scope_boundaries=row["scope_boundaries"],
        check_text=row["check_text"],
        grade=row["grade"],
        board=row["board"],
        change_note=row["change_note"],
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


def _row_to_concept(row, version: Optional[ConceptVersion] = None) -> Concept:
    return Concept(
        id=row["id"],
        owner_id=row["owner_id"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        latest_version=version,
    )


class SqliteConceptRepository(ConceptRepository):

    def save_concept(self, concept: Concept) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO concepts (id, owner_id, status, created_at, updated_at)
            VALUES (:id, :owner_id, :status, :created_at, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                status     = excluded.status,
                updated_at = excluded.updated_at
            """,
            {
                "id": concept.id,
                "owner_id": concept.owner_id,
                "status": concept.status,
                "created_at": concept.created_at,
                "updated_at": concept.updated_at,
            },
        )
        conn.commit()
        conn.close()

    def save_version(self, version: ConceptVersion) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO concept_versions (
                id, concept_id, version_number, name,
                core_definition, expanded_explanation, learning_objective,
                examples, misconceptions, prerequisites,
                scope_boundaries, check_text, grade, board,
                change_note, created_by, created_at
            ) VALUES (
                :id, :concept_id, :version_number, :name,
                :core_definition, :expanded_explanation, :learning_objective,
                :examples, :misconceptions, :prerequisites,
                :scope_boundaries, :check_text, :grade, :board,
                :change_note, :created_by, :created_at
            )
            """,
            {
                "id": version.id,
                "concept_id": version.concept_id,
                "version_number": version.version_number,
                "name": version.name,
                "core_definition": version.core_definition,
                "expanded_explanation": version.expanded_explanation,
                "learning_objective": version.learning_objective,
                "examples": json.dumps(version.examples),
                "misconceptions": json.dumps(version.misconceptions),
                "prerequisites": json.dumps(version.prerequisites),
                "scope_boundaries": version.scope_boundaries,
                "check_text": version.check_text,
                "grade": version.grade,
                "board": version.board,
                "change_note": version.change_note,
                "created_by": version.created_by,
                "created_at": version.created_at,
            },
        )
        conn.commit()
        conn.close()

    def get_by_id(self, concept_id: str) -> Optional[Concept]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM concepts WHERE id = ?", (concept_id,)
        ).fetchone()
        if not row:
            conn.close()
            return None
        version_row = conn.execute(
            """
            SELECT * FROM concept_versions
            WHERE concept_id = ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (concept_id,),
        ).fetchone()
        conn.close()
        version = _row_to_version(version_row) if version_row else None
        return _row_to_concept(row, version)

    def list_all(self) -> List[Concept]:
        conn = get_connection()
        concept_rows = conn.execute(
            "SELECT * FROM concepts ORDER BY created_at DESC"
        ).fetchall()
        results = []
        for cr in concept_rows:
            version_row = conn.execute(
                """
                SELECT * FROM concept_versions
                WHERE concept_id = ?
                ORDER BY version_number DESC
                LIMIT 1
                """,
                (cr["id"],),
            ).fetchone()
            version = _row_to_version(version_row) if version_row else None
            results.append(_row_to_concept(cr, version))
        conn.close()
        return results

    def get_versions(self, concept_id: str) -> List[ConceptVersion]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM concept_versions WHERE concept_id = ? ORDER BY version_number ASC",
            (concept_id,),
        ).fetchall()
        conn.close()
        return [_row_to_version(r) for r in rows]

    def get_version(self, concept_id: str, version_number: int) -> Optional[ConceptVersion]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM concept_versions WHERE concept_id = ? AND version_number = ?",
            (concept_id, version_number),
        ).fetchone()
        conn.close()
        return _row_to_version(row) if row else None

    def delete(self, concept_id: str) -> bool:
        conn = get_connection()
        cur = conn.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def get_latest_version_number(self, concept_id: str) -> int:
        conn = get_connection()
        row = conn.execute(
            "SELECT MAX(version_number) FROM concept_versions WHERE concept_id = ?",
            (concept_id,),
        ).fetchone()
        conn.close()
        return row[0] if row and row[0] is not None else 0
