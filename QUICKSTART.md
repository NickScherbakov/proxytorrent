# ProxyTorrent - Quick Start Guide

## What is ProxyTorrent?

ProxyTorrent is a service that fetches content through a proxy/VPN, packages it as a BitTorrent file, and seeds it automatically. It's perfect for:
- Privacy-focused content distribution
- Creating torrents from web resources
- Bandwidth-efficient content sharing
- Geo-restricted content access (with proxy)

## Installation

### Option 1: Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent

# Start the service
docker-compose up -d

# Check if it's running
curl http://localhost:8080/health
```

### Option 2: Python
```bash
# Clone and install
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent
pip install -r requirements.txt

# Run the service
python server.py
```

## Basic Usage

### 1. Fetch and Create Torrent
```bash
curl -X POST http://localhost:8080/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/file.zip",
    "filename": "myfile.zip"
  }'
```

**Response:**
```json
{
  "success": true,
  "info_hash": "abc123def456...",
  "torrent_file": "/torrents/myfile_abc123de.torrent"
}
```

### 2. Download the Torrent File
```bash
curl -O http://localhost:8080/torrents/myfile_abc123de.torrent
```

### 3. Check Status
```bash
curl http://localhost:8080/status/abc123def456...
```

### 4. Use the Torrent
Open the `.torrent` file in your favorite BitTorrent client (qBittorrent, Transmission, etc.)

## Configuration

Edit `.env` or set environment variables:

```bash
# Basic settings
HOST=0.0.0.0
PORT=8080

# Proxy configuration (optional but recommended)
PROXY_HOST=your-vpn-server.com
PROXY_PORT=1080
PROXY_TYPE=socks5
PROXY_USERNAME=user
PROXY_PASSWORD=pass

# Storage
DOWNLOAD_DIR=/tmp/proxytorrent/downloads
TORRENT_DIR=/tmp/proxytorrent/torrents

# Seeding
SEED_TIME_HOURS=24
```

## Common Tasks

### Add Trackers to Improve Connectivity
```bash
curl -X POST http://localhost:8080/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/file.zip",
    "trackers": [
      "udp://tracker.opentrackr.org:1337/announce",
      "udp://open.demonii.com:1337/announce"
    ]
  }'
```

### Use with VPN
1. Set up your VPN/proxy server
2. Configure proxy settings in `.env`
3. Restart the service
4. All fetches now go through the proxy!

### Monitor Active Torrents
```bash
# Health check shows number of active torrents
curl http://localhost:8080/health
```

## Example with Python Client

```python
import requests

# Fetch content
response = requests.post('http://localhost:8080/fetch', json={
    'url': 'https://example.com/file.pdf',
    'filename': 'document.pdf'
})

result = response.json()
print(f"Info hash: {result['info_hash']}")

# Download torrent file
torrent_url = f"http://localhost:8080{result['torrent_file']}"
torrent = requests.get(torrent_url)
with open('document.torrent', 'wb') as f:
    f.write(torrent.content)

print("Torrent file saved! Open it in your BitTorrent client.")
```

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
sudo lsof -i :8080

# View logs
docker-compose logs -f
```

### Cannot fetch URLs
```bash
# Test connectivity
curl https://example.com

# Check proxy settings
cat .env | grep PROXY
```

### Torrent not seeding
- Check firewall settings
- Ensure ports are open for BitTorrent
- Wait a few minutes for DHT to propagate
- Add trackers to the request

## Project Structure

```
proxytorrent/
├── server.py              # Main API server
├── config.py              # Configuration management
├── fetcher.py             # Content fetching with proxy
├── torrent_manager.py     # Torrent creation and seeding
├── example_client.py      # Example usage script
├── test_unit.py           # Unit tests
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image
├── docker-compose.yml     # Docker Compose config
├── README.md              # Full documentation
├── DEPLOYMENT.md          # Deployment guide
└── SECURITY.md            # Security documentation
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/fetch` | Fetch content and create torrent |
| GET | `/status/{info_hash}` | Get torrent status |
| GET | `/torrents/{filename}` | Download .torrent file |
| GET | `/health` | Health check |

## Next Steps

1. **Read the Full Documentation**: Check `README.md` for detailed API reference
2. **Deploy to Production**: See `DEPLOYMENT.md` for deployment guides
3. **Security**: Review `SECURITY.md` for security best practices
4. **Contribute**: Submit issues or PRs on GitHub

## Support

- **Issues**: https://github.com/NickScherbakov/proxytorrent/issues
- **Documentation**: See README.md, DEPLOYMENT.md, SECURITY.md
- **Example**: Run `python example_client.py` for a working example

## Legal Notice

⚠️ **Important**: Only use this service for content you have the right to distribute. Respect copyright laws and terms of service.

---

**ProxyTorrent** - Private fetch, public share 🔒➡️🌐
