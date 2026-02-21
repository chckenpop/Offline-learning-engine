"""Abstract repository interface for the Concept aggregate."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from app.domain.concept.models import Concept, ConceptVersion


class ConceptRepository(ABC):

    @abstractmethod
    def save_concept(self, concept: Concept) -> None:
        """Insert or update the concept identity row."""
        ...

    @abstractmethod
    def save_version(self, version: ConceptVersion) -> None:
        """Append a new (immutable) version row — never call UPDATE on an existing version."""
        ...

    @abstractmethod
    def get_by_id(self, concept_id: str) -> Optional[Concept]:
        """Return the Concept with its latest_version populated, or None."""
        ...

    @abstractmethod
    def list_all(self) -> List[Concept]:
        """Return all concepts with their latest version populated."""
        ...

    @abstractmethod
    def get_versions(self, concept_id: str) -> List[ConceptVersion]:
        """Return all versions for a concept, ordered by version_number ASC."""
        ...

    @abstractmethod
    def get_version(self, concept_id: str, version_number: int) -> Optional[ConceptVersion]:
        """Return a specific version, or None if not found."""
        ...

    @abstractmethod
    def delete(self, concept_id: str) -> bool:
        """Delete concept and cascade to versions. Returns True if deleted."""
        ...

    @abstractmethod
    def get_latest_version_number(self, concept_id: str) -> int:
        """Return the highest version_number for a concept, or 0 if none."""
        ...
