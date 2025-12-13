# ProxyTorrent

A combined Proxy + BitTorrent service that fetches content through an isolated proxy/VPN, packages it into torrents, and seeds it for requesting clients.

## Features

- **Secure Fetching**: Fetch content through configurable SOCKS5/HTTP proxies or VPN
- **Torrent Packaging**: Automatically create private torrents from fetched content
- **Content Seeding**: Built-in BitTorrent seeder using libtorrent
- **Authentication**: HMAC-SHA256 or Bearer token authentication
- **Rate Limiting**: Per-user and per-IP rate limits
- **Content Deduplication**: Content-addressable storage with SHA256 hashing
- **Async Processing**: Background task queue for efficient request handling
- **Docker Support**: Fully containerized with docker-compose

## Architecture

### Components

1. **API (FastAPI)**: REST endpoints for request management
2. **Task Queue**: Async worker pool for processing fetch requests
3. **Fetcher**: HTTP client with proxy support and security validation
4. **Packager**: Torrent creation and content storage
5. **Seeder**: BitTorrent session for distributing content
6. **Storage**: Content-addressable filesystem storage

### Flow

```
Client → POST /v1/requests → Queue → Fetcher (via Proxy) → Packager → Seeder → Ready
                                                                                  ↓
Client ← GET /v1/requests/{id}/torrent ←──────────────────────────────────────────┘
```

## Documentation

### 📚 Project Handbook

A comprehensive Russian-language handbook is available at **[docs/handbook/](docs/handbook/README.md)**. The handbook covers:

- **Миссия и цели проекта** — why ProxyTorrent exists and what problems it solves
- **Архитектура системы** — detailed architecture with Mermaid diagrams
- **Жизненный цикл запроса** — complete request processing flow
- **API справочник** — all REST endpoints with examples
- **Конфигурация** — comprehensive guide to all settings from `.env.example`
- **Модель данных** — database schema and content-addressable storage
- **Безопасность** — authentication, authorization, and security best practices
- **Развёртывание** — step-by-step deployment guides for dev/staging/production
- **Тестирование** — testing strategy, running tests, and CI/CD
- **Roadmap** — known limitations and future plans
- **История изменений** — PR-based changelog with results and validation

**[→ Перейти к справочнику](docs/handbook/README.md)**

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent
```

2. Create environment file (optional):
```bash
cat > .env << EOF
# Security
HMAC_SECRET=your-secret-key-here
SECURITY__AUTH_ENABLED=false

# Proxy (optional)
PROXY_ENABLED=false
PROXY_TYPE=socks5
PROXY_HOST=your-proxy-host
PROXY_PORT=1080

# Logging
LOG_LEVEL=INFO
EOF
```

3. Start the service:
```bash
docker-compose up -d
```

4. Check health:
```bash
curl http://localhost:8000/v1/health
```

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Run the service:
```bash
cd src
uvicorn app.main:app --reload
```

## API Usage

### Authentication

The service supports two authentication methods:

#### 1. HMAC Signature (Recommended)
```bash
# Compute signature
BODY='{"url":"http://example.com","method":"GET","ttl":3600}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "your-secret-key" | cut -d' ' -f2)

# Make request
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

#### 2. Bearer Token
```bash
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token-here" \
  -d '{"url":"http://example.com","method":"GET","ttl":3600}'
```

### API Endpoints

#### Create Fetch Request
```bash
POST /v1/requests
```

**Request:**
```json
{
  "url": "http://example.com",
  "method": "GET",
  "headers": {
    "User-Agent": "Custom-Agent"
  },
  "body": null,
  "ttl": 3600
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_ready": 60,
  "created_at": "2025-10-20T19:00:00Z"
}
```

#### Get Request Status
```bash
GET /v1/requests/{id}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "url": "http://example.com",
  "method": "GET",
  "created_at": "2025-10-20T19:00:00Z",
  "updated_at": "2025-10-20T19:01:00Z",
  "completed_at": "2025-10-20T19:01:00Z",
  "infohash": "abcdef1234567890abcdef1234567890abcdef12",
  "content_hash": "sha256hash...",
  "content_size": 1024,
  "content_type": "text/html",
  "progress": 100
}
```

#### Download Torrent File
```bash
GET /v1/requests/{id}/torrent
```

Downloads the `.torrent` file for completed requests.

#### Get Magnet Link
```bash
GET /v1/requests/{id}/magnet
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "magnet_link": "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
  "infohash": "abcdef1234567890abcdef1234567890abcdef12"
}
```

#### Cancel Request
```bash
DELETE /v1/requests/{id}
```

Cancels a pending request or marks it as cancelled.

#### Health Check
```bash
GET /v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime": 3600.0,
  "checks": {
    "database": {"status": "healthy"},
    "storage": {"status": "healthy"},
    "task_queue": {"status": "healthy", "queue_size": 0}
  }
}
```

## Configuration

Configuration is managed through environment variables or a `.env` file.

### Security Settings

- `SECURITY__AUTH_ENABLED`: Enable authentication (default: true)
- `SECURITY__HMAC_SECRET`: HMAC secret for request signing
- `SECURITY__BEARER_TOKENS`: Comma-separated list of valid bearer tokens

### Proxy Settings

