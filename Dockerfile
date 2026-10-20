FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/learnflow-landing/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/learnflow-landing/ ./
ENV VITE_ENABLE_LOCAL_GPT_PREVIEW=false
RUN npm run build && test -f dist/index.html

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    ARTIFACTS_DIR=/app/artifacts

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        fonts-dejavu-core \
        graphviz \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts \
    && npm cache clean --force

COPY . .
COPY --from=frontend /frontend/dist /app/app/static/landing

# Exercise actual production dependencies, native font rendering and 720p
# FFmpeg H.264 for all four scene types while building the release image.
# This preflight uses deterministic local scenes and no paid API requests.
RUN python -m pytest -q \
    tests/test_v3_98_auth_production.py::test_paid_production_renderers_encode_all_four_visual_types \
    tests/test_v3_98_auth_production.py::test_scene_encode_errors_are_classified_and_redacted

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin learnflow \
    && mkdir -p /app/artifacts \
    && chown -R learnflow:learnflow /app

USER learnflow

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" >/dev/null || exit 1'

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
