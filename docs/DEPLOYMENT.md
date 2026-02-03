# Deployment Guide

## Overview

This guide covers deploying the AI Infrastructure Operations Platform using Docker Compose (local/development) or Kubernetes (production).

## Prerequisites

### System Requirements

**Minimum (Development):**
- 8 CPU cores
- 16GB RAM (32GB recommended with Ollama)
- 50GB disk space
- Docker & Docker Compose

**Recommended (Production):**
- 16+ CPU cores
- 64GB RAM
- 200GB SSD storage
- Kubernetes cluster (v1.27+)
- Ollama server (separate machine recommended)

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+
- kubectl 1.27+ (for K8s deployment)
- kustomize 5.0+ (for K8s deployment)
- Ollama server with models:
  - `llama3.3:70b` (or smaller model for testing)
  - `codellama:34b`
  - `nomic-embed-text`

---

## Docker Compose Deployment

### Quick Start

```bash
# 1. Clone and navigate
cd /home/ubuntu/talkai

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# 3. Start services
docker-compose -f infra/docker/docker-compose.yml up -d

# 4. Verify health
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:3000

# 5. Access platform
# Frontend: http://localhost:3000
# API: http://localhost:8000
```

### Environment Configuration

Edit `.env` with your settings:

```bash
# Required
OLLAMA_HOST=http://your-ollama-server:11434
JWT_SECRET=your-256-bit-secret-key-here
DB_PASSWORD=secure-password-here

# Optional - Service Ports
API_GATEWAY_PORT=8000
AI_ROUTER_PORT=8001
...

# Optional - Feature Flags
ENABLE_ACTIONS=true
ENABLE_APPROVALS=true
DRY_RUN_DEFAULT=true
```

### Service Management

```bash
# Start all services
docker-compose -f infra/docker/docker-compose.yml up -d

# View logs
docker-compose -f infra/docker/docker-compose.yml logs -f

# View specific service logs
docker-compose -f infra/docker/docker-compose.yml logs -f ai-router

# Stop all services
docker-compose -f infra/docker/docker-compose.yml down

# Stop and remove volumes (WARNING: data loss)
docker-compose -f infra/docker/docker-compose.yml down -v

# Restart specific service
docker-compose -f infra/docker/docker-compose.yml restart ai-router

# Scale a service
docker-compose -f infra/docker/docker-compose.yml up -d --scale api-gateway=3
```

### Troubleshooting

**Service won't start:**
```bash
# Check logs
docker-compose logs api-gateway

# Check port conflicts
netstat -tulpn | grep 8000

# Verify Ollama connection
curl ${OLLAMA_HOST}/api/tags
```

**Database connection issues:**
```bash
# Check postgres health
docker-compose exec postgres pg_isready -U opsai

# Reset database (WARNING: data loss)
docker-compose down -v
docker-compose up -d postgres
```

---

## Kubernetes Deployment

### Architecture

The K8s deployment uses:
- **Namespace**: `opsai`
- **Services**: 7 microservices + 3 databases
- **Storage**: PVCs for PostgreSQL, Redis, Qdrant
- **Networking**: ClusterIP for internal, NodePort for external
- **Scaling**: HPA for API Gateway and AI Router
- **Config**: ConfigMaps for environment, Secrets for sensitive data

### Quick Deploy

```bash
# Development environment
kubectl apply -k infra/k8s/overlays/development/

# Production environment
kubectl apply -k infra/k8s/overlays/production/

# Verify deployment
kubectl get pods -n opsai
kubectl get svc -n opsai
kubectl get ingress -n opsai
```

### Configuration

**ConfigMap** (`infra/k8s/base/00-namespace-config.yaml`):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opsai-config
  namespace: opsai
data:
  ENVIRONMENT: production
  LOG_LEVEL: info
  OLLAMA_HOST: http://ollama-server:11434
  # ... other settings
```

**Secrets** (`infra/k8s/base/01-secrets.yaml`):
```bash
# Generate secrets
kubectl create secret generic opsai-secrets \
  --from-literal=db-password=$(openssl rand -base64 32) \
  --from-literal=jwt-secret=$(openssl rand -base64 64) \
  -n opsai --dry-run=client -o yaml > infra/k8s/base/01-secrets.yaml
```

### Storage

Persistent Volumes:
- **postgres**: 10Gi (database)
- **redis**: 5Gi (cache)
- **qdrant**: 20Gi (vectors)

Check storage:
```bash
kubectl get pvc -n opsai
kubectl describe pvc postgres-pvc -n opsai
```

### Networking

**Internal Services** (ClusterIP):
- ai-router: 8001
- action-engine: 8002
- policy-engine: 8003
- ingestion-service: 8004
- audit-service: 8005

**External Services** (NodePort/LoadBalancer):
- api-gateway: 8000 (NodePort 30080)
- frontend: 3000 (NodePort 30030)

**Ingress** (optional):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: opsai-ingress
  namespace: opsai
spec:
  rules:
  - host: opsai.yourcompany.com
    http:
      paths:
      - path: /api
        backend:
          service:
            name: api-gateway
            port: 8000
```

