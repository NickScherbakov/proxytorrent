# 6. Справочник конфигурации

## Цель главы

Полное описание всех переменных окружения ProxyTorrent, их назначение, допустимые значения и примеры использования.

## Источник конфигурации

Конфигурация загружается из:
1. Файла `.env` (если существует)
2. Переменных окружения системы
3. Значений по умолчанию (в `src/app/core/config.py`)

**Приоритет:** переменные окружения > `.env` > значения по умолчанию

## Синтаксис именования

ProxyTorrent использует **вложенную структуру** с разделителем `__`:

```bash
# Формат: СЕКЦИЯ__ПАРАМЕТР
SECURITY__AUTH_ENABLED=true
PROXY__PROXY_HOST=localhost
FETCHER__MAX_SIZE=52428800
```

Это соответствует структуре в `config.py`:
```python
class Settings:
    security: SecuritySettings  # SECURITY__*
    proxy: ProxySettings        # PROXY__*
    fetcher: FetcherSettings    # FETCHER__*
    # и т.д.
```

## Создание конфигурационного файла

```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать
nano .env

# Установить права доступа
chmod 600 .env
```

---

## Группы настроек

### 1. Security Settings (SECURITY__*)

Настройки безопасности и аутентификации.

#### SECURITY__AUTH_ENABLED

**Назначение:** Включить/выключить аутентификацию

**Тип:** boolean  
**По умолчанию:** `true`  
**Допустимые значения:** `true`, `false`

```bash
SECURITY__AUTH_ENABLED=true   # Продакшен
SECURITY__AUTH_ENABLED=false  # Только для разработки!
```

**⚠️ ВАЖНО:** Всегда используйте `true` в продакшене!

#### SECURITY__HMAC_SECRET

**Назначение:** Секретный ключ для HMAC-SHA256 подписей

**Тип:** string  
**По умолчанию:** случайная строка (генерируется автоматически)  
**Рекомендация:** 32+ байта

```bash
# Генерация безопасного секрета
SECURITY__HMAC_SECRET=$(openssl rand -hex 32)

# Пример
SECURITY__HMAC_SECRET=a1b2c3d4e5f6...
```

**⚠️ ВАЖНО:** 
- Храните секрет в безопасности
- Не коммитьте в Git
- Меняйте регулярно

#### SECURITY__BEARER_TOKENS

**Назначение:** Список валидных Bearer токенов (через запятую)

**Тип:** string (comma-separated)  
**По умолчанию:** пусто  
**Опционально**

```bash
SECURITY__BEARER_TOKENS=token1,token2,secret-token-xyz
```

**Использование:**
```bash
curl -H "Authorization: Bearer token1" http://localhost:8000/v1/requests
```

---

### 2. Proxy Settings (PROXY__*)

Настройки прокси/VPN для изоляции сетевого трафика.

#### PROXY__PROXY_ENABLED

**Назначение:** Принудительное использование прокси для всех запросов

**Тип:** boolean  
**По умолчанию:** `true`  
**Допустимые значения:** `true`, `false`

```bash
PROXY__PROXY_ENABLED=true   # Все запросы через прокси (рекомендуется)
PROXY__PROXY_ENABLED=false  # Прямое подключение (небезопасно!)
```

#### PROXY__PROXY_TYPE

**Назначение:** Тип прокси-сервера

**Тип:** string  
**По умолчанию:** `socks5`  
**Допустимые значения:** `http`, `https`, `socks5`

```bash
PROXY__PROXY_TYPE=socks5  # Рекомендуется для VPN
PROXY__PROXY_TYPE=http    # HTTP прокси
PROXY__PROXY_TYPE=https   # HTTPS прокси
```

#### PROXY__PROXY_HOST

**Назначение:** Хост прокси-сервера

**Тип:** string  
**По умолчанию:** `null`  
**Обязательно:** если `PROXY_ENABLED=true`

