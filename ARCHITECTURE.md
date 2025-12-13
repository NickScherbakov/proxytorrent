# ProxyTorrent Architecture

This document provides a detailed overview of the ProxyTorrent system architecture.

## System Overview

ProxyTorrent is a service that fetches content through proxies/VPNs and distributes it via BitTorrent. It provides a RESTful API for creating fetch requests, monitoring progress, and downloading torrent files.

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                              │
│                    (HTTP/HTTPS API)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Server                          │
│  ┌───────────┬──────────────┬──────────────┬─────────────┐ │
│  │   Auth    │ Rate Limit   │   Logging    │   Metrics   │ │
│  │Middleware │  Middleware  │              │             │ │
│  └───────────┴──────────────┴──────────────┴─────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              API Endpoints                            │ │
│  │  /requests, /health, /torrent, /magnet               │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Task Queue                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Worker N │  │
│  └─────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└────────┼────────────┼─────────────┼─────────────┼──────────┘
         │            │             │             │
         ▼            ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                           │
│  ┌──────────────┬──────────────┬─────────────────────────┐ │
│  │   Fetcher    │  Packager    │      Seeder             │ │
│  │ (HTTP Client)│  (Torrent    │  (libtorrent Session)   │ │
│  │              │   Creator)   │                         │ │
│  └──────┬───────┴──────┬───────┴──────┬──────────────────┘ │
└─────────┼──────────────┼──────────────┼────────────────────┘
          │              │              │
          ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  Proxy  │    │ Storage │    │ Torrent │
    │   VPN   │    │ Backend │    │  Peers  │
    └─────────┘    └─────────┘    └─────────┘
```

## Core Components

### 1. FastAPI Application (`src/app/main.py`)

**Responsibilities:**
- HTTP server management
- Request routing
- Middleware orchestration
- Lifecycle management (startup/shutdown)

**Key Features:**
- Async request handling
- CORS support
- OpenAPI documentation
- Health checks

### 2. API Layer (`src/app/api/`)

#### Authentication (`auth.py`)
- HMAC-SHA256 signature verification
- Bearer token validation
- Client IP extraction

#### Rate Limiting (`ratelimit.py`)
- Per-user rate limits
- Per-IP rate limits
- In-memory counter storage
- Sliding window algorithm

#### Request Endpoints (`requests.py`)
- POST `/v1/requests` - Create fetch request
- GET `/v1/requests/{id}` - Get status
- GET `/v1/requests/{id}/torrent` - Download .torrent
- GET `/v1/requests/{id}/magnet` - Get magnet link
- DELETE `/v1/requests/{id}` - Cancel request

#### Health Endpoint (`health.py`)
- Service health status
- Component checks (database, storage, queue)
- Uptime tracking

### 3. Data Models (`src/app/models/`)

#### Pydantic Schemas (`schemas.py`)
- Request/response validation
- Type safety
- Automatic documentation

**Key Models:**
- `CreateRequestPayload` - Fetch request input
- `RequestStatusResponse` - Status information
- `MagnetLinkResponse` - Magnet URI
- `HealthResponse` - Health check data

#### Database Models (`database.py`)
- SQLAlchemy ORM models
- `FetchRequest` table
- Async database support

### 4. Configuration (`src/app/core/config.py`)

Environment-based configuration using Pydantic Settings:

**Settings Groups:**
- `SecuritySettings` - Auth, secrets
- `ProxySettings` - Proxy/VPN config
- `FetcherSettings` - HTTP client config
- `TorrentSettings` - Torrent creation/seeding
- `StorageSettings` - File storage paths
- `CacheSettings` - TTL and Redis
- `RateLimitSettings` - Rate limit thresholds
- `DatabaseSettings` - Database connection
- `MonitoringSettings` - Logging and metrics

### 5. Services Layer (`src/app/services/`)

#### Fetcher (`fetcher.py`)

**Purpose:** Fetch content through proxy with security validation

**Features:**
- SOCKS5/HTTP proxy support
- Timeout enforcement
- Size limit validation
- MIME type whitelist
- SSL certificate verification
- Content hashing (SHA256)

**Flow:**
```python
1. Create aiohttp session with proxy
2. Make HTTP request
3. Validate MIME type
4. Stream content with size checks
5. Compute content hash
6. Return FetchResult
```

#### Packager (`packager.py`)

**Purpose:** Package fetched content into BitTorrent files

**Features:**
- Content-addressable storage
- Torrent file creation (libtorrent)
- Metadata persistence
- Deduplication via content hash
- Private torrent support

**Storage Structure:**
```
data/
├── content/
│   └── ab/
│       └── cd/
│           ├── content          # Raw content
│           └── metadata.json    # Content metadata
├── torrents/
│   └── abcd...hash.torrent     # Torrent files
└── resume/
    └── infohash.resume         # Resume data
