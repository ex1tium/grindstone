# Agent station: the AHP host for agent sessions (ADR-15). Holds model
# credentials only; never a control-plane credential (I-09). Agents run as the
# pool's users gs-agent-1 to gs-agent-8, each in its own group only (SPEC-05,
# DEC-0502). The image starts as root only for its entrypoint, which copies
# the secrets for `gs-host` and keeps it exactly CAP_SETUID and CAP_SETGID.

FROM node:24.22.0-trixie-slim@sha256:7f486cabe892bff8fef04c0f7da8dba84a560be3e4e2740b7a86afc57ebec315 AS runtime
RUN groupadd --system --gid 10100 gs-workspaces \
 && groupadd --system --gid 10002 gs-host \
 && useradd --system --uid 10002 --gid gs-host --groups gs-workspaces \
      --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin gs-host \
 && for n in 1 2 3 4 5 6 7 8; do \
      groupadd --system --gid "1020$n" "gs-agent-$n" \
      && useradd --system --uid "1020$n" --gid "gs-agent-$n" \
           --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin "gs-agent-$n" \
      || exit 1; \
    done \
 && install -d -o root -g gs-workspaces -m 2770 /var/lib/grindstone/workspaces \
 && install -d -o root -g root -m 0711 /var/lib/grindstone/sessions
WORKDIR /opt/agent-host
# No runtime dependencies yet; @grindstone/contracts is imported for types only,
# which Node's type stripping erases.
COPY agent-host/package.json ./
COPY agent-host/src ./src
COPY --chmod=0555 docker/entrypoints/lib.sh docker/entrypoints/agent-host.sh /usr/local/lib/grindstone/entrypoints/
ENV NODE_ENV=production \
    GRINDSTONE_AGENT_HOST_BIND=0.0.0.0 \
    GRINDSTONE_AGENT_HOST_PORT=8090
EXPOSE 8090
ENTRYPOINT ["/usr/local/lib/grindstone/entrypoints/agent-host.sh"]
CMD ["node", "src/main.ts"]
