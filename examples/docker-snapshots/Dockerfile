# memory-vault — snapshot-only (Restic) in Docker.
# Does not install restic on the host OS. No GUI.
FROM python:3.12-slim-bookworm

ARG RESTIC_VERSION=0.17.3

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates bzip2 git \
 && curl -fsSL "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" \
    | bunzip2 > /usr/local/bin/restic \
 && chmod 755 /usr/local/bin/restic \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/memory-vault
RUN git clone --depth 1 https://github.com/daniquir/memory-vault.git . \
 && git rev-parse --short HEAD > /opt/memory-vault/.git-commit

# CLI only: boto3 is enough. No GUI dependencies.
RUN pip install --no-cache-dir boto3 \
 && pip install --no-cache-dir --no-deps .

COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

ENV HOME=/data \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

VOLUME ["/data"]
ENTRYPOINT ["/entrypoint.sh"]
