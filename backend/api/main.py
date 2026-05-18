"""FastAPI 진입점."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import storage
from api.routers import datasets, ml, qc, quantification


def create_app() -> FastAPI:
    storage.ensure_dirs()
    app = FastAPI(
        title="PCR Diagnostic API",
        version="0.1.0",
        description="Single-user MVP API for PCR diagnostic analysis.",
    )

    # dev only — vite dev server (5173)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(datasets.router)
    app.include_router(qc.router)
    app.include_router(quantification.router)
    app.include_router(ml.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