```

**Flow:**
```python
1. Save content to content-addressable path
2. Create torrent file with libtorrent
3. Set private flag and tracker
4. Generate and save .torrent file
5. Return TorrentPackage with infohash
```

#### Seeder (`seeder.py`)

**Purpose:** Seed torrents using libtorrent

**Features:**
- libtorrent session management
- Private torrent seeding
- Resume data persistence
- Encryption support
- Rate limiting
- Connection limits

**Configuration:**
```python
{
    "enable_dht": False,           # Private torrents
    "enable_lsd": False,           # Disable LSD
    "anonymous_mode": True,        # Enhanced privacy
    "upload_rate_limit": 0,        # Configurable
    "encryption": "enabled"        # Force encryption
}
```

### 6. Task Queue (`src/app/tasks/queue.py`)

**Purpose:** Async processing of fetch requests

**Features:**
- Worker pool management
- Async task execution
- Error handling and retry logic
- Progress tracking
- Graceful shutdown

**Processing Flow:**
```
1. Dequeue request ID
2. Update status: QUEUED → FETCHING
3. Fetch content (via proxy)
4. Update status: FETCHING → PACKAGING
5. Package into torrent
6. Update status: PACKAGING → SEEDING
7. Add to seeder
8. Update status: SEEDING → READY
9. Handle errors, update accordingly
```

### 7. Database Layer (`src/app/core/database.py`)

**Purpose:** Async database connection management

**Features:**
- SQLAlchemy async engine
- Session management
- Connection pooling
- SQLite (MVP) / PostgreSQL (production)

**Schema:**
```sql
CREATE TABLE fetch_requests (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    url TEXT NOT NULL,
    method VARCHAR(10) NOT NULL,
    headers JSON,
    body TEXT,
    ttl INTEGER NOT NULL,
    content_hash VARCHAR(64),
    content_size INTEGER,
    content_type VARCHAR(255),
    infohash VARCHAR(40),
    torrent_path TEXT,
    error_message TEXT,
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    completed_at DATETIME,
    user_id VARCHAR(255),
    client_ip VARCHAR(45)
);
```

## Data Flow

### Complete Request Flow

```
1. Client Request
   ├─> POST /v1/requests
   ├─> Validate payload
   ├─> Check authentication
   └─> Check rate limits

2. Request Creation
   ├─> Generate UUID
   ├─> Save to database (status: QUEUED)
   ├─> Enqueue task
   └─> Return request ID

3. Task Processing (Worker)
   ├─> Update status: FETCHING
   ├─> Fetch via proxy
   │   ├─> Validate MIME
   │   ├─> Check size
   │   └─> Compute hash
   ├─> Update status: PACKAGING
   ├─> Save content (content-addressable)
   ├─> Create .torrent file
   ├─> Update status: SEEDING
   ├─> Add to seeder
   └─> Update status: READY

4. Client Retrieval
   ├─> GET /v1/requests/{id}
   │   └─> Return status + metadata
   ├─> GET /v1/requests/{id}/torrent
   │   └─> Download .torrent file
   └─> GET /v1/requests/{id}/magnet
       └─> Return magnet link
