# 10. Тестирование и CI

## Цель главы

Описать стратегию тестирования ProxyTorrent, виды тестов, инструменты, запуск и CI/CD процессы.

## Стратегия тестирования

ProxyTorrent использует многоуровневое тестирование:

1. **Unit тесты** — отдельные функции и классы
2. **Integration тесты** — взаимодействие компонентов
3. **API тесты** — тестирование эндпоинтов
4. **E2E тесты** — полный цикл работы

## Инструменты

- **pytest** — тестовый фреймворк
- **pytest-asyncio** — поддержка async тестов
- **pytest-cov** — coverage отчёты
- **httpx** — HTTP клиент для API тестов (async)
- **ruff** — линтер
- **mypy** — статическая типизация
- **black** — форматирование кода
- **isort** — сортировка импортов

## Структура тестов

```
src/app/tests/
├── __init__.py
├── conftest.py           # Фикстуры pytest
├── test_api.py           # API тесты
├── test_fetcher.py       # Тесты Fetcher сервиса
├── test_integration.py   # Интеграционные тесты
└── test_*.py            # Другие тесты
```

## Фикстуры pytest

**Файл:** `src/app/tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.core.database import Base, get_db_session
from app.core.config import Settings

# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    """Создать тестовую БД."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def test_app():
    """Создать тестовое приложение."""
    app = create_app()
    return app

@pytest.fixture
def client(test_app):
    """HTTP клиент для тестов."""
    with TestClient(test_app) as c:
        yield c

@pytest.fixture
def test_settings():
    """Тестовые настройки."""
    return Settings(
        security={"auth_enabled": False},
        proxy={"proxy_enabled": False},
        storage={"base_path": "/tmp/test_proxytorrent"}
    )
```

## Unit тесты

### Пример: Тестирование Fetcher

**Файл:** `src/app/tests/test_fetcher.py`

```python
import pytest
from app.services.fetcher import Fetcher, FetchError

@pytest.mark.asyncio
async def test_fetch_success(test_settings):
    """Тест успешной загрузки."""
    fetcher = Fetcher(test_settings)
    
    result = await fetcher.fetch(
        url="http://httpbin.org/html",
        method="GET"
    )
    
    assert result.status_code == 200
    assert result.content_type.startswith("text/html")
    assert len(result.content) > 0
    assert result.content_hash.startswith("sha256:")

@pytest.mark.asyncio
async def test_fetch_invalid_mime_type(test_settings):
    """Тест блокировки невалидного MIME type."""
    settings = test_settings
    settings.fetcher.mime_whitelist = ["text/plain"]  # Только text/plain
    
    fetcher = Fetcher(settings)
    
    with pytest.raises(FetchError, match="Invalid content type"):
        await fetcher.fetch(
            url="http://httpbin.org/html",  # text/html
            method="GET"
        )

@pytest.mark.asyncio
async def test_fetch_size_limit(test_settings):
    """Тест ограничения размера."""
    settings = test_settings
    settings.fetcher.max_size = 100  # Только 100 байт
    
    fetcher = Fetcher(settings)
    
    with pytest.raises(FetchError, match="Content too large"):
        await fetcher.fetch(
            url="http://httpbin.org/html",  # Больше 100 байт
            method="GET"
        )

@pytest.mark.asyncio
async def test_fetch_timeout(test_settings):
    """Тест таймаута."""
    settings = test_settings
    settings.fetcher.read_timeout = 1  # 1 секунда
    
    fetcher = Fetcher(settings)
    
    with pytest.raises(FetchError, match="Timeout"):
        await fetcher.fetch(
            url="http://httpbin.org/delay/10",  # 10 сек задержка
            method="GET"
        )
```

### Пример: Тестирование Packager

```python
import pytest
from pathlib import Path
from app.services.packager import Packager

@pytest.mark.asyncio
async def test_package_content(test_settings, tmp_path):
    """Тест упаковки контента."""
    packager = Packager(test_settings)
    
    content = b"Hello, world!"
    content_hash = "sha256:abc123..."
    
    result = await packager.package(
        content=content,
        content_hash=content_hash,
        metadata={"url": "http://example.com"}
    )
    
    assert result.infohash
    assert result.torrent_path.exists()
    assert result.content_hash == content_hash

@pytest.mark.asyncio
async def test_package_deduplication(test_settings):
    """Тест дедупликации."""
    packager = Packager(test_settings)
    
    content = b"Same content"
    content_hash = "sha256:same123..."
    
    # Первая упаковка
    result1 = await packager.package(content, content_hash, {})
    
    # Вторая упаковка того же контента
    result2 = await packager.package(content, content_hash, {})
    
    # Должны использовать один и тот же файл
    assert result1.content_hash == result2.content_hash
```

