"""Small database boundary for the starter catalog."""

from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row


class CatalogRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.environ.get("DATABASE_URL", "")

    def _connect(self) -> psycopg.Connection:
        if not self._database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self._database_url, row_factory=dict_row, connect_timeout=3)

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1")

    def list_species(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.common_name_en, s.common_name_bn, s.category,
                       c.review_status AS evidence_status, c.title AS source_title
                  FROM species AS s
                  JOIN catalog_source AS c ON c.id = s.source_id
                 WHERE s.is_active = TRUE
                 ORDER BY s.common_name_en, s.id
                 LIMIT 100
                """
            ).fetchall()
        return list(rows)


def get_catalog_repository() -> CatalogRepository:
    """FastAPI dependency; replaceable in tests."""
    return CatalogRepository()
