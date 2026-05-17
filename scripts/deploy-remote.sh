#!/usr/bin/env bash
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/opt/RAG-for-Obsidian}"
DEPLOY_APP_URL="${DEPLOY_APP_URL:-http://localhost}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
SKIP_UI_BUILD="${SKIP_UI_BUILD:-false}"
BUILD_UI_ON_SERVER="${BUILD_UI_ON_SERVER:-false}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

has_frontend_dist() {
  [[ -f client/ui/dist/index.html ]]
}

cd "${DEPLOY_PATH}"

if [[ ! -f environment/.env ]]; then
  echo "Missing ${DEPLOY_PATH}/environment/.env"
  echo "Copy deploy/env.example to environment/.env and fill secrets first."
  exit 1
fi

if ! has_frontend_dist; then
  echo "WARN: dist missing before git pull"
fi

git fetch origin "${DEPLOY_BRANCH}"
git reset --hard "origin/${DEPLOY_BRANCH}"

export VITE_API_BASE_URL="${DEPLOY_APP_URL}"

build_ui_on_server() {
  echo "Building frontend on server (needs ~1.5 GB free RAM + swap)..."
  export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=1536}"
  ${COMPOSE} --profile ui-build build ui
  ${COMPOSE} --profile ui-build run --rm -e NODE_OPTIONS="${NODE_OPTIONS}" ui npm run build
}

if [[ "${BUILD_UI_ON_SERVER}" == "true" ]]; then
  build_ui_on_server
elif has_frontend_dist; then
  echo "Frontend: using existing client/ui/dist (skip server build)."
elif [[ "${SKIP_UI_BUILD}" == "true" ]]; then
  echo "ERROR: SKIP_UI_BUILD=true but client/ui/dist/index.html is missing."
  echo "Run GitHub Actions deploy (builds UI in CI) or upload dist manually."
  exit 1
else
  echo "WARN: No dist found — trying server build (may OOM on 2 GB VPS)."
  build_ui_on_server
fi

echo "Building and starting services..."
${COMPOSE} up -d --build --remove-orphans

echo "Pruning unused images..."
docker image prune -f

echo "Deploy finished. App URL: ${DEPLOY_APP_URL}"
