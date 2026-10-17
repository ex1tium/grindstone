# Agent station: the AHP host for agent sessions (ADR-15). Holds model
# credentials only; never a control-plane credential (I-09). M0 serves health
# only; agents as their own Unix users arrive with SPEC-05 and SPEC-06.

FROM node:26.11.1-trixie-slim@sha256:193fe51b64e77981119c98c2002c9e32a70e2f006fb4d25068ce0558998917f0 AS runtime
RUN groupadd --system --gid 10100 gs-workspaces \
 && groupadd --system --gid 10002 gs-host \
 && useradd --system --uid 10002 --gid gs-host --groups gs-workspaces \
      --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin gs-host \
 && install -d -o root -g gs-workspaces -m 2770 /var/lib/grindstone/workspaces
WORKDIR /opt/agent-host
# No runtime dependencies yet; @grindstone/contracts is imported for types only,
# which Node's type stripping erases.
COPY agent-host/package.json ./
COPY agent-host/src ./src
ENV NODE_ENV=production \
    GRINDSTONE_AGENT_HOST_BIND=0.0.0.0 \
    GRINDSTONE_AGENT_HOST_PORT=8090
USER gs-host
EXPOSE 8090
CMD ["node", "src/main.ts"]
