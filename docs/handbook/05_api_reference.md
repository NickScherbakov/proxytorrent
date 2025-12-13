# 5. Справочник API

## Цель главы

Полное описание всех REST API эндпоинтов ProxyTorrent с примерами запросов, ответов и обработкой ошибок.

## Базовый URL

```
http://localhost:8000
```

Для продакшена замените на ваш домен, например `https://api.proxytorrent.example.com`.

## Версионирование API

Текущая версия: **v1**

Все эндпоинты начинаются с `/v1/`.

## Аутентификация

ProxyTorrent поддерживает два метода аутентификации:

### 1. HMAC-SHA256 Signature (рекомендуется)

**Header:** `X-Signature`

**Вычисление подписи:**
```python
import hmac
import hashlib
import json

secret = "your-hmac-secret"
payload = {"url": "http://example.com", "method": "GET", "ttl": 3600}
body = json.dumps(payload)

signature = hmac.new(
    secret.encode(),
    body.encode(),
    hashlib.sha256
).hexdigest()
```

**Пример запроса:**
```bash
BODY='{"url":"http://example.com","method":"GET","ttl":3600}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "your-secret" | cut -d' ' -f2)

curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

### 2. Bearer Token

**Header:** `Authorization: Bearer <token>`

**Пример:**
```bash
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token-here" \
  -d '{"url":"http://example.com","method":"GET","ttl":3600}'
```

### Отключение аутентификации (только для разработки)

```bash
# В .env или docker-compose.yml
SECURITY__AUTH_ENABLED=false
```

## Эндпоинты

### 1. POST /v1/requests — Создать fetch-запрос

Создаёт новый запрос на загрузку контента через прокси и упаковку в торрент.

**Request:**
```http
POST /v1/requests HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-Signature: <hmac-signature>

{
  "url": "http://example.com",
  "method": "GET",
  "headers": {
    "User-Agent": "Custom-Agent/1.0"
  },
  "body": null,
  "ttl": 3600
}
```

**Parameters:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `url` | string | Да | URL для загрузки (http/https) |
| `method` | string | Да | HTTP метод: GET, POST, PUT, DELETE, PATCH |
| `headers` | object | Нет | Дополнительные HTTP заголовки |
| `body` | string | Нет | Тело запроса (для POST/PUT) |
| `ttl` | integer | Да | TTL в секундах (время жизни кеша) |

**Response 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_ready": 60,
  "created_at": "2025-12-13T10:00:00Z"
}
```

**Response 401 Unauthorized:**
```json
{
  "detail": "Authentication required"
}
```

**Response 422 Unprocessable Entity:**
```json
{
  "detail": [
    {
      "loc": ["body", "url"],
      "msg": "invalid or missing URL scheme",
      "type": "value_error"
    }
  ]
}
```

**Response 429 Too Many Requests:**
```json
{
  "detail": "Rate limit exceeded. Try again later."
}
```

**Примеры:**

```bash
# GET запрос
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://httpbin.org/html",
    "method": "GET",
    "ttl": 3600
  }'

# POST запрос с телом
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://httpbin.org/post",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "body": "{\"key\": \"value\"}",
    "ttl": 3600
  }'

# С кастомными headers
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://httpbin.org/user-agent",
    "method": "GET",
    "headers": {
      "User-Agent": "ProxyTorrent-Client/1.0",
      "Accept-Language": "en-US"
    },
    "ttl": 7200
  }'
```

### 2. GET /v1/requests/{id} — Получить статус запроса

Возвращает текущий статус и метаданные запроса.

**Request:**
```http
GET /v1/requests/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: localhost:8000
X-Signature: <hmac-signature>
```

