FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY constraints.txt ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY catalog ./catalog
RUN pip install --no-cache-dir -c constraints.txt .

FROM base AS test
COPY tests ./tests
# Historical init SQL is a legacy-upgrade test fixture, never a startup path.
COPY --from=legacy_init . ./tests/fixtures
RUN pip install --no-cache-dir -c constraints.txt '.[dev]'
RUN useradd --create-home --uid 10001 appuser
USER appuser
CMD ["python", "-m", "pytest", "-m", "not integration", "-p", "no:cacheprovider"]

FROM base AS runtime
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
