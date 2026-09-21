FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY contracts/package.json contracts/package-lock.json ./contracts/
RUN npm ci --prefix contracts --ignore-scripts
COPY apps/experience/package.json apps/experience/package-lock.json ./apps/experience/
RUN npm ci --prefix apps/experience
COPY apps/experience ./apps/experience
COPY apps/control-plane/studio/studio.schema.json ./apps/control-plane/studio/studio.schema.json
COPY contracts/generated ./contracts/generated
COPY contracts/schemas ./contracts/schemas
COPY fixtures/experience ./fixtures/experience
COPY design/tokens ./design/tokens
COPY aca/Generate-Example.mjs aca/example-input.json ./aca/
RUN node aca/Generate-Example.mjs --check && cd apps/experience && npm run check:studio && npm run typecheck && npm run build

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
COPY apps/control-plane/studio/requirements.txt /tmp/requirements.txt
COPY aca/wheelhouse /tmp/wheelhouse
RUN if ls /tmp/wheelhouse/*.whl >/dev/null 2>&1; then \
      pip install --no-cache-dir --no-index --find-links=/tmp/wheelhouse -r /tmp/requirements.txt; \
    else pip install --no-cache-dir -r /tmp/requirements.txt; fi \
    && rm -rf /tmp/wheelhouse
COPY --chown=studio:studio apps/control-plane/studio ./apps/control-plane/studio
COPY --chown=studio:studio aca/simulator.py aca/example-input.json ./aca/
COPY --from=frontend --chown=studio:studio /app/apps/experience/dist ./apps/experience/dist
RUN mkdir -p /app/.intent-to-impact/studio/runs && chown -R studio:studio /app/.intent-to-impact
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "studio.serve"]
