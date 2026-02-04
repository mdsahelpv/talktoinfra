# TalkAI Infrastructure Onboarding Service

**Port:** 8011

This service manages the onboarding and credential storage for Kubernetes clusters and cloud providers.

## Features

- **Kubernetes Cluster Onboarding**: Register clusters via kubeconfig or individual credentials
- **Cloud Provider Support**: AWS, Azure, GCP account registration
- **Secure Credential Storage**: AES-256 encryption + HashiCorp Vault integration
- **Connection Testing**: Validate credentials and permissions before storage
- **Credential Rotation**: Automated rotation support with history tracking

## API Endpoints

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check

### Clusters
- `POST /api/v1/clusters/register` - Register a new Kubernetes cluster
- `GET /api/v1/clusters` - List all clusters
- `GET /api/v1/clusters/{id}` - Get cluster details
- `PATCH /api/v1/clusters/{id}` - Update cluster configuration
- `POST /api/v1/clusters/{id}/test-connection` - Test connection
- `DELETE /api/v1/clusters/{id}` - Delete cluster

### Cloud Providers
- `POST /api/v1/cloud/aws/register` - Register AWS account
- `POST /api/v1/cloud/azure/register` - Register Azure subscription
- `POST /api/v1/cloud/gcp/register` - Register GCP project
- `GET /api/v1/cloud/aws` - List AWS accounts
- `GET /api/v1/cloud/azure` - List Azure subscriptions
- `GET /api/v1/cloud/gcp` - List GCP projects
- `POST /api/v1/cloud/{provider}/{id}/test-connection` - Test connection

### Credentials
- `POST /api/v1/credentials` - Create credential
- `GET /api/v1/credentials` - List credentials
- `GET /api/v1/credentials/{id}` - Get credential info
- `POST /api/v1/credentials/{id}/rotate` - Rotate credential
- `DELETE /api/v1/credentials/{id}` - Delete credential

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/talktoinfra"
export ENCRYPTION_KEY="your-32-byte-key-here"

# Run service
python -m uvicorn main:app --host 0.0.0.0 --port 8011 --reload
```

## Configuration

Environment variables:
- `DATABASE_URL` - PostgreSQL connection URL
- `ENCRYPTION_KEY` - AES-256 encryption key
- `VAULT_URL` - HashiCorp Vault URL (optional)
- `VAULT_TOKEN` - Vault token (optional)
- `SERVICE_PORT` - Port (default: 8011)

## Database Migrations

```bash
# Create migration
alembic revision --autogenereate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```
