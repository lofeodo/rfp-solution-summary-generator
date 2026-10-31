# RFP solution-summary generator: one image for the UI and the CLI.
#
#   docker build -t rfp-agent .
#   docker run --rm -p 8000:8000 --env-file .env -v "$PWD/runs:/app/runs" rfp-agent
#   docker run --rm --env-file .env -v "$PWD/runs:/app/runs" rfp-agent \
#       python -m rfp_agent run inputs/rfp_brief.pdf
#
# Keys stay on the host in .env (never copied into the image); run directories land in
# the mounted runs/. Without keys the UI still serves the four committed samples.

# --- Stage 1: build the frontend (same Node version as CI) ---------------------------
FROM node:22-alpine AS frontend
WORKDIR /build
COPY ui/frontend/package.json ui/frontend/package-lock.json ./
RUN npm ci
COPY ui/frontend/ ./
RUN npm run build

# --- Stage 2: runtime ---------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# requirements.txt ends with `-e .`, so the package metadata and source must be present
# before the install. Dependencies change rarely, so this layer caches well.
COPY requirements.txt pyproject.toml README.md ./
COPY src/ src/
RUN pip install -r requirements.txt

# Everything the pipeline, the UI and the evals read at run time.
COPY prompts/ prompts/
COPY inputs/ inputs/
COPY data/rfps/ data/rfps/
COPY runs/samples/ runs/samples/
COPY evals/ evals/
COPY tests/ tests/
COPY ui/__init__.py ui/
COPY ui/backend/ ui/backend/
COPY --from=frontend /build/dist ui/frontend/dist

RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8000
VOLUME ["/app/runs"]
CMD ["python", "-m", "ui.backend", "--host", "0.0.0.0", "--port", "8000"]
