"""HTTP entry point for the Groot starter service."""

from __future__ import annotations

from typing import Annotated, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.database import CatalogRepository, get_catalog_repository


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
        description="Starter catalog API. Demo rows are not planting recommendations.",
        version="0.1.0",
    )

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

    return api


app = create_app()
