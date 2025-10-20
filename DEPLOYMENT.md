# Deployment Guide

This guide covers various deployment scenarios for the ProxyTorrent service.

## Table of Contents
- [Docker Deployment](#docker-deployment)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Systemd Service](#systemd-service)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Production Checklist](#production-checklist)

## Docker Deployment

### Build the Image
```bash
docker build -t proxytorrent:latest .
```

### Run the Container
```bash
docker run -d \
  --name proxytorrent \
  -p 8080:8080 \
  -e PROXY_HOST=your-proxy.com \
  -e PROXY_PORT=1080 \
  -e PROXY_TYPE=socks5 \
  -v $(pwd)/data/downloads:/data/downloads \
  -v $(pwd)/data/torrents:/data/torrents \
  proxytorrent:latest
```

### View Logs
```bash
docker logs -f proxytorrent
```

## Docker Compose Deployment

### Basic Setup
```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit configuration
nano .env

# 3. Start service
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f
```

### Production Setup with Traefik
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  proxytorrent:
    build: .
    environment:
      - HOST=0.0.0.0
      - PORT=8080
    volumes:
      - ./data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.proxytorrent.rule=Host(`proxytorrent.example.com`)"
      - "traefik.http.routers.proxytorrent.tls=true"
      - "traefik.http.routers.proxytorrent.tls.certresolver=letsencrypt"
    networks:
      - traefik
    restart: unless-stopped

networks:
  traefik:
    external: true
```

Deploy:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Systemd Service

### Install Dependencies
```bash
# Create virtual environment
python3 -m venv /opt/proxytorrent/venv
source /opt/proxytorrent/venv/bin/activate
pip install -r requirements.txt
```

### Create Service File
Create `/etc/systemd/system/proxytorrent.service`:
```ini
[Unit]
Description=ProxyTorrent Service
After=network.target

[Service]
Type=simple
User=proxytorrent
Group=proxytorrent
WorkingDirectory=/opt/proxytorrent
Environment="PATH=/opt/proxytorrent/venv/bin"
ExecStart=/opt/proxytorrent/venv/bin/python server.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### Enable and Start
```bash
# Create user
sudo useradd -r -s /bin/false proxytorrent

# Set permissions
sudo chown -R proxytorrent:proxytorrent /opt/proxytorrent

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable proxytorrent
sudo systemctl start proxytorrent

# Check status
sudo systemctl status proxytorrent

# View logs
sudo journalctl -u proxytorrent -f
```

## Kubernetes Deployment

### ConfigMap
Create `k8s/configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: proxytorrent-config
data:
  HOST: "0.0.0.0"
  PORT: "8080"
  SEED_TIME_HOURS: "24"
```

### Secret
Create `k8s/secret.yaml`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: proxytorrent-secret
type: Opaque
stringData:
  PROXY_HOST: "your-proxy.com"
  PROXY_PORT: "1080"
  PROXY_TYPE: "socks5"
  PROXY_USERNAME: "username"
  PROXY_PASSWORD: "password"
```

### Deployment
Create `k8s/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: proxytorrent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: proxytorrent
  template:
    metadata:
      labels:
        app: proxytorrent
    spec:
      containers:
      - name: proxytorrent
        image: proxytorrent:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: proxytorrent-config
        - secretRef:
            name: proxytorrent-secret
        volumeMounts:
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: proxytorrent-pvc
```

### Service
Create `k8s/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: proxytorrent
spec:
  selector:
    app: proxytorrent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### PersistentVolumeClaim
Create `k8s/pvc.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: proxytorrent-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

### Deploy to Kubernetes
```bash
kubectl apply -f k8s/
kubectl get pods -l app=proxytorrent
kubectl logs -f deployment/proxytorrent
```

## Production Checklist

### Security
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificates
- [ ] Implement authentication
- [ ] Configure rate limiting
- [ ] Enable security headers
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Audit logs enabled

### Performance
- [ ] Configure appropriate resource limits
- [ ] Set up load balancing (if needed)
- [ ] Configure caching (if applicable)
- [ ] Optimize disk I/O
- [ ] Monitor bandwidth usage

### Reliability
- [ ] Set up automatic backups
- [ ] Configure health checks
- [ ] Implement graceful shutdown
- [ ] Set up log rotation
- [ ] Configure restart policies
- [ ] Test disaster recovery

### Monitoring
- [ ] Application metrics
- [ ] System metrics (CPU, RAM, Disk)
- [ ] Network metrics
- [ ] Error tracking
- [ ] Performance monitoring

### Recommended Tools
- **Reverse Proxy**: nginx, Traefik, Caddy
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack, Loki
- **Alerting**: AlertManager, PagerDuty
- **Backup**: Restic, Velero (K8s)

## Environment-Specific Notes

### Development
```bash
# Run without Docker
python3 server.py

# Run with auto-reload (requires watchdog)
pip install watchdog
watchmedo auto-restart --patterns="*.py" --recursive python3 server.py
```

### Staging
- Use separate proxy configuration
- Reduced seed times for testing
- Limited storage quotas
- Full logging enabled

### Production
- Production-grade proxy/VPN
- Appropriate seed times (24+ hours)
- Sufficient storage capacity
- Structured logging (JSON)
- Health checks every 30s
- Automatic restarts on failure

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8080
sudo lsof -i :8080
# or
sudo netstat -tlnp | grep 8080

# Kill the process
sudo kill -9 <PID>
```

### Permission Denied
```bash
# Fix directory permissions
sudo chown -R $USER:$USER /tmp/proxytorrent
chmod 755 /tmp/proxytorrent
```

### Out of Disk Space
```bash
# Check disk usage
df -h

# Clean old torrents manually
find /tmp/proxytorrent/downloads -mtime +7 -delete
find /tmp/proxytorrent/torrents -mtime +7 -delete
```

### Proxy Connection Issues
```bash
# Test proxy connectivity
curl --socks5 proxy-host:1080 https://api.ipify.org

# Check proxy credentials
# Verify PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD in .env
```

## Support

For issues or questions:
1. Check the logs first
2. Review SECURITY.md for security concerns
3. Open an issue on GitHub
4. Include relevant logs and configuration (remove sensitive data)
