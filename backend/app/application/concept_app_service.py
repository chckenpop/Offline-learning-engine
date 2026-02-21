"""Application service — orchestrates validate → domain op → persist."""
from __future__ import annotations
from typing import List, Optional

from app.domain.concept.models import Concept, ConceptVersion
from app.domain.concept.service import ConceptDomainService
from app.domain.common.result import Result
from app.persistence.interfaces.concept_repository import ConceptRepository


class ConceptAppService:
    def __init__(self, repo: ConceptRepository):
        self._repo = repo
        self._domain = ConceptDomainService()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    def create_concept(self, owner_id: str, data: dict) -> Result[Concept]:
        result = self._domain.create_concept(owner_id, data)
        if not result.is_success:
            return Result.fail(result.error)
        concept, version = result.value
        self._repo.save_concept(concept)
        self._repo.save_version(version)
        return Result.ok(concept)

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        return self._repo.get_by_id(concept_id)

    def list_concepts(self) -> List[Concept]:
        return self._repo.list_all()

    def get_versions(self, concept_id: str) -> List[ConceptVersion]:
        return self._repo.get_versions(concept_id)

    def get_version(self, concept_id: str, version_number: int) -> Optional[ConceptVersion]:
        return self._repo.get_version(concept_id, version_number)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update_concept(self, concept_id: str, editor_id: str, data: dict) -> Result[Concept]:
        concept = self._repo.get_by_id(concept_id)
        if not concept:
            return Result.fail(f"Concept '{concept_id}' not found.")

        current_version_number = self._repo.get_latest_version_number(concept_id)
        result = self._domain.update_concept(concept, data, editor_id, current_version_number)
        if not result.is_success:
            return Result.fail(result.error)

        updated_concept, new_version = result.value
        self._repo.save_concept(updated_concept)
        self._repo.save_version(new_version)
        return Result.ok(updated_concept)

    # ------------------------------------------------------------------
    # STATUS TRANSITION
    # ------------------------------------------------------------------
    def change_status(self, concept_id: str, new_status: str, user_role: str) -> Result[Concept]:
        concept = self._repo.get_by_id(concept_id)
        if not concept:
            return Result.fail(f"Concept '{concept_id}' not found.")

        result = self._domain.transition_status(concept, new_status, user_role)
        if not result.is_success:
            return Result.fail(result.error)

        self._repo.save_concept(result.value)
        return Result.ok(result.value)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def delete_concept(self, concept_id: str) -> Result[bool]:
        deleted = self._repo.delete(concept_id)
        if not deleted:
            return Result.fail(f"Concept '{concept_id}' not found.")
        return Result.ok(True)
