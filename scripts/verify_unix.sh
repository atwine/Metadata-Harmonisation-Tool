#!/usr/bin/env bash
set -euo pipefail

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[ERROR] $*"; exit 1; }

# 1) Verify Docker daemon
if ! docker info >/dev/null 2>&1; then
  fail "Docker does not appear to be running. Start Docker Desktop or your daemon and retry."
fi
info "Docker is running: $(docker --version)"

# 2) Determine Ollama endpoint (host by default)
OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://localhost:11434}
info "Using OLLAMA_BASE_URL=${OLLAMA_BASE_URL}"

# 3) Check Ollama reachability
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${OLLAMA_BASE_URL}/api/tags" || true)
if [[ "$http_code" != "200" ]]; then
  warn "Ollama not reachable at ${OLLAMA_BASE_URL} (HTTP ${http_code}). If running in Docker, consider http://host.docker.internal:11434."
else
  info "Ollama reachable (HTTP 200)."
fi

# 4) Check app container health (if running)
APP_NAME=${APP_NAME:-metadata-harmonisation-tool}
container_id=$(docker ps --filter "name=${APP_NAME}" --format '{{.ID}}')
if [[ -n "$container_id" ]]; then
  info "App container detected: ${APP_NAME} (${container_id})"
  # Try host health endpoint
  app_http=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/_stcore/health || true)
  if [[ "$app_http" == "200" ]]; then
    info "App health endpoint reachable on http://localhost:8501/_stcore/health"
  else
    warn "App health endpoint not reachable on host (HTTP ${app_http}). Checking container Health state..."
    docker inspect -f '{{json .State.Health}}' "$container_id" || true
  fi
else
  warn "No running container named '${APP_NAME}' found. If you expect it running, use docker ps to verify."
fi

info "Verification complete."
