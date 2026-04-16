#!/bin/bash
set -e

# Mirror Docker Hub infrastructure images to GitLab Container Registry
# to avoid rate limits in CI.
#
# Usage:
#   ./dev/scripts/mirror-infra-images.sh
#
# Prerequisites:
#   - Docker running locally
#   - Logged into GitLab registry: docker login registry.episkopos.community

REGISTRY="registry.episkopos.community/episkopos/community"

echo "=== Mirroring infrastructure images to GitLab registry ==="
echo "Target: $REGISTRY"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker daemon not running"
  exit 1
fi

# Images to mirror: source → tag
declare -A IMAGES=(
  ["eqalpha/keydb:latest"]="keydb:latest"
  ["mongo:8"]="mongo:8"
  ["rabbitmq:4-management"]="rabbitmq:4-management"
  ["maildev/maildev:latest"]="maildev:latest"
  ["minio/minio:latest"]="minio:latest"
  ["minio/mc:latest"]="mc:latest"
  ["postgres:17-alpine"]="postgres:17-alpine"
)

for src in "${!IMAGES[@]}"; do
  dst="${IMAGES[$src]}"
  echo "Mirroring $src → $REGISTRY/$dst"
  docker pull "$src"
  docker tag "$src" "$REGISTRY/$dst"
  docker push "$REGISTRY/$dst"
  echo "✓ Done"
  echo ""
done

echo "=== All images mirrored ==="
echo ""
echo "Available at:"
for dst in "${IMAGES[@]}"; do
  echo "  - $REGISTRY/$dst"
done
