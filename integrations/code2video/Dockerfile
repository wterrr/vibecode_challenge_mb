# Optional Code2Video service; does NOT alter LearnFlow's production Dockerfile.
# Upstream: showlab/Code2Video, MIT, pinned to an audited commit.
FROM python:3.12-slim-bookworm AS upstream
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
ARG CODE2VIDEO_REV=1142d8e14cdc2806df85aedb0fbb5dca474caa0f
RUN git clone --no-checkout https://github.com/showlab/Code2Video.git /opt/Code2Video \
 && git -C /opt/Code2Video checkout --detach "$CODE2VIDEO_REV" \
 && test "$(git -C /opt/Code2Video rev-parse HEAD)" = "$CODE2VIDEO_REV"

FROM python:3.12-slim-bookworm AS planner
RUN useradd --create-home --uid 10002 --shell /usr/sbin/nologin c2v
COPY --from=upstream /opt/Code2Video/prompts /opt/c2v/prompts
COPY --from=upstream /opt/Code2Video/LICENSE /opt/c2v/LICENSE
COPY integrations/code2video/planner_worker.py /srv/planner_worker.py
ENV PYTHONPATH=/opt/c2v PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER c2v
EXPOSE 8765
CMD ["python","/srv/planner_worker.py"]

FROM python:3.12-slim-bookworm AS renderer
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core fonts-cmu libpango1.0-dev libcairo2-dev \
    pkg-config build-essential cmake \
 && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir "manim==0.19.0"
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin c2v
COPY integrations/code2video/render_worker.py /srv/render_worker.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
USER c2v
EXPOSE 8788
CMD ["python","/srv/render_worker.py"]
