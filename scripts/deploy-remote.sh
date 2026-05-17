#!/usr/bin/env bash
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/opt/RAG-for-Obsidian}"
DEPLOY_APP_URL="${DEPLOY_APP_URL:-http://localhost}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

cd "${DEPLOY_PATH}"

if [[ ! -f environment/.env ]]; then
  echo "Missing ${DEPLOY_PATH}/environment/.env"
  echo "Copy deploy/env.example to environment/.env and fill secrets first."
  exit 1
fi

git fetch origin "${DEPLOY_BRANCH}"
git reset --hard "origin/${DEPLOY_BRANCH}"

export VITE_API_BASE_URL="${DEPLOY_APP_URL}"

echo "Building frontend..."
${COMPOSE} build ui
${COMPOSE} run --rm ui npm run build

echo "Building and starting services..."
${COMPOSE} up -d --build --remove-orphans

echo "Pruning unused images..."
docker image prune -f

echo "Deploy finished. App URL: ${DEPLOY_APP_URL}"
