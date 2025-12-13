# 11. Известные ограничения и roadmap

## Цель главы

Описать текущие ограничения ProxyTorrent, известные проблемы и планы по дальнейшему развитию проекта.

## Текущие ограничения

### 1. Размер контента

**Ограничение:** По умолчанию максимум 50 МБ на запрос

**Причина:**
- Защита от исчерпания памяти
- Ограничения дискового пространства
- Таймауты на больших файлах

**Обходной путь:**
```bash
# Увеличить лимит в .env
FETCHER__MAX_SIZE=524288000  # 500 МБ
FETCHER__READ_TIMEOUT=300    # 5 минут
```

**TODO:**
- Streaming упаковка для файлов > 1 ГБ
- Chunked download с resume support

### 2. Поддержка протоколов

**Текущая поддержка:**
- ✅ HTTP
- ✅ HTTPS

**Не поддерживается:**
- ❌ FTP
- ❌ WebSocket
- ❌ Другие протоколы

**Roadmap:** Низкий приоритет (основной use case — HTTP/HTTPS)

### 3. Очередь задач

**Ограничение:** In-memory очередь, не распределённая

**Проблемы:**
- Очередь теряется при перезапуске
- Нельзя масштабировать горизонтально (несколько инстансов)

**Текущее состояние:**
- Работает для одного инстанса
- Workers внутри одного процесса

**Roadmap:**
- Redis/RabbitMQ для распределённой очереди
- Celery интеграция

### 4. Торрент-трекер

**Ограничение:** Нет встроенного трекера

**Текущее состояние:**
- Опциональный внешний tracker через `TORRENT__ANNOUNCE_URL`
- Приватные торренты без DHT/PEX

**Последствия:**
- Нужен внешний tracker для раздачи peers
- Или peers должны знать IP напрямую

**Roadmap:**
- Встроенный simple tracker (низкий приоритет)
- WebTorrent support для браузеров

### 5. Storage backend

**Текущая поддержка:**
- ✅ Локальная файловая система

**Не поддерживается:**
- ❌ S3-compatible storage
- ❌ Distributed filesystem (GlusterFS, Ceph)

**Roadmap:**
- S3 backend для масштабирования
- Абстракция storage layer

### 6. База данных

**SQLite ограничения:**
- ❌ Не подходит для высокой нагрузки (> 1000 req/s)
- ❌ Concurrent write limitations
- ❌ Нет репликации

**Рекомендация:**
- PostgreSQL для продакшена

**Roadmap:**
- Миграции (Alembic)
- Multi-master репликация (PostgreSQL)

### 7. Аутентификация

**Текущая поддержка:**
- ✅ HMAC-SHA256
- ✅ Bearer tokens

**Не поддерживается:**
- ❌ OAuth 2.0
- ❌ JWT tokens
- ❌ API keys management UI
- ❌ User management

**Roadmap:**
- OAuth 2.0 / OpenID Connect (средний приоритет)
- Admin UI для управления токенами

### 8. Rate Limiting

**Текущая реализация:**
- In-memory счётчики
- Не персистентны
- Не распределённые

**Ограничения:**
- Сбрасываются при перезапуске
- Не работают между инстансами

**Roadmap:**
- Redis-based rate limiting
- Sliding window algorithm

### 9. Мониторинг и метрики

**Текущее состояние:**
- ✅ Health check endpoint
- ✅ Логирование
- ⚠️  Нет Prometheus metrics

**Не хватает:**
- ❌ Prometheus /metrics endpoint
- ❌ Grafana dashboards
- ❌ Alerting
- ❌ Tracing (OpenTelemetry)

**Roadmap:**
- Prometheus metrics (высокий приоритет)
- Grafana dashboard templates
- Jaeger tracing для debugging

### 10. Content validation

**Текущая валидация:**
- ✅ MIME type whitelist
- ✅ Size limits
- ⚠️  Базовая проверка SSL

**Не хватает:**
- ❌ Virus scanning (ClamAV)
- ❌ Content integrity verification (checksums from source)
- ❌ Blacklist URLs/domains

