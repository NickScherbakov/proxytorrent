# ProxyTorrent - Quick Start Guide

Get ProxyTorrent up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- 2GB+ RAM available
- Internet connection

## 1. Clone Repository

```bash
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent
```

## 2. Start Service

For **testing/development** (no authentication):

```bash
docker-compose up -d
```

For **production** (with authentication):

```bash
# Create .env file
cp .env.example .env

# Edit configuration (set SECURITY__AUTH_ENABLED=true)
nano .env

# Start service
docker-compose up -d
```

## 3. Verify Service

```bash
# Check health
curl http://localhost:8000/v1/health

# Expected output:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "uptime": 5.23,
#   "checks": { ... }
# }
```

## 4. Create Your First Request

### Without Authentication (Development)

```bash
# Create fetch request
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://httpbin.org/html",
    "method": "GET",
    "ttl": 3600
  }'

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "estimated_ready": 60,
#   "created_at": "2025-10-20T19:00:00Z"
# }
```

### With Authentication (Production)

```bash
# Set your secret from .env
HMAC_SECRET="your-secret-from-env-file"

# Create request body
BODY='{"url":"http://httpbin.org/html","method":"GET","ttl":3600}'

# Compute signature
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$HMAC_SECRET" | cut -d' ' -f2)

# Make authenticated request
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

## 5. Monitor Progress

```bash
# Replace with your request ID
REQUEST_ID="550e8400-e29b-41d4-a716-446655440000"

# Check status
curl http://localhost:8000/v1/requests/$REQUEST_ID

# Response shows progress:
# {
#   "id": "...",
#   "status": "ready",  # queued → fetching → packaging → seeding → ready
#   "progress": 100,
#   ...
# }
```

## 6. Download Torrent

Once status is "ready":

```bash
# Get magnet link
curl http://localhost:8000/v1/requests/$REQUEST_ID/magnet

# Response:
# {
#   "id": "...",
#   "magnet_link": "magnet:?xt=urn:btih:...",
#   "infohash": "..."
# }

# Download .torrent file
curl http://localhost:8000/v1/requests/$REQUEST_ID/torrent \
  -o downloaded.torrent
```

## 7. Use Example Scripts

### Python Client

```bash
# Install requests
pip install requests

# Run client
./examples/client.py \
  --url "http://example.com" \
  --output example.torrent

# With authentication
./examples/client.py \
  --url "http://example.com" \
  --hmac-secret "your-secret" \
  --output example.torrent
```

### Shell Script

```bash
# Set environment
export BASE_URL="http://localhost:8000"
export HMAC_SECRET="your-secret"

# Run script
./examples/curl_example.sh
```

## Common Commands

### View Logs
```bash
docker-compose logs -f proxytorrent
```

### Stop Service
```bash
docker-compose down
```

### Restart Service
```bash
docker-compose restart proxytorrent
```

### Update Service
```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs proxytorrent

# Verify permissions
ls -la data/
```

### Can't connect
```bash
# Check if running
docker-compose ps

# Test from inside container
docker-compose exec proxytorrent curl -I http://localhost:8000/v1/health
```

### Authentication errors
```bash
# Verify auth is disabled for testing
grep AUTH_ENABLED docker-compose.yml

# Or check .env
cat .env | grep AUTH_ENABLED
```

## Next Steps

- 📖 Read [README.md](README.md) for full documentation
- 🚀 See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- 🏗️ Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- 🔒 Review [SECURITY.md](SECURITY.md) for security best practices

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/requests` | POST | Create fetch request |
| `/v1/requests/{id}` | GET | Get status |
| `/v1/requests/{id}/torrent` | GET | Download .torrent |
| `/v1/requests/{id}/magnet` | GET | Get magnet link |
| `/v1/requests/{id}` | DELETE | Cancel request |
| `/v1/health` | GET | Health check |

## Configuration Quick Reference

Set in `.env` or `docker-compose.yml`:

```bash
# Security
SECURITY__AUTH_ENABLED=false          # Disable for testing
SECURITY__HMAC_SECRET=your-secret     # Set strong secret

# Proxy (optional)
PROXY__PROXY_ENABLED=false            # Enable for VPN/proxy
PROXY__PROXY_TYPE=socks5              # socks5, http, https
PROXY__PROXY_HOST=your-proxy-host
PROXY__PROXY_PORT=1080

# Limits
FETCHER__MAX_SIZE=52428800           # 50 MiB
FETCHER__CONNECT_TIMEOUT=10          # seconds
FETCHER__READ_TIMEOUT=30             # seconds

# Rate Limiting
RATE_LIMIT__REQUESTS_PER_MINUTE=60
RATE_LIMIT__REQUESTS_PER_HOUR=1000
```

## Support

- **Issues**: https://github.com/NickScherbakov/proxytorrent/issues
- **Discussions**: Use GitHub Discussions
- **Security**: See [SECURITY.md](SECURITY.md)

---

**Happy torrenting! 🎉**