### Scaling

**Horizontal Pod Autoscaler:**
- API Gateway: min 2, max 10 replicas
- AI Router: min 2, max 5 replicas

Manual scaling:
```bash
# Scale API Gateway
kubectl scale deployment api-gateway --replicas=5 -n opsai

# Check HPA
kubectl get hpa -n opsai
```

### Monitoring

```bash
# Check pod status
kubectl get pods -n opsai -w

# Check resource usage
kubectl top pods -n opsai

# Check logs
kubectl logs -f deployment/ai-router -n opsai

# Check events
kubectl get events -n opsai --sort-by='.lastTimestamp'
```

### Updates

**Rolling Update:**
```bash
# Update image
kubectl set image deployment/api-gateway \
  api-gateway=opsai/api-gateway:v1.1.0 -n opsai

# Watch rollout
kubectl rollout status deployment/api-gateway -n opsai

# Rollback if needed
kubectl rollout undo deployment/api-gateway -n opsai
```

**Kustomize Update:**
```bash
# Edit kustomization.yaml
# Change image tags

# Apply changes
kubectl apply -k infra/k8s/overlays/production/
```

---

## Production Checklist

Before going to production, ensure:

### Security
- [ ] Change all default passwords
- [ ] Enable mTLS between services
- [ ] Configure proper secrets management (Vault)
- [ ] Enable network policies
- [ ] Configure WAF rules
- [ ] Enable audit logging
- [ ] Set up log aggregation

### Reliability
- [ ] Configure health checks
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure alerts
- [ ] Test failover procedures
- [ ] Set up backup schedules
- [ ] Document runbooks

### Performance
- [ ] Load testing completed
- [ ] Resource limits configured
- [ ] HPA configured and tested
- [ ] Database optimized
- [ ] Cache warmed
- [ ] CDN configured (for frontend)

### Compliance
- [ ] Audit logs enabled
- [ ] Data retention configured
- [ ] Access controls tested
- [ ] Compliance documentation
- [ ] Security audit completed

---

## Troubleshooting

### Common Issues

**Pod stuck in Pending:**
```bash
# Check events
kubectl describe pod <pod-name> -n opsai

# Common causes:
# - Insufficient resources
# - PVC not bound
# - Image pull errors
```

**Service not accessible:**
```bash
# Check service endpoints
kubectl get endpoints <service-name> -n opsai

# Test from inside cluster
kubectl run debug --rm -i --tty --image=curlimages/curl -- /bin/sh
# Then: curl http://ai-router:8001/health
```

**Database connection failures:**
```bash
# Check postgres pod
kubectl logs postgres-0 -n opsai

# Test connection
kubectl exec -it postgres-0 -n opsai -- psql -U opsai -c "\dt"
```

**Ollama connection issues:**
```bash
# Test Ollama from a pod
kubectl exec -it deployment/ai-router -n opsai -- /bin/sh
# Then: curl ${OLLAMA_HOST}/api/tags
```

---

## Backup and Recovery

### Backup

```bash
# Backup PostgreSQL
kubectl exec postgres-0 -n opsai -- pg_dump -U opsai opsai > backup.sql

# Backup Redis
kubectl exec redis-0 -n opsai -- redis-cli BGSAVE
kubectl cp redis-0:/data/dump.rdb ./redis-backup.rdb -n opsai

# Backup Qdrant
kubectl exec qdrant-0 -n opsai -- tar czf /tmp/qdrant-backup.tar.gz /qdrant/storage
kubectl cp qdrant-0:/tmp/qdrant-backup.tar.gz ./qdrant-backup.tar.gz -n opsai
```

### Recovery

```bash
# Restore PostgreSQL
kubectl exec -i postgres-0 -n opsai -- psql -U opsai opsai < backup.sql

# Restore Redis
kubectl cp ./redis-backup.rdb redis-0:/data/dump.rdb -n opsai
kubectl exec redis-0 -n opsai -- redis-cli SHUTDOWN SAVE

# Restore Qdrant
kubectl cp ./qdrant-backup.tar.gz qdrant-0:/tmp/ -n opsai
kubectl exec qdrant-0 -n opsai -- tar xzf /tmp/qdrant-backup.tar.gz -C /
```

---

## Security Hardening

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-router-policy
  namespace: opsai
spec:
  podSelector:
    matchLabels:
      app: ai-router
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8001
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
```

### Pod Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
```

---

## Support

For deployment issues:
- Check service READMEs in `services/*/README.md`
- Review logs: `kubectl logs -f <pod> -n opsai`
- Open an issue with logs and configuration

---

**Last Updated**: February 2026
