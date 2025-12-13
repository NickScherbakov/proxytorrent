# ProxyTorrent Deployment Guide

This guide provides step-by-step instructions for deploying ProxyTorrent in various environments.

## Table of Contents

1. [Quick Start (Docker)](#quick-start-docker)
2. [Production Deployment](#production-deployment)
3. [VPS Deployment](#vps-deployment)
4. [Using with VPN](#using-with-vpn)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Quick Start (Docker)

The fastest way to get ProxyTorrent running:

```bash
# Clone repository
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent

# Create environment file
cp .env.example .env

# Start service (development mode, no auth)
docker-compose up -d

# Check health
curl http://localhost:8000/v1/health

# View logs
docker-compose logs -f proxytorrent
```

The service will be available at `http://localhost:8000`.

## Production Deployment

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker and Docker Compose
- Domain name (optional, for HTTPS)
- VPN/Proxy (recommended)

### Step 1: Server Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Reboot to apply changes
sudo reboot
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/NickScherbakov/proxytorrent.git
cd proxytorrent

# Create production environment file
cat > .env << EOF
# Security (IMPORTANT: Change these!)
SECURITY__AUTH_ENABLED=true
SECURITY__HMAC_SECRET=$(openssl rand -hex 32)

# Generate bearer tokens (optional)
# SECURITY__BEARER_TOKENS=token1,token2

# Proxy configuration
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=your-vpn-host
PROXY__PROXY_PORT=1080

# Storage
STORAGE__BASE_PATH=/app/data

# Database (use PostgreSQL for production)
DATABASE__DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/proxytorrent

# Monitoring
MONITORING__LOG_LEVEL=INFO

# Other settings
DEBUG=false
EOF

# Set secure permissions
chmod 600 .env
```

### Step 3: Configure PostgreSQL (Optional but Recommended)

Edit `docker-compose.yml` and uncomment the PostgreSQL service:

```yaml
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
```

### Step 4: Start Services

```bash
# Start in background
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f proxytorrent

# Check health
curl http://localhost:8000/v1/health
```

### Step 5: Configure Reverse Proxy (Nginx)

Install Nginx:
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/proxytorrent
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

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
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
```

Enable configuration:
```bash
sudo ln -s /etc/nginx/sites-available/proxytorrent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 6: Enable HTTPS with Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com
```

Follow the prompts to set up automatic HTTPS.

## VPS Deployment

### Using DigitalOcean

1. **Create Droplet**
   - Choose Ubuntu 22.04 LTS
   - Minimum: 2GB RAM, 1 vCPU, 50GB SSD
   - Recommended: 4GB RAM, 2 vCPU, 80GB SSD

2. **Initial Setup**
```bash
# SSH into droplet
ssh root@your-server-ip

# Create non-root user
adduser proxytorrent
usermod -aG sudo proxytorrent
su - proxytorrent
```

3. **Follow Production Deployment steps above**

### Using AWS EC2

1. **Launch Instance**
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t3.medium or larger
   - Storage: 50GB+ gp3

2. **Security Group Rules**
   - SSH (22): Your IP
   - HTTP (80): 0.0.0.0/0
   - HTTPS (443): 0.0.0.0/0

3. **Connect and Deploy**
```bash
ssh -i your-key.pem ubuntu@ec2-instance-public-ip
# Follow Production Deployment steps
```

## Using with VPN

### Option 1: System VPN

Configure your server to use a VPN connection, then set proxy settings:

```bash
# In .env
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=localhost
PROXY__PROXY_PORT=1080
```

### Option 2: OpenVPN Container

1. **Prepare OpenVPN Config**
```bash
mkdir -p vpn
# Copy your .ovpn file to vpn/config.ovpn
```

2. **Update docker-compose.yml**

Uncomment VPN service and configure proxytorrent to use it:

```yaml
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
  # ... other config ...
  network_mode: "service:vpn"  # Route through VPN
  depends_on:
    - vpn
```

3. **Start Services**
```bash
docker-compose up -d

# Verify VPN connection
docker-compose exec vpn curl -s https://ifconfig.me
```

### Option 3: External SOCKS5 Proxy

Use a separate proxy server:

```bash
# In .env
PROXY__PROXY_ENABLED=true
PROXY__PROXY_TYPE=socks5
PROXY__PROXY_HOST=proxy.example.com
PROXY__PROXY_PORT=1080
PROXY__PROXY_USERNAME=your-username
PROXY__PROXY_PASSWORD=your-password
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check service health
curl http://localhost:8000/v1/health

# Monitor with watch
watch -n 5 'curl -s http://localhost:8000/v1/health | jq'
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f proxytorrent

# Last 100 lines
docker-compose logs --tail=100 proxytorrent

# Filter by level
docker-compose logs proxytorrent | grep ERROR
```

### Backups

```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup database (if using PostgreSQL)
docker-compose exec postgres pg_dump -U proxytorrent proxytorrent > backup.sql
```

### Updates

```bash
# Pull latest code
cd proxytorrent
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
curl http://localhost:8000/v1/health
```

### Resource Monitoring

```bash
# Container resource usage
docker stats proxytorrent

# Disk usage
df -h
du -sh data/

# Clean old data (if needed)
docker-compose exec proxytorrent find /app/data -type f -mtime +30 -delete
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs proxytorrent

# Verify configuration
docker-compose config

# Check permissions
ls -la data/
```

### Connection Issues

```bash
# Test from inside container
docker-compose exec proxytorrent curl -I http://example.com

# Verify proxy
docker-compose exec proxytorrent env | grep PROXY

# Check network
docker network ls
docker network inspect proxytorrent_default
```

### High Memory Usage

```bash
# Adjust worker count in docker-compose.yml
environment:
  - TASK_QUEUE_WORKERS=2  # Reduce workers

# Restart service
docker-compose restart proxytorrent
```

### Database Issues

```bash
# Check database connection
docker-compose exec proxytorrent python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"

# Reset database (WARNING: Deletes all data)
docker-compose down
rm -rf data/proxytorrent.db
docker-compose up -d
```

## Security Hardening

1. **Enable Firewall**
```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

2. **Fail2ban Protection**
```bash
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
```

3. **Regular Updates**
```bash
# System updates
sudo apt-get update && sudo apt-get upgrade -y

# Docker image updates
docker-compose pull
docker-compose up -d
```

4. **Rotate Secrets**
```bash
# Generate new HMAC secret
openssl rand -hex 32

# Update .env
nano .env

# Restart service
docker-compose restart proxytorrent
```

## Performance Tuning

### For High Volume

```yaml
# In docker-compose.yml
proxytorrent:
  environment:
    # Increase workers
    - TASK_QUEUE_WORKERS=10
    
    # Adjust rate limits
    - RATE_LIMIT__REQUESTS_PER_MINUTE=120
    - RATE_LIMIT__REQUESTS_PER_HOUR=5000
    
    # Increase connection limits
    - TORRENT__MAX_CONNECTIONS=500
    
  # Add resource limits
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/NickScherbakov/proxytorrent/issues
- Documentation: See README.md
- Security: See SECURITY.md
