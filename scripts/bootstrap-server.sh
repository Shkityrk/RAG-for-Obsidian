#!/usr/bin/env bash
# One-time setup for Ubuntu 22.04/24.04 on a small VPS.
# Run as root: curl -fsSL ... | bash   OR   sudo bash scripts/bootstrap-server.sh
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/rag-for-obsidian}"
REPO_URL="${REPO_URL:-}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin
fi

if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "${DEPLOY_USER}"
fi
usermod -aG docker "${DEPLOY_USER}"

if ! swapon --show | grep -q '/swapfile'; then
  if [[ ! -f /swapfile ]]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

sysctl -w vm.swappiness=10 >/dev/null
grep -q '^vm.swappiness=' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

mkdir -p "${DEPLOY_PATH}"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_PATH}"

if [[ -n "${REPO_URL}" && ! -d "${DEPLOY_PATH}/.git" ]]; then
  sudo -u "${DEPLOY_USER}" git clone "${REPO_URL}" "${DEPLOY_PATH}"
fi

echo ""
echo "Bootstrap complete."
echo "Next steps:"
echo "  1) Add deploy user's SSH public key to ~${DEPLOY_USER}/.ssh/authorized_keys"
echo "  2) Create ${DEPLOY_PATH}/environment/.env from deploy/env.example"
echo "  3) Add GitHub Secrets (SSH_HOST, SSH_USER, SSH_PRIVATE_KEY, DEPLOY_PATH, DEPLOY_APP_URL)"
echo "  4) Push to main or run workflow_dispatch"
