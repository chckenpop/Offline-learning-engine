"""FastAPI application entry point."""
from __future__ import annotations
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.persistence.db import init_db
from app.api import auth, concepts, panels

# ------------------------------------------------------------------
# App creation
# ------------------------------------------------------------------
app = FastAPI(
    title="Offline Learning Engine API",
    description="Backend API for the Offline-First Learning Engine",
    version="2.0.0",
)

# CORS — allow everything for local dev (restrict for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Startup: initialise DB schema
# ------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(concepts.router)
app.include_router(panels.router)

# ------------------------------------------------------------------
# Serve the existing UI as a static site
# ------------------------------------------------------------------
_UI_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ui")
)

if os.path.isdir(_UI_DIR):
    # Mount at root / to allow index.html to find styles.css, main.js etc directly.
    # We do this LAST so it doesn't shadow the explicit /auth, /concepts routes.
    app.mount("/", StaticFiles(directory=_UI_DIR, html=True), name="ui")