**Response 200 (queued/processing):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "fetching",
  "url": "http://example.com",
  "method": "GET",
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T10:00:15Z",
  "completed_at": null,
  "infohash": null,
  "content_hash": null,
  "content_size": null,
  "content_type": null,
  "progress": 20,
  "error_message": null
}
```

**Response 200 (ready):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "url": "http://example.com",
  "method": "GET",
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T10:01:30Z",
  "completed_at": "2025-12-13T10:01:30Z",
  "infohash": "abcdef1234567890abcdef1234567890abcdef12",
  "content_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "content_size": 12345,
  "content_type": "text/html",
  "progress": 100,
  "error_message": null
}
```

**Response 404 Not Found:**
```json
{
  "detail": "Request not found"
}
```

**Статусы запроса:**

| Статус | Описание | Progress |
|--------|----------|----------|
| `queued` | В очереди на обработку | 0 |
| `fetching` | Загрузка контента через прокси | 10-40 |
| `packaging` | Создание торрента | 50-70 |
| `seeding` | Добавление в seeder | 80-90 |
| `ready` | Торрент готов к скачиванию | 100 |
| `failed` | Ошибка при обработке | — |
| `cancelled` | Отменён пользователем | — |

**Пример:**
```bash
REQUEST_ID="550e8400-e29b-41d4-a716-446655440000"

# Получить статус
curl http://localhost:8000/v1/requests/$REQUEST_ID | jq .

# Polling до готовности
while true; do
  STATUS=$(curl -s http://localhost:8000/v1/requests/$REQUEST_ID | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "ready" ] && break
  sleep 5
done
```

### 3. GET /v1/requests/{id}/torrent — Скачать .torrent файл

Скачивает готовый .torrent файл для запроса со статусом `ready`.

**Request:**
```http
GET /v1/requests/550e8400-e29b-41d4-a716-446655440000/torrent HTTP/1.1
Host: localhost:8000
X-Signature: <hmac-signature>
```

**Response 200:**
```
Content-Type: application/x-bittorrent
Content-Disposition: attachment; filename="content.torrent"

<binary .torrent file>
```

**Response 404 Not Found:**
```json
{
  "detail": "Request not found"
}
```

**Response 400 Bad Request:**
```json
{
  "detail": "Torrent not ready yet"
}
```

**Пример:**
```bash
REQUEST_ID="550e8400-e29b-41d4-a716-446655440000"

# Скачать торрент
curl http://localhost:8000/v1/requests/$REQUEST_ID/torrent -o downloaded.torrent

# Проверить файл
file downloaded.torrent
# Ожидается: downloaded.torrent: BitTorrent file

# Посмотреть инфо о торренте (если установлен transmission-cli)
transmission-show downloaded.torrent
```

### 4. GET /v1/requests/{id}/magnet — Получить magnet ссылку

Возвращает magnet URI для торрента.

**Request:**
```http
GET /v1/requests/550e8400-e29b-41d4-a716-446655440000/magnet HTTP/1.1
Host: localhost:8000
X-Signature: <hmac-signature>
```

**Response 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "magnet_link": "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
  "infohash": "abcdef1234567890abcdef1234567890abcdef12"
}
```

**Response 404 Not Found:**
```json
{
  "detail": "Request not found"
}
```

**Response 400 Bad Request:**
```json
{
  "detail": "Torrent not ready yet"
}
```

**Пример:**
```bash
REQUEST_ID="550e8400-e29b-41d4-a716-446655440000"

