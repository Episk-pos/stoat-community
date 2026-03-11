#!/usr/bin/env bash
# Pull pre-built backend images from the GitLab registry and load into KinD.
# This skips the local cargo build, useful for CI and contributors without Rust.
#
# Usage:
#   ./scripts/pull-images.sh                     # latest main build
#   ./scripts/pull-images.sh main-1234567890-abc # specific tag
set -euo pipefail

REGISTRY="${STOAT_REGISTRY:-work.episkopos.community:5050/episkopos/stoat-backend}"
TAG="${1:-latest}"
CLUSTER="${STOAT_CLUSTER:-stoat}"

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
  kind load docker-image "$dst" --name "$CLUSTER"
done

echo "All images loaded into KinD cluster '$CLUSTER'."