## API тесты

**Файл:** `src/app/tests/test_api.py`

```python
import pytest
from fastapi.testclient import TestClient

def test_root_endpoint(client):
    """Тест корневого эндпоинта."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ProxyTorrent"
    assert "version" in data

def test_health_check(client):
    """Тест health check."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "checks" in data

def test_create_request_without_auth(client):
    """Тест создания запроса без аутентификации."""
    # Если auth_enabled=false в тестах
    payload = {
        "url": "http://httpbin.org/html",
        "method": "GET",
        "ttl": 3600
    }
    response = client.post("/v1/requests", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "queued"

def test_create_request_invalid_url(client):
    """Тест с невалидным URL."""
    payload = {
        "url": "not-a-url",
        "method": "GET",
        "ttl": 3600
    }
    response = client.post("/v1/requests", json=payload)
    assert response.status_code == 422  # Validation error

def test_get_request_not_found(client):
    """Тест получения несуществующего запроса."""
    response = client.get("/v1/requests/non-existent-id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_and_get_request(client, db_session):
    """Тест создания и получения запроса."""
    # Создать запрос
    payload = {
        "url": "http://httpbin.org/html",
        "method": "GET",
        "ttl": 3600
    }
    create_response = client.post("/v1/requests", json=payload)
    assert create_response.status_code == 200
    request_id = create_response.json()["id"]
    
    # Получить статус
    get_response = client.get(f"/v1/requests/{request_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == request_id
    assert data["status"] in ["queued", "fetching", "ready"]
```

## Integration тесты

**Файл:** `src/app/tests/test_integration.py`

```python
import pytest
import asyncio
from app.services.fetcher import Fetcher
from app.services.packager import Packager
from app.services.seeder import Seeder

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline(test_settings):
    """Тест полного pipeline: fetch → package → seed."""
    # 1. Fetch
    fetcher = Fetcher(test_settings)
    fetch_result = await fetcher.fetch(
        url="http://httpbin.org/html",
        method="GET"
    )
    
    assert fetch_result.content
    assert fetch_result.content_hash
    
    # 2. Package
    packager = Packager(test_settings)
    package_result = await packager.package(
        content=fetch_result.content,
        content_hash=fetch_result.content_hash,
        metadata={"url": "http://httpbin.org/html"}
    )
    
    assert package_result.infohash
    assert package_result.torrent_path.exists()
    
    # 3. Seed
    seeder = Seeder(test_settings)
    await seeder.add_torrent(package_result.torrent_path)
    
    # Проверка что торрент добавлен
    # (в реальном тесте нужно проверить через libtorrent API)
    
    # Cleanup
    seeder.shutdown()
```

## E2E тесты

**Скрипт:** `tests/e2e_test.sh`

```bash
#!/bin/bash
set -e

BASE_URL="http://localhost:8000"

echo "=== E2E Test ==="

# 1. Health check
echo "1. Health check..."
curl -f "$BASE_URL/v1/health" || exit 1

# 2. Create request
echo "2. Create request..."
REQUEST_ID=$(curl -s -X POST "$BASE_URL/v1/requests" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://httpbin.org/html","method":"GET","ttl":3600}' \
  | jq -r '.id')

echo "Request ID: $REQUEST_ID"

# 3. Wait for ready
echo "3. Waiting for ready status..."
for i in {1..30}; do
  STATUS=$(curl -s "$BASE_URL/v1/requests/$REQUEST_ID" | jq -r '.status')
  echo "  Status: $STATUS"
  
  if [ "$STATUS" = "ready" ]; then
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "Request failed!"
    exit 1
  fi
  
  sleep 2
done

# 4. Get magnet link
echo "4. Get magnet link..."
MAGNET=$(curl -s "$BASE_URL/v1/requests/$REQUEST_ID/magnet" | jq -r '.magnet_link')
echo "Magnet: $MAGNET"

# 5. Download torrent
echo "5. Download torrent..."
curl -f "$BASE_URL/v1/requests/$REQUEST_ID/torrent" -o /tmp/test.torrent

# 6. Verify torrent file
echo "6. Verify torrent..."
file /tmp/test.torrent | grep -q "BitTorrent" || exit 1

echo "=== E2E Test PASSED ==="
```

