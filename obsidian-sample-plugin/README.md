# Vault Gateway Sync Plugin

Плагин для Obsidian, который:

- авторизуется через `backend/gateway`,
- подписывается на события `modify/create/delete/rename` в vault,
- фильтрует мусор (`.obsidian`, временные и бинарные файлы),
- читает markdown, считает `sha256`,
- отправляет события в gateway с debounce.

## Быстрый старт

1. `npm install`
2. `npm run build`
3. Скопируйте `main.js`, `manifest.json`, `styles.css` в:
   - `<Vault>/.obsidian/plugins/obsidian-sample-plugin/`
4. Включите плагин в Obsidian.

## Настройки плагина

- `Gateway URL` — адрес gateway (например `http://127.0.0.1:8001`)
- `Username` / `Password` — учетные данные auth
- `Enable sync` — включить отправку событий
- `Auto login on load` — логин при старте
- `Debounce (ms)` — задержка отправки событий

## Команды

- `Login to gateway`
- `Logout from gateway`

## Backend контракт

Плагин использует:

- `POST /api/auth/login`
- `POST /api/files/events`

Формат события:

```json
{
  "event_type": "modify",
  "path": "Notes/example.md",
  "content": "# markdown",
  "sha256": "hex",
  "timestamp": "2026-01-01T00:00:00.000Z"
}
```
