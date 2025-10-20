# ProxyTorrent

A combined Proxy + BitTorrent service that fetches content through an isolated proxy/VPN, packages it into a torrent, and seeds it for requesting clients.

## Features

- **Proxy/VPN Support**: Fetch content through SOCKS5/HTTP proxies for privacy and isolation
- **Automatic Torrent Creation**: Downloaded content is automatically packaged into .torrent files
- **Built-in Seeding**: Torrents are automatically seeded for a configurable duration
- **RESTful API**: Simple HTTP API for requesting content and monitoring status
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent
```

2. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your proxy settings
```

3. Start the service:
```bash
docker-compose up -d
```

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env as needed
```

3. Run the server:
```bash
python server.py
```

## API Usage

### Fetch and Create Torrent

Request content to be fetched, packaged as a torrent, and seeded:

```bash
curl -X POST http://localhost:8080/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/file.zip",
    "filename": "myfile.zip",
    "trackers": [
      "udp://tracker.opentrackr.org:1337/announce",
      "udp://open.demonii.com:1337/announce"
    ]
  }'
```

Response:
```json
{
  "success": true,
  "info_hash": "abc123def456...",
  "torrent_file": "/torrents/myfile_abc123de.torrent",
  "message": "Content fetched and seeding started"
}
```

### Check Torrent Status

```bash
curl http://localhost:8080/status/{info_hash}
```

Response:
```json
{
  "info_hash": "abc123def456...",
  "state": "seeding",
  "progress": 1.0,
  "upload_rate": 102400,
  "download_rate": 0,
  "num_peers": 3,
  "num_seeds": 1,
  "total_upload": 1048576,
  "total_download": 0
}
```

### Download Torrent File

```bash
curl -O http://localhost:8080/torrents/{filename}.torrent
```

### Health Check

```bash
curl http://localhost:8080/health
```

## Configuration

Configuration is done via environment variables. See `.env.example` for all options:

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8080` |
| `PROXY_HOST` | Proxy server hostname | (none) |
| `PROXY_PORT` | Proxy server port | (none) |
| `PROXY_TYPE` | Proxy type (socks5/http) | `socks5` |
| `PROXY_USERNAME` | Proxy authentication username | (none) |
| `PROXY_PASSWORD` | Proxy authentication password | (none) |
| `DOWNLOAD_DIR` | Directory for downloaded files | `/tmp/proxytorrent/downloads` |
| `TORRENT_DIR` | Directory for .torrent files | `/tmp/proxytorrent/torrents` |
| `SEED_TIME_HOURS` | Hours to seed each torrent | `24` |
| `MAX_UPLOAD_RATE_KB` | Max upload rate in KB/s (0=unlimited) | `0` |
| `MAX_DOWNLOAD_RATE_KB` | Max download rate in KB/s (0=unlimited) | `0` |

## Architecture

The service consists of three main components:

1. **Fetcher (`fetcher.py`)**: Handles downloading content through the configured proxy
2. **Torrent Manager (`torrent_manager.py`)**: Creates torrents and manages seeding using libtorrent
3. **API Server (`server.py`)**: Provides RESTful API endpoints and coordinates the workflow

### Workflow

1. Client sends a POST request to `/fetch` with a URL
2. Service downloads the content through the configured proxy/VPN
3. Service creates a .torrent file from the downloaded content
4. Service starts seeding the torrent via DHT and optional trackers
5. Client receives the torrent info hash and can download the .torrent file
6. Torrent is automatically unseeded after the configured seed time

## Use Cases

- **Privacy-focused content distribution**: Fetch sensitive content through VPN and distribute via torrent
- **Content mirroring**: Create torrents from web resources for distributed access
- **Bandwidth saving**: Single fetch + multiple torrent downloads reduces origin server load
- **Geo-restricted content**: Use proxy to access region-locked content and redistribute

## Security Considerations

- Always use this service in compliance with applicable laws and terms of service
- Configure proper proxy/VPN to ensure privacy during content fetching
- Consider implementing authentication for the API in production environments
- Be mindful of copyright and licensing when distributing content

## Development

Run tests (when implemented):
```bash
pytest
```

Lint code:
```bash
pylint *.py
```

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.