# Check station: runs mechanical checks with no credentials (ADR-01, I-09).
# The runner is standard-library Python, so the same layer can be added to any
# project's toolchain image; this image is the base toolchain (M0-04 grows it).

FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime
RUN groupadd --system --gid 10200 gs-runs \
 && groupadd --system --gid 10003 gs-runner \
 && useradd --system --uid 10003 --gid gs-runner --groups gs-runs \
      --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin gs-runner \
 && install -d -o root -g gs-runs -m 2770 /var/lib/grindstone/runs
COPY runner/src/grindstone_runner /opt/grindstone-runner/grindstone_runner
ENV PYTHONPATH=/opt/grindstone-runner \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRINDSTONE_RUNS_DIR=/var/lib/grindstone/runs \
    GRINDSTONE_RUNNER_HEARTBEAT=/tmp/grindstone-runner.heartbeat
USER gs-runner
CMD ["python", "-m", "grindstone_runner", "serve"]
