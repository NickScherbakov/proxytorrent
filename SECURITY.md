# Security Policy

## Implemented Security Measures

### Path Traversal Protection
The `/torrents/{filename}` endpoint implements multiple layers of protection:
- **Filename Validation**: Strict regex pattern `^[a-zA-Z0-9._-]+\.torrent$` prevents directory traversal
- **Path Resolution**: Uses `Path.resolve()` and `relative_to()` to ensure paths stay within `TORRENT_DIR`
- **File Existence Check**: Verifies file exists before serving

### Dependency Security
All dependencies are checked against the GitHub Advisory Database:
- **aiohttp**: Updated to 3.9.4 (fixes CVE-2024-23334 and CVE-2024-23829)
- All other dependencies: No known vulnerabilities

### Network Security
- **Proxy Support**: Content fetching can be isolated through SOCKS5/HTTP proxies
- **Request Validation**: All API endpoints validate input parameters
- **Timeout Protection**: HTTP requests have 300-second timeout to prevent hanging

### Recommended Production Hardening

1. **Authentication**: Implement API authentication (JWT, API keys, or OAuth)
   ```python
   # Add to server.py
   @web.middleware
   async def auth_middleware(request, handler):
       token = request.headers.get('Authorization')
       if not verify_token(token):
           return web.Response(status=401)
       return await handler(request)
   ```

2. **Rate Limiting**: Add rate limiting to prevent abuse
   ```python
   # Consider using aiohttp-ratelimit
   from aiohttp_ratelimit import RateLimiter
   ```

3. **HTTPS**: Deploy behind a reverse proxy with TLS
   ```yaml
   # nginx example
   server {
       listen 443 ssl;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       location / {
           proxy_pass http://localhost:8080;
       }
   }
   ```

4. **Input Sanitization**: Additional URL validation
   ```python
   # Add to fetcher.py
   def validate_url(url):
       parsed = urlparse(url)
       if parsed.scheme not in ['http', 'https']:
           raise ValueError("Only HTTP/HTTPS URLs allowed")
       if parsed.hostname in ['localhost', '127.0.0.1', '::1']:
           raise ValueError("Local URLs not allowed")
   ```

5. **Disk Quota**: Implement disk space monitoring and limits
   ```python
   # Add to config.py
   MAX_DOWNLOAD_SIZE_MB = 1000
   MAX_STORAGE_SIZE_GB = 100
   ```

## Known Limitations

### CodeQL Alerts
The following CodeQL alerts are **false positives**:
- `py/path-injection` in `server.py` lines 127, 136, 142
  - **Status**: Mitigated
  - **Reason**: Filename is validated with strict regex and path resolution before use
  - **Evidence**: Regex `^[a-zA-Z0-9._-]+\.torrent$` + `relative_to()` check prevents traversal

## Reporting a Vulnerability

If you discover a security vulnerability, please:
1. **Do NOT** open a public issue
2. Email the maintainer with details
3. Allow 90 days for a fix before public disclosure

## Legal Considerations

**IMPORTANT**: Users are responsible for:
- Complying with copyright laws
- Respecting terms of service of fetched content
- Following applicable laws in their jurisdiction
- Not using this service for illegal activities

The service should only be used for:
- Legal content distribution
- Personal backups
- Open-source software mirroring
- Content you own or have permission to distribute

## Security Best Practices for Users

1. **Use VPN/Proxy**: Always configure proxy settings for privacy
2. **Validate Content**: Only fetch from trusted sources
3. **Monitor Resources**: Track disk usage and bandwidth
4. **Update Regularly**: Keep dependencies updated
5. **Audit Logs**: Review access logs regularly
6. **Network Isolation**: Run in isolated network environment
7. **Access Control**: Restrict API access to trusted clients only

## Compliance

This service should be deployed in compliance with:
- DMCA (Digital Millennium Copyright Act)
- GDPR (if handling user data)
- Local copyright and distribution laws
- Service provider terms of service