**Roadmap:**
- ClamAV integration (опционально)
- URL blacklist/whitelist

## Известные проблемы (Issues)

### Issue #1: libtorrent compatibility

**Проблема:** Некоторые версии libtorrent-rasterbar несовместимы с Python 3.11+

**Workaround:**
```bash
# Использовать конкретную версию
pip install libtorrent==2.0.8
```

**Статус:** Open  
**Приоритет:** High  
**Roadmap:** Документировать совместимые версии

### Issue #2: Graceful shutdown timing

**Проблема:** При shutdown торренты могут не сохранить resume data

**Impact:** После перезапуска раздача начинается заново

**Workaround:**
```bash
# Дать больше времени на shutdown
docker-compose down --timeout 60
```

**Статус:** Open  
**Приоритет:** Medium  
**Roadmap:** Улучшить shutdown sequence

### Issue #3: Proxy connection pool

**Проблема:** Каждый запрос создаёт новое подключение к прокси

**Impact:** Медленнее, чем могло бы быть

**Workaround:** Нет (требует рефакторинга)

**Статус:** Open  
**Приоритет:** Low  
**Roadmap:** Connection pooling для прокси

### Issue #4: Content deduplication race condition

**Проблема:** Два одновременных запроса на один URL могут скачать контент дважды

**Impact:** Временная дупликация, потом один файл удаляется

**Workaround:** Нет (очень редко происходит)

**Статус:** Open  
**Приоритет:** Low  
**Roadmap:** Distributed locks (Redis)

## Performance ограничения

### Throughput

**Текущая производительность:**
- ~10-50 запросов в минуту (на 1 CPU, 1 ГБ RAM)
- Зависит от размера контента и скорости прокси

**Bottlenecks:**
- Прокси скорость
- Disk I/O
- Создание торрентов (CPU intensive)

**Масштабирование:**
- Вертикальное: + CPU, + RAM → больше workers
- Горизонтальное: требует distributed queue (roadmap)

### Latency

**Типичное время обработки:**
- Маленькие файлы (< 1 МБ): 5-15 секунд
- Средние файлы (1-10 МБ): 15-60 секунд
- Большие файлы (10-50 МБ): 1-5 минут

**Факторы:**
- Скорость прокси
- Latency до целевого сервера
- Скорость диска

### Concurrent requests

**Лимиты:**
- По умолчанию: 10 workers
- Ограничено RAM и CPU
- SQLite bottleneck при > 100 concurrent writes

**Рекомендации:**
- PostgreSQL для > 100 concurrent
- Redis queue для > 1000 concurrent

## Roadmap

### v0.2.0 (Q1 2026) — Observability

**Цели:**
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboard template
- [ ] Structured logging (JSON) by default
- [ ] Request ID tracing through all components

**Приоритет:** High

### v0.3.0 (Q2 2026) — Distributed Queue

**Цели:**
- [ ] Redis queue backend
- [ ] Celery integration
- [ ] Horizontal scaling support
- [ ] Resume queue after restart

**Приоритет:** High

### v0.4.0 (Q2 2026) — Storage Abstraction

**Цели:**
- [ ] S3-compatible storage backend
- [ ] Storage interface abstraction
- [ ] Migration tool (local → S3)

**Приоритет:** Medium

### v0.5.0 (Q3 2026) — Enhanced Security

**Цели:**
- [ ] OAuth 2.0 / OpenID Connect
- [ ] Admin UI для управления токенами
- [ ] URL blacklist/whitelist
- [ ] Content scanning (ClamAV опционально)

**Приоритет:** Medium

### v1.0.0 (Q4 2026) — Production Ready

**Цели:**
- [ ] Встроенный BitTorrent tracker
- [ ] WebTorrent support
- [ ] Database migrations (Alembic)
- [ ] Performance optimizations
- [ ] Complete documentation
- [ ] Security audit
- [ ] Load testing

**Приоритет:** High

### Future (v1.x)

