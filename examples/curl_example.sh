#!/bin/bash
# Example shell script demonstrating API usage with curl

BASE_URL="${BASE_URL:-http://localhost:8000}"
HMAC_SECRET="${HMAC_SECRET:-change-me-in-production}"

echo "ProxyTorrent API Example"
echo "========================"
echo ""

# Function to compute HMAC signature
compute_signature() {
    local body="$1"
    echo -n "$body" | openssl dgst -sha256 -hmac "$HMAC_SECRET" | cut -d' ' -f2
}

# Step 1: Create a fetch request
echo "1. Creating fetch request..."
BODY='{"url":"http://httpbin.org/html","method":"GET","ttl":3600}'
SIGNATURE=$(compute_signature "$BODY")

RESPONSE=$(curl -s -X POST "$BASE_URL/v1/requests" \
    -H "Content-Type: application/json" \
    -H "X-Signature: $SIGNATURE" \
    -d "$BODY")

REQUEST_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$REQUEST_ID" ]; then
    echo "✗ Failed to create request"
    echo "$RESPONSE"
    exit 1
fi

echo "✓ Request created: $REQUEST_ID"
echo ""

# Step 2: Monitor status
echo "2. Monitoring status..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    EMPTY_SIG=$(compute_signature "")
    STATUS_RESPONSE=$(curl -s "$BASE_URL/v1/requests/$REQUEST_ID" \
        -H "X-Signature: $EMPTY_SIG")
    
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    PROGRESS=$(echo "$STATUS_RESPONSE" | grep -o '"progress":[0-9]*' | cut -d':' -f2)
    
    echo "  Status: $STATUS (Progress: $PROGRESS%)"
    
    if [ "$STATUS" = "ready" ]; then
        echo "✓ Request completed!"
        break
    elif [ "$STATUS" = "error" ]; then
        echo "✗ Request failed"
        echo "$STATUS_RESPONSE"
        exit 1
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "✗ Timeout waiting for completion"
    exit 1
fi

echo ""

# Step 3: Get magnet link
echo "3. Getting magnet link..."
EMPTY_SIG=$(compute_signature "")
MAGNET_RESPONSE=$(curl -s "$BASE_URL/v1/requests/$REQUEST_ID/magnet" \
    -H "X-Signature: $EMPTY_SIG")

MAGNET_LINK=$(echo "$MAGNET_RESPONSE" | grep -o '"magnet_link":"[^"]*' | cut -d'"' -f4)
echo "✓ Magnet link: $MAGNET_LINK"
echo ""

# Step 4: Download torrent file
echo "4. Downloading torrent file..."
EMPTY_SIG=$(compute_signature "")
curl -s "$BASE_URL/v1/requests/$REQUEST_ID/torrent" \
    -H "X-Signature: $EMPTY_SIG" \
    -o "output.torrent"

if [ -f "output.torrent" ]; then
    SIZE=$(stat -f%z "output.torrent" 2>/dev/null || stat -c%s "output.torrent" 2>/dev/null)
    echo "✓ Torrent saved: output.torrent ($SIZE bytes)"
else
    echo "✗ Failed to download torrent"
    exit 1
fi

echo ""
echo "✓ Done!"
