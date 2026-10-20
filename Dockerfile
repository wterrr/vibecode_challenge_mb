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
        fonts-cmu \
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

# VibeHost deploys have constrained build CPU/RAM/time. Never burn 720p
# test videos in the deploy build. GitHub Actions sets this ARG to 1 and
# verifies real renderers + audiovisual assembly against the SAME image.
ARG RUN_BUILD_MEDIA_SMOKE=0
RUN if [ "$RUN_BUILD_MEDIA_SMOKE" = "1" ]; then \
      python -m pytest -q \
        tests/test_v3_98_auth_production.py::test_paid_production_renderers_encode_all_four_visual_types \
        tests/test_v3_98_auth_production.py::test_scene_encode_errors_are_classified_and_redacted \
        tests/test_assembly_production_hotfix.py \
        tests/test_v3_production_semantic_motion.py \
        tests/test_v3_production_visual_director.py; \
    elif [ "$RUN_BUILD_MEDIA_SMOKE" != "0" ]; then \
      echo "RUN_BUILD_MEDIA_SMOKE must be 0 or 1" >&2; exit 2; \
    fi

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin learnflow \
    && mkdir -p /app/artifacts \
    && chown -R learnflow:learnflow /app

USER learnflow

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" >/dev/null || exit 1'

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
