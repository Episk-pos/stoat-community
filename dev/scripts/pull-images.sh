#!/usr/bin/env bash
# Pull pre-built backend images from the GitLab container registry.
# This skips the local cargo build, useful for CI and contributors without Rust.
#
# Usage:
#   ./scripts/pull-images.sh                     # latest main build
#   ./scripts/pull-images.sh main-1234567890-abc # specific tag
#
# Environment:
#   STOAT_REGISTRY  Override registry path (default: registry.episkopos.community/episkopos/stoat-backend)
#   STOAT_CLUSTER   KinD cluster name (default: stoat). Set to "" to skip kind load.
#   STOAT_NO_KIND   Set to "1" to skip loading images into KinD (e.g. for Compose mode)
set -euo pipefail

REGISTRY="${STOAT_REGISTRY:-registry.episkopos.community/episkopos/stoat-backend}"
TAG="${1:-latest}"
CLUSTER="${STOAT_CLUSTER:-stoat}"
NO_KIND="${STOAT_NO_KIND:-0}"

# CI image names → local dev image names
declare -A IMAGE_MAP=(
  [api]=delta
  [events]=bonfire
  [file-server]=autumn
  [proxy]=january
)

for ci_name in "${!IMAGE_MAP[@]}"; do
  local_name="${IMAGE_MAP[$ci_name]}"
  src="$REGISTRY/$ci_name:$TAG"
  dst="stoat-$local_name:dev"

  echo "Pulling $ci_name ($TAG) → $dst"
  docker pull "$src"
  docker tag "$src" "$dst"

  if [ "$NO_KIND" != "1" ] && [ -n "$CLUSTER" ] && command -v kind &>/dev/null; then
    kind load docker-image "$dst" --name "$CLUSTER"
  fi
done

if [ "$NO_KIND" != "1" ] && [ -n "$CLUSTER" ] && command -v kind &>/dev/null; then
  echo "All images loaded into KinD cluster '$CLUSTER'."
else
  echo "All images pulled and tagged locally."
fi
