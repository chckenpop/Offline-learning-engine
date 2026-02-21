"""API tests using FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient


def create_test_app():
    """Create the app with an in-memory SQLite DB for testing."""
    import os
    # Point config to an in-memory path for tests
    os.environ["DATABASE_PATH"] = ":memory:"

    # Clear any cached singletons from container
    import importlib
    from app import container
    container.get_concept_repo.cache_clear()
    container.get_concept_app_service.cache_clear()

    from app.main import app
    return app


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from app.persistence.db import init_db
    init_db()
    return TestClient(app)


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
def test_login_success(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"


def test_login_bad_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_get_profile(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    token = login.json()["token"]
    resp = client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


# ------------------------------------------------------------------
# Concept CRUD
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def auth_headers(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    token = login.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_concept(client, auth_headers):
    resp = client.post(
        "/concepts/",
        json={"name": "Test Concept", "core_definition": "A test.", "examples": ["Example 1"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["latest_version"]["name"] == "Test Concept"
    assert data["latest_version"]["version_number"] == 1


def test_list_concepts(client):
    resp = client.get("/concepts/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_update_concept_creates_new_version(client, auth_headers):
    # Create
    c = client.post(
        "/concepts/",
        json={"name": "Versioned Concept"},
        headers=auth_headers,
    ).json()
    concept_id = c["id"]

    # Update
    resp = client.put(
        f"/concepts/{concept_id}",
        json={"name": "Versioned Concept Updated", "change_note": "Fixed typo"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["latest_version"]["version_number"] == 2

    # Versions list should have 2 entries
    versions = client.get(f"/concepts/{concept_id}/versions").json()
    assert len(versions) == 2


# ------------------------------------------------------------------
# Lifecycle state machine
# ------------------------------------------------------------------
def test_status_transition_draft_to_review(client, auth_headers):
    c = client.post("/concepts/", json={"name": "Lifecycle Test"}, headers=auth_headers).json()
    concept_id = c["id"]
    resp = client.post(
        f"/concepts/{concept_id}/status",
        json={"new_status": "REVIEW"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REVIEW"


def test_status_transition_skip_rejected(client, auth_headers):
    c = client.post("/concepts/", json={"name": "Skip Test"}, headers=auth_headers).json()
    concept_id = c["id"]
    # Try to jump from DRAFT directly to PUBLISHED — should fail
    resp = client.post(
        f"/concepts/{concept_id}/status",
        json={"new_status": "PUBLISHED"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_status_transition_reverse_rejected(client, auth_headers):
    c = client.post("/concepts/", json={"name": "Reverse Test"}, headers=auth_headers).json()
    concept_id = c["id"]
    # Forward to REVIEW
    client.post(f"/concepts/{concept_id}/status", json={"new_status": "REVIEW"}, headers=auth_headers)
    # Try to go back to DRAFT — should fail
    resp = client.post(
        f"/concepts/{concept_id}/status",
        json={"new_status": "DRAFT"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ------------------------------------------------------------------
# Comments
# ------------------------------------------------------------------
def test_post_and_get_comment(client, auth_headers):
    c = client.post("/concepts/", json={"name": "Comment Test"}, headers=auth_headers).json()
    concept_id = c["id"]

    resp = client.post(
        f"/concepts/{concept_id}/comments",
        json={"body": "Looks good to me!"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    comments = client.get(f"/concepts/{concept_id}/comments").json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Looks good to me!"
