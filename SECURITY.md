# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via:
- Email: [maintainer email]
- GitHub Security Advisory (preferred): Use the "Security" tab

### What to Include

When reporting a vulnerability, please include:

1. **Description**: Clear description of the vulnerability
2. **Impact**: Potential impact if exploited
3. **Reproduction**: Steps to reproduce the issue
4. **Environment**: Version, OS, configuration details
5. **Suggested Fix**: If you have ideas for remediation

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Varies by severity (critical: ASAP, high: 2 weeks, medium: 1 month)
- **Disclosure**: After fix is released and users have time to update

## Security Best Practices

### Deployment Security

1. **Always Enable Authentication**
```bash
SECURITY__AUTH_ENABLED=true
SECURITY__HMAC_SECRET=<strong-random-secret>
```

2. **Use HTTPS**
- Deploy behind reverse proxy with SSL/TLS
- Use valid certificates (Let's Encrypt)
- Redirect HTTP to HTTPS

3. **Enforce Proxy Usage**
```bash
PROXY__PROXY_ENABLED=true
PROXY__PROXY_HOST=your-vpn-host
```

4. **Restrict MIME Types**
```bash
FETCHER__MIME_WHITELIST=["text/html","application/json"]
```

5. **Enable SSL Verification**
```bash
FETCHER__VERIFY_SSL=true
```

6. **Set Private Torrents**
```bash
TORRENT__PRIVATE_TRACKER=true
TORRENT__ENCRYPTION_ENABLED=true
```

7. **Configure Rate Limits**
```bash
RATE_LIMIT__RATE_LIMIT_ENABLED=true
RATE_LIMIT__REQUESTS_PER_MINUTE=60
```

### Network Security

1. **Firewall Configuration**
```bash
# Only expose necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8000/tcp  # Don't expose app port directly
```

2. **Use VPN/Proxy**
- Route all fetch requests through VPN
- Use SOCKS5 proxy with authentication
- Verify VPN kill switch is active

3. **Network Isolation**
- Use Docker networks
- Separate data plane from control plane
- Limit container network access

### Data Security

1. **Protect Secrets**
```bash
# Never commit .env files
# Use secret management (Vault, AWS Secrets Manager)
# Rotate secrets regularly
```

2. **File Permissions**
```bash
# Restrict data directory access
chmod 700 data/
chown -R app:app data/
```

3. **Database Security**
- Use PostgreSQL with authentication in production
- Enable SSL for database connections
- Regular backups with encryption

### Application Security

1. **Input Validation**
- All URLs are validated
- Request bodies are size-limited
- Headers are sanitized

2. **Output Encoding**
- Sensitive data masked in logs
- No PII in error messages
- Safe error handling

3. **Authentication**
- HMAC-SHA256 for request signing
- Bearer tokens with sufficient entropy
- Token rotation support

4. **Rate Limiting**
- Per-user limits
- Per-IP limits
- Prevents DoS attacks

### Monitoring

1. **Log Security Events**
```bash
MONITORING__LOG_LEVEL=INFO
MONITORING__MASK_SENSITIVE=true
```

2. **Watch for Anomalies**
- Unusual request patterns
- High error rates
- Failed authentication attempts

3. **Regular Updates**
```bash
# Keep dependencies updated
pip install --upgrade -r requirements.txt
docker-compose pull
```

## Known Security Considerations

### 1. Content Validation
- **Risk**: Malicious content could be fetched
- **Mitigation**: MIME type whitelist, size limits
- **Action**: Only allow trusted content types

### 2. Proxy Bypass
- **Risk**: Requests could bypass proxy
- **Mitigation**: Enforce proxy at application level
- **Action**: Set `PROXY__PROXY_ENABLED=true`

### 3. DoS via Large Files
- **Risk**: Large files could consume resources
- **Mitigation**: Size limits enforced
- **Action**: Set appropriate `FETCHER__MAX_SIZE`

### 4. Torrent Privacy
- **Risk**: Public torrents leak IP addresses
- **Mitigation**: Private torrents by default
- **Action**: Keep `TORRENT__PRIVATE_TRACKER=true`

### 5. Information Disclosure
- **Risk**: Error messages could reveal system info
- **Mitigation**: Generic error messages in production
- **Action**: Set `DEBUG=false`

## Security Checklist for Production

- [ ] Authentication enabled (`SECURITY__AUTH_ENABLED=true`)
- [ ] Strong HMAC secret set (32+ bytes)
- [ ] HTTPS/TLS configured on reverse proxy
- [ ] Proxy/VPN enforced for all fetches
- [ ] SSL verification enabled
- [ ] MIME whitelist configured
- [ ] Rate limiting enabled
- [ ] Private torrents enabled
- [ ] Encryption enabled
- [ ] Debug mode disabled
- [ ] Sensitive logging masked
- [ ] Firewall configured
- [ ] Regular security updates scheduled
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented

## Contact

For security concerns, contact:
- GitHub Security: Use "Security" tab
- Maintainer: [Email to be added]

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who help improve ProxyTorrent's security.