# Получить magnet link
MAGNET=$(curl -s http://localhost:8000/v1/requests/$REQUEST_ID/magnet | jq -r '.magnet_link')
echo "$MAGNET"

# Открыть в торрент-клиенте
transmission-remote -a "$MAGNET"
# или
qbittorrent "$MAGNET"
```

### 5. DELETE /v1/requests/{id} — Отменить запрос

Отменяет обработку запроса (если он ещё не завершён).

**Request:**
```http
DELETE /v1/requests/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: localhost:8000
X-Signature: <hmac-signature>
```

**Response 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled"
}
```

**Response 404 Not Found:**
```json
{
  "detail": "Request not found"
}
```

**Response 400 Bad Request:**
```json
{
  "detail": "Cannot cancel completed request"
}
```

**Пример:**
```bash
REQUEST_ID="550e8400-e29b-41d4-a716-446655440000"

# Отменить запрос
curl -X DELETE http://localhost:8000/v1/requests/$REQUEST_ID

# Проверить статус
curl http://localhost:8000/v1/requests/$REQUEST_ID | jq .status
# Ожидается: "cancelled"
```

### 6. GET /v1/health — Health Check

Проверяет состояние сервиса и его компонентов.

**Request:**
```http
GET /v1/health HTTP/1.1
Host: localhost:8000
```

**Аутентификация не требуется.**

**Response 200 (healthy):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime": 3600.5,
  "checks": {
    "database": {
      "status": "healthy"
    },
    "storage": {
      "status": "healthy"
    },
    "task_queue": {
      "status": "healthy",
      "queue_size": 3
    }
  }
}
```

**Response 503 Service Unavailable (degraded):**
```json
{
  "status": "degraded",
  "version": "0.1.0",
  "uptime": 3600.5,
  "checks": {
    "database": {
      "status": "unhealthy",
      "error": "Connection timeout"
    },
    "storage": {
      "status": "healthy"
    },
    "task_queue": {
      "status": "healthy",
      "queue_size": 0
    }
  }
}
```

**Пример:**
```bash
# Проверка здоровья
curl http://localhost:8000/v1/health | jq .

# Мониторинг каждые 10 секунд
watch -n 10 'curl -s http://localhost:8000/v1/health | jq .'

