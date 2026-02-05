# Cost Management Service

Cloud cost tracking, estimation, and optimization recommendations for TalkAI Platform.

## Features

- **Cost Tracking**: Collect and aggregate costs from AWS, Azure, GCP, and Kubernetes
- **Budget Management**: Set budgets and receive alerts when spending thresholds are exceeded
- **Cost Estimation**: Estimate costs before deploying resources
- **Optimization Recommendations**: AI-powered recommendations for cost savings
- **Cost Dashboards**: Visualize costs by provider, cluster, namespace, and service

## Architecture

```
services/cost-service/
├── main.py                      # FastAPI application entry point
├── config.py                    # Pydantic settings
├── requirements.txt             # Python dependencies
├── Dockerfile                  # Container configuration
├── README.md                   # This file
├── app/
│   ├── __init__.py
│   ├── database.py             # Database connection
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── api/v1/
│   │   ├── __init__.py
│   │   ├── costs.py            # Cost query endpoints
│   │   ├── budgets.py          # Budget management endpoints
│   │   ├── estimates.py        # Cost estimation endpoints
│   │   └── recommendations.py  # Optimization recommendations
│   └── services/
│       ├── __init__.py
│       ├── estimator.py        # Cost estimation engine
│       ├── optimizer.py        # Optimization recommendation engine
│       └── collectors/         # Cloud provider cost collectors
│           ├── __init__.py
│           ├── aws_costs.py
│           ├── azure_costs.py
│           ├── gcp_costs.py
│           └── kubernetes_costs.py
└── tests/
    └── test_*.py
```

## API Endpoints

### Costs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/costs/summary` | Get cost summary for a period |
| GET | `/api/v1/costs/by-provider` | Get costs grouped by cloud provider |
| GET | `/api/v1/costs/by-cluster` | Get costs grouped by cluster |
| GET | `/api/v1/costs/by-service` | Get costs grouped by service |
| GET | `/api/v1/costs/by-region` | Get costs grouped by region |
| GET | `/api/v1/costs/trends` | Get cost trend data |
| GET | `/api/v1/costs/top-resources` | Get top expensive resources |
| POST | `/api/v1/costs/records` | Create a cost record |
| GET | `/api/v1/costs/records/{id}` | Get a cost record |

### Budgets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/budgets` | List all budgets |
| GET | `/api/v1/budgets/{id}` | Get a budget |
| POST | `/api/v1/budgets` | Create a budget |
| PATCH | `/api/v1/budgets/{id}` | Update a budget |
| DELETE | `/api/v1/budgets/{id}` | Delete a budget |
| GET | `/api/v1/budgets/{id}/alerts` | Get budget alerts |
| GET | `/api/v1/budgets/alerts` | List all budget alerts |
| POST | `/api/v1/budgets/alerts/{id}/acknowledge` | Acknowledge an alert |
| GET | `/api/v1/budgets/summary` | Get budget summary |

### Cost Estimation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/estimates` | Create a cost estimate |
| GET | `/api/v1/estimates/{id}` | Get a saved estimate |
| POST | `/api/v1/estimates/compare` | Compare pricing models |
| GET | `/api/v1/estimates/instance-types/{provider}` | Get recommended instance types |
| GET | `/api/v1/estimates/pricing-models` | Get available pricing models |

### Recommendations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/recommendations` | List recommendations |
| GET | `/api/v1/recommendations/{id}` | Get a recommendation |
| POST | `/api/v1/recommendations` | Create a recommendation |
| PATCH | `/api/v1/recommendations/{id}` | Update recommendation status |
| DELETE | `/api/v1/recommendations/{id}` | Delete a recommendation |
| GET | `/api/v1/recommendations/summary` | Get recommendations summary |
| POST | `/api/v1/recommendations/generate` | Generate recommendations |
| GET | `/api/v1/recommendations/idle-resources` | Get idle resources |
| GET | `/api/v1/recommendations/right-sizing` | Get right-sizing opportunities |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COST_SERVICE_PORT` | Service port | `8010` |
| `COST_SERVICE_HOST` | Service host | `0.0.0.0` |
| `DATABASE_URL` | PostgreSQL connection URL | - |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/4` |
| `AWS_COST_EXPLORER_ENABLED` | Enable AWS Cost Explorer | `false` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AZURE_COST_MANAGEMENT_ENABLED` | Enable Azure Cost Management | `false` |
| `GCP_BILLING_ENABLED` | Enable GCP Billing | `false` |
| `KUBECOST_ENABLED` | Enable Kubecost integration | `false` |

## Running the Service

### Local Development

```bash
cd services/cost-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the service
uvicorn main:app --reload --port 8010
```

### Docker

```bash
docker build -t cost-service:latest .
docker run -p 8010:8010 cost-service:latest
```

## Cloud Provider Setup

### AWS

1. Enable AWS Cost Explorer in the AWS Console
2. Create an IAM user with `ce:*` permissions
3. Set environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_COST_EXPLORER_ENABLED=true`

### Azure

1. Enable Cost Management + Billing in Azure
2. Create a service principal with Cost Management permissions
3. Set environment variables:
   - `AZURE_TENANT_ID`
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
   - `AZURE_SUBSCRIPTION_ID`
   - `AZURE_COST_MANAGEMENT_ENABLED=true`

### GCP

1. Enable Cloud Billing API
2. Set up BigQuery billing export
3. Set environment variables:
   - `GCP_PROJECT_ID`
   - `GCP_CREDENTIALS_FILE`
   - `GCP_BILLING_ENABLED=true`

### Kubernetes

1. Install Kubecost: `helm install kubecost kubecost/cost-analyzer`
2. Set environment variables:
   - `KUBECOST_URL` (Kubecost API URL)
   - `KUBECOST_API_KEY`
   - `KUBECOST_ENABLED=true`

## License

MIT