- `PROXY__PROXY_ENABLED`: Enforce proxy usage (default: true)
- `PROXY__PROXY_TYPE`: Proxy type (http, https, socks5)
- `PROXY__PROXY_HOST`: Proxy host
- `PROXY__PROXY_PORT`: Proxy port
- `PROXY__PROXY_USERNAME`: Proxy username (optional)
- `PROXY__PROXY_PASSWORD`: Proxy password (optional)

### Fetcher Settings

- `FETCHER__CONNECT_TIMEOUT`: Connection timeout in seconds (default: 10)
- `FETCHER__READ_TIMEOUT`: Read timeout in seconds (default: 30)
- `FETCHER__MAX_SIZE`: Maximum response size in bytes (default: 52428800)
- `FETCHER__MIME_WHITELIST`: Allowed MIME types (JSON array)
- `FETCHER__VERIFY_SSL`: Verify SSL certificates (default: true)

### Torrent Settings

- `TORRENT__PRIVATE_TRACKER`: Create private torrents (default: true)
- `TORRENT__PIECE_SIZE`: Torrent piece size in bytes (default: 262144)
- `TORRENT__ANNOUNCE_URL`: Tracker announce URL (optional)
- `TORRENT__ENCRYPTION_ENABLED`: Enable torrent encryption (default: true)
- `TORRENT__UPLOAD_RATE_LIMIT`: Upload rate limit in bytes/sec (default: 0=unlimited)

### Storage Settings

- `STORAGE__BASE_PATH`: Base storage path (default: ./data)
- `STORAGE__CONTENT_PATH`: Content storage path
- `STORAGE__TORRENT_PATH`: Torrent file storage path
- `STORAGE__RESUME_PATH`: Resume data storage path

### Rate Limiting

- `RATE_LIMIT__RATE_LIMIT_ENABLED`: Enable rate limiting (default: true)
- `RATE_LIMIT__REQUESTS_PER_MINUTE`: Max requests per minute per user (default: 60)
- `RATE_LIMIT__REQUESTS_PER_HOUR`: Max requests per hour per user (default: 1000)
- `RATE_LIMIT__REQUESTS_PER_IP_MINUTE`: Max requests per minute per IP (default: 100)

## Deployment

### VPS Deployment

1. **Prepare Server**:
```bash
# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt-get install docker-compose-plugin
```

2. **Clone and Configure**:
```bash
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent

# Create production .env
cp .env.example .env
nano .env  # Edit configuration
```

3. **Start Service**:
```bash
docker-compose up -d
```

4. **Configure Reverse Proxy (Nginx)**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Using with VPN/Proxy

#### Option 1: System Proxy
Configure proxy settings in `.env`:
```bash
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=vpn-gateway
PROXY__PROXY_PORT=1080
```

#### Option 2: OpenVPN Container
Uncomment the VPN service in `docker-compose.yml` and mount your VPN config:
```yaml
vpn:
  image: dperson/openvpn-client
  cap_add:
    - NET_ADMIN
  devices:
    - /dev/net/tun
  volumes:
    - ./vpn:/vpn:ro
  restart: unless-stopped

proxytorrent:
  network_mode: "service:vpn"  # Route through VPN
```

## Development

### Running Tests
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest src/app/tests/ -v

# Run with coverage
pytest src/app/tests/ -v --cov=app --cov-report=html
```

### Linting
```bash
# Run ruff
ruff check src/

# Run mypy
mypy src/
```

### Code Formatting
```bash
# Format with black
black src/

# Sort imports
isort src/
```

## Security Considerations

1. **Always enable authentication in production**: Set `SECURITY__AUTH_ENABLED=true`
2. **Use strong HMAC secrets**: Generate with `openssl rand -hex 32`
3. **Enable SSL/TLS**: Use a reverse proxy with HTTPS
4. **Enforce proxy usage**: Set `PROXY__PROXY_ENABLED=true` to ensure all requests go through proxy
5. **Limit MIME types**: Configure `FETCHER__MIME_WHITELIST` to only allow required content types
6. **Set rate limits**: Adjust rate limiting settings based on your use case
7. **Private torrents**: Keep `TORRENT__PRIVATE_TRACKER=true` for security
8. **SSL verification**: Keep `FETCHER__VERIFY_SSL=true` to prevent MITM attacks

## Monitoring

### Logs
```bash
# View logs
docker-compose logs -f proxytorrent

# View specific component logs
docker-compose logs -f proxytorrent | grep "Fetcher"
```

### Metrics
Prometheus metrics are available at `/metrics` (if enabled).

### Health Checks
Regular health checks ensure service availability:
```bash
curl http://localhost:8000/v1/health
```

## Troubleshooting

### Common Issues

1. **Libtorrent import errors**:
   - Ensure libtorrent is properly installed
   - Check Python version compatibility (3.11+)

2. **Proxy connection failures**:
   - Verify proxy credentials
   - Check network connectivity to proxy
   - Review proxy logs

3. **Database errors**:
   - Check database file permissions
   - Ensure data directory exists and is writable

4. **Torrent creation failures**:
   - Verify storage paths are writable
   - Check disk space availability

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/NickScherbakov/proxytorrent/issues
- Documentation: See docs/ directory