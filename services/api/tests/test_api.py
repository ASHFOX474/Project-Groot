from fastapi.testclient import TestClient

from app.database import get_catalog_repository
from app.main import create_app


class FakeCatalogRepository:
    def ping(self) -> None:
        return None

    def list_species(self) -> list[dict]:
        return [
            {
                "id": "demo-neem",
                "common_name_en": "Neem",
                "common_name_bn": "নিম",
                "category": "tree",
                "evidence_status": "demo",
                "source_title": "Starter sample data",
            }
        ]


class UnavailableCatalogRepository:
    def ping(self) -> None:
        raise RuntimeError("No database")

    def list_species(self) -> list[dict]:
        raise RuntimeError("No database")


def test_live_and_ready() -> None:
    app = create_app()
    app.dependency_overrides[get_catalog_repository] = FakeCatalogRepository
    client = TestClient(app)

    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_catalog_marks_sample_as_demo() -> None:
    app = create_app()
    app.dependency_overrides[get_catalog_repository] = FakeCatalogRepository
    response = TestClient(app).get("/v1/catalog/species")

    assert response.status_code == 200
    assert response.json()[0]["evidence_status"] == "demo"
    assert response.json()[0]["common_name_bn"] == "নিম"


def test_database_failure_returns_service_unavailable() -> None:
    app = create_app()
    app.dependency_overrides[get_catalog_repository] = UnavailableCatalogRepository
    client = TestClient(app)

    assert client.get("/health/ready").status_code == 503
    assert client.get("/v1/catalog/species").status_code == 503