```bash
PROXY__PROXY_HOST=vpn-gateway.example.com
PROXY__PROXY_HOST=127.0.0.1
PROXY__PROXY_HOST=10.8.0.1
```

#### PROXY__PROXY_PORT

**Назначение:** Порт прокси-сервера

**Тип:** integer  
**По умолчанию:** `null`  
**Обязательно:** если `PROXY_ENABLED=true`

```bash
PROXY__PROXY_PORT=1080   # SOCKS5
PROXY__PROXY_PORT=8080   # HTTP/HTTPS
PROXY__PROXY_PORT=3128   # Squid proxy
```

#### PROXY__PROXY_USERNAME

**Назначение:** Имя пользователя для аутентификации на прокси

**Тип:** string  
**По умолчанию:** `null`  
**Опционально**

```bash
PROXY__PROXY_USERNAME=proxyuser
```

#### PROXY__PROXY_PASSWORD

**Назначение:** Пароль для аутентификации на прокси

**Тип:** string  
**По умолчанию:** `null`  
**Опционально**

```bash
PROXY__PROXY_PASSWORD=securepassword123
```

**Пример полной конфигурации прокси:**
```bash
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=vpn.example.com
PROXY__PROXY_PORT=1080
PROXY__PROXY_USERNAME=user
PROXY__PROXY_PASSWORD=pass
```

---

### 3. Fetcher Settings (FETCHER__*)

Настройки HTTP-клиента для загрузки контента.

#### FETCHER__CONNECT_TIMEOUT

**Назначение:** Таймаут подключения к серверу (секунды)

**Тип:** integer  
**По умолчанию:** `10`  
**Диапазон:** 1-300

```bash
FETCHER__CONNECT_TIMEOUT=10  # По умолчанию
FETCHER__CONNECT_TIMEOUT=30  # Для медленных соединений
```

#### FETCHER__READ_TIMEOUT

**Назначение:** Таймаут чтения ответа (секунды)

**Тип:** integer  
**По умолчанию:** `30`  
**Диапазон:** 1-600

```bash
FETCHER__READ_TIMEOUT=30   # По умолчанию
FETCHER__READ_TIMEOUT=300  # Для больших файлов (5 минут)
```

#### FETCHER__MAX_SIZE

**Назначение:** Максимальный размер ответа в байтах

**Тип:** integer  
**По умолчанию:** `52428800` (50 МБ)

```bash
FETCHER__MAX_SIZE=52428800    # 50 МБ (по умолчанию)
FETCHER__MAX_SIZE=104857600   # 100 МБ
FETCHER__MAX_SIZE=524288000   # 500 МБ
FETCHER__MAX_SIZE=1073741824  # 1 ГБ
```

#### FETCHER__VERIFY_SSL

**Назначение:** Проверять SSL-сертификаты

**Тип:** boolean  
**По умолчанию:** `true`  
**Допустимые значения:** `true`, `false`

```bash
FETCHER__VERIFY_SSL=true   # Рекомендуется
FETCHER__VERIFY_SSL=false  # Только для тестирования с самоподписанными сертификатами
```

**⚠️ ВАЖНО:** Не отключайте в продакшене без необходимости!

#### FETCHER__USER_AGENT

**Назначение:** User-Agent для HTTP запросов

**Тип:** string  
**По умолчанию:** `ProxyTorrent/0.1.0`

```bash
FETCHER__USER_AGENT=ProxyTorrent/0.1.0
FETCHER__USER_AGENT=Mozilla/5.0 (compatible; ProxyTorrent/0.1.0)
```

---

### 4. Torrent Settings (TORRENT__*)

Настройки создания и раздачи торрентов.

#### TORRENT__PRIVATE_TRACKER

**Назначение:** Создавать приватные торренты

**Тип:** boolean  
**По умолчанию:** `true`  
**Рекомендация:** всегда `true` для безопасности

