# AI Infrastructure Operations Platform - Kubernetes Manifests

This directory contains Kubernetes manifests for deploying the AI Infrastructure Operations Platform (OpsAI) using Kustomize.

## Architecture Overview

The platform consists of the following components:

### Core Services
- **api-gateway** (Port 8000) - API Gateway for external requests
- **ai-router** (Port 8001) - AI model routing and orchestration
- **action-engine** (Port 8002) - Action execution engine
- **policy-engine** (Port 8003) - Policy enforcement and validation
- **ingestion-service** (Port 8004) - Data ingestion pipeline
- **audit-service** (Port 8005) - Audit logging and compliance
- **frontend** (Port 3000) - Web UI

### Data Layer
- **postgres** - PostgreSQL database (StatefulSet, 10Gi PVC)
- **redis** - Redis cache (StatefulSet, 5Gi PVC)
- **qdrant** - Vector database (StatefulSet, 20Gi PVC)

## Directory Structure

```
infra/k8s/
├── base/                          # Base manifests
│   ├── 00-namespace-config.yaml   # Namespace and ConfigMap
│   ├── 01-secrets.yaml            # Secrets (requires update)
│   ├── 02-pvc.yaml                # PersistentVolumeClaims
│   ├── 03-statefulsets.yaml       # Data layer StatefulSets
│   ├── 04-services-data.yaml      # Data layer Services
│   ├── 05-deployment-api-gateway.yaml
│   ├── 06-deployments-core.yaml
│   ├── 07-deployments-services.yaml
│   ├── 08-deployments-frontend.yaml
│   ├── 09-hpa.yaml                # HorizontalPodAutoscalers
│   ├── 10-ingress.yaml            # Ingress rules
│   └── kustomization.yaml
├── overlays/
│   ├── development/               # Development environment
│   │   ├── configmap-patch.yaml
│   │   ├── replicas-patch.yaml
│   │   └── kustomization.yaml
│   └── production/                # Production environment
│       ├── configmap-patch.yaml
│       ├── replicas-patch.yaml
│       └── kustomization.yaml
├── kustomization.yaml             # Root kustomization
└── README.md                      # This file
```

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured to access your cluster
- Kustomize (v4.5+) - built into kubectl v1.14+
- Ingress controller (nginx-ingress recommended)
- cert-manager (optional, for TLS)
- Metrics server (required for HPA)

## Quick Start

### 1. Update Secrets

Before deploying, update the secrets in `base/01-secrets.yaml`:

```bash
# Generate secure secrets
export DB_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 64)
export REDIS_PASSWORD=$(openssl rand -base64 32)

# Update the secrets file
cat > base/01-secrets.yaml << EOF
---
apiVersion: v1
kind: Secret
metadata:
  name: opsai-secrets
  namespace: opsai
type: Opaque
stringData:
  DATABASE_URL: "postgresql://opsai:${DB_PASSWORD}@postgres:5432/opsai"
  DATABASE_PASSWORD: "${DB_PASSWORD}"
  JWT_SECRET_KEY: "${JWT_SECRET}"
  REDIS_PASSWORD: "${REDIS_PASSWORD}"
  QDRANT_API_KEY: "$(openssl rand -base64 32)"
  OPENAI_API_KEY: "${OPENAI_API_KEY:-}"
  ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY:-}"
  ENCRYPTION_KEY: "$(openssl rand -base64 32)"
EOF
```

### 2. Deploy to Development

```bash
# Using kubectl with kustomize
kubectl apply -k overlays/development/

# Or using kustomize directly
kustomize build overlays/development/ | kubectl apply -f -
```

### 3. Deploy to Production

```bash
# Using kubectl with kustomize
kubectl apply -k overlays/production/

# Or using kustomize directly
kustomize build overlays/production/ | kubectl apply -f -
```

## Deployment Commands Reference

### Apply base manifests only
```bash
kubectl apply -k base/
```

### Preview manifests before applying
```bash
# Development
kustomize build overlays/development/

# Production
kustomize build overlays/production/
```

