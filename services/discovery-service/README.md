# Discovery Service

Production-ready network discovery and infrastructure scanning service for TalkAI Platform.

## Architecture

This service implements a **hybrid scanning architecture** with three scanner backends:

1. **Masscan** - Ultra-fast SYN scanner (1000x faster than traditional scanners)
2. **Nmap** - Industry standard with excellent service detection
3. **Python Async** - Pure Python implementation, always available

### Hybrid Scan Flow
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Masscan   │ ───> │    Nmap     │ ───> │   Results   │
│  (Phase 1)  │      │  (Phase 2)  │      │   (DB)      │
│ Fast Host   │      │  Detailed   │      │             │
│ Discovery   │      │  Service    │      │             │
└─────────────┘      │  Detection  │      └─────────────┘
                     └─────────────┘
```

## Features

- **Multiple Scanner Backends**: Choose between Python (no deps), Masscan (fastest), or Nmap (most detailed)
- **Hybrid Mode**: Automatically uses best scanner for the job
- **Database Persistence**: All scan results stored in PostgreSQL
- **Background Health Monitoring**: Automatic health checks every 5 minutes
- **Job Management**: Start, stop, and monitor scans in real-time
- **Host Management**: Add discovered hosts to persistent managed list

## API Endpoints

### Scans
- `POST /api/v1/scans` - Start a new scan
- `GET /api/v1/scans` - List all scans
- `GET /api/v1/scans/{id}` - Get scan details
- `GET /api/v1/scans/{id}/status` - Get scan status
- `GET /api/v1/scans/{id}/results` - Get scan results
- `POST /api/v1/scans/{id}/stop` - Stop a running scan
- `DELETE /api/v1/scans/{id}` - Delete a scan

### Hosts
- `GET /api/v1/hosts` - List managed hosts
- `POST /api/v1/hosts` - Create managed host
- `POST /api/v1/hosts/from-discovery` - Add from discovered host
- `GET /api/v1/hosts/{id}` - Get host details
- `PUT /api/v1/hosts/{id}` - Update host
- `DELETE /api/v1/hosts/{id}` - Delete host

### Discovery
- `GET /api/v1/discovery/status` - Get overall status
- `GET /api/v1/discovery/config` - Get configuration
- `GET /api/v1/scan/presets` - Get port presets
- `GET /api/v1/scan/scanners` - Get available scanners

## Database Schema

The service uses the following PostgreSQL tables:

- `scan_jobs` - Scan job tracking and persistence
- `discovered_hosts` - Hosts found during scans
- `discovered_ports` - Open ports on discovered hosts
- `managed_hosts` - Persistent host records
- `host_health_checks` - Health check history
- `scan_exclusions` - Networks excluded from scanning

## Configuration

Environment variables (see `app/config.py`):

```env
# Service
SERVICE_PORT=8007

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/1

# Scanner Binaries
MASSCAN_PATH=/usr/bin/masscan
NMAP_PATH=/usr/bin/nmap

# Scan Limits
MAX_NETWORK_SIZE=65536
SCAN_RESULT_RETENTION_DAYS=7

# Health Monitoring
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL_SECONDS=300
```

## Development

### Running Locally

```bash
cd services/discovery-service

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload --port 8007

# Run Celery worker (for background tasks)
celery -A app.workers.celery_app worker --loglevel=info

# Run Celery beat (for scheduled tasks)
celery -A app.workers.celery_app beat --loglevel=info
```

### Running with Docker

```bash
# Build and run with docker-compose
docker-compose up -d discovery-service
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## Production Notes

1. **Masscan**: For production use with Masscan, you may need to run the container with `--privileged` flag for SYN scanning
2. **Database**: Use Alembic for database migrations in production
3. **Security**: Configure `excluded_networks` to prevent scanning sensitive networks
4. **Rate Limiting**: Configure `scan_rate_limit_per_minute` to prevent abuse
5. **Monitoring**: Health checks run every 5 minutes via Celery beat

## License

Part of TalkAI Platform