**Возможные фичи:**
- WebSocket API для real-time updates
- Batch request processing
- Custom CDN integration
- Advanced caching strategies
- Multi-tenancy support
- Web UI (admin panel)

## Вклад в проект

### Как помочь

**Для разработчиков:**
1. Выбрать issue из GitHub Issues
2. Форкнуть репозиторий
3. Создать feature branch
4. Реализовать + тесты
5. Создать Pull Request

**Для тестировщиков:**
- Найти и зарепортить баги
- Написать E2E тесты
- Проверить безопасность

**Для документаторов:**
- Улучшить документацию
- Перевести на другие языки
- Создать tutorials и примеры

**Для DevOps:**
- Kubernetes deployment guides
- Terraform modules
- Docker optimizations

См. [CONTRIBUTING.md](../../CONTRIBUTING.md) для деталей.

## Альтернативы и конкуренты

### Похожие проекты

1. **Seedr.cc** (коммерческий)
   - Аналогичная функциональность
   - Closed source
   - Платный

2. **Put.io** (коммерческий)
   - Cloud torrent client
   - Closed source
   - Платный

3. **Custom solutions**
   - Transmission + custom scripts
   - rTorrent + web UI
   - qBittorrent + API

**Преимущества ProxyTorrent:**
- ✅ Open source
- ✅ Self-hosted
- ✅ API-first design
- ✅ Proxy/VPN integration
- ✅ Content-addressable storage
- ✅ Private torrents by default

**Недостатки:**
- ❌ Пока нет UI
- ❌ Меньше features
- ❌ Требует self-hosting

## Запросы от пользователей (Feature Requests)

### Top requested features

1. **Web UI** (11 votes)
   - Status: Планируется в v1.x
   - Complexity: High

2. **WebTorrent support** (8 votes)
   - Status: Планируется в v1.0
   - Complexity: Medium

3. **RSS feed monitoring** (7 votes)
   - Status: Under consideration
   - Complexity: Medium

4. **Scheduled downloads** (5 votes)
   - Status: Under consideration
   - Complexity: Low

5. **Download history export** (4 votes)
   - Status: Easy to add
   - Complexity: Low

## Источники

- **GitHub Issues**: https://github.com/NickScherbakov/proxytorrent/issues
- **Project Board**: https://github.com/NickScherbakov/proxytorrent/projects
- **Discussions**: https://github.com/NickScherbakov/proxytorrent/discussions

## Проверка текущих ограничений

### Проверить размер контента

```bash
# Попробовать большой файл
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.com/large-file.zip","method":"GET","ttl":3600}'

# Если > MAX_SIZE, получите ошибку
```

### Проверить in-memory queue

```bash
# Создать запрос
REQUEST_ID=$(curl -s -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"url":"http://httpbin.org/delay/10","method":"GET","ttl":3600}' | jq -r '.id')

# Перезапустить сервис
docker-compose restart proxytorrent

# Проверить статус — может быть "queued" (не обработан)
curl http://localhost:8000/v1/requests/$REQUEST_ID
```

### Проверить SQLite limits

```bash
# Создать много запросов параллельно
for i in {1..100}; do
  curl -X POST http://localhost:8000/v1/requests \
    -H "Content-Type: application/json" \
    -d '{"url":"http://httpbin.org/delay/1","method":"GET","ttl":3600}' &
done
wait

# Проверить логи на DB errors
docker-compose logs proxytorrent | grep -i "database"
```

## Связанные главы

- [Architecture](./03_architecture_overview.md) — где видны архитектурные ограничения
- [Testing](./10_testing_and_ci.md) — тесты для проверки лимитов
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — как помочь улучшить проект

## Обратная связь

Если вы столкнулись с ограничением или хотите предложить новую фичу:

1. Проверьте [GitHub Issues](https://github.com/NickScherbakov/proxytorrent/issues)
2. Если нет похожего — создайте новый Issue
3. Опишите use case и почему это важно
4. (Опционально) Предложите реализацию

---

**Дата последнего обновления roadmap:** 2025-12-13
