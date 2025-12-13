# 7. Хранилище и модель данных

## Цель главы

Описать структуру базы данных, файлового хранилища, модели данных и принципы работы content-addressable storage.

## Обзор

ProxyTorrent использует гибридное хранилище:
- **SQLite/PostgreSQL** — метаданные запросов, статусы
- **Файловая система** — контент, торренты, resume data
- **Content-addressable storage** — дедупликация по SHA256 хешу

## База данных

### Схема БД

ProxyTorrent использует одну основную таблицу `fetch_requests`.

```sql
CREATE TABLE fetch_requests (
    -- Идентификация
    id VARCHAR(36) PRIMARY KEY,              -- UUID запроса
    
    -- Статус обработки
    status VARCHAR(20) NOT NULL,             -- queued, fetching, packaging, seeding, ready, failed, cancelled
    progress INTEGER DEFAULT 0,              -- 0-100
    
    -- Параметры запроса
    url TEXT NOT NULL,                       -- URL для загрузки
    method VARCHAR(10) NOT NULL,             -- GET, POST, PUT, DELETE, PATCH
    headers JSON,                            -- Дополнительные заголовки
    body TEXT,                               -- Тело запроса (для POST/PUT)
    ttl INTEGER NOT NULL,                    -- TTL в секундах
    
    -- Результаты загрузки
    content_hash VARCHAR(64),                -- SHA256 хеш контента
    content_size INTEGER,                    -- Размер в байтах
    content_type VARCHAR(255),               -- MIME type
    
    -- Торрент информация
    infohash VARCHAR(40),                    -- BitTorrent infohash (hex)
    torrent_path TEXT,                       -- Путь к .torrent файлу
    
    -- Обработка ошибок
    error_message TEXT,                      -- Описание ошибки (если failed)
    retry_count INTEGER DEFAULT 0,           -- Количество попыток
    
    -- Временные метки
    created_at DATETIME NOT NULL,            -- Время создания
    updated_at DATETIME NOT NULL,            -- Последнее обновление
    completed_at DATETIME,                   -- Время завершения
    
    -- Аудит
    user_id VARCHAR(255),                    -- ID пользователя (из auth)
    client_ip VARCHAR(45)                    -- IP клиента
);

-- Индексы для быстрого поиска
CREATE INDEX idx_fetch_requests_status ON fetch_requests(status);
CREATE INDEX idx_fetch_requests_created_at ON fetch_requests(created_at);
CREATE INDEX idx_fetch_requests_content_hash ON fetch_requests(content_hash);
CREATE INDEX idx_fetch_requests_infohash ON fetch_requests(infohash);
CREATE INDEX idx_fetch_requests_user_id ON fetch_requests(user_id);
```

### SQLAlchemy модель

**Файл:** `src/app/models/database.py`

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FetchRequest(Base):
    __tablename__ = "fetch_requests"
    
    # Идентификация
    id = Column(String(36), primary_key=True)
    
    # Статус
    status = Column(String(20), nullable=False)
    progress = Column(Integer, default=0)
    
    # Параметры запроса
    url = Column(Text, nullable=False)
    method = Column(String(10), nullable=False)
    headers = Column(JSON)
    body = Column(Text)
    ttl = Column(Integer, nullable=False)
    
    # Результаты
    content_hash = Column(String(64))
    content_size = Column(Integer)
    content_type = Column(String(255))
    
    # Торрент
    infohash = Column(String(40))
    torrent_path = Column(Text)
    
    # Ошибки
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Временные метки
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Аудит
    user_id = Column(String(255))
    client_ip = Column(String(45))
