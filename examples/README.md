# ProxyTorrent Examples

This directory contains example scripts demonstrating how to use the ProxyTorrent API.

## Examples

### 1. Python Client (`client.py`)

A complete Python client demonstrating all API operations.

**Requirements:**
```bash
pip install requests
```

**Usage:**
```bash
# Without authentication (for testing)
./client.py --url "http://example.com" --output example.torrent

# With HMAC authentication
./client.py \
    --url "http://example.com" \
    --hmac-secret "your-secret-key" \
    --output example.torrent

# Custom API endpoint
./client.py \
    --url "http://example.com" \
    --base-url "http://your-server:8000" \
    --output example.torrent
```

**What it does:**
1. Creates a fetch request
2. Monitors progress until completion
3. Retrieves the magnet link
4. Downloads the torrent file

### 2. Shell Script (`curl_example.sh`)

A bash script using curl for API interaction.

**Requirements:**
- `curl`
- `openssl`

**Usage:**
```bash
# Set environment variables
export BASE_URL="http://localhost:8000"
export HMAC_SECRET="your-secret-key"

# Run script
./curl_example.sh
```

**What it does:**
1. Creates a fetch request with HMAC signature
2. Polls status until ready
3. Gets magnet link
4. Downloads torrent file to `output.torrent`

## API Endpoints

### Create Request
```bash
POST /v1/requests
Content-Type: application/json
X-Signature: <hmac-sha256-signature>

{
  "url": "http://example.com",
  "method": "GET",
  "ttl": 3600
}
```

### Get Status
```bash
GET /v1/requests/{id}
X-Signature: <hmac-sha256-signature>
```

### Get Magnet Link
```bash
GET /v1/requests/{id}/magnet
X-Signature: <hmac-sha256-signature>
```

### Download Torrent
```bash
GET /v1/requests/{id}/torrent
X-Signature: <hmac-sha256-signature>
```

### Cancel Request
```bash
DELETE /v1/requests/{id}
X-Signature: <hmac-sha256-signature>
```

### Health Check
```bash
GET /v1/health
```

## HMAC Authentication

To compute the HMAC signature:

**Python:**
```python
import hashlib
import hmac
import json

payload = {"url": "http://example.com", "method": "GET", "ttl": 3600}
body = json.dumps(payload)
signature = hmac.new(
    secret.encode(),
    body.encode(),
    hashlib.sha256
).hexdigest()
```

**Shell:**
```bash
BODY='{"url":"http://example.com","method":"GET","ttl":3600}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "your-secret" | cut -d' ' -f2)
```

## Testing Without Authentication

For testing purposes, you can disable authentication:

```bash
# In .env or docker-compose.yml
SECURITY__AUTH_ENABLED=false
```

Then make requests without the `X-Signature` header:

```bash
curl -X POST http://localhost:8000/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.com","method":"GET","ttl":3600}'
```

## Notes

- The examples assume the service is running on `http://localhost:8000`
- For production use, always enable authentication
- Use HTTPS in production environments
- Adjust timeouts based on expected fetch duration
