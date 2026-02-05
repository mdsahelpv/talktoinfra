# Monitoring Service

Real-time monitoring and alerting service for infrastructure.

## Features

- **Real-Time Monitoring**: Collect metrics from PostgreSQL, Redis, Kubernetes, and custom sources
- **Smart Alerting**: Threshold-based alerts with anomaly detection
- **Health Checks**: Automated health monitoring for all services
- **Notification Dispatch**: Email, Slack, and PagerDuty integrations
- **Dashboard Ready**: API-first design for easy dashboard integration

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Monitoring Service                           │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                           │
│  ├── /api/v1/health     - Health check endpoints               │
│  ├── /api/v1/metrics    - Metric queries and submission         │
│  ├── /api/v1/alerts     - Alert CRUD and actions                │
│  └── /api/v1/rules      - Alert rules and policies              │
├─────────────────────────────────────────────────────────────────┤
│  Services Layer                                                │
│  ├── Collector       - Metric collection from various sources   │
│  ├── Alerting        - Alert evaluation engine                  │
│  ├── AnomalyDetector - ML-based anomaly detection               │
│  └── Notification    - Multi-channel notifications              │
├─────────────────────────────────────────────────────────────────┤
│  Workers Layer (Celery)                                         │
│  ├── collect_metrics      - Periodic metric collection          │
│  ├── evaluate_alerts     - Periodic alert evaluation           │
│  ├── learn_baselines      - Baseline learning (hourly)          │
│  └── cleanup_old_metrics  - Data retention (daily)              │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer (PostgreSQL + Redis)                                │
│  ├── Metrics         - Time-series metric storage                │
│  ├── Alerts          - Alert instances and history               │
│  ├── Rules           - Alert rule configurations                │
│  └── Baselines       - Learned baselines for anomaly detection   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- (Optional) Kubernetes cluster access

### Installation

```bash
cd services/monitoring-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set environment variables or create a `.env` file:

```env
# Service
SERVICE_PORT=8009
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/monitoring

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3

# Monitored Services
MONITORED_SERVICES=http://localhost:8000,http://localhost:8001
```

### Running

```bash
# Start the API server
uvicorn main:app --host 0.0.0.0 --port 8009 --reload

# Start Celery workers (in another terminal)
celery -A workers.celery_app worker --loglevel=info --queues=monitoring

# Start Celery beat (scheduler)
celery -A workers.celery_app beat --loglevel=info
```

### Docker

```bash
docker-compose up -d monitoring-service
```

## API Endpoints

### Health

- `GET /health` - Basic health check
- `GET /api/v1/health` - Overall health overview
- `GET /api/v1/health/dashboard` - Dashboard data
- `GET /api/v1/health/services/{name}` - Service health details
- `POST /api/v1/health/check-all` - Trigger all health checks

### Metrics

- `GET /api/v1/metrics` - List available metrics
- `GET /api/v1/metrics/{name}` - Query metric time series
- `GET /api/v1/metrics/{name}/latest` - Get latest value
- `GET /api/v1/metrics/{name}/statistics` - Get statistics
- `POST /api/v1/metrics/submit` - Submit custom metric

### Alerts

- `GET /api/v1/alerts` - List alerts with filtering
- `GET /api/v1/alerts/active` - Get active alerts
- `GET /api/v1/alerts/{id}` - Get alert details
- `GET /api/v1/alerts/statistics` - Get alert statistics
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/v1/alerts/{id}/resolve` - Resolve alert
- `POST /api/v1/alerts/{id}/silence` - Silence alert

### Rules

- `GET /api/v1/rules` - List alert rules
- `GET /api/v1/rules/{id}` - Get rule details
- `POST /api/v1/rules` - Create alert rule
- `PATCH /api/v1/rules/{id}` - Update rule
- `DELETE /api/v1/rules/{id}` - Delete rule
- `POST /api/v1/rules/{id}/enable` - Enable rule
- `POST /api/v1/rules/{id}/disable` - Disable rule

