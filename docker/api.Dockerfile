# API and pipeline image (one image, two commands): Python 3.11 + the locked dependencies.
FROM python:3.11-slim

# Behind a TLS-intercepting corporate proxy, pass its CA as a build secret (see README, "Docker").
# It is only used during these RUN steps and never stored in the image; without it nothing changes.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install --no-cache-dir "uv==0.11.32"

# uv installs exactly the versions in uv.lock; no Python download, bytecode compiled at build time.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app
# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock .python-version ./
# The uv download cache lives in a BuildKit cache mount: reused between builds, never in the image.
RUN --mount=type=secret,id=extra_ca,required=false \
    --mount=type=cache,target=/root/.cache/uv \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca UV_NATIVE_TLS=1; fi; \
    uv sync --frozen --no-dev --no-install-project

COPY config.yaml ./
COPY data/ref ./data/ref
COPY pipeline ./pipeline
COPY api ./api

# Data (raw CSV, DuckDB, gold Parquet) lives in a volume mounted at /data, never in the image.
ENV LADEWUESTE_DATA_DIR=/data
RUN useradd --uid 1000 --create-home app && mkdir -p /data && chown -R app /app /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/config')" || exit 1
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