```

### Жизненный цикл записи

1. **Создание** (POST /v1/requests):
   ```python
   FetchRequest(
       id="uuid",
       status="queued",
       progress=0,
       url="http://example.com",
       method="GET",
       created_at=now,
       updated_at=now
   )
   ```

2. **Обработка** (worker):
   ```python
   # fetching
   request.status = "fetching"
   request.progress = 20
   
   # packaging
   request.status = "packaging"
   request.progress = 50
   request.content_hash = "sha256:..."
   request.content_size = 12345
   request.content_type = "text/html"
   
   # seeding
   request.status = "seeding"
   request.progress = 80
   request.infohash = "abc123..."
   request.torrent_path = "/data/torrents/abc123.torrent"
   
   # ready
   request.status = "ready"
   request.progress = 100
   request.completed_at = now
   ```

3. **Ошибка**:
   ```python
   request.status = "failed"
   request.error_message = "Connection timeout"
   request.retry_count += 1
   ```

### Запросы к БД

**Создание запроса:**
```python
async def create_request(db: AsyncSession, payload: CreateRequestPayload) -> FetchRequest:
    request = FetchRequest(
        id=str(uuid.uuid4()),
        status="queued",
        url=payload.url,
        method=payload.method,
        ...
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request
```

**Получение по ID:**
```python
async def get_request(db: AsyncSession, request_id: str) -> FetchRequest | None:
    result = await db.execute(
        select(FetchRequest).where(FetchRequest.id == request_id)
    )
    return result.scalar_one_or_none()
```

**Поиск по хешу (дедупликация):**
```python
async def find_by_content_hash(db: AsyncSession, content_hash: str) -> FetchRequest | None:
    result = await db.execute(
        select(FetchRequest).where(
            FetchRequest.content_hash == content_hash,
            FetchRequest.status == "ready"
        )
    )
    return result.scalar_one_or_none()
```

## Файловое хранилище

### Структура директорий

```
data/
├── content/              # Content-addressable хранилище
│   ├── ab/
│   │   └── cd/
│   │       └── abcdef1234.../
│   │           ├── content          # Бинарный файл контента
│   │           └── metadata.json    # Метаданные
│   └── ...
├── torrents/             # .torrent файлы
│   ├── abcdef1234567890abcdef1234567890.torrent
│   └── ...
├── resume/               # Resume data для libtorrent
│   ├── abcdef1234567890abcdef1234567890.resume
│   └── ...
└── proxytorrent.db       # SQLite база (если используется)
```

### Content-Addressable Storage

**Принцип:** Контент хранится по пути, определяемому его SHA256 хешем.

**Формат пути:**
```
data/content/{hash[0:2]}/{hash[2:4]}/{hash}/
```

**Пример:**
```
SHA256: abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890

Путь:
data/content/ab/cd/abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890/
├── content
└── metadata.json
```

**Преимущества:**
- ✅ Автоматическая дедупликация: один контент = один файл
- ✅ Быстрая проверка существования
- ✅ Иммутабельность: хеш не меняется → контент не меняется
- ✅ Равномерное распределение по директориям (первые 2 байта хеша)

**Реализация:**

```python
# src/app/services/packager.py

def _get_content_path(self, content_hash: str) -> Path:
    """Вычислить путь для контента по хешу."""
    # data/content/ab/cd/abcd.../
    content_dir = (
        self.content_path
        / content_hash[:2]    # Первые 2 символа
        / content_hash[2:4]   # Следующие 2 символа
        / content_hash        # Полный хеш
    )
    content_dir.mkdir(parents=True, exist_ok=True)
    return content_dir
```

### Metadata.json

Каждый файл контента сопровождается файлом метаданных:

**Файл:** `data/content/{hash}/metadata.json`

**Структура:**
```json
{
  "url": "http://example.com",
  "method": "GET",
  "request_headers": {
    "User-Agent": "ProxyTorrent/0.1.0"
  },
  "response_headers": {
    "Content-Type": "text/html; charset=utf-8",
    "Content-Length": "12345",
    "Last-Modified": "Mon, 11 Dec 2025 10:00:00 GMT"
  },
  "status_code": 200,
  "content_type": "text/html",
  "content_size": 12345,
  "content_hash": "sha256:abcdef...",
  "fetched_at": "2025-12-13T10:00:00Z",
  "proxy_used": "socks5://vpn.example.com:1080"
}
```

**Создание:**
```python
metadata = {
    "url": fetch_result.url,
    "method": fetch_result.method,
    "request_headers": fetch_result.request_headers,
    "response_headers": fetch_result.response_headers,
    "status_code": fetch_result.status_code,
    "content_type": fetch_result.content_type,
    "content_size": len(fetch_result.content),
    "content_hash": fetch_result.content_hash,
    "fetched_at": datetime.utcnow().isoformat(),
    "proxy_used": config.proxy.proxy_url if config.proxy.proxy_enabled else None
}

metadata_path = content_dir / "metadata.json"
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)
```

### Torrent файлы

**Путь:** `data/torrents/{content_hash}.torrent`

**Создание с libtorrent:**
```python
import libtorrent as lt

# Создание torrent_info
fs = lt.file_storage()
fs.add_file("content", content_size)

ct = lt.create_torrent(fs)
ct.set_piece_hashes(content_path.parent)