```bash
TORRENT__PRIVATE_TRACKER=true  # Приватные торренты (рекомендуется)
TORRENT__PRIVATE_TRACKER=false # Публичные торренты
```

#### TORRENT__PIECE_SIZE

**Назначение:** Размер куска (piece) торрента в байтах

**Тип:** integer  
**По умолчанию:** `262144` (256 КБ)

```bash
TORRENT__PIECE_SIZE=262144   # 256 КБ (по умолчанию)
TORRENT__PIECE_SIZE=524288   # 512 КБ
TORRENT__PIECE_SIZE=1048576  # 1 МБ
```

**Рекомендации:**
- Маленькие файлы (< 10 МБ): 256 КБ
- Средние файлы (10-100 МБ): 512 КБ
- Большие файлы (> 100 МБ): 1-2 МБ

#### TORRENT__ANNOUNCE_URL

**Назначение:** URL трекера для объявления

**Тип:** string  
**По умолчанию:** `null`  
**Опционально**

```bash
TORRENT__ANNOUNCE_URL=http://tracker.example.com:8080/announce
TORRENT__ANNOUNCE_URL=https://tracker.example.com/announce
```

#### TORRENT__ENCRYPTION_ENABLED

**Назначение:** Включить шифрование BitTorrent

**Тип:** boolean  
**По умолчанию:** `true`

```bash
TORRENT__ENCRYPTION_ENABLED=true  # Рекомендуется
TORRENT__ENCRYPTION_ENABLED=false
```

#### TORRENT__UPLOAD_RATE_LIMIT

**Назначение:** Лимит скорости отдачи (байт/сек), 0 = без лимита

**Тип:** integer  
**По умолчанию:** `0`

```bash
TORRENT__UPLOAD_RATE_LIMIT=0          # Без лимита
TORRENT__UPLOAD_RATE_LIMIT=1048576   # 1 МБ/с
TORRENT__UPLOAD_RATE_LIMIT=10485760  # 10 МБ/с
```

#### TORRENT__DOWNLOAD_RATE_LIMIT

**Назначение:** Лимит скорости загрузки (байт/сек), 0 = без лимита

**Тип:** integer  
**По умолчанию:** `0`

```bash
TORRENT__DOWNLOAD_RATE_LIMIT=0
TORRENT__DOWNLOAD_RATE_LIMIT=5242880  # 5 МБ/с
```

#### TORRENT__MAX_CONNECTIONS

**Назначение:** Максимальное количество peer соединений

**Тип:** integer  
**По умолчанию:** `200`

```bash
TORRENT__MAX_CONNECTIONS=200  # По умолчанию
TORRENT__MAX_CONNECTIONS=500  # Для высокой нагрузки
TORRENT__MAX_CONNECTIONS=50   # Для ограничения ресурсов
```

---

### 5. Storage Settings (STORAGE__*)

Настройки файлового хранилища.

#### STORAGE__BASE_PATH

**Назначение:** Базовая директория для всех данных

**Тип:** string (путь)  
**По умолчанию:** `./data`

```bash
STORAGE__BASE_PATH=./data
STORAGE__BASE_PATH=/var/lib/proxytorrent/data
STORAGE__BASE_PATH=/mnt/storage/proxytorrent
```

#### STORAGE__CONTENT_PATH

**Назначение:** Директория для хранения контента

**Тип:** string (путь)  
**По умолчанию:** `./data/content`

```bash
STORAGE__CONTENT_PATH=./data/content
STORAGE__CONTENT_PATH=/var/lib/proxytorrent/content
```

#### STORAGE__TORRENT_PATH

**Назначение:** Директория для .torrent файлов

**Тип:** string (путь)  
**По умолчанию:** `./data/torrents`

```bash
STORAGE__TORRENT_PATH=./data/torrents
STORAGE__TORRENT_PATH=/var/lib/proxytorrent/torrents
```

#### STORAGE__RESUME_PATH

**Назначение:** Директория для resume data торрентов

