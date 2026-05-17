# Деплой на VPS через GitHub Actions

Креды сервера **не передавайте в чат**. Используйте GitHub Secrets и SSH-ключ.

## Что уже настроено в репозитории

- `.github/workflows/deploy.yml` — деплой по push в `main`/`master` и вручную (`workflow_dispatch`)
- `docker-compose.prod.yml` — лимиты памяти и только порт `80` наружу
- `scripts/bootstrap-server.sh` — первичная настройка Ubuntu
- `scripts/deploy-remote.sh` — обновление на сервере

## 1. Подготовка сервера (один раз)

Подключитесь по SSH как `root` и выполните:

```bash
apt-get update && apt-get install -y git
git clone https://github.com/YOUR_USER/RAG-for-Obsidian.git /opt/rag-for-obsidian
cd /opt/rag-for-obsidian
sudo DEPLOY_USER=deploy DEPLOY_PATH=/opt/rag-for-obsidian bash scripts/bootstrap-server.sh
```

Создайте `.env` на сервере:

```bash
sudo -u deploy mkdir -p /opt/rag-for-Obsidian/environment
sudo -u deploy cp /opt/rag-for-Obsidian/deploy/env.example /opt/rag-for-Obsidian/environment/.env
sudo -u deploy nano /opt/rag-for-Obsidian/environment/.env
```

В `ORIGIN_URLS` укажите IP или домен сервера.

## 2. SSH-ключ для GitHub Actions

На своём ПК:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./gha_deploy -N ""
```

На сервере (под пользователем `deploy`):

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys   # вставьте содержимое gha_deploy.pub
chmod 600 ~/.ssh/authorized_keys
```

Приватный ключ `gha_deploy` добавьте в GitHub Secrets.

## 3. Deploy key для `git pull` на сервере

На сервере под `deploy`:

```bash
ssh-keygen -t ed25519 -C "server-deploy-key" -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub
```

Добавьте этот публичный ключ в репозиторий GitHub: **Settings → Deploy keys → Add deploy key** (read-only).

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

Если репозиторий приватный, клонируйте через SSH:

```bash
git clone git@github.com:YOUR_USER/RAG-for-Obsidian.git /opt/rag-for-obsidian
```

## 4. GitHub Secrets

В репозитории: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Пример |
|--------|--------|
| `SSH_HOST` | `203.0.113.10` |
| `SSH_USER` | `deploy` |
| `SSH_PRIVATE_KEY` | содержимое `gha_deploy` (приватный ключ) |
| `SSH_PORT` | `22` (опционально) |
| `DEPLOY_PATH` | `/opt/rag-for-Obsidian` |
| `DEPLOY_APP_URL` | `http://203.0.113.10` или `https://your.domain` |

`DEPLOY_APP_URL` попадает в сборку UI (`VITE_API_BASE_URL`).

## 5. Первый и последующие деплои

Первый раз на сервере:

```bash
sudo -u deploy bash /opt/rag-for-Obsidian/scripts/deploy-remote.sh
```

Дальше — push в `main` или **Actions → Deploy to server → Run workflow**.

## Ограничения VPS 1 CPU / 2 GB

- Включён swap 2 GB (bootstrap)
- Сервисы с лимитами памяти в `docker-compose.prod.yml`
- Первый `docker compose build` может занять 15–25 минут

## Проверка

```bash
curl http://YOUR_SERVER_IP/api/healthcheck
```