# Флаги
ct.set_priv(config.torrent.private_tracker)  # Приватный торрент

# Tracker (опционально)
if config.torrent.announce_url:
    ct.add_tracker(config.torrent.announce_url)

# Генерация .torrent
torrent_data = lt.bencode(ct.generate())

# Сохранение
torrent_path = torrent_dir / f"{content_hash}.torrent"
with open(torrent_path, "wb") as f:
    f.write(torrent_data)
```

### Resume Data

**Назначение:** Восстановление состояния раздачи после перезапуска

**Путь:** `data/resume/{infohash}.resume`

**Формат:** Бинарный (bencode)

**Сохранение:**
```python
async def _save_resume_data(self, handle: lt.torrent_handle) -> None:
    """Сохранить resume data для торрента."""
    resume_data = handle.save_resume_data()
    
    resume_path = self.resume_path / f"{handle.info_hash()}.resume"
    with open(resume_path, "wb") as f:
        f.write(lt.bencode(resume_data))
```

**Загрузка при старте:**
```python
async def load_resume_data(self) -> None:
    """Загрузить все resume data при старте seeder."""
    for resume_file in self.resume_path.glob("*.resume"):
        try:
            with open(resume_file, "rb") as f:
                resume_data = lt.bdecode(f.read())
            
            # Восстановить торрент
            params = {"resume_data": resume_data}
            self.session.async_add_torrent(params)
        except Exception as e:
            logger.error(f"Failed to load resume data: {e}")
```

## Модели данных (Pydantic)

### Request/Response Schemas

**Файл:** `src/app/models/schemas.py`

```python
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class CreateRequestPayload(BaseModel):
    """Схема для создания запроса."""
    url: HttpUrl
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    headers: dict[str, str] | None = None
    body: str | None = None
    ttl: int = Field(..., gt=0, description="TTL in seconds")

class RequestResponse(BaseModel):
    """Схема ответа при создании."""
    id: str
    status: str
    estimated_ready: int
    created_at: datetime

class RequestStatusResponse(BaseModel):
    """Схема полного статуса запроса."""
    id: str
    status: str
    url: str
    method: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    infohash: str | None
    content_hash: str | None
    content_size: int | None
    content_type: str | None
    progress: int
    error_message: str | None

class MagnetLinkResponse(BaseModel):
    """Схема magnet ссылки."""
    id: str
    magnet_link: str
    infohash: str
```

### Service Models

**FetchResult** (из Fetcher):
```python
@dataclass
class FetchResult:
    content: bytes
    content_hash: str          # SHA256
    content_size: int
    content_type: str
    status_code: int
    response_headers: dict
    metadata: dict
```

**TorrentPackage** (из Packager):
```python
@dataclass
class TorrentPackage:
    infohash: str              # Hex string
    torrent_path: Path
    content_hash: str
    content_size: int
```

## Операции с данными

### Дедупликация контента

**Проверка существования:**
```python
async def check_existing_content(content_hash: str) -> bool:
    content_path = _get_content_path(content_hash)
    content_file = content_path / "content"
    return content_file.exists()
```

**Повторное использование:**
```python
async def package(content: bytes, content_hash: str) -> TorrentPackage:
    content_path = _get_content_path(content_hash)
    content_file = content_path / "content"
    
    if content_file.exists():
        logger.info(f"Content already exists: {content_hash}")
        # Не сохраняем повторно, используем существующий
    else:
        # Сохраняем новый контент
        with open(content_file, "wb") as f:
            f.write(content)
    
    # Создаём торрент (или используем существующий)
    torrent_path = create_torrent(content_path)
    return TorrentPackage(...)
```

### Очистка старых данных

**Удаление по TTL:**
```python
async def cleanup_expired_content(max_age_days: int = 30):
    """Удалить контент старше max_age_days дней."""
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    
    # Найти старые записи в БД
    old_requests = await db.execute(
        select(FetchRequest).where(
            FetchRequest.created_at < cutoff,
            FetchRequest.status == "ready"
        )
    )
    
    for request in old_requests.scalars():
        # Удалить .torrent
        torrent_path = Path(request.torrent_path)
        torrent_path.unlink(missing_ok=True)
        
        # Проверить, используется ли контент другими запросами
        other_requests = await db.execute(
            select(FetchRequest).where(
                FetchRequest.content_hash == request.content_hash,
                FetchRequest.id != request.id
            )
        )
        
        if not other_requests.scalars().first():
            # Контент не используется — удалить
            content_path = _get_content_path(request.content_hash)
            shutil.rmtree(content_path, ignore_errors=True)
        
        # Удалить запись из БД
        await db.delete(request)
    
    await db.commit()
