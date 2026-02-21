"""Concept domain models — pure Python, no DB or HTTP dependencies."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConceptVersion:
    id: str
    concept_id: str
    version_number: int
    name: str
    core_definition: Optional[str] = None
    expanded_explanation: Optional[str] = None
    learning_objective: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    misconceptions: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    scope_boundaries: Optional[str] = None
    check_text: Optional[str] = None
    grade: Optional[str] = None
    board: Optional[str] = None
    change_note: Optional[str] = None
    created_by: str = ""
    created_at: str = ""


@dataclass
class Concept:
    id: str
    owner_id: str
    status: str  # DRAFT | REVIEW | APPROVED | PUBLISHED
    created_at: str
    updated_at: str
    latest_version: Optional[ConceptVersion] = None
