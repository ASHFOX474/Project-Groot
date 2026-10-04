"""HTTP entry point for the Groot starter service."""

from __future__ import annotations

from typing import Annotated, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.database import CatalogRepository, get_catalog_repository
from app.account_routes import router as account_router
from app.privacy_middleware import PrivacyMiddleware


class SpeciesResponse(BaseModel):
    id: str
    common_name_en: str
    common_name_bn: str
    category: Literal["crop", "tree"]
    evidence_status: Literal["demo", "reviewed"]
    source_title: str


Repository = Annotated[CatalogRepository, Depends(get_catalog_repository)]


def create_app() -> FastAPI:
    api = FastAPI(
        title="Groot API",
        description="Plant catalog and private accounts/Plant Passports. Demo rows are not planting recommendations.",
        version="0.1.0",
    )
    api.add_middleware(PrivacyMiddleware)
    api.include_router(account_router)

    @api.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default error response can echo passwords and private notes.
        return JSONResponse(status_code=422, content={'detail': [
            {'loc': list(error['loc']), 'type': error['type'], 'msg': 'Invalid value'}
            for error in exc.errors()
        ]})

    @api.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        return JSONResponse(status_code=503, content={'detail': 'Service unavailable'})

    @api.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/health/ready")
    def readiness(repository: Repository) -> dict[str, str]:
        try:
            repository.ping()
        except (psycopg.Error, RuntimeError) as exc:
            raise HTTPException(status_code=503, detail="Database unavailable") from exc
        return {"status": "ready"}

    @api.get("/v1/catalog/species", response_model=list[SpeciesResponse])
    def list_species(repository: Repository) -> list[dict]:
        try:
            return repository.list_species()
        except (psycopg.Error, RuntimeError) as exc:
            raise HTTPException(status_code=503, detail="Catalog unavailable") from exc

    @api.get("/v1/catalog/recommendation-candidates", response_model=list[dict],
             summary="Reviewed reference profiles, not personalized planting advice")
    def recommendation_candidates(repository: Repository) -> list[dict]:
        try:
            return repository.list_recommendation_candidates()
        except (psycopg.Error, RuntimeError) as exc:
            raise HTTPException(status_code=503, detail="Reviewed catalog unavailable") from exc

    return api


app = create_app()