### Deploy with custom image tags
```bash
cd overlays/production
kustomize edit set image opsai/api-gateway=myregistry/api-gateway:v1.1.0
kubectl apply -k .
```

### Delete deployment
```bash
kubectl delete -k overlays/development/
# or
kubectl delete -k overlays/production/
```

## Environment Differences

| Feature | Development | Production |
|---------|------------|------------|
| Namespace | `opsai-dev` | `opsai` |
| Replicas | 1 per service | 2-3 per service |
| HPA | Disabled | Enabled (api-gateway, ai-router) |
| TLS | Disabled | Enabled (cert-manager) |
| Log Level | debug | warn |
| Rate Limit | 100/min | 5000/min |
| CORS | `*` | `https://app.opsai.example.com` |

## Accessing the Application

### Using NodePort (Default)

- API Gateway: `http://<node-ip>:30080`
- Frontend: `http://<node-ip>:30300`

### Using Ingress (Production)

Configure DNS to point to your ingress controller:
- API: `https://api.opsai.example.com`
- UI: `https://app.opsai.example.com`

Update the ingress hosts in `base/10-ingress.yaml`:
```yaml
spec:
  rules:
    - host: api.yourdomain.com
      ...
    - host: app.yourdomain.com
      ...
```

## Monitoring and Operations

### View all resources
```bash
kubectl get all -n opsai
```

### Check pod status
```bash
kubectl get pods -n opsai -w
```

### View logs
```bash
# API Gateway
kubectl logs -f deployment/api-gateway -n opsai

# AI Router
kubectl logs -f deployment/ai-router -n opsai

# All pods
kubectl logs -f -l app.kubernetes.io/name=opsai -n opsai
```

### Scale deployments
```bash
kubectl scale deployment api-gateway --replicas=5 -n opsai
```

### Port forwarding for local development
```bash
# API Gateway
kubectl port-forward svc/api-gateway 8000:8000 -n opsai

# PostgreSQL
kubectl port-forward svc/postgres 5432:5432 -n opsai

# Redis
kubectl port-forward svc/redis 6379:6379 -n opsai
```

## Troubleshooting

### Pods stuck in Pending
Check PVC binding:
```bash
kubectl get pvc -n opsai
kubectl describe pvc postgres-pvc -n opsai
```

### ImagePullBackOff
Ensure images are available in your registry or use local images:
```bash
# Build and load images into kind/minikube
make docker-build
kind load docker-image opsai/api-gateway:latest
```

### HPA not working
Verify metrics server is installed:
```bash
kubectl get apiservices | grep metrics
kubectl top nodes
```

## Security Considerations

1. **Never commit secrets** - Use external secret management (Sealed Secrets, Vault, etc.)
2. **Enable Network Policies** - Restrict pod-to-pod communication
3. **Use Pod Security Standards** - Apply restricted security context
4. **Enable RBAC** - Least privilege access for service accounts
5. **Regular Updates** - Keep images and dependencies updated

## Customization

### Add a new environment

1. Create directory: `overlays/staging/`
2. Copy and modify files from `overlays/development/`
3. Update `kustomization.yaml` references
4. Apply: `kubectl apply -k overlays/staging/`

### Modify resource limits

Edit deployment patches in the overlay:
```yaml
# overlays/production/resource-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-router
spec:
  template:
    spec:
      containers:
        - name: ai-router
          resources:
            limits:
              memory: "4Gi"
              cpu: "2000m"
```

## Maintenance

### Database backups
```bash
# Backup PostgreSQL
kubectl exec -it postgres-0 -n opsai -- pg_dump -U opsai opsai > backup.sql
```

### Update deployments
```bash
# Rolling update
kubectl set image deployment/api-gateway api-gateway=opsai/api-gateway:v1.1.0 -n opsai

# Or via kustomize
kustomize build overlays/production/ | kubectl apply -f -
```

## Support

For issues and questions:
- Check logs: `kubectl logs -f <pod-name> -n opsai`
- Describe resources: `kubectl describe pod <pod-name> -n opsai`
- Review events: `kubectl get events -n opsai --sort-by='.lastTimestamp'`
