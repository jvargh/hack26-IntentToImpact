FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY intent-to-impact-studio/contracts/package.json intent-to-impact-studio/contracts/package-lock.json ./intent-to-impact-studio/contracts/
RUN npm ci --prefix intent-to-impact-studio/contracts --ignore-scripts
COPY intent-to-impact-studio/apps/experience/package.json intent-to-impact-studio/apps/experience/package-lock.json ./intent-to-impact-studio/apps/experience/
RUN npm ci --prefix intent-to-impact-studio/apps/experience
COPY intent-to-impact-studio/apps/experience ./intent-to-impact-studio/apps/experience
COPY intent-to-impact-studio/apps/control-plane/studio/studio.schema.json ./intent-to-impact-studio/apps/control-plane/studio/studio.schema.json
COPY intent-to-impact-studio/contracts/generated ./intent-to-impact-studio/contracts/generated
COPY intent-to-impact-studio/contracts/schemas ./intent-to-impact-studio/contracts/schemas
COPY intent-to-impact-studio/fixtures/experience ./intent-to-impact-studio/fixtures/experience
COPY intent-to-impact-studio/design/tokens ./intent-to-impact-studio/design/tokens
COPY aca/Generate-Example.mjs aca/example-input.json ./aca/
RUN node aca/Generate-Example.mjs --check && cd intent-to-impact-studio/apps/experience && npm run check:studio && npm run typecheck && npm run build

FROM python:3.13-slim-bookworm AS runtime
ARG BICEP_VERSION=0.47.16
ARG BICEP_SHA256=64c345a58e0c3e48b1bc98a4e62d6b3adb1d238281297de3400aeafb2697aa5a
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/app/apps/control-plane STUDIO_MODEL_MODE=simulated \
    HOME=/home/studio
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl libicu72 \
    && groupadd --gid 10001 studio && useradd --uid 10001 --gid studio --create-home studio \
    && test -n "$BICEP_SHA256" \
    && curl --fail --location --retry 3 "https://github.com/Azure/bicep/releases/download/v${BICEP_VERSION}/bicep-linux-x64" -o /usr/local/bin/bicep \
    && echo "${BICEP_SHA256}  /usr/local/bin/bicep" | sha256sum --check \
    && chmod 755 /usr/local/bin/bicep \
    && HOME=/root /usr/local/bin/bicep --version \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY intent-to-impact-studio/apps/control-plane/studio/requirements.txt /tmp/requirements.txt
COPY aca/wheelhouse /tmp/wheelhouse
RUN if ls /tmp/wheelhouse/*.whl >/dev/null 2>&1; then \
      pip install --no-cache-dir --no-index --find-links=/tmp/wheelhouse -r /tmp/requirements.txt; \
    else pip install --no-cache-dir -r /tmp/requirements.txt; fi \
    && rm -rf /tmp/wheelhouse
COPY --chown=studio:studio intent-to-impact-studio/apps/control-plane/studio ./apps/control-plane/studio
COPY --chown=studio:studio aca/example-input.json ./aca/
COPY --from=frontend --chown=studio:studio /app/intent-to-impact-studio/apps/experience/dist ./apps/experience/dist
RUN mkdir -p /app/.intent-to-impact/studio/runs && chown -R studio:studio /app/.intent-to-impact
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "studio.serve"]
