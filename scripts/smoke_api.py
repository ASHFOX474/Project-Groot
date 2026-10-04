"""Read-only live check of the phone -> API -> database contract."""
import json
import os
from urllib.request import urlopen


def get_json(path: str):
    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    with urlopen(f"{base_url.rstrip('/')}{path}", timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{path}: unexpected status {response.status}")
        return json.load(response)


def main() -> None:
    if get_json("/health/live") != {"status": "ok"}:
        raise RuntimeError("Liveness check failed")
    if get_json("/health/ready") != {"status": "ready"}:
        raise RuntimeError("Database readiness check failed")
    species = get_json("/v1/catalog/species")
    if not isinstance(species, list) or not species:
        raise RuntimeError("Catalog must contain seed rows for this demo")
    for item in species:
        for key in ("id", "common_name_en", "common_name_bn", "source_title"):
            if not isinstance(item.get(key), str) or not item[key]:
                raise RuntimeError(f"Invalid catalog field: {key}")
        if item.get("category") not in ("crop", "tree"):
            raise RuntimeError("Invalid category")
        if item.get("evidence_status") not in ("demo", "reviewed"):
            raise RuntimeError("Invalid evidence status")
    print(f"PASS: live API, database readiness, {len(species)} catalog rows with Bangla names")


if __name__ == "__main__":
    main()