```

### Резервное копирование

**Backup БД (SQLite):**
```bash
# Остановить сервис
docker-compose stop proxytorrent

# Скопировать БД
cp data/proxytorrent.db backup/proxytorrent-$(date +%Y%m%d).db

# Запустить сервис
docker-compose start proxytorrent
```

**Backup БД (PostgreSQL):**
```bash
docker-compose exec postgres pg_dump -U proxytorrent proxytorrent > backup.sql
```

**Backup файлов:**
```bash
tar -czf backup-data-$(date +%Y%m%d).tar.gz data/content data/torrents data/resume
```

## Источники в коде

- **Database models**: `src/app/models/database.py`
- **Pydantic schemas**: `src/app/models/schemas.py`
- **Database connection**: `src/app/core/database.py`
- **Packager (CAS)**: `src/app/services/packager.py`
- **Migrations**: (пока нет, схема создаётся при старте)

## Проверка/валидация

### Проверить структуру БД

```bash
# SQLite
docker-compose exec proxytorrent python -c "
import sqlite3
conn = sqlite3.connect('/app/data/proxytorrent.db')
cursor = conn.cursor()
cursor.execute('SELECT sql FROM sqlite_master WHERE type=\"table\" AND name=\"fetch_requests\"')
print(cursor.fetchone()[0])
"

# PostgreSQL
docker-compose exec postgres psql -U proxytorrent -d proxytorrent -c '\d fetch_requests'
```

### Проверить content-addressable storage

```bash
# Создать запрос
REQUEST_ID=$(curl -s -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"url":"http://httpbin.org/html","method":"GET","ttl":3600}' | jq -r '.id')

# Дождаться ready
sleep 30

# Получить хеш
HASH=$(curl -s http://localhost:8000/v1/requests/$REQUEST_ID | jq -r '.content_hash' | cut -d: -f2)

# Проверить структуру
ls -la data/content/${HASH:0:2}/${HASH:2:2}/$HASH/
# Должны быть: content, metadata.json

# Проверить metadata
cat data/content/${HASH:0:2}/${HASH:2:2}/$HASH/metadata.json | jq .

# Проверить торрент
ls -la data/torrents/$HASH.torrent

# Проверить resume data
INFOHASH=$(curl -s http://localhost:8000/v1/requests/$REQUEST_ID | jq -r '.infohash')
ls -la data/resume/$INFOHASH.resume
```

### Проверить дедупликацию

```bash
# Создать два одинаковых запроса
URL="http://httpbin.org/html"
REQ1=$(curl -s -X POST http://localhost:8000/v1/requests -H "Content-Type: application/json" -d "{\"url\":\"$URL\",\"method\":\"GET\",\"ttl\":3600}" | jq -r '.id')
sleep 30
REQ2=$(curl -s -X POST http://localhost:8000/v1/requests -H "Content-Type: application/json" -d "{\"url\":\"$URL\",\"method\":\"GET\",\"ttl\":3600}" | jq -r '.id')
sleep 30

# Получить хеши
HASH1=$(curl -s http://localhost:8000/v1/requests/$REQ1 | jq -r '.content_hash')
HASH2=$(curl -s http://localhost:8000/v1/requests/$REQ2 | jq -r '.content_hash')

echo "Hash 1: $HASH1"
echo "Hash 2: $HASH2"

# Должны совпадать
test "$HASH1" = "$HASH2" && echo "✓ Дедупликация работает" || echo "✗ Разные хеши"

# Проверить, что файл контента один
find data/content -name "content" | wc -l
# Должно быть 1 (если это первые запросы)
```

### Статистика хранилища

```bash
# Размер БД
du -h data/proxytorrent.db

# Размер контента
du -sh data/content

# Размер торрентов
du -sh data/torrents

# Количество файлов
find data/content -name "content" | wc -l
find data/torrents -name "*.torrent" | wc -l

# Общий размер
du -sh data/
```

## Связанные главы

- [Архитектура](./03_architecture_overview.md) — общая картина хранилища
- [Жизненный цикл](./04_request_lifecycle.md) — как данные создаются и обновляются
- [Конфигурация](./06_configuration_reference.md) — настройка путей хранилища
- [Deployment](./09_deployment_playbook.md) — backup и миграция данных
