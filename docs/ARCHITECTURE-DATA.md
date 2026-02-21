# Data Models & API Reference

This document provides detailed information about data models and API endpoints across all services.

---

## Database Schema

### PostgreSQL Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    team_id UUID REFERENCES teams(id),
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(255),
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### teams
```sql
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### roles
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### team_members
```sql
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);
```

#### clusters
```sql
CREATE TABLE clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    kubeconfig TEXT NOT NULL,
    kubeconfig_encrypted TEXT,
    user_id UUID REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
    provider VARCHAR(50),
    region VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    last_connected TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### cluster_access
```sql
CREATE TABLE cluster_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID REFERENCES clusters(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    namespace_pattern VARCHAR(255),
    permissions JSONB DEFAULT '{"read": true, "write": false}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### discovered_hosts
```sql
CREATE TABLE discovered_hosts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_address VARCHAR(45) NOT NULL,
    hostname VARCHAR(255),
    mac_address VARCHAR(17),
    os_detection VARCHAR(255),
    ports JSONB DEFAULT '[]',
    services JSONB DEFAULT '[]',
    scan_id UUID,
    network_range VARCHAR(100),
    is_managed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW()
);
```

#### discovered_ports
```sql
CREATE TABLE discovered_ports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID REFERENCES discovered_hosts(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    protocol VARCHAR(10) DEFAULT 'tcp',
    service VARCHAR(100),
    service_version VARCHAR(100),
    state VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### workflows
```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    user_id UUID REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### workflow_executions
```sql
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    current_step INTEGER DEFAULT 0,
    context JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### notifications
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(50) DEFAULT 'in_app',
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    action_url VARCHAR(1000),
    metadata JSONB DEFAULT '{}',
    sent_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### notification_preferences
```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    email_enabled BOOLEAN DEFAULT true,
    slack_enabled BOOLEAN DEFAULT false,
    teams_enabled BOOLEAN DEFAULT false,
    pagerduty_enabled BOOLEAN DEFAULT false,
    in_app_enabled BOOLEAN DEFAULT true,
    alerts_enabled BOOLEAN DEFAULT true,
    approvals_enabled BOOLEAN DEFAULT true,
    workflow_enabled BOOLEAN DEFAULT true,
    digest_enabled BOOLEAN DEFAULT false,
    email VARCHAR(255),
    slack_user_id VARCHAR(100),
    teams_user_id VARCHAR(100),
    pagerduty_user_id VARCHAR(100),
    digest_frequency VARCHAR(20) DEFAULT 'daily',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

### Authentication

#### POST /api/v1/auth/register
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user",
  "created_at": "2026-02-16T10:00:00Z"
}
```

#### POST /api/v1/auth/login
Login with email/password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /api/v1/auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### Users

#### GET /api/v1/users/me
Get current user profile.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user",
  "team_id": "uuid",
  "mfa_enabled": false,
  "created_at": "2026-02-16T10:00:00Z"
}
```

#### PUT /api/v1/users/me
Update current user profile.

**Request:**
```json
{
  "name": "John Updated",
  "password": "newpassword"
}
```

---

### Clusters

#### POST /api/v1/clusters/register
Register a new cluster.

**Request:**
```json
{
  "name": "production-k8s",
  "kubeconfig": "apiVersion: v1\nclusters:...",
  "provider": "aws",
  "region": "us-east-1"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "production-k8s",
  "provider": "aws",
  "region": "us-east-1",
  "status": "connected",
  "created_at": "2026-02-16T10:00:00Z"
}
```

#### GET /api/v1/clusters
List all clusters.

**Query Parameters:**
- `team_id` - Filter by team
- `status` - Filter by status

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "production-k8s",
      "provider": "aws",
      "region": "us-east-1",
      "status": "connected"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

#### POST /api/v1/clusters/{id}/test
Test cluster connection.

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "cluster_info": {
    "version": "1.28",
    "nodes": 5,
    "namespaces": ["default", "production", "staging"]
  }
}
```

---

### Discovery

#### POST /api/v1/discovery/scan
Start a discovery scan.

**Request:**
```json
{
  "target": "192.168.1.0/24",
  "scan_type": "full",
  "ports": "1-1000"
}
```

**Response:**
```json
{
  "scan_id": "uuid",
  "status": "started",
  "target": "192.168.1.0/24"
}
```

#### GET /api/v1/discovery/hosts
List discovered hosts.

