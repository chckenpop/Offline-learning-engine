"""Domain service — pure business logic for concept lifecycle and versioning."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.domain.concept.models import Concept, ConceptVersion
from app.domain.concept.rules import validate_status_transition, validate_concept_content
from app.domain.common.result import Result


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class ConceptDomainService:
    """
    Pure domain operations — no I/O. All methods return Result[T].
    The application layer calls these and then persists via the repository.
    """

    def create_concept(self, owner_id: str, data: dict) -> Result[tuple[Concept, ConceptVersion]]:
        """Create a brand-new Concept in DRAFT with version 1."""
        validation = validate_concept_content(data)
        if not validation.is_success:
            return Result.fail(validation.error)

        now = _now_iso()
        concept_id = _new_id()

        concept = Concept(
            id=concept_id,
            owner_id=owner_id,
            status="DRAFT",
            created_at=now,
            updated_at=now,
        )

        version = ConceptVersion(
            id=_new_id(),
            concept_id=concept_id,
            version_number=1,
            name=data["name"],
            core_definition=data.get("core_definition"),
            expanded_explanation=data.get("expanded_explanation"),
            learning_objective=data.get("learning_objective"),
            examples=data.get("examples", []),
            misconceptions=data.get("misconceptions", []),
            prerequisites=data.get("prerequisites", []),
            scope_boundaries=data.get("scope_boundaries"),
            check_text=data.get("check_text"),
            grade=data.get("grade"),
            board=data.get("board"),
            change_note=data.get("change_note", "Initial version"),
            created_by=owner_id,
            created_at=now,
        )

        concept.latest_version = version
        return Result.ok((concept, version))

    def update_concept(
        self,
        concept: Concept,
        data: dict,
        editor_id: str,
        current_version_number: int,
    ) -> Result[tuple[Concept, ConceptVersion]]:
        """Produce a new version for an existing concept. Rejects PUBLISHED concepts."""
        if concept.status == "PUBLISHED":
            return Result.fail("PUBLISHED concepts are immutable. Cannot update.")

        validation = validate_concept_content(data)
        if not validation.is_success:
            return Result.fail(validation.error)

        now = _now_iso()
        new_version = ConceptVersion(
            id=_new_id(),
            concept_id=concept.id,
            version_number=current_version_number + 1,
            name=data["name"],
            core_definition=data.get("core_definition"),
            expanded_explanation=data.get("expanded_explanation"),
            learning_objective=data.get("learning_objective"),
            examples=data.get("examples", []),
            misconceptions=data.get("misconceptions", []),
            prerequisites=data.get("prerequisites", []),
            scope_boundaries=data.get("scope_boundaries"),
            check_text=data.get("check_text"),
            grade=data.get("grade"),
            board=data.get("board"),
            change_note=data.get("change_note", ""),
            created_by=editor_id,
            created_at=now,
        )

        concept.updated_at = now
        concept.latest_version = new_version
        return Result.ok((concept, new_version))

    def transition_status(
        self,
        concept: Concept,
        new_status: str,
        user_role: str,
    ) -> Result[Concept]:
        """Apply a lifecycle status transition. Returns updated Concept on success."""
        validation = validate_status_transition(concept.status, new_status, user_role)
        if not validation.is_success:
            return Result.fail(validation.error)

        concept.status = new_status
        concept.updated_at = _now_iso()
        return Result.ok(concept)