**Тип:** string (путь)  
**По умолчанию:** `./data/resume`

```bash
STORAGE__RESUME_PATH=./data/resume
STORAGE__RESUME_PATH=/var/lib/proxytorrent/resume
```

---

### 6. Cache Settings (CACHE__*)

Настройки кеширования.

#### CACHE__CACHE_ENABLED

**Назначение:** Включить кеширование запросов

**Тип:** boolean  
**По умолчанию:** `true`

```bash
CACHE__CACHE_ENABLED=true
CACHE__CACHE_ENABLED=false
```

#### CACHE__DEFAULT_TTL

**Назначение:** TTL кеша по умолчанию (секунды)

**Тип:** integer  
**По умолчанию:** `3600` (1 час)

```bash
CACHE__DEFAULT_TTL=3600   # 1 час
CACHE__DEFAULT_TTL=7200   # 2 часа
CACHE__DEFAULT_TTL=86400  # 24 часа
```

#### CACHE__MAX_TTL

**Назначение:** Максимальный TTL кеша (секунды)

**Тип:** integer  
**По умолчанию:** `86400` (24 часа)

```bash
CACHE__MAX_TTL=86400   # 24 часа
CACHE__MAX_TTL=604800  # 7 дней
```

#### CACHE__REDIS_URL

**Назначение:** URL для подключения к Redis (опционально)

**Тип:** string  
**По умолчанию:** `null`

```bash
CACHE__REDIS_URL=redis://localhost:6379/0
CACHE__REDIS_URL=redis://user:password@redis-host:6379/0
```

---

### 7. Rate Limiting Settings (RATE_LIMIT__*)

Настройки ограничения частоты запросов.

#### RATE_LIMIT__RATE_LIMIT_ENABLED

**Назначение:** Включить rate limiting

**Тип:** boolean  
**По умолчанию:** `true`

```bash
RATE_LIMIT__RATE_LIMIT_ENABLED=true
RATE_LIMIT__RATE_LIMIT_ENABLED=false
```

#### RATE_LIMIT__REQUESTS_PER_MINUTE

**Назначение:** Максимум запросов в минуту на пользователя

**Тип:** integer  
**По умолчанию:** `60`

```bash
RATE_LIMIT__REQUESTS_PER_MINUTE=60   # По умолчанию
RATE_LIMIT__REQUESTS_PER_MINUTE=120  # Увеличенный лимит
```

#### RATE_LIMIT__REQUESTS_PER_HOUR

**Назначение:** Максимум запросов в час на пользователя

**Тип:** integer  
**По умолчанию:** `1000`

```bash
RATE_LIMIT__REQUESTS_PER_HOUR=1000
RATE_LIMIT__REQUESTS_PER_HOUR=5000
```

#### RATE_LIMIT__REQUESTS_PER_IP_MINUTE

**Назначение:** Максимум запросов в минуту с одного IP

**Тип:** integer  
**По умолчанию:** `100`

```bash
RATE_LIMIT__REQUESTS_PER_IP_MINUTE=100
RATE_LIMIT__REQUESTS_PER_IP_MINUTE=200
```

---

### 8. Database Settings (DATABASE__*)

Настройки подключения к базе данных.

#### DATABASE__DATABASE_URL

**Назначение:** Connection string для базы данных

**Тип:** string  
**По умолчанию:** `sqlite+aiosqlite:///./data/proxytorrent.db`

```bash
# SQLite (по умолчанию, для разработки)
DATABASE__DATABASE_URL=sqlite+aiosqlite:///./data/proxytorrent.db

# PostgreSQL (рекомендуется для продакшена)
DATABASE__DATABASE_URL=postgresql+asyncpg://user:password@localhost/proxytorrent
DATABASE__DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/proxytorrent
```

#### DATABASE__ECHO_SQL

**Назначение:** Выводить SQL запросы в логи (для отладки)

**Тип:** boolean  
**По умолчанию:** `false`

