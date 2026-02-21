"""Concept CRUD + lifecycle API endpoints."""
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.auth import get_current_user, optional_current_user
from app.application.concept_app_service import ConceptAppService
from app.container import get_concept_app_service
from app.domain.concept.models import Concept, ConceptVersion

router = APIRouter(tags=["concepts"])


# ------------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------------
class ConceptContentBody(BaseModel):
    name: str
    core_definition: Optional[str] = None
    expanded_explanation: Optional[str] = None
    learning_objective: Optional[str] = None
    examples: List[str] = []
    misconceptions: List[str] = []
    prerequisites: List[str] = []
    scope_boundaries: Optional[str] = None
    check_text: Optional[str] = None
    grade: Optional[str] = None
    board: Optional[str] = None
    change_note: Optional[str] = None


class StatusChangeBody(BaseModel):
    new_status: str


# ------------------------------------------------------------------
# Serializers
# ------------------------------------------------------------------
def _serialize_version(v: ConceptVersion) -> dict:
    return {
        "id": v.id,
        "concept_id": v.concept_id,
        "version_number": v.version_number,
        "name": v.name,
        "core_definition": v.core_definition,
        "expanded_explanation": v.expanded_explanation,
        "learning_objective": v.learning_objective,
        "examples": v.examples,
        "misconceptions": v.misconceptions,
        "prerequisites": v.prerequisites,
        "scope_boundaries": v.scope_boundaries,
        "check_text": v.check_text,
        "grade": v.grade,
        "board": v.board,
        "change_note": v.change_note,
        "created_by": v.created_by,
        "created_at": v.created_at,
    }


def _serialize_concept(c: Concept) -> dict:
    return {
        "id": c.id,
        "owner_id": c.owner_id,
        "status": c.status,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "latest_version": _serialize_version(c.latest_version) if c.latest_version else None,
    }


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@router.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------------------------
# Concept endpoints
# ------------------------------------------------------------------
@router.get("/concepts/")
def list_concepts(
    svc: ConceptAppService = Depends(get_concept_app_service),
    current_user: Optional[dict] = Depends(optional_current_user),
):
    return [_serialize_concept(c) for c in svc.list_concepts()]


@router.post("/concepts/", status_code=status.HTTP_201_CREATED)
def create_concept(
    body: ConceptContentBody,
    svc: ConceptAppService = Depends(get_concept_app_service),
    current_user: dict = Depends(get_current_user),
):
    result = svc.create_concept(owner_id=current_user["sub"], data=body.model_dump())
    if not result.is_success:
        raise HTTPException(status_code=400, detail=result.error)
    return _serialize_concept(result.value)


@router.get("/concepts/{concept_id}")
def get_concept(
    concept_id: str,
    svc: ConceptAppService = Depends(get_concept_app_service),
):
    concept = svc.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found")
    return _serialize_concept(concept)


@router.put("/concepts/{concept_id}")
def update_concept(
    concept_id: str,
    body: ConceptContentBody,
    svc: ConceptAppService = Depends(get_concept_app_service),
    current_user: dict = Depends(get_current_user),
):
    result = svc.update_concept(concept_id, editor_id=current_user["sub"], data=body.model_dump())
    if not result.is_success:
        raise HTTPException(status_code=400, detail=result.error)
    return _serialize_concept(result.value)


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(
    concept_id: str,
    svc: ConceptAppService = Depends(get_concept_app_service),
    current_user: dict = Depends(get_current_user),
):
    result = svc.delete_concept(concept_id)
    if not result.is_success:
        raise HTTPException(status_code=404, detail=result.error)


@router.post("/concepts/{concept_id}/status")
def change_status(
    concept_id: str,
    body: StatusChangeBody,
    svc: ConceptAppService = Depends(get_concept_app_service),
    current_user: dict = Depends(get_current_user),
):
    result = svc.change_status(concept_id, new_status=body.new_status, user_role=current_user["role"])
    if not result.is_success:
        raise HTTPException(status_code=400, detail=result.error)
    return _serialize_concept(result.value)


# ------------------------------------------------------------------
# Speed Test endpoint
# ------------------------------------------------------------------
@router.get("/api/speedtest")
def speed_test():
    """Returns 1MB of random data for speed testing."""
    import os
    from fastapi import Response
    # Generate 1MB of random data
    data = os.urandom(1024 * 1024)
    return Response(content=data, media_type="application/octet-stream")


# ------------------------------------------------------------------
# Versioning endpoints
# ------------------------------------------------------------------
@router.get("/concepts/{concept_id}/versions")
def get_versions(
    concept_id: str,
    svc: ConceptAppService = Depends(get_concept_app_service),
):
    versions = svc.get_versions(concept_id)
    return [_serialize_version(v) for v in versions]


@router.get("/concepts/{concept_id}/versions/{version_number}")
def get_version(
    concept_id: str,
    version_number: int,
    svc: ConceptAppService = Depends(get_concept_app_service),
):
    version = svc.get_version(concept_id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found for concept '{concept_id}'")
    return _serialize_version(version)