**Query Parameters:**
- `scan_id` - Filter by scan
- `managed` - Filter by managed status

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "ip_address": "192.168.1.10",
      "hostname": "web-server-1",
      "ports": [
        {"port": 22, "service": "ssh"},
        {"port": 80, "service": "http"},
        {"port": 443, "service": "https"}
      ],
      "is_managed": false
    }
  ],
  "total": 1
}
```

---

### Chat/AI

#### POST /ai/v1/chat
Send a chat message.

**Request:**
```json
{
  "message": "Show me pods in production namespace",
  "conversation_id": "uuid (optional)",
  "context": {}
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Here are the pods in the production namespace...",
    "sources": [
      {
        "type": "k8s_pod",
        "name": "web-0",
        "namespace": "production",
        "status": "Running"
      }
    ]
  },
  "intent": "query",
  "requires_approval": false
}
```

---

### Workflows

#### POST /api/v1/workflows
Create a workflow.

**Request:**
```json
{
  "name": "Deploy Application",
  "description": "Deploy application to production",
  "definition": {
    "steps": [
      {
        "id": "step1",
        "type": "action",
        "action": "deploy",
        "params": {"image": "myapp:latest"}
      },
      {
        "id": "step2",
        "type": "approval",
        "message": "Deploy to production?"
      }
    ]
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Deploy Application",
  "status": "draft",
  "version": 1,
  "created_at": "2026-02-16T10:00:00Z"
}
```

#### POST /api/v1/workflows/{id}/execute
Execute a workflow.

**Response:**
```json
{
  "execution_id": "uuid",
  "workflow_id": "uuid",
  "status": "running",
  "current_step": 0,
  "started_at": "2026-02-16T10:00:00Z"
}
```

---

### Monitoring

#### GET /api/v1/monitoring/health
Get cluster health.

**Response:**
```json
{
  "cluster": "production-k8s",
  "health": "healthy",
  "nodes": {
    "total": 5,
    "ready": 5,
    "cpu_percent": 45,
    "memory_percent": 62
  },
  "pods": {
    "total": 120,
    "running": 118,
    "pending": 2,
    "failed": 0
  }
}
```

#### GET /api/v1/monitoring/metrics
Get metrics.

**Query Parameters:**
- `cluster_id` - Filter by cluster
- `metric` - Metric type (cpu, memory, network)
- `duration` - Time range (1h, 24h, 7d)

**Response:**
```json
{
  "metric": "cpu",
  "data_points": [
    {"timestamp": "2026-02-16T09:00:00Z", "value": 45},
    {"timestamp": "2026-02-16T10:00:00Z", "value": 52}
  ]
}
```

---

### Costs

#### GET /api/v1/costs/daily
Get daily costs.

**Query Parameters:**
- `cluster_id` - Filter by cluster
- `start_date` - Start date
- `end_date` - End date

**Response:**
```json
{
  "costs": [
    {"date": "2026-02-15", "amount": 125.50, "currency": "USD"},
    {"date": "2026-02-16", "amount": 118.25, "currency": "USD"}
  ],
  "total": 243.75,
  "currency": "USD"
}
```

#### GET /api/v1/costs/recommendations
Get cost optimization recommendations.

**Response:**
```json
{
  "recommendations": [
    {
      "id": "uuid",
      "type": "right_size",
      "resource": "production/web",
      "current": "t3.large",
      "recommended": "t3.medium",
      "savings_monthly": 45.00
    }
  ]
}
```

---

### Notifications

#### POST /api/v1/notifications/send
Send a notification.

**Request:**
```json
{
  "user_id": "uuid",
  "title": "Alert: High CPU",
  "message": "CPU usage is at 95%",
  "channel": "email",
  "priority": "high"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "sent",
  "sent_at": "2026-02-16T10:00:00Z"
}
```

#### GET /api/v1/notifications
List notifications.

**Query Parameters:**
- `user_id` - Filter by user
- `status` - Filter by status
- `channel` - Filter by channel

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Alert: High CPU",
      "message": "CPU usage is at 95%",
      "channel": "email",
      "status": "sent",
      "created_at": "2026-02-16T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## WebSocket Events

### /ws/chat
Real-time chat updates.

**Client → Server:**
```json
{
  "type": "message",
  "conversation_id": "uuid",
  "content": "Show me pods"
}
```

**Server → Client:**
```json
{
  "type": "message",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Here are the pods..."
  }
}
```

### /ws/workflow
Workflow execution updates.

**Server → Client:**
```json
{
  "type": "step_completed",
  "execution_id": "uuid",
  "step_id": "step1",
  "status": "success"
}
```

---

*Last Updated: 2026-02-16*