## Запуск тестов

### Все тесты

```bash
# Из корня репозитория
pytest src/app/tests/ -v
```

### Только unit тесты (без интеграционных)

```bash
pytest src/app/tests/ -v -m "not integration"
```

### С coverage

```bash
pytest src/app/tests/ -v --cov=app --cov-report=html
```

### Конкретный тест

```bash
pytest src/app/tests/test_api.py::test_health_check -v
```

### С детальным выводом

```bash
pytest src/app/tests/ -vv -s
```

## Coverage (покрытие кода)

### Генерация отчёта

```bash
pytest src/app/tests/ --cov=app --cov-report=html --cov-report=term
```

### Просмотр HTML отчёта

```bash
open htmlcov/index.html
```

### Минимальный порог coverage

```bash
# В pytest.ini или pyproject.toml
[tool:pytest]
addopts = --cov=app --cov-fail-under=80
```

## Линтинг и форматирование

### Ruff (линтер)

```bash
# Проверка
ruff check src/

# Автоисправление
ruff check src/ --fix

# Конфигурация в pyproject.toml
```

### Mypy (типы)

```bash
# Проверка типов
mypy src/

# С более строгими правилами
mypy src/ --strict
```

### Black (форматирование)

```bash
# Форматировать код
black src/

# Проверка без изменений
black src/ --check
```

### Isort (импорты)

```bash
# Сортировка импортов
isort src/

# Проверка
isort src/ --check
```

### Всё вместе

```bash
#!/bin/bash
# scripts/lint.sh

set -e

echo "Running ruff..."
ruff check src/ --fix

echo "Running black..."
black src/

echo "Running isort..."
isort src/

echo "Running mypy..."
mypy src/

echo "All checks passed!"
```

## CI/CD

### GitHub Actions

**Файл:** `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with ruff
      run: ruff check src/
    
    - name: Type check with mypy
      run: mypy src/
    
    - name: Run tests
      run: |
        pytest src/app/tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Docker Build

```yaml
name: Docker Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t proxytorrent:test .
    
    - name: Run container
      run: |
        docker run -d -p 8000:8000 --name pt-test proxytorrent:test
        sleep 10
    
    - name: Health check
      run: curl -f http://localhost:8000/v1/health
    
    - name: Stop container
      run: docker stop pt-test
```

## Pre-commit hooks

**Файл:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

```bash
# Установка
pip install pre-commit
pre-commit install

# Запуск вручную
pre-commit run --all-files
```

## Тестовые данные

**Фикстуры для тестов:**

```python
# tests/fixtures.py

SAMPLE_URLS = [
    "http://httpbin.org/html",
    "http://httpbin.org/json",
    "http://httpbin.org/xml",
]

SAMPLE_PAYLOADS = [
    {"url": "http://httpbin.org/html", "method": "GET", "ttl": 3600},
    {"url": "http://httpbin.org/post", "method": "POST", "body": '{"key":"value"}', "ttl": 3600},
]

INVALID_URLS = [
    "not-a-url",
    "ftp://invalid-scheme.com",
    "http://",
]
```

## Источники в коде

- **Тесты**: `src/app/tests/`
- **Конфигурация pytest**: `pyproject.toml` ([tool.pytest])
- **Конфигурация ruff**: `pyproject.toml` ([tool.ruff])
- **Конфигурация mypy**: `pyproject.toml` ([tool.mypy])
- **GitHub Actions**: `.github/workflows/`

## Проверка/валидация

### Запустить все тесты

```bash
cd /path/to/proxytorrent
pytest src/app/tests/ -v
```

### Проверить coverage

```bash
pytest src/app/tests/ --cov=app --cov-report=term
# Ожидается: > 80% coverage
```

### Запустить линтеры

```bash
ruff check src/
mypy src/
black src/ --check
isort src/ --check
```

## Связанные главы

- [CONTRIBUTING.md](../../CONTRIBUTING.md) — правила разработки
- [Deployment](./09_deployment_playbook.md) — CI/CD для продакшена

## Дополнительные ресурсы

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [ruff](https://beta.ruff.rs/docs/)
- [mypy](https://mypy.readthedocs.io/)
