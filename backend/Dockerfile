# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt requirements-lock.txt ./
RUN pip install --upgrade pip setuptools wheel
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    for attempt in 1 2 3; do \
        pip install --retries 10 --timeout 120 -r requirements-lock.txt && exit 0; \
        echo "Dependency installation attempt ${attempt} failed; retrying..."; \
        sleep $((attempt * 5)); \
    done; \
    exit 1


FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime-only tools used by the healthcheck and database readiness entrypoint.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

COPY . .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/wait-for-db.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
