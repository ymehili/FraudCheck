# Production Deployment Guide

This guide covers secure production deployment of CheckGuard AI using Docker Compose.

## Security Overview

The original `docker-compose.yml` file contains multiple critical security vulnerabilities:

- ❌ Hardcoded weak passwords ("checkguard", "admin")
- ❌ Trust-based PostgreSQL authentication
- ❌ Database ports exposed to host (5432, 6379)
- ❌ Hardcoded API keys in environment variables
- ❌ Development configurations used in production
- ❌ Docker socket exposure through LocalStack

## Production Setup

### 1. Environment Configuration

Copy the production environment template:
```bash
cp .env.production.template .env.production
```

**CRITICAL**: Edit `.env.production` with secure values. Never use example values in production.

Generate secure passwords:
```bash
# Database password (32+ characters)
openssl rand -base64 32

# Redis password (32+ characters) 
openssl rand -base64 32

# JWT secret (64+ characters)
openssl rand -hex 64

# Backup encryption key
openssl rand -base64 32
```

### 2. SSL Certificate Setup

Create SSL certificates for HTTPS:
```bash
mkdir -p ssl
# Option 1: Use Let's Encrypt (recommended)
certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Option 2: Self-signed for testing (NOT for production)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key -out ssl/certificate.crt
```

### 3. Nginx Configuration

Create production Nginx config at `nginx/nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name yourdomain.com api.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/certificate.crt;
        ssl_certificate_key /etc/nginx/ssl/private.key;
        
        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header Content-Security-Policy "default-src 'self'" always;

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/certificate.crt;
        ssl_certificate_key /etc/nginx/ssl/private.key;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### 4. Production Deployment

Deploy using the production compose file:
```bash
# Build and start services
docker-compose -f docker-compose.production.yml up -d

# Monitor logs
docker-compose -f docker-compose.production.yml logs -f

# Check service health
docker-compose -f docker-compose.production.yml ps
```

## Security Features Implemented

### Network Security
- **Internal network**: Database and cache isolated from external access
- **External network**: Only public services (Nginx) exposed
- **No port exposure**: Database ports not accessible from host
- **Reverse proxy**: All traffic routed through Nginx with SSL termination

### Authentication & Authorization
- **Strong passwords**: All passwords 32+ characters minimum
- **JWT secrets**: Cryptographically secure random tokens
- **Clerk integration**: Production authentication keys
- **Redis authentication**: Password-protected cache access

### Container Security
- **Non-root users**: Services run as user 1000:1000
- **Read-only filesystems**: Containers with read-only root
- **Security options**: `no-new-privileges` prevents privilege escalation
- **Health checks**: Comprehensive service monitoring

### Data Protection
- **Environment variables**: Secrets loaded from protected .env files
- **Volume isolation**: Data persistence without code exposure
- **Backup encryption**: Database backups encrypted at rest
- **HTTPS only**: All traffic encrypted in transit

## Production Checklist

### Pre-deployment
- [ ] Generate all secure passwords using `openssl rand`
- [ ] Configure `.env.production` with actual production values
- [ ] Set up SSL certificates for your domain
- [ ] Configure Nginx with production domain names
- [ ] Set up AWS S3 bucket and IAM roles
- [ ] Configure Clerk with production keys
- [ ] Set up monitoring and logging (Sentry, CloudWatch)

### Deployment
- [ ] Build production Docker images
- [ ] Deploy using `docker-compose.production.yml`
- [ ] Verify all health checks pass
- [ ] Test SSL certificate validity
- [ ] Verify database connectivity (internal only)
- [ ] Test file upload to S3
- [ ] Validate authentication flow

### Post-deployment
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Enable security monitoring
- [ ] Set up alerting for service failures
- [ ] Schedule security updates
- [ ] Document runbooks for common operations

## Monitoring & Maintenance

### Health Monitoring
```bash
# Check all service health
docker-compose -f docker-compose.production.yml ps

# View service logs
docker-compose -f docker-compose.production.yml logs [service-name]

# Monitor resource usage
docker stats
```

### Backup Procedures
```bash
# Database backup
docker exec checkguard-postgres-prod pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Encrypt backup
openssl enc -aes-256-cbc -salt -in backup.sql -out backup.sql.enc -k $BACKUP_ENCRYPTION_KEY
```

### Security Updates
```bash
# Update base images
docker-compose -f docker-compose.production.yml pull

# Rebuild with latest security patches
docker-compose -f docker-compose.production.yml build --no-cache

# Rolling update (zero downtime)
docker-compose -f docker-compose.production.yml up -d
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   - Verify certificate files exist in `ssl/` directory
   - Check domain name matches certificate
   - Ensure certificates not expired

2. **Database Connection Failures**
   - Verify PostgreSQL is healthy: `docker-compose -f docker-compose.production.yml logs postgres`
   - Check environment variables in `.env.production`
   - Confirm password matches between services

3. **Service Health Check Failures**
   - Review health check logs: `docker-compose -f docker-compose.production.yml logs [service]`
   - Verify service dependencies are running
   - Check resource constraints (memory, disk)

### Emergency Procedures

1. **Service Restart**
   ```bash
   docker-compose -f docker-compose.production.yml restart [service-name]
   ```

2. **Complete System Restart**
   ```bash
   docker-compose -f docker-compose.production.yml down
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **Database Recovery**
   ```bash
   # Restore from encrypted backup
   openssl enc -aes-256-cbc -d -in backup.sql.enc -out backup.sql -k $BACKUP_ENCRYPTION_KEY
   docker exec -i checkguard-postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB < backup.sql
   ```

## Security Incident Response

1. **Immediate Actions**
   - Take affected services offline
   - Preserve logs for forensic analysis
   - Document timeline of events

2. **Investigation**
   - Review access logs
   - Check for unauthorized changes
   - Analyze security monitoring alerts

3. **Recovery**
   - Apply security patches
   - Rotate compromised secrets
   - Restore from clean backups if needed
   - Update security measures

## Compliance & Auditing

- **Log Retention**: 90 days minimum
- **Access Control**: Document all user permissions
- **Change Management**: Track all production changes
- **Security Reviews**: Monthly security assessments
- **Incident Documentation**: Maintain incident response logs