"""Dependency injection container — wires implementations to interfaces."""
from __future__ import annotations
from functools import lru_cache

from app.persistence.repositories.sqlite.sqlite_concept_repository import SqliteConceptRepository
from app.application.concept_app_service import ConceptAppService


@lru_cache(maxsize=1)
def get_concept_repo() -> SqliteConceptRepository:
    return SqliteConceptRepository()


@lru_cache(maxsize=1)
def get_concept_app_service() -> ConceptAppService:
    return ConceptAppService(repo=get_concept_repo())
