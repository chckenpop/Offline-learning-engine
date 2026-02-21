-- ============================================================
-- Offline Learning Engine — SQLite Schema
-- Migration 001: Initial schema
-- Uses CREATE TABLE IF NOT EXISTS — safe to run on every startup
-- ============================================================

-- Core concept identity + current status
CREATE TABLE IF NOT EXISTS concepts (
    id          TEXT PRIMARY KEY,       -- UUID
    owner_id    TEXT NOT NULL,          -- UUID of creating user
    status      TEXT NOT NULL DEFAULT 'DRAFT',  -- DRAFT | REVIEW | APPROVED | PUBLISHED
    created_at  TEXT NOT NULL,          -- ISO8601
    updated_at  TEXT NOT NULL           -- ISO8601
);

-- Immutable version history (never UPDATE a row here)
CREATE TABLE IF NOT EXISTS concept_versions (
    id                   TEXT PRIMARY KEY,   -- UUID
    concept_id           TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    version_number       INTEGER NOT NULL,
    name                 TEXT NOT NULL,
    core_definition      TEXT,
    expanded_explanation TEXT,
    learning_objective   TEXT,
    examples             TEXT,              -- JSON array of strings
    misconceptions       TEXT,              -- JSON array of strings
    prerequisites        TEXT,              -- JSON array of strings
    scope_boundaries     TEXT,
    check_text           TEXT,              -- renamed from 'check' (SQL keyword)
    grade                TEXT,
    board                TEXT,
    change_note          TEXT,
    created_by           TEXT NOT NULL,     -- UUID of user who created this version
    created_at           TEXT NOT NULL      -- ISO8601
);

CREATE INDEX IF NOT EXISTS idx_concept_versions_concept_id ON concept_versions(concept_id);
CREATE INDEX IF NOT EXISTS idx_concept_versions_version ON concept_versions(concept_id, version_number);

-- Comments on concepts (for BottomPanel)
CREATE TABLE IF NOT EXISTS concept_comments (
    id          TEXT PRIMARY KEY,
    concept_id  TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    author_id   TEXT NOT NULL,
    author_name TEXT,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- Users (simple local user store)
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,           -- UUID
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'author',  -- author | reviewer | approver | admin
    display_name    TEXT,
    email           TEXT,
    created_at      TEXT NOT NULL
);

-- ============================================================
-- Preserved existing tables (used by engine/ and updater.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS progress (
    concept_id TEXT PRIMARY KEY,
    status TEXT
);

CREATE TABLE IF NOT EXISTS lessons (
    lesson_id TEXT PRIMARY KEY,
    status TEXT
);

CREATE TABLE IF NOT EXISTS installed_content (
    content_id TEXT NOT NULL,
    type TEXT NOT NULL,
    version TEXT,
    PRIMARY KEY (content_id, type)
);

CREATE TABLE IF NOT EXISTS content_aliases (
    alias TEXT PRIMARY KEY,
    canonical TEXT
);
