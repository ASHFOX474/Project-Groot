"""Small database boundary for the starter catalog."""

from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from app.migrations import head_revision
from app.catalog_bundle import Requirement


class CatalogRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.environ.get("DATABASE_URL", "")

    def _connect(self) -> psycopg.Connection:
        if not self._database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self._database_url, row_factory=dict_row, connect_timeout=3)

    def ping(self) -> None:
        with self._connect() as connection:
            versions = connection.execute("SELECT version_num FROM public.alembic_version").fetchall()
            if [row["version_num"] for row in versions] != [head_revision()]:
                raise RuntimeError("Database migrations are pending")
            connection.execute("SELECT id FROM public.catalog_source LIMIT 0")
            connection.execute("SELECT id FROM public.species LIMIT 0")

    def list_species(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.common_name_en, s.common_name_bn, s.category,
                       c.review_status AS evidence_status, c.title AS source_title
                  FROM public.species AS s
                  JOIN public.catalog_source AS c ON c.id = s.source_id
                 WHERE s.is_active = TRUE
                 ORDER BY s.common_name_en, s.id
                 LIMIT 100
                """
            ).fetchall()
        return list(rows)

    def list_recommendation_candidates(self) -> list[dict]:
        """Eligible reference profiles, not personalized suitability recommendations."""
        with self._connect() as connection:
            return self.recommendation_candidates_from(connection)

    @staticmethod
    def recommendation_candidates_from(connection, profile_id=None) -> list[dict]:
        """Share the exact eligibility boundary inside an authenticated transaction."""
        rows = connection.execute('''
                SELECT p.id, p.country_code, p.locality, p.growing_context, p.variety,
                       p.reviewed_by, p.reviewed_at, p.valid_until, p.limitations,
                       p.import_sha256, primary_source.valid_until AS primary_valid_until,
                       s.id AS species_id, s.scientific_name,
                       s.common_name_en, s.common_name_bn, s.category,
                       jsonb_agg(jsonb_build_object(
                         'key',r.key,'value',r.value,'source_id',r.source_id,
                         'source_locator',r.source_locator,'interpretation_note',r.interpretation_note,
                         'source_url',e.source_url,'source_title',e.title,'publisher',e.publisher,
                         'checked_at',e.checked_at,'valid_until',e.valid_until,
                         'license_name',e.license_name,'license_url',e.license_url,
                         'attribution',e.attribution
                       ) ORDER BY r.key) AS requirements
                FROM (SELECT * FROM public.recommendation_profile
                      WHERE (%s::text IS NULL OR id=%s) ORDER BY id LIMIT 100) p
                JOIN public.species s ON s.id=p.species_id
                JOIN public.catalog_source primary_source ON primary_source.id=s.source_id
                JOIN public.plant_requirement r ON r.profile_id=p.id
                JOIN public.catalog_source e ON e.id=r.source_id
                GROUP BY p.id,p.country_code,p.locality,p.growing_context,p.variety,
                         p.reviewed_by,p.reviewed_at,p.valid_until,p.limitations,p.import_sha256,
                         primary_source.valid_until,
                         s.id,s.scientific_name,s.common_name_en,s.common_name_bn,s.category
                ORDER BY p.id
            ''', (profile_id, profile_id)).fetchall()
        for row in rows:
            # Direct database writes must not bypass typed requirement validation.
            for requirement in row['requirements']:
                try:
                    Requirement.model_validate({key: requirement[key] for key in Requirement.model_fields})
                except ValueError:
                    raise RuntimeError('Catalog contains invalid requirements') from None
        return list(rows)


def get_catalog_repository() -> CatalogRepository:
    """FastAPI dependency; replaceable in tests."""
    return CatalogRepository()
