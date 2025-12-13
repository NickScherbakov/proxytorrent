# 9. Руководство по развёртыванию

## Цель главы

Пошаговые инструкции по развёртыванию ProxyTorrent в различных окружениях: разработка, staging, продакшен.

## Оглавление

1. [Требования](#требования)
2. [Локальная разработка](#локальная-разработка)
3. [Docker Compose (рекомендуется)](#docker-compose)
4. [Продакшен на VPS](#продакшен-на-vps)
5. [С VPN/прокси](#развёртывание-с-vpnпрокси)
6. [Мониторинг и обслуживание](#мониторинг-и-обслуживание)

## Требования

### Минимальные

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- **RAM**: 1 ГБ
- **Disk**: 10 ГБ свободного места
- **CPU**: 1 core

### Рекомендуемые для продакшена

- **OS**: Ubuntu 22.04 LTS
- **RAM**: 2-4 ГБ
- **Disk**: 50-100 ГБ SSD
- **CPU**: 2+ cores
- **Network**: Стабильное подключение, 100+ Mbps

### Программное обеспечение

- Docker 20.10+
- Docker Compose 2.0+ (или docker-compose-plugin)
- Git
- (Опционально) Nginx для reverse proxy
- (Опционально) PostgreSQL для продакшена

## Локальная разработка

### Вариант 1: Docker Compose (быстрый старт)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent

# 2. Создать .env (опционально, для кастомизации)
cp .env.example .env
nano .env  # Установить SECURITY__AUTH_ENABLED=false для удобства

# 3. Запустить
docker-compose up -d

# 4. Проверить
curl http://localhost:8000/v1/health

# 5. Логи
docker-compose logs -f proxytorrent

# 6. Остановить
docker-compose down
```

### Вариант 2: Локальный Python

```bash
# 1. Установить зависимости
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Установить libtorrent
sudo apt-get install python3-libtorrent  # Ubuntu/Debian
# или
brew install libtorrent-rasterbar  # macOS

# 3. Настроить окружение
cp .env.example .env
nano .env

# 4. Запустить
cd src
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Проверить
curl http://localhost:8000/v1/health
```

## Docker Compose

### Базовая конфигурация

**Файл:** `docker-compose.yml` (уже в репозитории)

```yaml
version: '3.8'

services:
  proxytorrent:
    build: .
    container_name: proxytorrent
    ports:
      - "8000:8000"
    environment:
      # Разработка: без аутентификации
      - SECURITY__AUTH_ENABLED=false
      # Продакшен: см. .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### С PostgreSQL (продакшен)

```yaml
version: '3.8'

services:
  proxytorrent:
    build: .
    container_name: proxytorrent
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE__DATABASE_URL=postgresql+asyncpg://proxytorrent:${POSTGRES_PASSWORD}@postgres:5432/proxytorrent
    volumes:
      - ./data:/app/data
    depends_on:
      - postgres
    restart: unless-stopped
  
  postgres:
    image: postgres:15-alpine
    container_name: proxytorrent-db
    environment:
      - POSTGRES_USER=proxytorrent
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
      - POSTGRES_DB=proxytorrent
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### С VPN (OpenVPN)

```yaml
version: '3.8'

services:
  vpn:
    image: dperson/openvpn-client
    container_name: proxytorrent-vpn
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./vpn:/vpn:ro
    environment:
      - VPNCONF=config.ovpn
    restart: unless-stopped
  
  proxytorrent:
    build: .
    container_name: proxytorrent
    network_mode: "service:vpn"  # Весь трафик через VPN
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - vpn
    restart: unless-stopped
```

## Продакшен на VPS

### Шаг 1: Подготовка сервера

```bash
# Подключиться к серверу
ssh root@your-vps-ip

# Обновить систему
apt-get update && apt-get upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com | sh

# Установить Docker Compose
apt-get install -y docker-compose-plugin

# Создать non-root пользователя
adduser proxytorrent
usermod -aG docker proxytorrent
su - proxytorrent
```

### Шаг 2: Клонирование и конфигурация

```bash
# Клонировать репозиторий
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent

# Создать .env для продакшена
cat > .env << 'EOF'
# === БЕЗОПАСНОСТЬ ===
SECURITY__AUTH_ENABLED=true
SECURITY__HMAC_SECRET=$(openssl rand -hex 32)

# === PROXY/VPN ===
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=your-vpn-host
PROXY__PROXY_PORT=1080
# PROXY__PROXY_USERNAME=user
# PROXY__PROXY_PASSWORD=pass

# === БАЗА ДАННЫХ ===
DATABASE__DATABASE_URL=postgresql+asyncpg://proxytorrent:CHANGE_THIS_PASSWORD@postgres:5432/proxytorrent
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD

# === ХРАНИЛИЩЕ ===
STORAGE__BASE_PATH=/app/data

# === ТОРРЕНТЫ ===
TORRENT__PRIVATE_TRACKER=true
TORRENT__ENCRYPTION_ENABLED=true
# TORRENT__ANNOUNCE_URL=https://tracker.example.com/announce

# === МОНИТОРИНГ ===
MONITORING__LOG_LEVEL=INFO
MONITORING__JSON_LOGS=true
MONITORING__MASK_SENSITIVE=true

# === API ===
DEBUG=false
EOF

# Отредактировать (заменить CHANGE_THIS_PASSWORD и т.д.)
nano .env

# Установить права
chmod 600 .env
```

### Шаг 3: Запуск сервиса

```bash
# Запустить с PostgreSQL
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Проверить логи
docker-compose logs -f proxytorrent

# Проверить health
curl http://localhost:8000/v1/health
```

### Шаг 4: Nginx Reverse Proxy

```bash
# Установить Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Создать конфигурацию
sudo nano /etc/nginx/sites-available/proxytorrent
```

**Содержимое:**
```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    listen 80;
    server_name api.proxytorrent.example.com;
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name api.proxytorrent.example.com;
    
    # SSL (Let's Encrypt заполнит автоматически)
    ssl_certificate /etc/letsencrypt/live/api.proxytorrent.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.proxytorrent.example.com/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate limiting
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }
}
```

```bash
# Активировать конфигурацию
sudo ln -s /etc/nginx/sites-available/proxytorrent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Получить SSL сертификат
sudo certbot --nginx -d api.proxytorrent.example.com

# Проверить
curl https://api.proxytorrent.example.com/v1/health
```

### Шаг 5: Firewall

```bash
# Установить UFW
sudo apt-get install -y ufw

# Правила
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Не открывать app порт

# Активировать
sudo ufw enable

# Проверить статус
sudo ufw status
```

## Развёртывание с VPN/прокси

### Вариант 1: Внешний SOCKS5 прокси

```bash
# В .env
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=vpn.example.com
PROXY__PROXY_PORT=1080
PROXY__PROXY_USERNAME=user
PROXY__PROXY_PASSWORD=password
```

### Вариант 2: OpenVPN контейнер

```bash
# 1. Подготовить VPN config
mkdir vpn
cp your-config.ovpn vpn/config.ovpn

# 2. Обновить docker-compose.yml (см. выше пример с VPN)

# 3. Запустить
docker-compose up -d

# 4. Проверить VPN подключение
docker-compose exec vpn curl -s https://ifconfig.me
# Должен показать IP VPN-сервера, а не ваш
```

### Вариант 3: Wireguard

```yaml
services:
  wireguard:
    image: linuxserver/wireguard
    container_name: proxytorrent-wg
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    environment:
      - PUID=1000
      - PGID=1000
    volumes:
      - ./wireguard:/config
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
    restart: unless-stopped
  
  proxytorrent:
    network_mode: "service:wireguard"
    # ...
```

## Обновление

### Обновление до новой версии

```bash
cd proxytorrent

# 1. Остановить сервис
docker-compose down

# 2. Сделать backup
./scripts/backup.sh  # или вручную:
tar -czf backup-$(date +%Y%m%d).tar.gz data/ .env

# 3. Получить обновления
git pull origin main

# 4. Пересобрать образы
docker-compose build --no-cache

# 5. Запустить
docker-compose up -d

# 6. Проверить логи
docker-compose logs -f proxytorrent

# 7. Проверить health
curl http://localhost:8000/v1/health
```

### Rollback (откат)

```bash
# 1. Остановить
docker-compose down

# 2. Вернуться к предыдущей версии
git checkout <previous-commit-or-tag>

# 3. Пересобрать
docker-compose build --no-cache

# 4. Восстановить данные из backup (если нужно)
tar -xzf backup-20251213.tar.gz

# 5. Запустить
docker-compose up -d
```

## Мониторинг и обслуживание

### Логи

```bash
# Все логи
docker-compose logs -f

# Только proxytorrent
docker-compose logs -f proxytorrent

# Последние 100 строк
docker-compose logs --tail=100 proxytorrent

# Фильтр по уровню
docker-compose logs proxytorrent | grep ERROR
docker-compose logs proxytorrent | grep WARNING
```

### Health Checks

```bash
# Вручную
curl http://localhost:8000/v1/health

# Автоматический мониторинг (cron)
cat > /etc/cron.d/proxytorrent-health << 'EOF'
*/5 * * * * curl -f http://localhost:8000/v1/health || echo "ProxyTorrent health check failed" | mail -s "Alert" admin@example.com
EOF
```

### Использование ресурсов

```bash
# Docker stats
docker stats proxytorrent

# Размер данных
du -sh data/

# Количество запросов в БД
docker-compose exec proxytorrent python -c "
from app.core.database import get_db_session
from app.models.database import FetchRequest
import asyncio

async def count():
    async with get_db_session() as db:
        result = await db.execute('SELECT count(*) FROM fetch_requests')
        print(f'Total requests: {result.scalar()}')

asyncio.run(count())
"
```

### Backup

**Скрипт backup:**
```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup .env
cp .env "$BACKUP_DIR/env-$DATE"

# Backup database
if [ "$DB_TYPE" = "postgres" ]; then
    docker-compose exec postgres pg_dump -U proxytorrent proxytorrent > "$BACKUP_DIR/db-$DATE.sql"
else
    cp data/proxytorrent.db "$BACKUP_DIR/db-$DATE.db"
fi

# Backup data
tar -czf "$BACKUP_DIR/data-$DATE.tar.gz" data/

# Удалить старые backup (> 30 дней)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x scripts/backup.sh

# Запустить вручную
./scripts/backup.sh

# Или добавить в cron (ежедневно в 2:00)
echo "0 2 * * * /path/to/proxytorrent/scripts/backup.sh" | crontab -
```

### Восстановление

```bash
# 1. Остановить сервис
docker-compose down

# 2. Восстановить данные
tar -xzf backup-20251213.tar.gz

# 3. Восстановить БД (PostgreSQL)
docker-compose up -d postgres
docker-compose exec -T postgres psql -U proxytorrent proxytorrent < backup-20251213.sql

# 4. Запустить сервис
docker-compose up -d proxytorrent
```

### Очистка старых данных

```bash
# Вручную удалить запросы старше 30 дней
docker-compose exec proxytorrent python -c "
from app.core.database import get_db_session
from app.models.database import FetchRequest
from datetime import datetime, timedelta
import asyncio

async def cleanup():
    async with get_db_session() as db:
        cutoff = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            'DELETE FROM fetch_requests WHERE created_at < :cutoff',
            {'cutoff': cutoff}
        )
        await db.commit()
        print(f'Deleted {result.rowcount} old requests')

asyncio.run(cleanup())
"

# Очистить orphaned контент (без ссылок в БД)
# TODO: написать скрипт
```

## Troubleshooting

### Проблема: Контейнер не стартует

```bash
# Проверить логи
docker-compose logs proxytorrent

# Проверить конфигурацию
docker-compose config

# Проверить права на data/
ls -la data/
chmod 755 data/
```

### Проблема: Не работает прокси

```bash
# Проверить настройки прокси в .env
cat .env | grep PROXY

# Проверить подключение к прокси из контейнера
docker-compose exec proxytorrent curl -x socks5://vpn-host:1080 https://ifconfig.me

# Проверить логи
docker-compose logs proxytorrent | grep -i proxy
```

### Проблема: Ошибки БД

```bash
# PostgreSQL: проверить подключение
docker-compose exec proxytorrent python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://proxytorrent:pass@postgres:5432/proxytorrent')
conn = engine.connect()
print('Connected!')
"

# Пересоздать БД (WARNING: удалит все данные!)
docker-compose down
docker volume rm proxytorrent_postgres_data
docker-compose up -d
```

### Проблема: Нет места на диске

```bash
# Проверить использование
df -h

# Очистить Docker
docker system prune -a --volumes

# Очистить старые запросы (см. выше)
```

## Источники

- **Docker**: [Dockerfile](../../Dockerfile), [docker-compose.yml](../../docker-compose.yml)
- **Конфигурация**: [.env.example](../../.env.example)
- **Документация**: [README.md](../../README.md), [DEPLOYMENT.md](../../DEPLOYMENT.md)

## Проверка/валидация

```bash
# E2E тест после развёртывания
./examples/client.py --url "http://httpbin.org/html" --output test.torrent

# Если успешно — развёртывание прошло успешно
ls -lh test.torrent
```

## Связанные главы

- [Конфигурация](./06_configuration_reference.md) — все настройки
- [Безопасность](./08_security_model.md) — безопасное развёртывание
- [Тестирование](./10_testing_and_ci.md) — проверка перед deploy

## Дополнительная документация

- [DEPLOYMENT.md](../../DEPLOYMENT.md) — детальное руководство по развёртыванию
- [QUICKSTART.md](../../QUICKSTART.md) — быстрый старт