# Использование в health check скриптах
#!/bin/bash
STATUS=$(curl -s http://localhost:8000/v1/health | jq -r '.status')
if [ "$STATUS" != "healthy" ]; then
  echo "Service unhealthy!"
  exit 1
fi
```

### 7. GET / — Root endpoint

Информация о сервисе.

**Request:**
```http
GET / HTTP/1.1
Host: localhost:8000
```

**Response 200:**
```json
{
  "service": "ProxyTorrent",
  "version": "0.1.0",
  "docs": "/v1/docs"
}
```

### 8. GET /docs — OpenAPI Documentation (Swagger UI)

Интерактивная документация API.

**URL:** `http://localhost:8000/docs`

Открывается в браузере, позволяет:
- Просмотреть все эндпоинты
- Посмотреть схемы запросов/ответов
- Протестировать API прямо в браузере

## Схемы данных (Pydantic Models)

### CreateRequestPayload

```python
{
  "url": str,              # Обязательно, HTTP(S) URL
  "method": str,           # Обязательно, GET|POST|PUT|DELETE|PATCH
  "headers": dict | None,  # Опционально, доп. заголовки
  "body": str | None,      # Опционально, тело запроса
  "ttl": int               # Обязательно, TTL в секундах (> 0)
}
```

### RequestResponse

```python
{
  "id": str,               # UUID запроса
  "status": str,           # queued|fetching|packaging|seeding|ready|failed|cancelled
  "estimated_ready": int   # Примерное время до готовности (секунды)
  "created_at": datetime   # ISO 8601
}
```

### RequestStatusResponse

```python
{
  "id": str,
  "status": str,
  "url": str,
  "method": str,
  "created_at": datetime,
  "updated_at": datetime,
  "completed_at": datetime | None,
  "infohash": str | None,
  "content_hash": str | None,
  "content_size": int | None,
  "content_type": str | None,
  "progress": int,          # 0-100
  "error_message": str | None
}
```

### MagnetLinkResponse

```python
{
  "id": str,
  "magnet_link": str,       # magnet:?xt=urn:btih:...
  "infohash": str
}
```

### HealthResponse

```python
{
  "status": str,            # healthy|degraded|unhealthy
  "version": str,
  "uptime": float,          # Секунды с момента запуска
  "checks": {
    "database": {
      "status": str,
      "error": str | None
    },
    "storage": {
      "status": str,
      "error": str | None
    },
    "task_queue": {
      "status": str,
      "queue_size": int,
      "error": str | None
    }
  }
}
```

## Обработка ошибок

### HTTP коды ответов

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 400 | Неверный запрос (например, торрент не готов) |
| 401 | Не авторизован (неверная подпись/токен) |
| 404 | Запрос не найден |
| 422 | Ошибка валидации (неверные параметры) |
| 429 | Превышен rate limit |
| 500 | Внутренняя ошибка сервера |
| 503 | Сервис недоступен |

### Формат ошибок

```json
{
  "detail": "Описание ошибки"
}
```

или для ошибок валидации:

```json
{
  "detail": [
    {
      "loc": ["body", "url"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Rate Limiting

### Лимиты по умолчанию

- **Per user**: 60 requests/minute, 1000 requests/hour
- **Per IP**: 100 requests/minute

### Headers при превышении

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1670923200
Retry-After: 60
```

### Настройка лимитов

```bash
# В .env
RATE_LIMIT__REQUESTS_PER_MINUTE=120
RATE_LIMIT__REQUESTS_PER_HOUR=5000
RATE_LIMIT__REQUESTS_PER_IP_MINUTE=200
```

## Примеры использования

### Python Client

```python
#!/usr/bin/env python3
import requests
import hmac
import hashlib
import json
import time

BASE_URL = "http://localhost:8000"
HMAC_SECRET = "your-secret"

def sign_request(body: str) -> str:
    return hmac.new(
        HMAC_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

# Создать запрос
payload = {"url": "http://httpbin.org/html", "method": "GET", "ttl": 3600}
body = json.dumps(payload)
signature = sign_request(body)

response = requests.post(
    f"{BASE_URL}/v1/requests",
    headers={
        "Content-Type": "application/json",
        "X-Signature": signature
    },
    data=body
)
request_id = response.json()["id"]
print(f"Request ID: {request_id}")

# Ждать готовности
while True:
    status_response = requests.get(f"{BASE_URL}/v1/requests/{request_id}")
    status = status_response.json()["status"]
    print(f"Status: {status}")
    
    if status == "ready":
        break
    elif status == "failed":
        print("Request failed!")
        exit(1)
    
    time.sleep(5)

# Скачать торрент
torrent_response = requests.get(f"{BASE_URL}/v1/requests/{request_id}/torrent")
with open("downloaded.torrent", "wb") as f:
    f.write(torrent_response.content)

print("Done! Torrent saved to downloaded.torrent")
```

### Bash Script

См. [examples/curl_example.sh](../../examples/curl_example.sh)

## Источники в коде

- **API Endpoints**: `src/app/api/requests.py`, `src/app/api/health.py`
- **Schemas**: `src/app/models/schemas.py`
- **Auth**: `src/app/api/auth.py`
- **Rate Limit**: `src/app/api/ratelimit.py`

## Проверка/валидация

```bash
# Проверить все эндпоинты
curl http://localhost:8000/v1/health
curl -X POST http://localhost:8000/v1/requests -H "Content-Type: application/json" -d '{"url":"http://httpbin.org/html","method":"GET","ttl":3600}'
REQUEST_ID=<id из ответа>
curl http://localhost:8000/v1/requests/$REQUEST_ID
curl http://localhost:8000/v1/requests/$REQUEST_ID/magnet
curl http://localhost:8000/v1/requests/$REQUEST_ID/torrent -o test.torrent
curl -X DELETE http://localhost:8000/v1/requests/$REQUEST_ID

# Проверить OpenAPI документацию
curl http://localhost:8000/openapi.json | jq .
# Открыть в браузере: http://localhost:8000/docs
```

## Связанные главы

- [Жизненный цикл запроса](./04_request_lifecycle.md) — как обрабатываются запросы
- [Конфигурация](./06_configuration_reference.md) — настройка аутентификации и лимитов
- [Безопасность](./08_security_model.md) — HMAC подписи и защита
- [Примеры](../../examples/) — готовые скрипты для работы с API