```

## Security Architecture

### Authentication Flow

```
Client
  │
  ├─> Prepare request body
  ├─> Compute HMAC-SHA256(secret, body)
  ├─> Add X-Signature header
  │
  ▼
Server
  │
  ├─> Extract X-Signature
  ├─> Read request body
  ├─> Compute expected signature
  ├─> Compare signatures (constant-time)
  │
  ├─> ✓ Valid → Process request
  └─> ✗ Invalid → 401 Unauthorized
```

### Proxy Enforcement

```
Fetch Request
  │
  ├─> Check PROXY__PROXY_ENABLED
  │   └─> If false: Direct connection (unsafe)
  │   └─> If true: Enforce proxy
  │
  ├─> Create aiohttp connector
  │   └─> ProxyConnector(proxy_url)
  │
  ├─> Make request through proxy
  │   ├─> Connect timeout: 10s
  │   ├─> Read timeout: 30s
  │   └─> Verify SSL: true
  │
  └─> Return result
```

### Security Layers

1. **Network Security**
   - All fetches through proxy/VPN
   - SSL/TLS verification
   - Private torrent tracking

2. **Application Security**
   - HMAC authentication
   - Rate limiting
   - Input validation
   - Size limits

3. **Data Security**
   - Content-addressable storage
   - Sensitive data masking in logs
   - Secure secret management

## Scalability Considerations

### Horizontal Scaling

The architecture supports horizontal scaling:

1. **API Layer**
   - Stateless design
   - Can run multiple instances behind load balancer

2. **Task Queue**
   - Each instance has its own worker pool
   - Redis can be added for distributed queue

3. **Database**
   - PostgreSQL supports connection pooling
   - Read replicas for status queries

4. **Storage**
   - Content-addressable storage prevents duplication
   - Can be moved to S3-compatible backend

### Performance Optimizations

1. **Async I/O**
   - Non-blocking HTTP requests
   - Concurrent task processing
   - Async database operations

2. **Caching**
   - Content deduplication via hashing
   - TTL-based result caching
   - Optional Redis integration

3. **Resource Limits**
   - Configurable worker pool size
   - Connection limits per service
   - Rate limiting to prevent abuse

## Monitoring and Observability

### Logging

- Structured JSON logs
- Sensitive data masking
- Request/response tracking
- Error logging with stack traces

### Health Checks

- Component-level health checks
- Database connectivity
- Storage availability
- Task queue status

### Metrics (Planned)

- Request count
- Request duration
- Error rates
- Queue depth
- Active torrents
- Upload/download rates

## Technology Stack

### Core
- **Python 3.11+** - Modern async features
- **FastAPI** - High-performance web framework
- **Uvicorn** - ASGI server
- **SQLAlchemy 2.x** - Async ORM
- **Pydantic 2.x** - Data validation

### Services
- **aiohttp** - Async HTTP client
- **aiohttp-socks** - SOCKS5 proxy support
- **libtorrent** - BitTorrent implementation

### Storage
- **SQLite** - MVP database
- **PostgreSQL** - Production database (optional)
- **Redis** - Distributed cache (optional)

### Development
- **pytest** - Testing framework
- **ruff** - Fast linter
- **mypy** - Static type checker
- **black** - Code formatter

### Deployment
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

## Future Enhancements

1. **Distributed Queue**
   - Redis/RabbitMQ integration
   - Cross-instance task distribution

2. **Object Storage**
   - S3-compatible backend
   - Reduced local storage needs

3. **Enhanced Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alerting system

4. **Advanced Features**
   - WebSocket for real-time updates
   - Batch request processing
   - Custom tracker support
   - DHT integration (for public torrents)

5. **Performance**
   - Request coalescing
   - Advanced caching strategies
   - CDN integration

## Conclusion

ProxyTorrent provides a secure, scalable architecture for fetching content through proxies and distributing it via BitTorrent. The modular design allows for easy extension and customization while maintaining security and performance.