### Escalation Policies

- `GET /api/v1/rules/escalation` - List policies
- `POST /api/v1/rules/escalation` - Create policy

### Notification Channels

- `GET /api/v1/rules/channels` - List channels
- `POST /api/v1/rules/channels` - Create channel

## Alert Rules

### Creating a Rule

```python
import requests

rule = {
    "name": "High CPU Usage",
    "description": "Alert when CPU usage exceeds 80%",
    "metric_name": "cpu_usage_percent",
    "comparison_operator": "GT",
    "threshold_value": 80.0,
    "duration_seconds": 300,
    "severity": "WARNING",
    "notify_channels": ["slack_alerts"]
}

response = requests.post("http://localhost:8009/api/v1/rules", json=rule)
print(response.json())
```

### Condition Types

- `THRESHOLD` - Compare against static threshold
- `RATE_OF_CHANGE` - Detect spikes/changes
- `ANOMALY` - ML-based anomaly detection
- `STATUS` - Service status checks

### Severity Levels

- `INFO` - Informational alerts
- `WARNING` - Warning conditions
- `ERROR` - Error conditions
- `CRITICAL` - Critical issues

## Notification Channels

### Slack

```python
channel = {
    "name": "slack_alerts",
    "channel_type": "slack",
    "config": {
        "webhook_url": "https://hooks.slack.com/services/..."
    }
}
```

### Email

```python
channel = {
    "name": "email_alerts",
    "channel_type": "email",
    "config": {
        "to_addresses": ["team@example.com"]
    }
}
```

### PagerDuty

```python
channel = {
    "name": "pagerduty_critical",
    "channel_type": "pagerduty",
    "config": {
        "service_id": "P12345"
    }
}
```

## Metric Collection

### Built-in Collectors

- **PostgreSQL**: Connection pool stats, query metrics
- **Redis**: Connected clients, memory usage, commands
- **Kubernetes**: Node resources, pod counts
- **HTTP Services**: Health checks, response times

### Custom Metrics

```python
import requests

metric = {
    "name": "business_logic_counter",
    "value": 42,
    "metric_type": "counter",
    "labels": {
        "operation": "create_user"
    },
    "source_service": "my-service"
}

requests.post("http://localhost:8009/api/v1/metrics/submit", json=metric)
```

## Anomaly Detection

The service includes ML-based anomaly detection:

```python
# Baselines are automatically learned
# Z-score based detection with configurable sensitivity

# Prediction endpoint
response = requests.get(
    "http://localhost:8009/api/v1/anomaly/predict",
    params={"metric_name": "cpu_usage_percent"}
)
print(response.json())
# {
#   "predicted_value": 45.2,
#   "lower_bound": 35.0,
#   "upper_bound": 55.4,
#   "confidence": 0.95
# }
```

## Development

### Running Tests

```bash
pytest
pytest tests/test_collector.py
pytest tests/test_alerting.py -v
```

### Linting

```bash
ruff check . --fix
black .
mypy app/
```

### Database Migrations

```bash
cd services/monitoring-service
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## File Structure

```
services/monitoring-service/
├── config.py              # Pydantic settings
├── main.py               # FastAPI application
├── models.py             # SQLAlchemy models (metrics)
├── models_alerts.py      # SQLAlchemy models (alerts)
├── schemas.py            # Pydantic schemas
├── database.py           # Database connection
├── requirements.txt      # Dependencies
├── Dockerfile
├── alembic/              # Database migrations
│   └── versions/
├── api/v1/
│   ├── alerts.py         # Alert endpoints
│   ├── metrics.py        # Metric endpoints
│   ├── health.py         # Health endpoints
│   └── rules.py          # Rule management
├── services/
│   ├── collector.py       # Metric collection
│   ├── alerting.py        # Alert evaluation
│   ├── anomaly_detection.py
│   └── notification.py    # Notification dispatch
└── workers/
    └── celery_app.py      # Celery workers
```

## License

MIT
