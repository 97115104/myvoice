#!/usr/bin/env bash
# deploy-locally.sh
# One-shot launcher for My Voice on this machine.
# - Builds the Docker image (Python 3.11 + ffmpeg + TTS deps) if missing
# - Starts/reuses a container exposing http://localhost:5123
# - Persists the XTTS model + HF cache across restarts (no re-download)
# - Persists generated/output audio under ./output
# - Waits for the server to be healthy, then opens the UI in your browser
#
# Usage:
#   ./deploy-locally.sh           # start (builds if needed) + open browser
#   ./deploy-locally.sh --rebuild # force rebuild of the image
#   ./deploy-locally.sh --logs    # tail container logs
#   ./deploy-locally.sh --stop    # stop and remove the container
#   ./deploy-locally.sh --status  # show container status

set -euo pipefail

IMAGE_NAME="myvoice-app"
CONTAINER_NAME="myvoice"
HOST_PORT="${MYVOICE_PORT:-5123}"
URL="http://localhost:${HOST_PORT}/ui"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Persistent caches: keep the ~2GB XTTS download outside the container
CACHE_DIR="${SCRIPT_DIR}/.cache"
HF_CACHE="${CACHE_DIR}/huggingface"
TTS_CACHE="${CACHE_DIR}/tts"
OUTPUT_DIR="${SCRIPT_DIR}/output"
mkdir -p "$HF_CACHE" "$TTS_CACHE" "$OUTPUT_DIR"

color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
info()  { color "1;34" "▶ $*"; }
ok()    { color "1;32" "✓ $*"; }
warn()  { color "1;33" "! $*"; }
err()   { color "1;31" "✗ $*"; }

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    err "docker is required but not installed. Install it from https://docs.docker.com/engine/install/"
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    err "Cannot talk to the Docker daemon. Is it running? Try: sudo systemctl start docker"
    exit 1
  fi
}

image_exists() { docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; }
container_exists() { docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; }
container_running() { docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; }

build_image() {
  info "Building Docker image '$IMAGE_NAME' (first build downloads ~2GB of ML deps)..."
  docker build -t "$IMAGE_NAME" .
  ok   "Image built."
}

stop_container() {
  if container_exists; then
    info "Stopping & removing container '$CONTAINER_NAME'..."
    docker rm -f "$CONTAINER_NAME" >/dev/null
    ok "Container removed."
  else
    warn "No container named '$CONTAINER_NAME' to stop."
  fi
}

start_container() {
  if container_running; then
    ok "Container '$CONTAINER_NAME' already running."
    return
  fi
  if container_exists; then
    info "Starting existing container '$CONTAINER_NAME'..."
    docker start "$CONTAINER_NAME" >/dev/null
  else
    info "Launching new container '$CONTAINER_NAME' on port $HOST_PORT..."
    # GPU passthrough: enable if 'nvidia' runtime is available
    GPU_FLAG=()
    if docker info 2>/dev/null | grep -qi 'Runtimes:.*nvidia'; then
      GPU_FLAG=(--gpus all)
      info "NVIDIA runtime detected — enabling GPU passthrough."
    fi
    docker run -d \
      --name "$CONTAINER_NAME" \
      --restart unless-stopped \
      -p "${HOST_PORT}:5123" \
      -v "${HF_CACHE}:/root/.cache/huggingface" \
      -v "${TTS_CACHE}:/root/.local/share/tts" \
      -v "${OUTPUT_DIR}:/app/output" \
      "${GPU_FLAG[@]}" \
      "$IMAGE_NAME" >/dev/null
  fi
  ok "Container is up."
}

wait_for_health() {
  info "Waiting for the server at $URL ..."
  info "(First run will download the XTTS v2 model — this can take several minutes.)"
  local tries=0
  local max_tries=600   # ~20 minutes max for first-run model download
  while (( tries < max_tries )); do
    if curl -fsS "http://localhost:${HOST_PORT}/api/health" >/dev/null 2>&1; then
      ok "Server is healthy."
      return 0
    fi
    if ! container_running; then
      err "Container exited unexpectedly. Recent logs:"
      docker logs --tail 80 "$CONTAINER_NAME" || true
      exit 1
    fi
    sleep 2
    ((tries++))
    if (( tries % 15 == 0 )); then
      info "Still loading... (recent logs)"
      docker logs --tail 5 "$CONTAINER_NAME" 2>&1 | sed 's/^/   | /' || true
    fi
  done
  err "Server did not become healthy in time. Check: $0 --logs"
  exit 1
}

open_browser() {
  info "Opening $URL in your browser..."
  if command -v xdg-open >/dev/null 2>&1; then
    (xdg-open "$URL" >/dev/null 2>&1 &) || true
  elif command -v open >/dev/null 2>&1; then
    (open "$URL" >/dev/null 2>&1 &) || true
  else
    warn "Could not auto-open a browser. Visit: $URL"
  fi
}

usage() {
  sed -n '2,18p' "$0"
}

case "${1:-}" in
  --stop)    require_docker; stop_container; exit 0 ;;
  --logs)    require_docker; docker logs -f "$CONTAINER_NAME" ;;
  --status)  require_docker; docker ps -a --filter "name=^/${CONTAINER_NAME}$"; exit 0 ;;
  --rebuild) require_docker; stop_container; docker image rm -f "$IMAGE_NAME" >/dev/null 2>&1 || true ;;
  -h|--help) usage; exit 0 ;;
  "" )       : ;;
  * )        err "Unknown option: $1"; usage; exit 2 ;;
esac

require_docker
image_exists || build_image
start_container
wait_for_health
open_browser

cat <<EOF

$(color "1;32" "My Voice is running!")
   UI:        $URL
   Batch UI:  http://localhost:${HOST_PORT}/batch
   API:       http://localhost:${HOST_PORT}/api/health

Useful:
   ./deploy-locally.sh --logs      # follow server logs
   ./deploy-locally.sh --stop      # stop the server
   ./deploy-locally.sh --rebuild   # rebuild image and restart

Generated audio is saved to: ${OUTPUT_DIR}
EOF