```bash
DATABASE__ECHO_SQL=false  # Продакшен
DATABASE__ECHO_SQL=true   # Отладка
```

---

### 9. Monitoring Settings (MONITORING__*)

Настройки логирования и мониторинга.

#### MONITORING__LOG_LEVEL

**Назначение:** Уровень логирования

**Тип:** string  
**По умолчанию:** `INFO`  
**Допустимые значения:** `DEBUG`, `INFO`, `WARNING`, `ERROR`

```bash
MONITORING__LOG_LEVEL=INFO     # Продакшен
MONITORING__LOG_LEVEL=DEBUG    # Разработка
MONITORING__LOG_LEVEL=WARNING  # Минимальные логи
```

#### MONITORING__JSON_LOGS

**Назначение:** Использовать JSON формат для логов

**Тип:** boolean  
**По умолчанию:** `true`

```bash
MONITORING__JSON_LOGS=true   # Структурированные логи (для парсинга)
MONITORING__JSON_LOGS=false  # Обычный текстовый формат
```

#### MONITORING__MASK_SENSITIVE

**Назначение:** Маскировать чувствительные данные в логах

**Тип:** boolean  
**По умолчанию:** `true`

```bash
MONITORING__MASK_SENSITIVE=true  # Рекомендуется
MONITORING__MASK_SENSITIVE=false # Только для отладки
```

#### MONITORING__METRICS_ENABLED

**Назначение:** Включить сбор метрик (Prometheus)

**Тип:** boolean  
**По умолчанию:** `true`

```bash
MONITORING__METRICS_ENABLED=true
MONITORING__METRICS_ENABLED=false
```

---

### 10. API Settings

Общие настройки API.

#### APP_NAME

**Назначение:** Название приложения

**Тип:** string  
**По умолчанию:** `ProxyTorrent`

```bash
APP_NAME=ProxyTorrent
```

#### APP_VERSION

**Назначение:** Версия приложения

**Тип:** string  
**По умолчанию:** `0.1.0`

```bash
APP_VERSION=0.1.0
```

#### DEBUG

**Назначение:** Режим отладки

**Тип:** boolean  
**По умолчанию:** `false`

```bash
DEBUG=false  # Продакшен
DEBUG=true   # Разработка (детальные трейсбеки)
```

⚠️ **ВАЖНО:** Всегда `false` в продакшене!

#### API_PREFIX

**Назначение:** Префикс для всех API эндпоинтов

**Тип:** string  
**По умолчанию:** `/v1`

```bash
API_PREFIX=/v1
API_PREFIX=/api/v1
```

#### HOST

**Назначение:** Хост для привязки сервера

**Тип:** string  
**По умолчанию:** `0.0.0.0`

```bash
HOST=0.0.0.0     # Слушать на всех интерфейсах
HOST=127.0.0.1   # Только localhost
```

#### PORT

**Назначение:** Порт сервера

**Тип:** integer  
**По умолчанию:** `8000`

```bash
PORT=8000
PORT=8080
PORT=3000
```

---

## Примеры конфигураций

### Разработка (Development)

```bash
# .env
# Безопасность отключена для удобства
SECURITY__AUTH_ENABLED=false
SECURITY__HMAC_SECRET=dev-secret-not-for-production

# Прокси отключён
PROXY__PROXY_ENABLED=false

# Отладка включена
DEBUG=true
MONITORING__LOG_LEVEL=DEBUG
DATABASE__ECHO_SQL=true

# SQLite БД
DATABASE__DATABASE_URL=sqlite+aiosqlite:///./data/proxytorrent.db

# Логи в текстовом формате
MONITORING__JSON_LOGS=false
```

### Продакшен (Production)

```bash
# .env
# БЕЗОПАСНОСТЬ (обязательно!)
SECURITY__AUTH_ENABLED=true
SECURITY__HMAC_SECRET=a1b2c3d4e5f6789...  # 64 символа от openssl rand -hex 32
SECURITY__BEARER_TOKENS=prod-token-1,prod-token-2

# Прокси/VPN обязательно
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=vpn.example.com
PROXY__PROXY_PORT=1080
PROXY__PROXY_USERNAME=proxyuser
PROXY__PROXY_PASSWORD=securepass

# PostgreSQL
DATABASE__DATABASE_URL=postgresql+asyncpg://ptuser:securedbpass@postgres:5432/proxytorrent

# Продакшен настройки
DEBUG=false
MONITORING__LOG_LEVEL=INFO
MONITORING__JSON_LOGS=true
MONITORING__MASK_SENSITIVE=true

# Хранилище
STORAGE__BASE_PATH=/var/lib/proxytorrent/data

# Торренты
TORRENT__PRIVATE_TRACKER=true
TORRENT__ENCRYPTION_ENABLED=true
TORRENT__ANNOUNCE_URL=https://tracker.example.com/announce

# Rate limits
RATE_LIMIT__RATE_LIMIT_ENABLED=true
RATE_LIMIT__REQUESTS_PER_MINUTE=60
RATE_LIMIT__REQUESTS_PER_HOUR=1000
```

### Высокая нагрузка (High Load)

```bash
# Дополнительно к продакшен настройкам:

# Увеличенные лимиты
FETCHER__MAX_SIZE=524288000          # 500 МБ
FETCHER__READ_TIMEOUT=300            # 5 минут
RATE_LIMIT__REQUESTS_PER_MINUTE=120
RATE_LIMIT__REQUESTS_PER_HOUR=5000

# Торренты
TORRENT__MAX_CONNECTIONS=500
TORRENT__UPLOAD_RATE_LIMIT=10485760  # 10 МБ/с

# Redis для кеша
CACHE__REDIS_URL=redis://redis:6379/0
```

---

## Источники в коде

- **Определения настроек**: `src/app/core/config.py`
- **Шаблон**: `.env.example`
- **Валидация**: Pydantic Settings (автоматически)

## Проверка/валидация

### Проверка текущей конфигурации

```bash
# Вывести все настройки (из контейнера)
docker-compose exec proxytorrent python -c "
from app.core.config import settings
import json

config_dict = {
    'app_name': settings.app_name,
    'debug': settings.debug,
    'security': {
        'auth_enabled': settings.security.auth_enabled,
        'hmac_secret': '***' if settings.security.hmac_secret else None
    },
    'proxy': {
        'enabled': settings.proxy.proxy_enabled,
        'type': settings.proxy.proxy_type,
        'host': settings.proxy.proxy_host
    },
    'database': {
        'url': settings.database.database_url.split('@')[-1] if '@' in settings.database.database_url else settings.database.database_url
    }
}

print(json.dumps(config_dict, indent=2))
"
```

### Валидация .env файла

```bash
# Проверка синтаксиса
cat .env | grep -v "^#" | grep -v "^$"

# Проверка обязательных параметров для продакшена
required_prod_vars=(
  "SECURITY__AUTH_ENABLED"
  "SECURITY__HMAC_SECRET"
  "PROXY__PROXY_ENABLED"
)

for var in "${required_prod_vars[@]}"; do
  if ! grep -q "^${var}=" .env; then
    echo "⚠️  Missing: $var"
  fi
done
```

### Тест конфигурации

```bash
# Запустить с проверкой конфигурации
docker-compose config

# Проверить, что сервис стартует
docker-compose up -d
docker-compose logs proxytorrent | grep -i "error"
```

## Связанные главы

- [Безопасность](./08_security_model.md) — настройки безопасности
- [Deployment](./09_deployment_playbook.md) — конфигурация для разных окружений
- [Architecture](./03_architecture_overview.md) — как используются настройки

## Шаблон .env

Полный шаблон доступен в `.env.example`. Используйте его как основу:

```bash
cp .env.example .env
nano .env
```
