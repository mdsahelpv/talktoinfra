# TASKLIST.md - TalkAI Platform Development

## Phase 0 - Foundation & Core Services

### Week 1-2: Infrastructure Setup

- [x] **Task 0.1**: Mock Data Removal
  - Remove hardcoded mock data from all services
  - Replace with database queries
  - Update API responses to use real data
  - Status: COMPLETED

- [x] **Task 0.2**: Infrastructure Onboarding Service (Port 8011)
  - Create FastAPI service for cluster onboarding
  - Kubeconfig validation and storage
  - Vault integration for credential management
  - Connection testing logic
  - Status: COMPLETED

### Week 3-4: Frontend & Integration

- [x] **Task 0.3**: Frontend Onboarding UI
  - 5-step ConnectWizard component
  - ConnectionDashboard component
  - API client for onboarding
  - Status: COMPLETED

- [x] **Task 0.4**: Update Existing Services
  - Update all services to remove mock data references
  - Integrate with new onboarding service
  - Update Docker configurations
  - Status: COMPLETED

### Week 5-6: Discovery Integration

- [x] **Task 0.5**: Discovery → Onboarding Integration
  - Link discovered resources to onboarding flow
  - Pre-fill onboarding from discovery data
  - Status: COMPLETED

- [x] **Task 0.6**: Unified Discovered Infrastructure
  - Unified model for all discovered resources
  - Consistent API across resource types
  - Status: COMPLETED

### Week 7-8: User Interaction

- [x] **Task 0.7**: User Interaction & Query Workflows
  - Chat interface for queries
  - Query processing pipeline
  - Result display and interaction
  - Status: COMPLETED

### Week 9-10: Monitoring & Alerting

- [x] **Task 0.8**: Continuous Monitoring & Alerting ✅ COMPLETED
  - [x] Real-Time Monitoring Service (Port 8009)
    - [x] Health check endpoints
    - [x] Resource utilization tracking
    - [x] K8s cluster monitoring
    - [x] Database monitoring
    - [x] Queue depth monitoring
    - [x] SSL certificate tracking
  - [x] Smart Alerting Engine
    - [x] Alert rules with thresholds
    - [x] Anomaly detection
    - [x] Rate of change alerts
    - [x] Severity levels (INFO/WARNING/ERROR/CRITICAL)
    - [x] Alert deduplication
    - [x] Escalation policies
    - [x] Notification channels (Email, Slack, PagerDuty)
  - [x] Dashboard Integration
    - [x] Grafana-ready API
    - [x] Pre-built panels data format
  - [x] Anomaly Detection
    - [x] Baseline learning
    - [x] Statistical outlier detection
    - [x] Predictive alerts
  - [x] Alert Correlation
    - [x] Root cause analysis support
    - [x] Related alert grouping
    - [x] Alert storm detection
  - [x] Frontend Components
    - [x] AlertList.tsx
    - [x] MetricsChart.tsx
    - [x] ServiceHealth.tsx
    - [x] Monitoring.tsx dashboard
  - [x] Docker Integration
    - [x] Dockerfile
    - [x] docker-compose.yml update
  - Status: COMPLETED (2024-02-25)

### Week 11-12: Additional Features

- [ ] **Task 0.9**: Cost Management & Optimization ✅ COMPLETED
  - [x] Cost Tracking Service (Port 8010)
    - [x] AWS Cost Explorer API integration
    - [x] Azure Cost Management API integration
    - [x] GCP Cloud Billing API integration
    - [x] Kubernetes resource cost allocation
    - [x] Daily/weekly/monthly cost aggregation
    - [x] Cost by cluster, namespace, workload
    - [x] Historical trend analysis
    - [x] Budget tracking and alerts
  - [x] Cost Estimation API
    - [x] Estimate cost before deployment
    - [x] Resource specifications (CPU, memory, storage, network)
    - [x] Estimated monthly cost per cloud provider
    - [x] Reserved instances vs on-demand support
    - [x] Spot instance pricing comparison
  - [x] Optimization Recommendations Engine
    - [x] Resource utilization vs cost analysis
    - [x] Underutilized resources detection (idle > 80%)
    - [x] Over-provisioned resources identification
    - [x] Right-sizing opportunities
    - [x] Spot instance candidates
    - [x] Storage optimization (gp2 → gp3, delete snapshots)
    - [x] Actionable recommendations with priority ranking
  - [x] Cost Dashboard UI
    - [x] Cost overview with trends
    - [x] Cost by cluster/cloud provider/namespace
    - [x] Budget tracking with alerts
    - [x] Optimization recommendations list
    - [x] "What-if" scenario planning
  - [x] Files Created:
    - [x] services/cost-service/config.py
    - [x] services/cost-service/main.py
    - [x] services/cost-service/models.py
    - [x] services/cost-service/schemas.py
    - [x] services/cost-service/database.py
    - [x] services/cost-service/api/v1/costs.py
    - [x] services/cost-service/api/v1/budgets.py
    - [x] services/cost-service/api/v1/estimates.py
    - [x] services/cost-service/api/v1/recommendations.py
    - [x] services/cost-service/services/estimator.py
    - [x] services/cost-service/services/optimizer.py
    - [x] services/cost-service/services/collectors/*.py
    - [x] services/cost-service/requirements.txt
    - [x] services/cost-service/Dockerfile
    - [x] services/cost-service/README.md
    - [x] services/frontend/src/types/cost.ts
    - [x] services/frontend/src/lib/api/cost.ts
    - [x] services/frontend/src/components/cost/*.tsx
    - [x] services/frontend/src/pages/CostManagement.tsx
  - [x] docker-compose.yml update
  - Status: COMPLETED (2026-02-04)

- [x] **Task 0.10**: AI Engine Configuration ✅ COMPLETED
  - [x] Model Management API
    - [x] Provider configurations (OpenAI, Anthropic, Azure, Bedrock, Ollama, vLLM)
    - [x] Model settings (temperature, max_tokens, top_p, frequency_penalty)
    - [x] Fallback chain configuration
    - [x] Model cost tracking per request
  - [x] Agent Configuration
    - [x] Agent types (Query, Action, Analysis, Planning)
    - [x] Model assignment per agent
    - [x] Agent-specific system prompts
    - [x] Tool access control per agent
  - [x] RAG Configuration
    - [x] Vector store settings (Qdrant, Pinecone, Weaviate)
    - [x] Embedding model selection
    - [x] Chunk size, overlap settings
    - [x] Similarity threshold configuration
  - [x] Prompt Management
    - [x] Prompt templates library
    - [x] Version control for prompts
    - [x] A/B testing framework
    - [x] Prompt performance analytics
  - [x] Settings UI
    - [x] Models tab (provider, model, config)
    - [x] Agents tab (agent configs, tool access)
    - [x] RAG tab (vector store, embeddings)
    - [x] Prompts tab (template library)
    - [x] Safety tab (approval thresholds, blocking rules)
    - [x] Live preview of model responses
    - [x] Configuration export/import
  - [x] Files Created:
    - [x] services/ai-router/models_config.py
    - [x] services/ai-router/config.py (MODIFIED)
    - [x] services/ai-router/main.py (MODIFIED)
    - [x] services/ai-router/api/v1/settings.py
    - [x] services/ai-router/services/model_manager.py
    - [x] services/ai-router/services/agent_config.py
    - [x] services/ai-router/services/rag_config.py
    - [x] services/ai-router/tests/test_settings.py
    - [x] services/frontend/src/pages/Settings/AISettings.tsx
    - [x] services/frontend/src/pages/Settings/ModelSettings.tsx
    - [x] services/frontend/src/pages/Settings/AgentSettings.tsx
    - [x] services/frontend/src/pages/Settings/RAGSettings.tsx
    - [x] services/frontend/src/pages/Settings/PromptSettings.tsx
    - [x] services/frontend/src/pages/Settings/SafetySettings.tsx
    - [x] services/frontend/src/components/settings/ModelCard.tsx
    - [x] services/frontend/src/components/settings/AgentCard.tsx
    - [x] services/frontend/src/components/settings/PromptEditor.tsx
    - [x] services/frontend/src/components/settings/index.ts
    - [x] services/frontend/src/lib/api/settings.ts
    - [x] services/frontend/src/lib/types/settings.ts
    - [x] services/frontend/src/pages/SettingsPage.tsx (MODIFIED)
  - Status: COMPLETED (2026-02-05)

### 0.11 Data Architecture & RAG Pipeline (CRITICAL - Prevents AI Hallucinations) ✅ COMPLETED

**DISCOVERY SCAN DATA → STRUCTURED STORAGE → VECTOR EMBEDDINGS → RAG → AI ANSWERS**

**Status:** ✅ COMPLETED (2026-02-05) - RAG Service implemented on Port 8012

#### Data Storage Architecture (3-Layer) ✅

- [x] **Layer 1: Structured Storage (PostgreSQL)**
  - [x] Discovery Data Tables - Enhanced with scan_metadata, service_banners, ssl_certificate, last_seen_at
  - [x] K8s Resource Tables - pods, deployments, services, nodes, events, logs
  - [x] Cloud Resource Tables - AWS instances/RDS, Azure VMs, GCP instances
  - [x] Relationships & Graph - resource_relationships table

- [x] **Layer 2: Searchable Document Store (Elasticsearch/OpenSearch)**
  - [x] infrastructure-logs index
  - [x] infrastructure-events index
  - [x] infrastructure-configs index

- [x] **Layer 3: Vector Embeddings (Qdrant)**
  - [x] infrastructure-resources collection (main)
  - [x] infrastructure-logs collection
  - [x] infrastructure-docs collection
  - [x] infrastructure-runbooks collection

#### Data Transformation Pipeline ✅

- [x] **Discovery Data → RAG Documents**
  - [x] Text generation for embeddings
  - [x] K8s Resource → RAG Document transformation

- [x] **Automated Indexing Pipeline**
  - [x] Discovery Service → RAG (batch indexing)
  - [x] K8s Ingestion → RAG (event-driven)
  - [x] Incremental Updates with last_indexed_at tracking

#### RAG Query Flow ✅

- [x] User Query Processing with embeddings and similarity search
- [x] Source Citations with full traceability
- [x] Context Window Management (hierarchical RAG)
- [x] Multi-Source RAG Architecture

#### Real-Time Data Synchronization ✅

- [x] Event-Driven Updates via NATS
- [x] Data Freshness Indicators in UI

#### Files Created:
  - [x] services/rag-service/config.py
  - [x] services/rag-service/main.py (Port 8012)
  - [x] services/rag-service/models.py
  - [x] services/rag-service/schemas.py
  - [x] services/rag-service/database.py
  - [x] services/rag-service/api/v1/index.py
  - [x] services/rag-service/api/v1/search.py
  - [x] services/rag-service/api/v1/sources.py
  - [x] services/rag-service/services/embedder.py
  - [x] services/rag-service/services/indexer.py
  - [x] services/rag-service/services/pipeline.py
  - [x] services/rag-service/Dockerfile
  - [x] services/rag-service/requirements.txt
  - [x] services/rag-service/README.md
  - [x] docker-compose.yml update (rag-service Port 8012)

**DISCOVERY SCAN DATA → STRUCTURED STORAGE → VECTOR EMBEDDINGS → RAG → AI ANSWERS**

**The Problem:** Discovery scan data is in PostgreSQL but NOT in RAG. AI can't answer "What servers do I have?" without hallucinating.

#### Current Data Flow (Broken):
```
Discovery Scan → PostgreSQL (Only) 
                    ↓
              ❌ NOT in RAG!
                    ↓
User: "What servers do I have?"
AI: "I don't know" or Hallucinates ❌
```

#### Required Data Flow (Fixed):
```
Discovery Scan → PostgreSQL (Structured) ──┐
                                            ├──▶ Unified Index ──▶ RAG (Qdrant)
K8s Resources ──▶ Real-time Watch API ────┘        (Vector Search)
                                                    ↓
User: "What servers do I have?"                     ↓
AI: Retrieves from RAG → "Found 5 servers:" ✓
   • web-server-1 (192.168.1.10) - Running
   • db-server-1 (192.168.1.11) - PostgreSQL
   Source: Discovery Scan #123, Jan 15 2024
```

#### Data Storage Architecture (3-Layer) ✅ COMPLETED

- [x] **Layer 1: Structured Storage (PostgreSQL)**
  - [x] **Discovery Data Tables** (Already exist, enhance them):
    - [x] `discovered_hosts` - IP, hostname, ports, banners
    - [x] `discovered_ports` - Port, service, version, status
    - [x] `managed_hosts` - Promoted from discovered
    - [x] Add `scan_metadata` JSON field to store full nmap/masscan output
    - [x] Add `service_banners` TEXT field for grab banners (HTTP headers, SSH version, etc.)
    - [x] Add `ssl_certificate` JSON for cert info (expiry, issuer)
    - [x] Add `last_seen_at` timestamp for tracking
  - [x] **K8s Resource Tables** (NEW):
    - [x] `k8s_pods` - name, namespace, status, node, images, labels
    - [x] `k8s_deployments` - name, namespace, replicas, strategy
    - [x] `k8s_services` - name, type, cluster_ip, ports, selectors
    - [x] `k8s_nodes` - name, status, capacity, labels, taints
    - [x] `k8s_events` - reason, message, timestamp, involved_object
    - [x] `k8s_logs` - pod_name, container, timestamp, log_line, level
  - [x] **Cloud Resource Tables** (NEW):
    - [x] `aws_instances` - instance_id, type, state, region, tags
    - [x] `aws_rds` - db_id, engine, version, status, endpoint
    - [x] `azure_vms`, `gcp_instances` (similar)
  - [x] **Relationships & Graph** (NEW):
    - [x] `resource_relationships` - from_resource, to_resource, relation_type
    - [x] Types: "hosts_pod", "service_targets_deployment", "node_runs_pod"
    - [x] Use for topology, impact analysis

- [x] **Layer 2: Searchable Document Store (Elasticsearch/OpenSearch)**
  - [x] **Why needed:** Full-text search on logs, error messages, unstructured data
  - [x] **Indexes:**
    - [x] `infrastructure-logs` - Pod logs, system logs
    - [x] `infrastructure-events` - K8s events, scan events
    - [x] `infrastructure-configs` - ConfigMaps, Secrets (redacted values)
    - [x] `infrastructure-docs` - Confluence, READMEs
  - [x] **Features:**
    - [x] Log aggregation from all clusters
    - [x] Full-text search: "Find all errors about 'connection refused'"
    - [x] Log pattern detection
    - [x] Time-series aggregation

- [x] **Layer 3: Vector Embeddings (Qdrant)**
  - [x] **Purpose:** Semantic search for AI RAG
  - [x] **Collections:**
    - [x] `infrastructure-resources` - Embeddings of all infrastructure (main)
    - [x] `infrastructure-logs` - Embeddings of log patterns
    - [x] `infrastructure-docs` - Documentation embeddings
    - [x] `infrastructure-runbooks` - Troubleshooting guides
  - [ ] **Document Structure in Qdrant:**
    ```json
    {
      "id": "host-192-168-1-10",
      "vector": [0.1, 0.2, ...],  // 384-dim embedding
      "payload": {
        "resource_type": "host",
        "source": "discovery_scan",
        "source_id": "scan-123",
        "text": "Host 192.168.1.10 running Ubuntu 20.04, ports: 22(ssh), 80(http), 443(https), services: nginx/1.18",
        "structured_data": {
          "ip": "192.168.1.10",
          "hostname": "web-server-1",
          "ports": [22, 80, 443],
          "services": ["ssh", "nginx"],
          "status": "online"
        },
        "metadata": {
          "discovered_at": "2024-01-15T10:30:00Z",
          "scan_job_id": "123",
          "confidence": 0.95
        }
      }
    }
    ```

#### Data Transformation Pipeline ✅

- [x] **Discovery Data → RAG Documents**
  - [x] **Text Generation for Embeddings:**
    ```python
    # Transform discovered host to searchable text
    def host_to_text(host):
      return f"""
      Host: {host.ip_address} ({host.hostname or 'unknown'})
      Status: {host.status}
      Operating System: {detected_os_from_banner}
      Open Ports: {', '.join([f"{p.port}/{p.protocol} ({p.service})" for p in host.ports])}
      Services: {', '.join([p.service for p in host.ports if p.service])}
      Service Versions: {', '.join([p.service_version for p in host.ports if p.service_version])}
      Located in network: {host.network_range}
      First discovered: {host.discovered_at}
      Last seen: {host.last_seen_at}
      Management status: {'Managed' if host.is_managed else 'Unmanaged'}
      Notes: {host.notes or 'None'}
      """
    ```
  - [x] **K8s Resource → RAG Document:**
    ```python
    # Transform K8s pod to searchable text
    def pod_to_text(pod):
      return f"""
      Pod: {pod.name} in namespace {pod.namespace}
      Status: {pod.status.phase} ({pod.status.conditions})
      Node: {pod.spec.node_name}
      Containers: {', '.join([c.name for c in pod.spec.containers])}
      Images: {', '.join([c.image for c in pod.spec.containers])}
      Labels: {json.dumps(pod.metadata.labels)}
      Resource Usage: CPU {pod.metrics.cpu}%, Memory {pod.metrics.memory}Mi
      Restarts: {pod.status.container_statuses[0].restart_count}
      Age: {time_since(pod.metadata.creation_timestamp)}
      Cluster: {pod.cluster_id}
      """
    ```

- [x] **Automated Indexing Pipeline**
  - [x] **Discovery Service → RAG:**
    - [x] Trigger: Scan job completes
    - [x] Action: Transform all discovered hosts → text → embeddings → Qdrant
    - [x] Batch size: 100 hosts at a time
    - [x] Update frequency: Real-time (within 30 seconds of scan completion)
  - [x] **K8s Ingestion → RAG:**
    - [x] Trigger: Resource change detected via Watch API
    - [x] Action: 
      - [x] Pod created → Add to Qdrant
      - [x] Pod deleted → Remove from Qdrant
      - [x] Pod updated → Update embedding
    - [x] Frequency: Event-driven (no polling)
  - [x] **Incremental Updates:**
    - [x] Don't re-index everything every time
    - [x] Track `last_indexed_at` timestamps
    - [x] Only index changed resources
    - [x] Handle deletions properly (remove from Qdrant)

#### RAG Query Flow (Prevents Hallucinations) ✅

- [x] **User Query Processing:**
  ```
  User: "What web servers do I have?"
           ↓
  Step 1: Generate embedding for query
           ↓
  Step 2: Search Qdrant (vector similarity)
           - Finds documents about "web servers"
           - Returns top 5 matches with scores
           ↓
  Step 3: Filter by relevance (score > 0.7)
           ↓
  Step 4: Build context window
           - Document 1: "Host 192.168.1.10 running nginx..."
           - Document 2: "Host 192.168.1.11 running apache..."
           - Document 3: "Pod web-server-1 in namespace production..."
           ↓
  Step 5: Send to LLM with prompt:
           "Answer based ONLY on these sources:
            [Source 1] Host 192.168.1.10 running nginx...
            [Source 2] Host 192.168.1.11 running apache...
            
            Question: What web servers do I have?"
           ↓
  Step 6: LLM generates answer using ONLY provided context
           ↓
  Step 7: Return to user with source citations
  ```

- [x] **Source Citations (CRITICAL for Trust)**
  - [ ] Every AI answer includes:
    ```json
    {
      "answer": "You have 3 web servers: web-server-1 (nginx), web-server-2 (nginx), and apache-server-1.",
      "sources": [
        {
          "id": "host-192-168-1-10",
          "type": "discovered_host",
          "name": "192.168.1.10",
          "description": "Host running nginx on port 80",
          "retrieved_at": "2024-01-15T10:35:00Z",
          "confidence": 0.94,
          "raw_data": { /* full structured data */ }
        },
        {
          "id": "host-192-168-1-11",
          "type": "discovered_host",
          "name": "192-168-1-11",
          "description": "Host running apache on port 80",
          "confidence": 0.91
        }
      ],
      "retrieved_count": 2,
      "query_time_ms": 45
    }
    ```
  - [ ] UI shows: "Based on 2 sources: Discovery Scan #123, Jan 15 2024"
  - [ ] User can click source to see raw data
  - [ ] "View all sources" button expands full list

- [x] **Context Window Management**
  - [ ] **Problem:** LLM has limited context window (4K-128K tokens)
  - [ ] **Solution: Hierarchical RAG**
    - [ ] Level 1: Retrieve top 5 most relevant documents
    - [ ] Level 2: If not enough context, retrieve related documents
    - [ ] Level 3: For "list all" queries, use structured DB query instead
  - [ ] **Structured Query Fallback:**
    - [ ] Detect query type: "List all pods" vs "Why is my pod failing?"
    - [ ] For "list all" → Query PostgreSQL directly (not RAG)
    - [ ] For "analysis" → Use RAG for semantic understanding
    - [ ] Hybrid approach: Use both structured + RAG

#### Multi-Source RAG Architecture

- [x] **Combine Multiple Data Sources:**
  ```
  User: "Why is my web server slow?"
           ↓
  RAG retrieves from:
  ├─ Infrastructure DB: "web-server-1 (192.168.1.10) - CPU 95%, Memory 80%"
  ├─ Log Store: "ERROR: Connection pool exhausted at 14:30"
  ├─ Metrics: "Response time: 2.5s (normal: 200ms)"
  ├─ Documentation: "High CPU usually indicates..."
  └─ Runbooks: "Troubleshooting slow response times..."
           ↓
  AI Answer: "Your web server (192.168.1.10) is slow because:
             1. CPU is at 95% (threshold: 80%)
             2. Connection pool errors in logs
             3. Response time is 12x normal
             
             Suggested actions: [Scale up] [View logs] [Check connections]"
  ```

#### Real-Time Data Synchronization ✅

- [x] **Event-Driven Updates (NATS)**
  - [x] **Discovery Service publishes:**
    - [x] `discovery.scan.completed` → Ingestion Service indexes results
    - [x] `discovery.host.updated` → Update single host in Qdrant
  - [x] **K8s Watcher publishes:**
    - [x] `k8s.pod.created` → Add to Qdrant
    - [x] `k8s.pod.deleted` → Remove from Qdrant
    - [x] `k8s.pod.modified` → Update embedding
  - [x] **Ingestion Service subscribes:**
    - [x] Listen to all events
    - [x] Update Qdrant within 5 seconds
    - [x] Track lag metrics

- [x] **Data Freshness Indicators**
  - [ ] Show user: "Data last updated: 2 minutes ago"
  - [ ] Warning: "Some data may be stale (> 1 hour old)"
  - [ ] "Refresh data" button in chat

#### Data Quality & Validation

- [ ] **Preventing Stale Data Hallucinations**
  - [ ] **Timestamp validation:**
    - [ ] Reject documents older than 30 days for certain queries
    - [ ] Prefer recently updated documents
    - [ ] Show data age in citations
  - [ ] **Confidence scoring:**
    - [ ] Low confidence (< 0.6): "I'm not certain, but..."
    - [ ] No results: "I don't have information about that"
    - [ ] Never hallucinate: If no data, say "I don't know"
  - [ ] **Cross-validation:**
    - [ ] Compare RAG results with live K8s API
    - [ ] If mismatch: "My data shows X, but live check shows Y"

- [ ] **Data Lineage Tracking**
  - [ ] Every RAG document tracks:
    - [ ] Source system (Discovery, K8s, Cloud)
    - [ ] Original ID in source system
    - [ ] Ingestion timestamp
    - [ ] Transformation version
    - [ ] Last validation timestamp
  - [ ] UI: "This data came from Discovery Scan #123 on Jan 15"

#### Performance & Scaling

- [ ] **Indexing Performance**
  - [ ] Batch indexing: 100 documents at a time
  - [ ] Parallel processing: Multiple workers
  - [ ] Indexing queue (Celery/Redis)
  - [ ] Progress tracking: "Indexing 500/1000 hosts..."

- [ ] **Query Performance**
  - [ ] Qdrant caching layer
  - [ ] Frequently accessed documents cached in Redis
  - [ ] Query result caching (5-minute TTL)
  - [ ] Performance metrics: avg query time < 100ms

- [ ] **Storage Optimization**
  - [ ] Document deduplication
  - [ ] Compression for large payloads
  - [ ] Archival of old scan data (> 90 days)
  - [ ] Sharding by cluster/tenant

#### Backend API Endpoints

- [ ] **New API Endpoints in Ingestion Service:**
  - [ ] `POST /api/v1/ingest/discovery/{scan_id}` - Index scan results
  - [ ] `POST /api/v1/ingest/k8s/resources` - Index K8s resources
  - [ ] `DELETE /api/v1/ingest/{resource_id}` - Remove from index
  - [ ] `POST /api/v1/rag/search` - Search with natural language
  - [ ] `GET /api/v1/rag/sources/{query_id}` - Get sources for answer
  - [ ] `POST /api/v1/rag/refresh` - Force refresh index
  - [ ] `GET /api/v1/rag/stats` - Index statistics

#### Frontend Integration

- [ ] **Chat UI Enhancements**
  - [ ] Show "Thinking... Retrieving sources" while RAG searches
  - [ ] Collapsible "Sources" section under each answer
  - [ ] Source cards showing:
    - [ ] Icon (host/pod/database)
    - [ ] Name/IP
    - [ ] Type (Discovery Scan, K8s, etc.)
    - [ ] Timestamp
    - [ ] Relevance score
  - [ ] "Data as of [timestamp]" footer
  - [ ] "Refresh data" button if stale

### 0.7 User Interaction & Query Workflows (The "Day 2" Experience)

**After infrastructure is onboarded, users need to actually INTERACT with it. This is the core value of TalkAI.**

- [ ] **Query Intent Classification & Routing**
  - [ ] Define query types:
    - [ ] **Read Queries** (safe, auto-execute):
      - "Show me pods in namespace X"
      - "Get logs for deployment Y"
      - "What services are running?"
      - "Describe node Z"
      - "Show me AWS EC2 instances"
    - [ ] **Analysis Queries** (safe, auto-execute):
      - "Why is my pod failing?"
      - "Analyze resource usage"
      - "Find bottlenecks"
      - "Compare clusters"
    - [ ] **Action Queries** (requires approval):
      - "Scale deployment to 5 replicas"
      - "Restart pod X"
      - "Delete service Y"
      - "Update config map"
    - [ ] **Planning Queries** (create plans):
      - "Plan migration from v1 to v2"
      - "How do I add a new service?"
      - "Create backup strategy"
  - [ ] AI Router: Classify intent and route to appropriate agent
  - [ ] Safety check: Determine if query is read-only or destructive
  - [ ] Auto-execution: Read queries run immediately, actions wait for approval

- [ ] **Chat Interface Workflow**
  - [ ] **Message flow:**
    ```
    User: "scale web deployment to 3 replicas"
           │
           ▼
    AI Router: Classifies as ACTION (requires approval)
           │
           ▼
    Agent Service: Creates execution plan
           │
           ▼
    Policy Engine: "This requires approval - escalate?"
           │
           ▼
    Action Engine: DRY-RUN (simulate change, show preview)
           │
           ▼
    User sees: "Preview: deployment will scale 2→3 replicas"
           │
           ▼
    User: [Approve] or [Reject]
           │
           ▼
    Action Engine: EXECUTE real change
           │
           ▼
    Audit Service: Logs everything
           │
           ▼
    User sees: "✓ Deployment scaled successfully"
    ```
  - [ ] **Rich message rendering:**
    - [ ] Tables for pod lists with status colors
    - [ ] Code blocks for YAML manifests
    - [ ] Resource cards (showing CPU/memory/labels)
    - [ ] Action buttons (Approve/Reject/View Logs)
    - [ ] Links to resource details
    - [ ] Source citations (which cluster/namespace)

- [ ] **Approval Workflow UI**
  - [ ] **Pending Approvals Dashboard** (`/approvals`):
    - [ ] List of pending actions with:
      - Action type (scale, restart, delete)
      - Target resource (deployment name, namespace, cluster)
      - Who requested it
      - When it was requested
      - Risk level (Low/Medium/High)
      - Dry-run preview
    - [ ] Filter by: pending/approved/rejected, user, date range
    - [ ] Search by resource name or action type
  - [ ] **Approval Detail View**:
    - [ ] Show full context:
      - Original user query
      - AI's interpretation
      - Execution plan (step-by-step)
      - Dry-run results (before/after comparison)
      - Risk assessment
      - Required permissions
      - Similar past actions
    - [ ] Approve/Reject with comment
    - [ ] "Approve with conditions" option
    - [ ] Escalate to higher approver
  - [ ] **Approval Chains**:
    - [ ] Multi-level approval for critical actions
    - [ ] Configurable: "Scale > 10 replicas requires manager approval"
    - [ ] Notifications: Slack, email, in-app
    - [ ] Timeout handling (auto-reject after 24h)

- [ ] **Query Result Handling**
  - [ ] **Pagination for large results:**
    - [ ] "Found 247 pods. Showing first 20."
    - [ ] Load more / infinite scroll
    - [ ] Filter in chat: "only show failing pods"
  - [ ] **Result actions:**
    - [ ] "Export to CSV" button
    - [ ] "Save this query" (bookmark)
    - [ ] "Create alert from this" (notify when condition changes)
    - [ ] "Drill down" (click pod name to see details)
  - [ ] **Context preservation:**
    - [ ] Remember last cluster/namespace context
    - [ ] "In the same namespace, show me services"
    - [ ] Cross-cluster queries: "show me all pods across clusters"

- [ ] **Natural Language Understanding**
  - [ ] **Entity extraction:**
    - [ ] Cluster names: "production cluster", "k8s-prod-1"
    - [ ] Resource types: pods, deployments, services, nodes
    - [ ] Resource names: "web-deployment", "api-service"
    - [ ] Namespaces: "default", "kube-system", "production"
    - [ ] Time ranges: "last hour", "since yesterday"
    - [ ] Conditions: "failing", "pending", "high CPU"
  - [ ] **Ambiguity resolution:**
    - [ ] "Which cluster? (production/staging)"
    - [ ] "Which namespace? Found 3 web-deployments"
    - [ ] "Do you mean pods or deployments?"
  - [ ] **Fuzzy matching:**
    - [ ] "web dep" → "web-deployment"
    - [ ] "api svc" → "api-service"
    - [ ] Handle typos gracefully

- [ ] **Multi-Step Task Execution**
  - [ ] **Complex workflows:**
    - [ ] "Deploy new version of API":
      1. Update image tag
      2. Rolling restart
      3. Verify health checks
      4. Monitor for 5 minutes
      5. Rollback if errors > threshold
    - [ ] "Migrate database":
      1. Create backup
      2. Run migration
      3. Verify schema
      4. Update app config
  - [ ] **Progress tracking:**
    - [ ] Show step-by-step progress in chat
    - [ ] Real-time status updates
    - [ ] Pause/Resume/Cancel buttons
  - [ ] **Conditional logic:**
    - [ ] "If health checks pass, proceed. Else rollback."
    - [ ] "Wait for 5 minutes then check again."

- [ ] **Conversation Context & Memory**
  - [ ] **Session persistence:**
    - [ ] Remember conversation across page reloads
    - [ ] Show conversation history in sidebar
    - [ ] Search past conversations
  - [ ] **Contextual follow-ups:**
    - [ ] User: "show me pods"
      System: [lists pods]
    - [ ] User: "restart the failing ones"
      System: "Found 3 CrashLoopBackOff pods. Restart all? [Yes] [No] [Select]"
  - [ ] **User preferences learning:**
    - [ ] Learn preferred cluster (usually production)
    - [ ] Remember preferred output format (table vs JSON)
    - [ ] Suggest common queries based on role

### 0.8 Continuous Monitoring & Alerting Workflow (Background Intelligence)

**After infrastructure is onboarded, the system should proactively monitor and alert - not just react to user queries.**

- [ ] **Real-Time Resource Monitoring**
  - [ ] **What to monitor continuously:**
    - [ ] Pod status changes (Pending → Running → CrashLoopBackOff)
    - [ ] Node health (Ready → NotReady)
    - [ ] Deployment rollouts (progress, failures)
    - [ ] Service endpoints (available/unavailable)
    - [ ] Resource usage (CPU/memory trending up)
    - [ ] Certificate expirations (< 30 days warning)
    - [ ] Persistent volume capacity (> 80% warning)
    - [ ] Image pull failures
    - [ ] OOMKilled events
  - [ ] **Monitoring implementation:**
    - [ ] K8s Watch API for real-time events (not polling)
    - [ ] CloudWatch/Cloud Monitoring integration
    - [ ] Metric collection (Prometheus scraping)
    - [ ] Log aggregation (tail -f on pod logs)

- [ ] **Smart Alerting System**
  - [ ] **Alert types:**
    - [ ] **Critical** (immediate Slack/phone call):
      - Production outage
      - Database connection failures
      - 5xx errors spike
      - Certificate expired
    - [ ] **Warning** (Slack/email):
      - High resource usage (> 80% for 10min)
      - Pod restart loop
      - Unusual error rates
      - Node disk pressure
    - [ ] **Info** (in-app notification):
      - Successful deployments
      - New version detected
      - Scheduled maintenance reminder
  - [ ] **Alert deduplication:**
    - [ ] Don't spam: "Pod failing" sent once, not every minute
    - [ ] Group related alerts: "3 pods failing in deployment X"
    - [ ] Escalate if not acknowledged in 15 minutes
  - [ ] **Alert enrichment:**
    - [ ] Include context: "web-pod-5 failing, last logs: [ERROR: connection refused]"
    - [ ] Suggest actions: "Try: restart pod, check service endpoint, view logs"
    - [ ] Link to runbooks: "See troubleshooting guide for ConnectionRefused"

- [ ] **Proactive Insights (AI-Powered)**
  - [ ] **Anomaly detection:**
    - [ ] "Unusual traffic pattern detected: requests up 300%"
    - [ ] "CPU usage spiked at 2am (usually 10%, now 95%)"
    - [ ] "New outbound connection to unknown IP"
    - [ ] "Pod image changed from v1.2 to v1.3 without deployment"
  - [ ] **Trend analysis:**
    - [ ] "Resource usage trending up 15% per week - scale soon?"
    - [ ] "Disk will fill in 7 days at current growth rate"
    - [ ] "Cost increased 40% this month vs last month"
  - [ ] **Health scoring:**
    - [ ] Cluster health score (0-100)
    - [ ] Component-level scores (network, storage, compute)
    - [ ] Recommendations to improve score

- [ ] **Automated Response Actions**
  - [ ] **Self-healing (optional, configurable):**
    - [ ] Auto-restart CrashLoopBackOff pods (max 3 times)
    - [ ] Auto-scale HPA when CPU > 70% for 5min
    - [ ] Auto-retry failed jobs with exponential backoff
    - [ ] Clear evicted pods automatically
  - [ ] **Approval-required automations:**
    - [ ] "Pod failing 5 times. Suggest: [Auto-restart] [Investigate] [Ignore]"
    - [ ] "High memory usage. Suggest: [Scale up] [Optimize code] [Add alert]"
  - [ ] **Runbook automation:**
    - [ ] Detect issue → Execute runbook steps → Report results
    - [ ] Example: "Disk full detected" → "Clean logs > 7 days" → "Report freed space"

- [ ] **Monitoring Dashboard**
  - [ ] **Real-time status page** (`/monitoring`):
    - [ ] Cluster health overview (green/yellow/red)
    - [ ] Active alerts list with severity
    - [ ] Recent events timeline
    - [ ] Top resources by CPU/memory
    - [ ] Failing pods summary
  - [ ] **Drill-down views:**
    - [ ] Per-cluster status
    - [ ] Per-namespace resource usage
    - [ ] Node-level metrics
    - [ ] Pod-level logs and events

### 0.9 Cost Management & Optimization Workflow

**Infrastructure costs money. Track it and optimize.**

- [ ] **Cost Tracking & Attribution**
  - [ ] **Tagging strategy:**
    - [ ] Auto-tag resources with: team, project, environment
    - [ ] Track cost per namespace, per deployment, per service
    - [ ] Chargeback reports for teams
  - [ ] **Multi-cloud cost aggregation:**
    - [ ] AWS Cost Explorer integration
    - [ ] Azure Cost Management integration
    - [ ] GCP Billing integration
    - [ ] Kubernetes cost (Kubecost/opencost)
    - [ ] Unified dashboard: "Total spend across all clouds"

- [ ] **Cost Anomaly Detection**
  - [ ] "AWS spend increased $500/day (usual: $100/day)"
  - [ ] "New expensive instance type detected: m5.24xlarge"
  - [ ] "Unused EBS volumes costing $200/month"
  - [ ] "Data transfer costs spiked 500%"

- [ ] **Optimization Recommendations**
  - [ ] **Right-sizing:**
    - [ ] "Pod using 10% of requested CPU → suggest reduce request to 100m"
    - [ ] "Node at 20% utilization → suggest consolidate workloads"
  - [ ] **Resource cleanup:**
    - [ ] "15 unused PVCs detected (total: $150/month)"
    - [ ] "3 stopped EC2 instances still charging storage"
    - [ ] "Orphaned load balancers (no backends)"
  - [ ] **Savings opportunities:**
    - [ ] "Use Spot instances for dev workloads (save 70%)"
    - [ ] "Reserved capacity available (save 40% on steady workloads)"
    - [ ] "Enable cluster autoscaling (save 30% off-hours)"

- [ ] **Budgeting & Forecasting**
  - [ ] Set monthly budgets per team/project
  - [ ] Forecast next month spend based on trends
  - [ ] Alert at 50%, 80%, 100% of budget
  - [ ] "At current rate, you'll exceed budget by $500 on day 25"

### 0.10 AI Engine Configuration Section (Settings Page)

**Comprehensive AI/LLM configuration in Settings. Users need control over which models are used, their parameters, and performance tuning.**

#### Backend API & Database Schema

- [ ] **Create AI Configuration Service** (Extend AI Router or New Service)
  - [ ] **Database table: `ai_engine_config`**
    - [ ] `ollama_host` - URL endpoint
    - [ ] `ollama_timeout` - Request timeout seconds
    - [ ] `ollama_auth_token` - Optional authentication
    - [ ] `models_config` - JSON blob with all model settings
    - [ ] `feature_toggles` - JSON (enable/disable AI features)
    - [ ] `performance_settings` - Caching, rate limits
    - [ ] `prompt_templates` - Custom system prompts
    - [ ] `updated_at`, `updated_by`
  - [ ] **API Endpoints:**
    - [ ] `GET /api/v1/ai-engine/config` - Get current configuration
    - [ ] `POST /api/v1/ai-engine/config` - Update configuration
    - [ ] `POST /api/v1/ai-engine/test-connection` - Test Ollama connection
    - [ ] `GET /api/v1/ai-engine/models/available` - List available models from Ollama
    - [ ] `GET /api/v1/ai-engine/models/installed` - List installed models with info
    - [ ] `POST /api/v1/ai-engine/models/pull` - Pull/download a model
    - [ ] `DELETE /api/v1/ai-engine/models/{name}` - Remove a model
    - [ ] `POST /api/v1/ai-engine/models/{name}/test` - Test model with sample query
    - [ ] `GET /api/v1/ai-engine/health` - AI system health status

#### Ollama Connection Configuration

- [ ] **Connection Settings Section**
  - [ ] **Ollama URL Input**
    - [ ] URL field with validation (http:// or https://)
    - [ ] Default: `http://localhost:11434`
    - [ ] Help text: "Your Ollama server endpoint"
    - [ ] Examples button: "Local (localhost:11434)", "Remote (http://ai-server:11434)", "Docker (http://ollama:11434)"
  - [ ] **Authentication** (if Ollama is secured)
    - [ ] Toggle: "Enable Authentication"
    - [ ] Bearer token input (masked)
    - [ ] Or: API Key input
  - [ ] **Connection Parameters**
    - [ ] Timeout slider: 10s - 300s (default: 60s)
    - [ ] Retry attempts: 1-5 (default: 3)
    - [ ] Connection pool size: 5-50 (default: 10)
  - [ ] **Test Connection Button**
    - [ ] Shows loading spinner while testing
    - [ ] Success: "✓ Connected to Ollama v0.1.32" + shows available models count
    - [ ] Error: Detailed error message (connection refused, auth failed, timeout)
    - [ ] Re-test button

#### Model Management Section

- [ ] **Available Models List** (After successful connection test)
  - [ ] **Display as cards/grid:**
    - [ ] Model name (e.g., "llama3.3:70b")
    - [ ] Model size (e.g., "70B parameters, 40GB")
    - [ ] Status badge: "Installed ✓" / "Not Installed" / "Update Available"
    - [ ] Action buttons:
      - [ ] "Install/Pull" (if not installed)
      - [ ] "Use for Chat" (sets as chat model)
      - [ ] "Use for Code" (sets as code model)
      - [ ] "Use for Embeddings" (sets as embed model)
      - [ ] "Remove" (if installed, with confirmation)
  - [ ] **Model Categories/Tabs:**
    - [ ] "All Models"
    - [ ] "Chat Models" (llama, mistral, etc.)
    - [ ] "Code Models" (codellama, deepseek-coder, etc.)
    - [ ] "Embedding Models" (nomic-embed-text, etc.)
    - [ ] "Installed" (only show what's on this Ollama instance)
  - [ ] **Model Search/Filter:**
    - [ ] Search by name
    - [ ] Filter by: size (< 10B, 10-30B, 30B+), type (chat/code/embed)
    - [ ] Sort by: name, size, recently used

- [ ] **Model Assignment Section**
  - [ ] **Purpose-based Model Selection:**
    - [ ] **Chat/General Queries:** Dropdown of available chat models
      - [ ] Current: `llama3.3:70b` 
      - [ ] Description: "For general conversation and infrastructure queries"
    - [ ] **Code Analysis:** Dropdown of code models
      - [ ] Current: `codellama:34b`
      - [ ] Description: "For analyzing code, YAML manifests, scripts"
    - [ ] **Intent Classification:** Dropdown (usually smaller/faster model)
      - [ ] Current: `llama3.3:8b` or similar
      - [ ] Description: "For routing queries to correct agent (fast classification)"
    - [ ] **Embeddings:** Dropdown of embedding models
      - [ ] Current: `nomic-embed-text`
      - [ ] Description: "For vector search and RAG"
    - [ ] **RAG Generation:** Dropdown (can be same as chat or different)
      - [ ] Current: `llama3.3:70b`
      - [ ] Description: "For generating answers from retrieved context"
  - [ ] **Test Model Buttons** (next to each dropdown)
    - [ ] Opens modal with sample query
    - [ ] Shows response time, token count
    - [ ] User can edit prompt and re-test

#### Model Parameters Configuration

- [ ] **Per-Model Parameter Tuning** (Expandable sections)
  - [ ] **Common Parameters:**
    - [ ] Temperature: Slider 0.0 - 2.0 (default: 0.7)
      - [ ] Help: "0.1 = deterministic, 1.0 = creative, 2.0 = very random"
      - [ ] Presets: "Precise (0.1)", "Balanced (0.7)", "Creative (1.2)"
    - [ ] Top P: Slider 0.0 - 1.0 (default: 0.9)
    - [ ] Top K: Number input 1-100 (default: 40)
    - [ ] Max Tokens: Number input 256-8192 (default: 2048)
    - [ ] Context Window: Number input 2048-128000 (default: 8192)
  - [ ] **Advanced Parameters** (Collapsible)
    - [ ] Repeat Penalty: 1.0 - 2.0
    - [ ] Frequency Penalty: -2.0 - 2.0
    - [ ] Presence Penalty: -2.0 - 2.0
    - [ ] Stop Sequences: Comma-separated strings
    - [ ] Seed: Random or fixed for reproducibility
  - [ ] **Save as Preset** button
    - [ ] Name: "My Balanced Settings"
    - [ ] Can be applied to other models

#### Intent Classification Configuration

- [ ] **Query Intent Routing Settings**
  - [ ] **Intent Types & Confidence Thresholds:**
    - [ ] Read Query: Threshold 0.85 (auto-execute if confident)
    - [ ] Action Query: Threshold 0.90 (require approval)
    - [ ] Analysis Query: Threshold 0.80
    - [ ] Planning Query: Threshold 0.85
  - [ ] **Fallback Behavior:**
    - [ ] When uncertain: "Ask user for clarification" vs "Default to read query"
  - [ ] **Test Intent Classifier**
    - [ ] Input field: "scale web deployment to 5 replicas"
    - [ ] Shows: Detected intent (ACTION), confidence (0.94), routing decision

#### RAG (Retrieval-Augmented Generation) Configuration

- [ ] **RAG Settings Section**
  - [ ] **Retrieval Parameters:**
    - [ ] Top K Results: Slider 3-20 (default: 5)
    - [ ] Similarity Threshold: Slider 0.5 - 0.95 (default: 0.7)
    - [ ] Max Context Length: Characters to include from retrieved docs
  - [ ] **Indexing Settings:**
    - [ ] Auto-index interval: 5min, 15min, 30min, 1hour, manual
    - [ ] Chunk size for documents: 500-2000 characters
    - [ ] Chunk overlap: 0-500 characters
  - [ ] **Test RAG Button**
    - [ ] Input: "How do I restart a pod?"
    - [ ] Shows: Retrieved documents + generated answer
    - [ ] Displays: Retrieval time, generation time, sources used

#### System Prompts & Templates

- [ ] **Custom System Prompts** (Text areas with variables)
  - [ ] **Chat System Prompt:**
    ```
    You are an infrastructure operations assistant. 
    Current cluster: {cluster_name}
    User role: {user_role}
    Help the user with: {query}
    ```
  - [ ] **Action Confirmation Prompt:**
    ```
    The user wants to execute: {action_description}
    This will affect: {affected_resources}
    Risk level: {risk_level}
    Approve? Reply YES or NO and explain why.
    ```
  - [ ] **Variables:** Show available placeholders {cluster_name}, {user_name}, {timestamp}
  - [ ] **Reset to Default** button for each prompt
  - [ ] **Version history** (save previous versions)

#### Performance & Caching

- [ ] **Performance Tuning**
  - [ ] **Response Caching:**
    - [ ] Enable caching toggle
    - [ ] Cache TTL: 1min, 5min, 15min, 1hour
    - [ ] Cache size limit: 100MB - 10GB
    - [ ] Clear cache button
  - [ ] **Rate Limiting:**
    - [ ] Max requests per user per minute: 10-1000
    - [ ] Max concurrent requests: 5-50
    - [ ] Queue overflow behavior: Reject vs Wait
  - [ ] **Streaming:**
    - [ ] Enable streaming responses toggle
    - [ ] Chunk size: 10-100 tokens
    - [ ] Timeout between chunks: 1s - 30s
  - [ ] **Performance Metrics Display:**
    - [ ] Average response time (last 24h)
    - [ ] Token usage (last 24h)
    - [ ] Cache hit rate
    - [ ] Error rate

#### Feature Toggles & Debug

- [ ] **AI Feature Toggles**
  - [ ] Enable/Disable features:
    - [ ] Intent Classification
    - [ ] RAG (Retrieval-Augmented Generation)
    - [ ] Streaming Responses
    - [ ] Multi-step Task Execution
    - [ ] Code Analysis
    - [ ] Automated Actions (self-healing)
  - [ ] **Debug Mode:**
    - [ ] Show raw AI responses in chat (toggle)
    - [ ] Show thinking/reasoning steps
    - [ ] Log level: INFO, DEBUG, TRACE
    - [ ] Export debug logs button

#### Frontend UI Components

- [ ] **AI Engine Settings Page Layout** (`/settings/ai-engine`)
  - [ ] **Tab Navigation:**
    - [ ] "Connection" - Ollama URL & testing
    - [ ] "Models" - Model management & assignment
    - [ ] "Parameters" - Temperature, top_p, etc.
    - [ ] "RAG" - Retrieval settings
    - [ ] "Prompts" - System prompt templates
    - [ ] "Performance" - Caching, rate limits
    - [ ] "Advanced" - Debug, feature toggles
  - [ ] **Sticky Action Bar:**
    - [ ] "Test Configuration" button (tests all models)
    - [ ] "Save Changes" button (disabled until changes made)
    - [ ] "Reset to Defaults" button
    - [ ] "Export Config" / "Import Config" (JSON)
  - [ ] **Validation & Warnings:**
    - [ ] Warning if no chat model selected
    - [ ] Warning if model size > available memory
    - [ ] Success toast on save

#### Integration with AI Router

- [ ] **Update AI Router Service**
  - [ ] **Dynamic Configuration Loading:**
    - [ ] Load config from database on startup
    - [ ] Watch for config changes (reload without restart)
    - [ ] Cache config in Redis for performance
  - [ ] **Per-Request Overrides:**
    - [ ] Accept override headers: `X-Model-Name`, `X-Temperature`
    - [ ] Allow users to override in chat: "Use llama3.3:8b for this query"
  - [ ] **Model Fallback Chain:**
    - [ ] If requested model unavailable → Try fallback model
    - [ ] Configurable fallback order
    - [ ] Alert admin if primary model down

#### Usage & Analytics

- [ ] **Model Usage Dashboard** (In AI Engine section)
  - [ ] **Usage Statistics:**
    - [ ] Queries per model (last 24h, 7d, 30d)
    - [ ] Average response time per model
    - [ ] Token consumption per model
    - [ ] Error rate per model
  - [ ] **Cost Estimation:**
    - [ ] Estimated compute cost (if running on cloud)
    - [ ] Compare costs between models
  - [ ] **Performance Trends:**
    - [ ] Response time over time (graph)
    - [ ] Token usage trends
    - [ ] Cache hit/miss ratio

### 0.12 Multi-Step Workflow Engine (Phase 0 Extension - HIGHEST IMPACT FEATURE)

**THE PROBLEM ENGINEERS FACE:**
```
Deploying a microservice manually takes 30-60 minutes:
1. Create namespace
2. Set up ConfigMap
3. Create Secrets
4. Deploy database
5. Wait for DB ready
6. Run migrations
7. Deploy app
8. Create Service
9. Create Ingress
10. Verify everything

Problems: Forget steps, typos, deploy app before DB ready,
          no rollback, no audit trail, can't pause
```

**THE SOLUTION:**
```
User: "Deploy payment-service with postgres database"
        ↓
AI: "I'll create an 8-step deployment plan:"

┌─────────────────────────────────────────┐
│ WORKFLOW: Deploy payment-service        │
│ Status: Running (Step 4 of 8)           │
│ Progress: ████████████░░░░ 50%        │
│ Time: 3m 12s elapsed                   │
├─────────────────────────────────────────┤
│ ✓ Step 1: Create namespace             │
│ ✓ Step 2: Create ConfigMap             │
│ ✓ Step 3: Create Secret               │
│ → Step 4: Deploy PostgreSQL [RUNNING] │
│   └─ Waiting for pod ready...          │
│ ⏸ Step 5: Run migrations [PENDING]     │
│ ⏸ Step 6: Deploy application           │
│ ⏸ Step 7: Create Service/Ingress       │
│ ⏸ Step 8: Verify deployment            │
├─────────────────────────────────────────┤
│ [Pause] [Cancel] [View Logs] [Dry-Run] │
└─────────────────────────────────────────┘

✓ Completed in 4m 30s
All 8 steps successful!
[View Resources] [Rollback if needed] [Save as Template]
```

#### Why This Is The Most Important Feature After Phase 0

- **10x Productivity**: What takes 1 hour manually → 4 minutes automated
- **Zero Mistakes**: AI never forgets a step or makes typos
- **Safety**: Each step dry-run + approval before executing
- **Transparency**: Full visibility into what happened and when
- **Reproducible**: Save as template, run again with one click
- **Team Enablement**: Junior engineers can deploy safely

#### Manual Engineering Workflows (Current Pain Points)

**Scenario 1: Database Migration**
```bash
# Engineer does this manually (error-prone):
1. kubectl exec -it db-pod -- pg_dump > backup.sql  # Forgot backup!
2. kubectl apply -f migration-job.yaml               # Wrong order
3. kubectl wait --for=condition=complete job/migration  # No wait
4. kubectl get pods                                  # Manual check
5. kubectl logs migration-job                        # Check logs

# Problems: No rollback plan, forgot to notify team,
#           no record of what was done, can't resume if interrupted
```

**Scenario 2: Blue-Green Deployment**
```bash
# Complex 15-step process:
1. Deploy green version (20% traffic)
2. Run smoke tests
3. Monitor metrics for 5 minutes
4. If healthy, shift 50% traffic
5. Monitor for 10 minutes
6. If healthy, shift 100% traffic
7. Wait 30 minutes
8. If all good, delete blue
9. If issues, rollback to blue

# Problems: Can't pause at step 4, no automatic rollback,
#           hard to coordinate across team
```

**Scenario 3: Disaster Recovery**
```bash
# Critical situation - high stress:
1. Scale down failing service
2. Restore from last backup
3. Verify backup integrity
4. Update DNS to standby
5. Verify failover success
6. Notify stakeholders
7. Post-incident review

# Problems: Forget steps under pressure, no coordination,
#           audit trail incomplete
```

#### Workflow Engine Architecture

- [ ] **Create Workflow Service** (Port 8012 - NEW SERVICE)
  - [ ] **Database Schema:**
    - [ ] `workflow_definitions` - Reusable templates
      - id, name, description, version, steps (JSON), tags, created_by
    - [ ] `workflow_instances` - Running workflows
      - id, definition_id, status, started_at, completed_at, created_by, context (JSON)
    - [ ] `workflow_steps` - Individual step execution
      - id, instance_id, step_number, step_type, name, status, started_at, completed_at
      - input_data (JSON), output_data (JSON), error_message, retry_count
    - [ ] `workflow_logs` - Detailed execution logs
      - id, step_id, timestamp, level, message, metadata (JSON)
    - [ ] `workflow_approvals` - Approval gates
      - id, step_id, requested_by, requested_at, approved_by, approved_at, status, comments
  - [ ] **API Endpoints:**
    - [ ] `POST /api/v1/workflows/definitions` - Create workflow template
    - [ ] `GET /api/v1/workflows/definitions` - List templates
    - [ ] `POST /api/v1/workflows/instances` - Start workflow
    - [ ] `GET /api/v1/workflows/instances/{id}` - Get workflow status
    - [ ] `POST /api/v1/workflows/instances/{id}/pause` - Pause workflow
    - [ ] `POST /api/v1/workflows/instances/{id}/resume` - Resume workflow
    - [ ] `POST /api/v1/workflows/instances/{id}/cancel` - Cancel workflow
    - [ ] `POST /api/v1/workflows/instances/{id}/retry` - Retry failed step
    - [ ] `POST /api/v1/workflows/instances/{id}/rollback` - Rollback all steps
    - [ ] `GET /api/v1/workflows/instances/{id}/logs` - Get execution logs
    - [ ] `POST /api/v1/workflows/steps/{id}/approve` - Approve step
    - [ ] `POST /api/v1/workflows/steps/{id}/reject` - Reject step

#### Step Types & Execution

- [ ] **Core Step Types:**
  - [ ] **ActionStep** - Execute single infrastructure action
    ```yaml
    type: action
    name: "Create namespace"
    action:
      type: "k8s.create_namespace"
      params:
        name: "{{workflow.namespace}}"
    timeout: 30s
    retry:
      max_attempts: 3
      backoff: exponential
    ```
  - [ ] **ConditionStep** - If/else logic
    ```yaml
    type: condition
    name: "Check if namespace exists"
    condition:
      type: "k8s.resource_exists"
      params:
        kind: "namespace"
        name: "{{workflow.namespace}}"
    on_true:  # Skip to step 3
      goto: 3
    on_false:  # Continue to next step
      goto: next
    ```
  - [ ] **WaitStep** - Wait for time or condition
    ```yaml
    type: wait
    name: "Wait for database ready"
    wait:
      type: "condition"  # or "duration"
      condition:
        type: "k8s.pod_ready"
        params:
          selector: "app=postgres"
          namespace: "{{workflow.namespace}}"
        timeout: 5m
        check_interval: 10s
    ```
  - [ ] **ApprovalStep** - Human approval gate
    ```yaml
    type: approval
    name: "Approve production deployment"
    approval:
      required_approvers: 1
      approver_roles: ["admin", "sre"]
      timeout: 24h
      reminder_interval: 4h
      on_timeout: "cancel"  # or "auto_approve", "escalate"
    ```
  - [ ] **ParallelStep** - Execute multiple steps concurrently
    ```yaml
    type: parallel
    name: "Deploy multiple services"
    parallel:
      steps:
        - name: "Deploy API"
          type: action
          action:
            type: "k8s.apply"
            params:
              manifest: "{{templates.api_deployment}}"
        - name: "Deploy Worker"
          type: action
          action:
            type: "k8s.apply"
            params:
              manifest: "{{templates.worker_deployment}}"
        - name: "Deploy Cache"
          type: action
          action:
            type: "k8s.apply"
            params:
              manifest: "{{templates.redis_deployment}}"
      completion_strategy: "all"  # or "any", "n_of_m"
    ```
  - [ ] **NotificationStep** - Send notification
    ```yaml
    type: notification
    name: "Notify team"
    notification:
      channels: ["slack", "email"]
      slack:
        channel: "#deployments"
        message: "Deployment {{workflow.name}} completed successfully!"
      email:
        to: ["{{workflow.created_by}}"]
        subject: "Deployment Complete"
    ```
  - [ ] **SubWorkflowStep** - Call another workflow
    ```yaml
    type: subworkflow
    name: "Run database setup"
    subworkflow:
      definition_id: "postgres-setup-v1"
      inputs:
        namespace: "{{workflow.namespace}}"
        db_name: "{{workflow.db_name}}"
      wait_for_completion: true
    ```

#### State Machine & Lifecycle

- [ ] **Workflow States:**
  ```
  CREATED → VALIDATING ─┐
           ↓            │
  PENDING_APPROVAL ←───┘ (if requires pre-approval)
           ↓
  RUNNING ─┬──▶ PAUSED (user pause)
      │    │      ↓
      │    └──▶ RESUMED
      │
      ├─▶ STEP_RUNNING → STEP_COMPLETED ─┐
      │                                    │
      ├─▶ STEP_FAILED ─┬──▶ RETRYING ──────┤
      │                │                   │
      │                └──▶ FAILED ───────┤
      │                                    │
      └─▶ CANCELLED (user cancel) ────────┤
                                          ↓
                                        COMPLETED
  ```
  - [ ] Track state transitions with timestamps
  - [ ] Allow manual state override (admin only)
  - [ ] State persistence across service restarts

- [ ] **Step Execution Lifecycle:**
  ```
  1. PENDING - Waiting for dependencies
  2. VALIDATING - Validate inputs/parameters
  3. DRY_RUN - Simulate execution (optional)
  4. APPROVAL_WAITING - Waiting for human approval
  5. RUNNING - Executing action
  6. VERIFYING - Verify result
  7. COMPLETED / FAILED
  ```

#### Workflow Templates & Library

- [ ] **Built-in Workflow Templates:**
  - [ ] **Deploy Microservice with Database**
    - 8 steps: namespace → configmap → secret → database → wait → migrations → app → ingress
  - [ ] **Blue-Green Deployment**
    - 12 steps: deploy green (20%) → smoke test → monitor → shift (50%) → monitor → shift (100%) → cleanup
  - [ ] **Database Migration**
    - 6 steps: backup → create migration job → wait → verify → cleanup backup
  - [ ] **Disaster Recovery**
    - 10 steps: stop services → restore backup → verify → restart → verify → notify
  - [ ] **Scale Up Infrastructure**
    - 5 steps: add nodes → verify capacity → scale deployment → verify → notify
  - [ ] **Security Patch Deployment**
    - 7 steps: scan → approve → cordon nodes → drain → patch → verify → uncordon

- [ ] **Template Customization:**
  - [ ] Variable substitution: `{{workflow.namespace}}`, `{{steps.step1.output.pod_name}}`
  - [ ] Conditional steps based on inputs
  - [ ] User-defined templates via UI or YAML
  - [ ] Template versioning
  - [ ] Template sharing (team templates, organization templates)

#### Safety & Rollback

- [ ] **Dry-Run Mode**
  - [ ] Simulate entire workflow without executing
  - [ ] Show what would be created/modified/deleted
  - [ ] Display estimated time and resource impact
  - [ ] Require confirmation before live execution
  - [ ] Can dry-run individual steps

- [ ] **Automatic Rollback**
  - [ ] Track all changes made by workflow
  - [ ] On failure: Automatic or manual rollback
  - [ ] Compensation steps for each action:
    ```yaml
    - name: "Create deployment"
      action:
        type: "k8s.create_deployment"
      compensation:
        type: "k8s.delete_deployment"  # Run on rollback
        params:
          name: "{{output.name}}"
    ```
  - [ ] Partial rollback: Rollback only failed step
  - [ ] Full rollback: Undo all steps in reverse order
  - [ ] Rollback approval for critical workflows

- [ ] **Safety Guards**
  - [ ] Resource quotas: Prevent creating too many resources
  - [ ] Budget limits: Stop if cost exceeds threshold
  - [ ] Time limits: Cancel if workflow runs too long
  - [ ] Concurrent workflow limits: Prevent resource exhaustion
  - [ ] Protected resources: Cannot delete critical infrastructure
  - [ ] Change windows: Only run during approved times

#### AI-Generated Workflows

- [ ] **Natural Language to Workflow**
  ```
  User: "Deploy a Python API with PostgreSQL, Redis cache, and a background worker"
          ↓
  AI analyzes request and creates workflow:
  
  Generated Workflow: "python-api-stack-v1"
  Steps:
    1. Create namespace: "python-api"
    2. Create ConfigMap with DB connection
    3. Create Secret with credentials
    4. Deploy PostgreSQL StatefulSet (1 replica, 10GB PVC)
    5. Wait for PostgreSQL ready (timeout: 5m)
    6. Deploy Redis cache (1 replica, 1GB memory)
    7. Wait for Redis ready
    8. Deploy API Deployment (2 replicas, port 8000)
    9. Deploy Worker Deployment (1 replica)
    10. Create Service for API (ClusterIP)
    11. Create Ingress for external access
    12. Verify all pods running
    13. Send success notification
  
  Estimated time: 6 minutes
  [Review] [Save & Run] [Edit] [Cancel]
  ```

- [ ] **AI Workflow Optimization**
  - [ ] Suggest parallel execution where safe
  - [ ] Recommend approval gates for risky steps
  - [ ] Detect missing dependencies
  - [ ] Suggest retries and timeouts based on history
  - [ ] Optimize step order for speed

#### IMPORTANT CLARIFICATION: 3 Modes of Operation

**The workflow engine supports THREE approaches - from fully manual to fully AI-driven:**

**Mode 1: Template-Based (Pre-defined Workflows)**
```
Use Case: Common, repeatable operations
How it works:
1. System has built-in templates (Blue-Green Deploy, Database Migration)
2. User selects template from gallery
3. User fills in parameters (service name, namespace, etc.)
4. System executes the fixed sequence of steps

Example:
User selects "Deploy Microservice with Database" template
├─ Template has FIXED 8 steps (hardcoded sequence)
├─ User inputs: service_name="payment-api", namespace="production"
└─ System executes the same 8 steps every time

Pros: Predictable, tested, fast to execute
Cons: Inflexible for unique scenarios
```

**Mode 2: AI-Generated from Natural Language (Recommended Default)**
```
Use Case: Custom deployments described in plain English
How it works:
1. User describes what they want in natural language
2. AI Planning Agent analyzes the request
3. AI generates a custom workflow on-the-fly
4. User reviews and approves the generated plan
5. System executes the AI-generated steps

Example:
User: "Deploy a Node.js API with MongoDB, Redis cache, and S3 bucket 
        for file uploads. Use 3 replicas and connect to existing 
        monitoring stack."
        ↓
AI analyzes:
├─ Detects: Need Node.js runtime
├─ Detects: Need MongoDB (new or existing?)
├─ Detects: Need Redis (cache layer)
├─ Detects: Need S3 bucket (file storage)
├─ Detects: Need 3 replicas (scalability)
├─ Detects: Need monitoring integration
└─ Infers: Should create ConfigMap for env vars

AI generates custom workflow (NOT from template):
├─ Step 1: Create namespace
├─ Step 2: Create ConfigMap (MongoDB URI, Redis URL, S3 bucket)
├─ Step 3: Create Secret (API keys, DB credentials)
├─ Step 4: Create S3 bucket and IAM role
├─ Step 5: Deploy MongoDB StatefulSet
├─ Step 6: Deploy Redis Deployment
├─ Step 7: Wait for databases ready
├─ Step 8: Deploy Node.js API (3 replicas)
├─ Step 9: Create Service
├─ Step 10: Create Ingress
├─ Step 11: Connect to monitoring (Prometheus ServiceMonitor)
└─ Step 12: Verify all components

AI: "I've created a 12-step deployment plan. This is a custom workflow 
     generated just for your request. Estimated time: 7 minutes."
     [Review Steps] [Edit Plan] [Execute Now] [Save as Template]

User reviews the generated steps, can edit any step, then executes.

Pros: Completely custom, adapts to unique requirements, no templates needed
Cons: Takes 10-30 seconds to generate plan, requires review
```

**Mode 3: Fully AI-Driven Real-Time Planning (Advanced)**
```
Use Case: Complex, novel, or emergency scenarios
How it works:
1. User gives high-level goal
2. AI reasons about current infrastructure state (queries live data)
3. AI plans steps dynamically in real-time
4. AI executes step-by-step, adapting if conditions change
5. AI can add/remove steps based on real-time feedback

Example:
User: "My production database is down. Fix it immediately."
        ↓
AI queries current state:
├─ Check: Which cluster? "production-us-east"
├─ Check: Which database? "postgres-primary"
├─ Check: Current status? "Pod CrashLoopBackOff"
├─ Check: Last backup? "2 hours ago"
├─ Check: Replicas available? "Yes, 2 replicas running"
└─ Check: Failover strategy? "Promote replica"

AI creates EMERGENCY RECOVERY plan dynamically:
├─ Step 1: [IMMEDIATE] Route traffic to replica (update DNS)
├─ Step 2: [IMMEDIATE] Stop writes to prevent data loss
├─ Step 3: [URGENT] Scale replica to handle full load
├─ Step 4: [URGENT] Notify team on Slack
├─ Step 5: [5min] Diagnose primary failure (check logs)
├─ Step 6: [CONDITIONAL] If disk full → clear logs
├─ Step 7: [CONDITIONAL] If OOM → increase memory limit
├─ Step 8: [CONDITIONAL] If corrupted → restore from backup
├─ Step 9: [10min] Restart primary with fixes
├─ Step 10: [CONDITIONAL] If primary healthy → rejoin cluster
└─ Step 11: [ONGOING] Monitor for 30 minutes

AI shows: "Emergency recovery in progress. I'm adapting the plan based on
          real-time conditions. Current step: 3 of 11."
          [View Live Status] [Pause] [Cancel] [Escalate to Human]

AI adapts dynamically:
- If Step 5 reveals disk is NOT full → Skip Step 6
- If Step 7 fixes the issue → Jump to Step 9
- If failover fails → Add emergency step: "Call DBA team"

Pros: Handles completely novel situations, adapts in real-time
Cons: Requires sophisticated AI reasoning, needs human oversight
```

**Implementation Priority:**
- **Week 8**: Build Mode 1 (Template-based) - Foundation
- **Week 9**: Build Mode 2 (AI-Generated) - Main value proposition
- **Week 10+**: Build Mode 3 (Fully AI-Driven) - Advanced feature

**Key Design Principle:**
```
Start with Mode 2 (AI-Generated) as the PRIMARY interface:
- User describes what they want
- AI generates custom workflow
- User reviews and approves
- System executes

Mode 1 (Templates) available for:
- Common operations users do frequently
- When speed matters (skip generation time)
- Compliance/audit requirements (pre-approved templates)

Mode 3 (Fully AI-Driven) for:
- Complex troubleshooting
- Emergency response
- Novel situations not covered by templates
```

#### Frontend UI Components

- [ ] **Workflow Dashboard** (`/workflows`)
  - [ ] **Running Workflows Widget:**
    - Live status of all active workflows
    - Progress bars, elapsed time, current step
    - Quick actions: Pause, Cancel, View
  - [ ] **Recent Workflows List:**
    - Completed, failed, cancelled workflows
    - Duration, success rate
    - Filter by: status, type, date range
  - [ ] **Templates Gallery:**
    - Browse built-in and custom templates
    - Search by name, tags
    - Preview template before using

- [ ] **Workflow Execution View** (`/workflows/{id}`)
  - [ ] **Visual Step Timeline:**
    ```
    Step 1  Step 2  Step 3  Step 4  Step 5
      ✓       ✓       →       ○       ○
    [Details for Step 3 - Running]
    ┌─────────────────────────────────────┐
    │ Deploy PostgreSQL                   │
    │ Status: RUNNING                     │
    │ Started: 2m 34s ago                 │
    │                                     │
    │ Progress:                           │
    │ Creating StatefulSet... ✓          │
    │ Waiting for pod ready... ▶ 2/1     │
    │ Initializing database... ○          │
    │                                     │
    │ Logs:                               │
    │ [2024-01-15 10:23:12] Creating...  │
    │ [2024-01-15 10:23:15] Created      │
    │ [2024-01-15 10:23:16] Waiting...   │
    │                                     │
    │ [View Pod Logs] [View Manifest]    │
    └─────────────────────────────────────┘
    ```
  - [ ] **Step Controls:**
    - Pause/Resume workflow
    - Retry failed step
    - Skip step (with confirmation)
    - Approve/Reject approval gates
  - [ ] **Execution Log Stream:**
    - Real-time log updates
    - Filter by step, level
    - Download logs
  - [ ] **Resource Impact View:**
    - What resources were created/modified
    - Visual diff: Before vs After
    - Cost impact

- [ ] **Workflow Builder** (`/workflows/builder`)
  - [ ] **Visual Drag-and-Drop Builder:**
    - Canvas with grid
    - Step library sidebar
    - Drag steps onto canvas
    - Connect steps with arrows (dependencies)
  - [ ] **Step Configuration Panel:**
    - Form fields for each step type
    - Variable autocomplete ({{workflow.XXX}})
    - Test button for individual steps
  - [ ] **YAML Editor Mode:**
    - Toggle between visual and YAML
    - Real-time sync between modes
    - Syntax validation
    - Template preview
  - [ ] **Workflow Validation:**
    - Check for circular dependencies
    - Validate all parameters
    - Detect missing required fields
    - Show warnings for potential issues

- [ ] **Workflow Templates UI** (`/workflows/templates`)
  - [ ] **Template Cards:**
    - Icon, name, description
    - Tags (deployment, migration, etc.)
    - Estimated duration
    - Success rate from history
    - "Use Template" button
  - [ ] **Template Details:**
    - Step-by-step preview
    - Required inputs
    - Safety warnings
    - Recent executions
  - [ ] **Create Custom Template:**
    - Save current workflow as template
    - Add description and tags
    - Share with team/organization

#### Integration with Existing Features

- [ ] **Chat Integration**
  - [ ] User can trigger workflows from chat
  - [ ] Show workflow status in chat
  - [ ] Approve workflows from chat
  - [ ] "Run workflow 'blue-green-deploy' for service 'api'"

- [ ] **Approval System Integration**
  - [ ] Approval steps use existing approval workflow
  - [ ] Show in `/approvals` dashboard
  - [ ] Slack/email notifications for approvals
  - [ ] Mobile approval support

- [ ] **Audit & Compliance**
  - [ ] All workflow executions logged
  - [ ] Who started it, who approved, when, what changed
  - [ ] Export workflow history
  - [ ] Compliance reports: "All production changes in January"

- [ ] **Monitoring & Alerts**
  - [ ] Alert if workflow fails
  - [ ] Alert if workflow stuck too long
  - [ ] Dashboard: Workflow success rate, avg duration
  - [ ] SRE metrics: MTTR, deployment frequency

#### Success Metrics

After building this feature:
- [ ] **Time to deploy new service:** 1 hour → 5 minutes (12x faster)
- [ ] **Deployment errors:** 15% → 2% (7x fewer)
- [ ] **Failed rollbacks:** 30% → 5% 
- [ ] **Engineer confidence:** "I can deploy safely without senior review"
- [ ] **Team productivity:** Junior engineers deploy independently

#### Implementation Priority

**Phase 0.12 Week 8-9 (Immediate after Phase 0):**
1. Create Workflow Service (Port 8012)
2. Database schema and API endpoints
3. Core step types (action, wait, approval)
4. Sequential workflow execution
5. Basic UI (list, status view)

**Week 10-11:**
6. Parallel execution
7. Condition and subworkflow steps
8. Rollback support
9. Dry-run mode
10. Template library (5 built-in templates)

**Week 12:**
11. Visual workflow builder
12. AI-generated workflows
13. Full chat integration
14. Analytics dashboard

### 0.13 First-Time User Experience & Productivity (Day 0 Onboarding)

**THE MISSING PIECE:** After building all these powerful features, users need to DISCOVER them easily. Without guided onboarding, users feel lost and underutilize the system.

**Current Problem:**
```
New user logs in → Sees empty dashboard → "What do I do?"
                    ↓
User manually explores → Finds chat by accident
                    ↓
User: "How do I scan my network?" → Can't find it
                    ↓
User gives up, goes back to kubectl
```

**The Solution - Progressive Onboarding:**
```
New user logs in → Guided setup wizard → "Let's connect your first cluster"
                    ↓
Step 1: Welcome tour (3 min)
Step 2: Quick setup (connect first K8s cluster)
Step 3: Try first query (guided chat tutorial)
Step 4: Explore features (interactive hotspots)
                    ↓
User: "I know how to use this!" → Becomes power user
```

#### First-Time Setup Wizard ("/welcome")

- [ ] **Progressive Onboarding Flow**
  - [ ] **Step 1: Welcome & Value Prop** (30 seconds)
    - [ ] "Welcome to TalkAI - Your Infrastructure Copilot"
    - [ ] Animated demo: "Here's what you can do..."
      - Scan network automatically
      - Chat with AI about infrastructure  
      - Deploy with guided workflows
      - Get alerts before issues happen
    - [ ] [Start Setup] [Skip for now] buttons
    
  - [ ] **Step 2: Connect First Cluster** (2-5 minutes)
    - [ ] "Let's connect your first Kubernetes cluster"
    - [ ] Smart detection: "We found kubeconfig at ~/.kube/config - use this?"
    - [ ] Visual cluster connection helper
    - [ ] Test connection with immediate feedback
    - [ ] Show discovered resources count: "Found 47 pods, 12 services!"
    - [ ] [Continue] [Connect Another] [Do This Later]
    
  - [ ] **Step 3: Try Your First Query** (3 minutes)
    - [ ] "Let's explore your infrastructure together"
    - [ ] Guided chat tutorial with suggestions:
      - [ ] "Try: 'show me all pods'" → AI shows results
      - [ ] "Try: 'get logs for deployment X'" → AI retrieves logs
      - [ ] "Try: 'scale deployment Y to 3 replicas'" → AI shows approval flow
    - [ ] Interactive: "Click this suggestion or type your own"
    - [ ] Celebrate success: "🎉 You just queried your cluster with AI!"
    
  - [ ] **Step 4: Discover Key Features** (5 minutes)
    - [ ] Interactive product tour with hotspots:
      - [ ] "💡 Pro tip: Use /discovered to see all infrastructure"
      - [ ] "💡 Pro tip: Create workflows for complex deployments"
      - [ ] "💡 Pro tip: Set up Slack alerts for critical issues"
    - [ ] Pulsing indicators on key UI elements
    - [ ] "Click here to try it" call-to-actions
    - [ ] Can skip any step, resume later

#### Empty States & Guidance

- [ ] **Dashboard Empty State** (Before first cluster)
  ```
  ┌─────────────────────────────────────────────┐
  │                                             │
  │    🚀 Welcome to TalkAI!                     │
  │                                             │
  │    You haven't connected any               │
  │    infrastructure yet.                       │
  │                                             │
  │    [Connect First Cluster]                  │
  │    or                                       │
  │    [Scan Network to Discover]               │
  │                                             │
  │    💡 Need help? Watch 2-min tutorial       │
  │                                             │
  └─────────────────────────────────────────────┘
  ```
  - [ ] Illustration/animation showing platform capabilities
  - [ ] Quick-start video (2 minutes)
  - [ ] "Import demo data" option (for exploration)
  
- [ ] **Feature Discovery Empty States**
  - [ ] **Workflows page empty:** "Create your first workflow"
    - [ ] Show 3 popular templates with "Use This" buttons
    - [ ] "What is a workflow?" explainer video
  - [ ] **Approvals page empty:** "No pending approvals"
    - [ ] "When you request actions, they'll appear here"
    - [ ] "Learn about approval workflows" link
  - [ ] **Monitoring page empty:** "Set up your first alert"
    - [ ] Quick alert creation wizard
    - [ ] Pre-configured alert templates

#### Command Palette & Universal Search ("Cmd+K")

- [ ] **Keyboard-First Navigation**
  - [ ] Press `Cmd/Ctrl + K` anywhere to open command palette
  - [ ] Search across ALL features:
    - [ ] Actions: "Scale deployment", "View logs", "Create workflow"
    - [ ] Resources: "Find pod web-app", "Show node worker-1"
    - [ ] Navigation: "Go to workflows", "Open settings"
    - [ ] Help: "How to deploy?", "What is dry-run?"
  - [ ] **Recent & Suggested:**
    - [ ] "You recently: Scaled api-deployment"
    - [ ] "Suggested: View failing pods"
  - [ ] **AI-Powered Commands:**
    - [ ] Type natural language: "deploy my api"
    - [ ] AI suggests: "Create workflow 'deploy-api'?"
    - [ ] One enter to execute

- [ ] **Smart Suggestions**
  - [ ] Context-aware based on current page
  - [ ] Time-aware: "Good morning! View overnight alerts?"
  - [ ] Pattern-aware: "You usually check logs at 9am"
  - [ ] Crisis-aware: "3 pods failing! View details?"

#### Contextual Help System

- [ ] **Inline Help & Tooltips**
  - [ ] Hover over any UI element → Shows tooltip
  - [ ] "What is this?" buttons on complex sections
  - [ ] Quick videos (30 seconds) explaining features
  - [ ] "Learn more" links to documentation

- [ ] **AI Assistant (Clippy-style but Smart)**
  - [ ] Friendly AI avatar in corner
  - [ ] Proactive suggestions: "Looks like you're deploying. Need help?"
  - [ ] "I noticed you run this command often. Create a workflow?"
  - [ ] Can be minimized or disabled

- [ ] **Help Center Integration**
  - [ ] Searchable knowledge base
  - [ ] Video tutorials library
  - [ ] Interactive guides (step-by-step walkthroughs)
  - [ ] "Was this helpful?" feedback

#### User Progress & Gamification

- [ ] **Progress Tracking**
  - [ ] "Setup Progress: 60% Complete"
    - [ ] ✓ Connected first cluster
    - [ ] ✓ Ran first query
    - [ ] ⏸ Run first workflow (next!)
    - [ ] ⏸ Set up monitoring
    - [ ] ⏸ Invite team member
  - [ ] Visual progress bar in sidebar
  
- [ ] **Achievements & Milestones** (Optional)
  - [ ] "First Query" - Asked AI about infrastructure
  - [ ] "Automation Champion" - Created first workflow
  - [ ] "Security Guru" - Fixed first vulnerability
  - [ ] "Team Player" - Shared first runbook
  - [ ] Celebrations with confetti animations!

#### Dashboard & Overview (Landing Page)

- [ ] **Personalized Dashboard** ("/dashboard")
  - [ ] **Morning Briefing Widget:**
    ```
    "Good morning, Alex! ☀️
    
    Overnight:
    • 47 pods scanned, 2 new ones detected
    • 1 alert: High CPU on api-deployment
    • 0 failed deployments
    
    Today's Priority:
    • Review 3 pending approvals
    • Certificate expires in 5 days
    "
    ```
  - [ ] **Quick Actions Grid:**
    - [ ] "Run Network Scan"
    - [ ] "Deploy New Service"
    - [ ] "View Failing Pods"
    - [ ] "Check Cost Report"
    - [ ] Customizable by user
  
  - [ ] **Recent Activity Feed:**
    - [ ] "You scaled web-deployment (2 hours ago)"
    - [ ] "AI auto-healed 1 pod (4 hours ago)"
    - [ ] "Mike approved production change (5 hours ago)"
    
  - [ ] **Health Overview:**
    - [ ] Mini status of all clusters
    - [ ] Traffic light colors (green/yellow/red)
    - [ ] "All systems operational" or "2 issues need attention"

#### Resource Relationship Visualization

- [ ] **Interactive Topology Map**
  - [ ] Visual graph: Clusters → Nodes → Pods → Services
  - [ ] Click any node to see details
  - [ ] Zoom in/out, drag to explore
  - [ ] Color-coded by health status
  - [ ] Filter by: namespace, type, status
  - [ ] "Show connections" - See which services talk to which

- [ ] **Impact Analysis Visualizer**
  - [ ] Hover over resource → Highlight dependents
  - [ ] "If I restart this pod, what breaks?"
  - [ ] Visual blast radius estimation
  - [ ] Critical path highlighting

#### Search & Discovery

- [ ] **Universal Search** ("/search")
  - [ ] Search across:
    - [ ] Infrastructure resources (pods, nodes, services)
    - [ ] Configuration (ConfigMaps, Secrets - redacted)
    - [ ] Workflows and runbooks
    - [ ] Chat history
    - [ ] Documentation
    - [ ] Team members
  - [ ] Filters: type, cluster, namespace, date range
  - [ ] Saved searches
  - [ ] Recent searches

#### Mobile & Responsive

- [ ] **Mobile-First Design**
  - [ ] All features work on mobile/tablet
  - [ ] Touch-optimized workflows
  - [ ] Mobile notifications for approvals
  - [ ] Quick actions from mobile home screen

#### Implementation Priority

**Phase 0.13 Week 10-11:**
1. Welcome wizard framework
2. Empty states for all pages
3. Command palette (Cmd+K)
4. Dashboard overview
5. Progress tracking

**Week 12-13:**
6. Contextual help system
7. Resource topology visualization
8. Universal search
9. Mobile responsiveness
10. User analytics (track completion rates)

#### Success Metrics

After implementing this:
- [ ] **Time to first query:** < 5 minutes (was: 30+ minutes)
- [ ] **User activation rate:** 80% complete setup (was: 40%)
- [ ] **Feature discovery:** Users find 5+ features in first week
- [ ] **Support tickets:** 50% reduction (self-service help)
- [ ] **User confidence:** "I know how to use this" score > 4/5

## Phase 1: Core Infrastructure Integration (Critical Path)

### 1.1 Kubernetes API Integration
- [ ] **Add kubernetes Python client dependency**
  - [ ] Add `kubernetes>=28.1.0` to all service requirements.txt files
  - [ ] Add `kubernetes-asyncio` for async operations
  - [ ] Update Docker images with kubectl binary

- [ ] **Create shared K8s client library** (`services/shared/k8s_client.py`)
  - [ ] Implement `K8sClient` class with kubeconfig loading
  - [ ] Support multiple cluster contexts
  - [ ] Implement connection pooling and caching
  - [ ] Add health checks and reconnection logic
  - [ ] Create async context manager for safe resource cleanup

- [ ] **Update Ingestion Service** (Port 8004)
  - [ ] Replace mock K8s client with real implementation
  - [ ] Implement resource watchers (pods, deployments, services)
  - [ ] Add resource change event publishing to NATS
  - [ ] Create indexing pipeline (K8s → Qdrant embeddings)
  - [ ] Add resource caching with Redis
  - [ ] Implement incremental updates (not full sync every time)

- [ ] **Update Agent Service Tools** (Port 8006)
  - [ ] Implement `k8s.read_tools` (list_pods, get_pod, get_logs, describe_resource)
  - [ ] Implement `k8s.write_tools` (scale_deployment, restart_pod, delete_resource)
  - [ ] Implement `k8s.exec_tools` (exec_command_in_pod, port_forward)
  - [ ] Add tool result caching
  - [ ] Implement tool execution timeouts
  - [ ] Add error handling for K8s API exceptions

- [ ] **Add multi-cluster support**
  - [ ] Create cluster registry in database
  - [ ] Implement cluster context switching
  - [ ] Add cluster health monitoring
  - [ ] Support kubeconfig from Secrets/ConfigMaps

### 1.2 Cloud Provider Integration (AWS/Azure/GCP)
- [ ] **AWS Integration**
  - [ ] Add `boto3` and `aiobotocore` dependencies
  - [ ] Create AWS credentials manager (IRSA, instance profiles, access keys)
  - [ ] Implement EC2 tools (list_instances, start/stop/terminate)
  - [ ] Implement ECS/EKS tools
  - [ ] Implement S3 tools (list_buckets, upload/download)
  - [ ] Implement CloudWatch integration for logs/metrics
  - [ ] Create AWS resource ingestion service

- [ ] **Azure Integration**
  - [ ] Add `azure-identity` and `azure-mgmt-*` packages
  - [ ] Implement Azure credential management
  - [ ] Create Azure VM tools
  - [ ] Implement AKS (Azure Kubernetes) integration

- [ ] **GCP Integration**
  - [ ] Add `google-cloud-*` packages
  - [ ] Implement GCP service account auth
  - [ ] Create GCE tools
  - [ ] Implement GKE integration

### 1.3 NATS Event-Driven Architecture
- [ ] **Set up NATS infrastructure**
  - [ ] Update docker-compose with NATS JetStream enabled
  - [ ] Create stream configurations
  - [ ] Set up durable consumers

- [ ] **Create shared NATS client** (`services/shared/nats_client.py`)
  - [ ] Implement `NatsClient` singleton with connection pooling
  - [ ] Add publish/subscribe methods with typing
  - [ ] Implement JetStream integration
  - [ ] Add retry logic with exponential backoff
  - [ ] Create message envelope standard (JSON Schema)

- [ ] **Define event schemas** (`services/shared/events/schemas.py`)
  - [ ] `TaskCreatedEvent` - When agent creates task
  - [ ] `TaskStepStartedEvent` - Step execution begins
  - [ ] `TaskStepCompletedEvent` - Step success/failure
  - [ ] `ApprovalRequestedEvent` - New approval needed
  - [ ] `ApprovalResolvedEvent` - Approved/rejected
  - [ ] `ActionExecutedEvent` - Infrastructure change made
  - [ ] `K8sResourceChangedEvent` - Pod/deployment changes
  - [ ] `AuditLogCreatedEvent` - New audit entry

- [ ] **Implement event publishing in all services**
  - [ ] Agent Service: Task lifecycle events
  - [ ] Action Engine: Action execution events
  - [ ] Policy Engine: Approval events
  - [ ] Ingestion Service: K8s resource change events
  - [ ] Audit Service: Audit log events

- [ ] **Implement event subscribers**
  - [ ] Audit Service: Subscribe to all events for logging
  - [ ] Notification Service (new): Subscribe to approval/alert events
  - [ ] Discovery Service: Subscribe to K8s events for correlation

## Phase 2: Authentication & User Management

### 2.1 User Management Service
- [ ] **Create new User Service** (Port 8008)
  - [ ] Define database schema (users, roles, permissions, teams)
  - [ ] Implement user CRUD API
  - [ ] Add role-based access control (RBAC) models
  - [ ] Create team/workspace organization
  - [ ] Implement API key management
  - [ ] Add user preferences/settings

- [ ] **Update API Gateway authentication**
  - [ ] Replace hardcoded JWT with User Service validation
  - [ ] Implement token refresh
  - [ ] Add OAuth2/OIDC integration (Google, GitHub, Azure AD)
  - [ ] Implement SAML support for enterprise
  - [ ] Add MFA/TOTP support
  - [ ] Create session management with Redis

- [ ] **Implement fine-grained permissions**
  - [ ] Resource-level permissions (namespace, cluster, resource type)
  - [ ] Action-level permissions (read, dry-run, execute)
  - [ ] Time-based permissions (business hours only)
  - [ ] Approval chain permissions
  - [ ] Create permission caching layer

### 2.2 Cluster & Resource Access Control
- [ ] **Implement cluster access mapping**
  - [ ] User → Team → Cluster → Namespace permissions
  - [ ] Support wildcard patterns (e.g., "*-prod-*" namespaces)
  - [ ] Add resource label-based access control
  - [ ] Implement environment segregation (dev/staging/prod)

- [ ] **Create impersonation system**
  - [ ] Service account per user for K8s API
  - [ ] Audit trail of impersonation
  - [ ] Support for elevated access requests

## Phase 3: Workflow Engine

### 3.1 Workflow Orchestration Service
- [ ] **Create Workflow Service** (Port 8009)
  - [ ] Define workflow DSL (YAML/JSON schema)
  - [ ] Implement state machine engine
  - [ ] Add DAG (Directed Acyclic Graph) execution
  - [ ] Support parallel step execution
  - [ ] Implement step retry logic with backoff
  - [ ] Create workflow versioning
  - [ ] Add workflow templates library

- [ ] **Implement workflow triggers**
  - [ ] Manual trigger (user-initiated)
  - [ ] Scheduled trigger (cron-based)
  - [ ] Event trigger (NATS message)
  - [ ] Webhook trigger
  - [ ] Auto-trigger on resource changes

- [ ] **Create workflow steps**
  - [ ] `query_step` - Run query agent
  - [ ] `action_step` - Execute infrastructure action
  - [ ] `approval_step` - Wait for human approval
  - [ ] `condition_step` - If/then/else logic
  - [ ] `notification_step` - Send alert
  - [ ] `delay_step` - Wait for time duration
  - [ ] `custom_step` - Execute arbitrary code (sandboxed)

- [ ] **Update Agent Service integration**
  - [ ] Support multi-step task execution
  - [ ] Implement workflow resume after approval
  - [ ] Add workflow state persistence
  - [ ] Create workflow execution monitoring

## Phase 4: Notification & Communication

### 4.1 Notification Service
- [ ] **Create Notification Service** (Port 8010)
  - [ ] Define notification templates
  - [ ] Implement notification preferences per user
  - [ ] Add notification history/deduplication
  - [ ] Create notification routing rules

- [ ] **Slack Integration**
  - [ ] OAuth app installation flow
  - [ ] Interactive Slack commands (`/talkai`)
  - [ ] Slack bot for approval requests
  - [ ] Rich message formatting with buttons
  - [ ] Thread-based conversation support
  - [ ] Channel notifications for cluster events

- [ ] **Email Notifications**
  - [ ] SMTP integration
  - [ ] Email template system (HTML/text)
  - [ ] Batch digest notifications
  - [ ] PGP encryption support

- [ ] **Microsoft Teams Integration**
  - [ ] Teams bot framework integration
  - [ ] Adaptive Cards for approvals
  - [ ] Channel notifications

- [ ] **Webhook Integration**
  - [ ] Outgoing webhooks for custom integrations
  - [ ] HMAC signature verification
  - [ ] Retry logic for failed deliveries
  - [ ] Webhook management UI

### 4.2 Real-Time Updates
- [ ] **WebSocket Infrastructure**
  - [ ] Scale WebSocket connections (Redis pub/sub)
  - [ ] Implement connection authentication
  - [ ] Add reconnection logic
  - [ ] Create room-based subscriptions (per user, per cluster)

- [ ] **Server-Sent Events (SSE)**
  - [ ] Implement SSE endpoints for task status
  - [ ] Add SSE for approval notifications
  - [ ] Create SSE for audit log streaming

- [ ] **Frontend Real-Time UI**
  - [ ] Live task status updates
  - [ ] Real-time approval notifications
  - [ ] Live infrastructure topology updates
  - [ ] Toast notifications for important events

## Phase 5: Safety & Reliability

### 5.1 Enhanced Safety Engine
- [ ] **Resource impact analysis**
  - [ ] Dependency graph analysis (what depends on this resource?)
  - [ ] Blast radius calculation
  - [ ] Resource criticality scoring
  - [ ] Historical failure rate analysis

- [ ] **Anomaly Detection**
  - [ ] Baseline behavior modeling
  - [ ] Unusual pattern detection
  - [ ] Drift detection from golden paths
  - [ ] Integration with Prometheus metrics

- [ ] **Rollback System**
  - [ ] Automatic state snapshots before changes
  - [ ] One-click rollback in UI
  - [ ] Automated rollback on failure detection
  - [ ] Rollback testing/dry-run

### 5.2 Observability
- [ ] **Distributed Tracing**
  - [ ] OpenTelemetry integration
  - [ ] Jaeger deployment
  - [ ] Trace correlation across services
  - [ ] Custom span attributes for business logic

- [ ] **Metrics & Monitoring**
  - [ ] Prometheus metrics in all services
  - [ ] Custom dashboards (Grafana)
  - [ ] SLA/SLO tracking
  - [ ] Error rate alerting

- [ ] **Log Aggregation**
  - [ ] Structured logging standardization
  - [ ] Log correlation IDs
  - [ ] Elasticsearch/Loki integration
  - [ ] Log-based alerting

## Phase 6: Data & Intelligence

### 6.1 Enhanced RAG System
- [ ] **Multi-source ingestion**
  - [ ] Confluence/Notion documentation
  - [ ] Terraform state files
  - [ ] Helm chart values
  - [ ] Git repository analysis
  - [ ] Runbook ingestion

- [ ] **Advanced embeddings**
  - [ ] Multi-modal embeddings (text + diagrams)
  - [ ] Code-aware embeddings
  - [ ] Incremental embedding updates
  - [ ] Embedding quality monitoring

- [ ] **Context windows**
  - [ ] Conversation history in vector search
  - [ ] User preference learning
  - [ ] Similar question detection
  - [ ] Auto-suggested follow-ups

### 6.2 Cost Management
- [ ] **Cost Analysis Integration**
  - [ ] AWS Cost Explorer integration
  - [ ] Kubecost integration for K8s
  - [ ] Resource cost tagging
  - [ ] Cost impact estimation in dry-runs
  - [ ] Cost anomaly detection

- [ ] **Resource Optimization**
  - [ ] Right-sizing recommendations
  - [ ] Idle resource detection
  - [ ] Reserved capacity planning

## Phase 7: Enterprise Features

### 7.1 Compliance & Governance
- [ ] **Policy as Code**
  - [ ] OPA (Open Policy Agent) integration
  - [ ] Rego policy authoring
  - [ ] Policy testing framework
  - [ ] Policy enforcement points

- [ ] **Compliance Reporting**
  - [ ] SOC 2 compliance reports
  - [ ] HIPAA audit trails
  - [ ] PCI DSS controls
  - [ ] Custom compliance frameworks

- [ ] **Data Retention**
  - [ ] Configurable retention policies
  - [ ] Automated data archival
  - [ ] GDPR compliance (right to be forgotten)

### 7.2 Multi-Tenancy
- [ ] **Tenant Isolation**
  - [ ] Database schema per tenant
  - [ ] Resource namespace isolation
  - [ ] Cross-tenant access controls
  - [ ] Tenant-specific configurations

- [ ] **White-Label Support**
  - [ ] Custom branding/theming
  - [ ] Custom domain support
  - [ ] Tenant-specific integrations

## Phase 8: Frontend Enhancements

### 8.1 Infrastructure Visualization
- [ ] **Topology Diagrams**
  - [ ] Interactive cluster topology
  - [ ] Service dependency graph
  - [ ] Network flow visualization
  - [ ] Cost flow diagrams

- [ ] **Resource Explorer**
  - [ ] Tree view of all resources
  - [ ] Resource relationship mapping
  - [ ] Timeline view of changes
  - [ ] Comparison view (before/after)

### 8.2 Advanced Chat Features
- [ ] **Rich Message Rendering**
  - [ ] Code blocks with syntax highlighting
  - [ ] Embedded resource cards
  - [ ] Interactive buttons in chat
  - [ ] File attachment support

- [ ] **Command Palette**
  - [ ] Quick action shortcuts
  - [ ] Command suggestions
  - [ ] Keyboard shortcuts
  - [ ] Searchable command history

### 8.3 Mobile Experience
- [ ] **Mobile App** (React Native/Flutter)
  - [ ] Core chat functionality
  - [ ] Approval workflows
  - [ ] Push notifications
  - [ ] Offline support

## Development Workflow

### Sprint Planning
- [ ] Break each phase into 2-week sprints
- [ ] Define acceptance criteria for each task
- [ ] Assign owners to services/components

### Testing Strategy
- [ ] Unit tests for all new code (>80% coverage)
- [ ] Integration tests for service interactions
- [ ] E2E tests for critical user flows
- [ ] Load testing for K8s API operations
- [ ] Chaos engineering tests

### Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Architecture decision records (ADRs)
- [ ] Runbooks for operations
- [ ] User guides and tutorials
- [ ] Developer onboarding guide

### Deployment Strategy
- [ ] Feature flags for gradual rollout
- [ ] Canary deployments per service
- [ ] Database migration strategy
- [ ] Rollback procedures

## Quick Wins (Start Here)

**CRITICAL: Phase 0 MUST be completed first - the app cannot work without real infrastructure connections.**

Start with these for immediate impact:

**Phase 0 - Foundation (Do These First):**

**Step 1: Clean & Onboard (Weeks 1-3):**
1. **Remove Mock Data** - Delete all mock data from ingestion service (3-5 days)
2. **Create Onboarding Service** - Basic cluster registration API (1 week)
3. **Build Discovery Integration** - Connect Discovery Service to Onboarding (5-7 days)
   - Detect K8s from port scans (port 6443)
   - One-click cluster onboarding from scan results
4. **Connect First Cluster** - Load kubeconfig and test real connection (2-3 days)

**Step 2: User Interaction Core (Weeks 4-5) - CRITICAL for usability:**
5. **Build Query Intent Classification** - Define what users can ask (3-4 days)
   - Read queries (show pods, get logs) → Auto-execute
   - Action queries (scale, restart) → Require approval
6. **Implement Chat Workflow** - The core interaction (5-7 days)
   - User types query → AI classifies → Routes to agent
   - Show dry-run previews → Get approval → Execute
   - Rich message rendering (tables, code, cards)
7. **Approval Workflow UI** - Essential for safety (4-5 days)
   - Pending approvals dashboard
   - Show dry-run results before approval
   - Approve/Reject with comments

**Step 3: Data Pipeline & Production (Week 6+):**
8. **Build Data Architecture & RAG Pipeline** ⭐ CRITICAL ⭐ (1.5 weeks)
    - Transform discovery data → RAG documents → Qdrant embeddings
    - Add source citations to prevent AI hallucinations
    - Real-time updates when new scans complete
9. **Update Ingestion Service** - Use real K8s client (3-5 days)
10. **Create Discovery Management Page** - /discovered view (1 week)
11. **AI Engine Settings** - Configure Ollama & models (1 week)
    - Ollama connection & testing
    - Model selection & assignment
    - Parameter tuning (temperature, etc.)
12. **Basic Monitoring** - Real-time alerts for critical issues (1 week)

**Phase 0 Extension - AI-Driven Workflow Automation (Weeks 8-10):** ⭐ HIGHEST IMPACT ⭐
13. **Build AI-Driven Multi-Step Workflow Engine** (2-3 weeks) - The "Game Changer"
    - **PRIMARY MODE**: AI generates custom workflows from natural language
      *Example: "Deploy my API with PostgreSQL" → AI creates 8-step plan on-the-fly*
    - Visual workflow builder with drag-and-drop
    - **SECONDARY**: Pre-built templates for common operations
      *Templates: Blue-Green Deploy, Database Migration, Disaster Recovery*
    - **ADVANCED**: Fully AI-driven real-time planning for novel scenarios
    - 10x productivity: 1 hour manual work → 5 minutes automated
    - NO hardcoded flows - AI plans dynamically based on user intent

**Phase 1+ - Advanced Features:**
14. **NATS Events** - Full event streaming (1 week)
15. **Slack Notifications** - Approval alerts (3-4 days)
16. **Cost Management** - Track and optimize spend (2 weeks)

## Dependencies Between Tasks

```
Phase 0 (FOUNDATION - REQUIRED FIRST):

Discovery Service ──┬──▶ Port Scanning (masscan/nmap)
             │    │
             │    ├──▶ K8s Detection (port 6443)
             │    │
             │    └──▶ Cloud Detection (IMDS)
             │
             └──▶ Onboarding Integration ──┬──▶ Smart Suggestions
                                        │
                                        └──▶ One-Click Onboard
                                         
Onboarding Service ──┬──▶ Cluster Registration
              │    │
              │    ├──▶ Vault/Secrets Management
              │    │
              │    └──▶ Credential Storage
              │
               └──▶ Mock Data Removal ──▶ Production Ready

AI Engine Config ──┬──▶ Ollama Connection
              │    │
              │    ├──▶ Model Selection (llama3.3, codellama)
              │    │
              │    ├──▶ Parameter Tuning (temperature, etc.)
              │    │
              │    └──▶ RAG Configuration
              │
              └──▶ Chat Interface (Query Classification)

Data Architecture ──┬──▶ Discovery Data (PostgreSQL)
               │    │
               │    ├──▶ K8s Resources (Watch API)
               │    │
               │    └──▶ Cloud Resources (API)
               │
               ├──▶ Data Transformation (Text Generation)
               │
               ├──▶ Vector Embeddings (Qdrant)
               │    │
               │    ├──▶ Semantic Search
               │    │
               │    └──▶ Source Citations ✓
               │
               └──▶ AI Answers (No Hallucinations!)

Phase 1+ (Depends on Phase 0):
K8s Client ─────────────────┬──▶ Agent Tools
       │                      │
       ├──▶ Ingestion Service ──▶ RAG System
       │
       └──▶ Action Engine ──▶ Dry-Run Sandbox

NATS Setup ──┬──▶ Event Publishing ──▶ Audit Service
       │    │
       │    ├──▶ Notification Service ──▶ Slack/Email
       │    │
       │    └──▶ Workflow Engine
       │
       └──▶ Real-Time Updates ──▶ Frontend

User Service ──┬──▶ API Gateway Auth
          │
          ├──▶ Policy Engine RBAC
          │
          └──▶ Cluster Access Control
```

---

**Estimated Timeline:**

### Phase 0: Foundation (6-7 weeks - MUST BE FIRST)
**Without this, the app is just a demo.**

**Weeks 1-3: Clean & Onboard**
- Mock data removal: 1 week
- Onboarding service: 2 weeks
- Discovery → Onboarding integration: 1-2 weeks

**Weeks 4-5: User Interaction Core (CRITICAL - without this, users can't actually use the app)**
- Query intent classification: 3-4 days
- Chat workflow (dry-run → approval → execute): 5-7 days
- Approval workflow UI: 4-5 days

**Week 6-7: Production Readiness & AI Tuning**
- Discovery management page (/discovered): 1 week
- Ingestion service with real K8s: 3-5 days
- AI Engine Settings (/settings/ai-engine): 1 week
  └─ Configure Ollama, select models, tune parameters
- Basic monitoring/alerts: 1 week

**Weeks 8-10: Multi-Step Workflow Engine ⭐ HIGHEST IMPACT ⭐**
- Workflow Service (Port 8012) with database: 1 week
- Core step types (action, wait, approval, parallel): 1 week
- Visual workflow builder + Templates: 1 week
- Dry-run mode + Rollback support: 3-5 days
- Result: 10x productivity for deployments

### Phase 1-8: Features (32-46 weeks)
- Phase 1 (Core Infrastructure): 6-8 weeks
- Phase 2 (Auth): 4-6 weeks  
- Phase 3 (Workflows): 6-8 weeks
- Phase 4 (Notifications): 4-6 weeks
- Phase 5 (Safety): 4-6 weeks
- Phase 6 (Intelligence): 4-6 weeks
- Phase 7 (Enterprise): 4-6 weeks
- Phase 8 (Frontend): 6-8 weeks

**Total: ~44-59 weeks for complete platform**

**Working MVP (Phase 0 only): 6-7 weeks**
**Feature-Complete MVP (Phases 0-1): 12-15 weeks**

**CRITICAL PATH:**
```
Week 1: Remove mock data
Week 2: Build onboarding service
Week 3: Connect discovery → onboarding
Week 4: Implement chat query flow
Week 5: Build approval workflow UI
Week 6: Create discovered infrastructure page + AI Engine settings
Week 7: Production testing & bug fixes
Week 8-9: Build Workflow Engine (sequential steps)
Week 10: Workflow templates + Visual builder

→ After Week 7: Users can:
   • Scan network, discover K8s
   • Configure Ollama & select AI models
   • Chat with AI to query pods
   • Approve scaling actions
   • Get real-time alerts
   
→ After Week 10: Users can:
   • Deploy microservices with database in 5 minutes (not 1 hour)
   • Use blue-green deployment templates
   • Run automated disaster recovery
   • Visual workflow builder
```

**IMPORTANT:** 
- Phase 0.7 (User Interaction) is CRITICAL - without it, users can't actually use the app after onboarding
- Do NOT start Phase 1 until Phase 0.7 is complete
- The app needs: Onboarding → Discovery → Chat → Approval → Working System

### Complete User Journey (Visual Summary)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 0: FOUNDATION (Weeks 1-7)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  WEEK 1: CLEAN                                                   │
│  ├─ Remove all mock data                                        │
│  └─ Setup testing infrastructure                                 │
│                                                                  │
│  WEEK 2-3: ONBOARD                                               │
│  ├─ Build Onboarding Service (Port 8011)                        │
│  ├─ Create cluster registration APIs                            │
│  ├─ Integrate Discovery → Onboarding                            │
│  │   └─ Detect K8s from port 6443                              │
│  └─ Frontend: /discovered page with smart suggestions            │
│                                                                  │
│  WEEK 4-5: INTERACT ⭐ CRITICAL ⭐                                │
│  ├─ Chat Intent Classification                                  │
│  │   ├─ Read queries → Auto-execute                            │
│  │   └─ Action queries → Require approval                      │
│  ├─ Chat Workflow Implementation                                │
│  │   ├─ AI Router classifies intent                            │
│  │   ├─ Dry-run simulation                                       │
│  │   ├─ Approval workflow                                       │
│  │   └─ Real execution                                          │
│  └─ Rich message rendering (tables, cards, buttons)              │
│                                                                  │
│  WEEK 6-7: PRODUCTION-READY & AI CONFIGURATION                   │
│  ├─ Real-time monitoring (pod status, node health)             │
│  ├─ Basic alerting (Slack/email for critical issues)           │
│  ├─ AI Engine Settings (/settings/ai-engine)                    │
│  │   ├─ Connect to Ollama server                               │
│  │   ├─ Test available models                                  │
│  │   ├─ Assign: llama3.3:70b for chat                         │
│  │   ├─ Assign: codellama:34b for code                         │
│  │   └─ Tune temperature & parameters                         │
│  ├─ Cost tracking (show spend)                                 │
│  └─ Performance testing & bug fixes                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AFTER WEEK 7: WORKING SYSTEM                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  USER WORKFLOW:                                                  │
│                                                                  │
│  1. Run Network Scan                                             │
│     ├─ Scan 192.168.1.0/24                                      │
│     └─ Find: 3 hosts with port 6443 (K8s API)                   │
│                                                                  │
│  2. Discover Infrastructure                                      │
│     ├─ /discovered page shows: "K8s Cluster Detected"           │
│     └─ Click "Connect Cluster" → Pre-filled onboarding form     │
│                                                                  │
│  3. Onboard Cluster                                              │
│     ├─ Provide credentials                                     │
│     ├─ Test connection ✓                                        │
│     └─ Cluster now shows in /infra page                         │
│                                                                  │
│  4. Query Infrastructure (CHAT)                                  │
│     User: "show me pods in default namespace"                   │
│        ↓                                                         │
│     AI: Classifies as READ query → Auto-executes               │
│        ↓                                                         │
│     System: Lists pods in table format                          │
│                                                                  │
│  5. Execute Action (with Approval)                               │
│     User: "scale web-deployment to 5 replicas"                │
│        ↓                                                         │
│     AI: Classifies as ACTION → Requires approval               │
│        ↓                                                         │
│     System: Shows dry-run preview                               │
│        ↓                                                         │
│     User: Clicks [Approve]                                      │
│        ↓                                                         │
│     System: Executes scaling                                    │
│        ↓                                                         │
│     Audit: Logs everything                                        │
│                                                                  │
│  6. Monitor & Alert (BACKGROUND)                                 │
│     ├─ Pod crashes detected                                      │
│     ├─ Slack notification sent                                 │
│     └─ User sees alert in UI                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AFTER WEEK 10: AUTOMATED WORKFLOWS (Phase 0.12)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  7. Deploy Complex Applications (MULTI-STEP WORKFLOW)           │
│     User: "Deploy payment-service with PostgreSQL"            │
│        ↓                                                         │
│     AI: Generates 8-step workflow:                               │
│     ├─ Step 1: Create namespace ✓                              │
│     ├─ Step 2: Create ConfigMap ✓                              │
│     ├─ Step 3: Create Secret ✓                                 │
│     ├─ Step 4: Deploy PostgreSQL → Waiting for ready...          │
│     ├─ Step 5: Run migrations [Pending]                          │
│     ├─ Step 6: Deploy application [Pending]                      │
│     ├─ Step 7: Create Ingress [Pending]                          │
│     └─ Step 8: Verify deployment [Pending]                     │
│        ↓                                                         │
│     Visual Progress: 50% Complete (4/8 steps)                   │
│     Time: 3m 12s elapsed                                        │
│        ↓                                                         │
│     ✓ Workflow completed in 5m 30s                              │
│     All resources deployed successfully!                        │
│     [View Resources] [Save as Template]                          │
│                                                                  │
│  8. Blue-Green Deployment (TEMPLATE)                           │
│     User: Selects "Blue-Green Deployment" template              │
│     Parameters: service=api, version=v2.1                       │
│        ↓                                                         │
│     Workflow executes 12 steps automatically:                   │
│     ├─ Deploy green version (20% traffic)                       │
│     ├─ Run smoke tests ✓                                        │
│     ├─ Monitor for 5 minutes ✓                                  │
│     ├─ Shift 50% traffic ✓                                      │
│     ├─ Monitor for 10 minutes ✓                                 │
│     ├─ Shift 100% traffic ✓                                       │
│     └─ Wait 30min, then cleanup blue                            │
│        ↓                                                         │
│     Result: Zero-downtime deployment completed                   │
│     Rollback available if issues detected                       │
│                                                                  │
│  9. Disaster Recovery (RUNBOOK)                                 │
│     Alert: "Database primary down"                              │
│        ↓                                                         │
│     AI: Suggests "Database Failover" workflow                     │
│     User: [Execute Workflow]                                     │
│        ↓                                                         │
│     10-step recovery executes:                                  │
│     ├─ Stop writes to primary                                   │
│     ├─ Promote replica to primary                                │
│     ├─ Update connection strings                                  │
│     ├─ Verify new primary healthy ✓                              │
│     ├─ Notify team on Slack                                     │
│     └─ Generate incident report                                  │
│        ↓                                                         │
│     Recovery completed in 4 minutes                             │
│     Team notified, post-mortem scheduled                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1-8: ADVANCED FEATURES (Months 2-14)                       │
├─────────────────────────────────────────────────────────────────┤
│  • Multi-cluster support                                         │
│  • Cloud provider integration (AWS/Azure/GCP)                   │
│  • Workflow automation                                           │
│  • Advanced monitoring & observability                           │
│  • Cost optimization                                             │
│  • Multi-tenancy                                                 │
│  • Compliance & governance                                       │
│  • Mobile app                                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Production Readiness Checklist

Before deploying to production, ensure ALL of the following are complete:

### Infrastructure Onboarding (Phase 0)
- [ ] **ZERO mock data** in the application codebase
- [ ] Discovery Service can detect K8s clusters from network scans
- [ ] At least one Kubernetes cluster registered and connected
- [ ] Credentials stored securely in Vault/AWS Secrets Manager
- [ ] Connection health monitoring is active
- [ ] Onboarding UI tested with real users
- [ ] Discovery → Onboarding integration working (one-click cluster setup)

### Data Architecture & RAG Pipeline (Phase 0.11) ⭐ CRITICAL ⭐
- [ ] **Discovery scan data is indexed in RAG (Qdrant)**
- [ ] **K8s resources are indexed in real-time** (Watch API → RAG)
- [ ] **Source citations are working** (AI answers show "Based on Discovery Scan #123")
- [ ] **No AI hallucinations** (AI only answers based on retrieved data)
- [ ] **Data freshness < 5 minutes** (changes appear in RAG quickly)
- [ ] **Structured + Vector storage working** (PostgreSQL + Qdrant)
- [ ] **Data transformation pipeline** (Discovery → Text → Embeddings)
- [ ] **Context window management** (relevant docs fit in LLM context)
- [ ] **Fallback to database queries** (for "list all" type queries)

### AI Engine Configuration (Phase 0.10)
- [ ] **Ollama server connected and tested**
- [ ] At least one chat model selected and tested (e.g., llama3.3:70b)
- [ ] Intent classification model working (test with sample queries)
- [ ] Embedding model configured for RAG (e.g., nomic-embed-text)
- [ ] Model parameters tuned (temperature ~0.7 for balanced responses)
- [ ] AI Engine settings page accessible in production
- [ ] Fallback models configured (in case primary model fails)
- [ ] Rate limiting and caching configured for AI requests
- [ ] AI response performance tested (response time < 5 seconds)

### Security & Compliance
- [ ] mTLS enabled between all services
- [ ] Secrets management implemented (no hardcoded credentials)
- [ ] RBAC policies configured and tested
- [ ] Audit logging capturing all infrastructure changes
- [ ] Data retention policies configured
- [ ] GDPR compliance (if applicable)

### Observability
- [ ] Distributed tracing enabled (OpenTelemetry)
- [ ] Prometheus metrics exporting
- [ ] Centralized logging (ELK/Loki)
- [ ] Alerting rules configured (PagerDuty/Opsgenie)
- [ ] SLO/SLA dashboards created

### High Availability
- [ ] Database replicas configured
- [ ] Redis cluster enabled
- [ ] NATS JetStream persistence enabled
- [ ] Services deployed with multiple replicas
- [ ] Health checks and readiness probes configured
- [ ] Circuit breakers implemented

### Disaster Recovery
- [ ] Automated database backups
- [ ] Disaster recovery runbook documented
- [ ] RTO/RPO targets defined and tested
- [ ] Rollback procedures tested

### Performance
- [ ] Load testing completed (100x expected traffic)
- [ ] K8s API rate limiting configured
- [ ] Connection pooling optimized
- [ ] Redis caching strategy validated
- [ ] Qdrant vector search benchmarked

### Documentation
- [ ] API documentation complete (OpenAPI/Swagger)
- [ ] Runbooks for on-call engineers
- [ ] User guides and tutorials
- [ ] Architecture diagrams updated
- [ ] ADRs for all major decisions

### Testing
- [ ] Unit test coverage >80%
- [ ] Integration tests passing
- [ ] E2E tests for critical flows
- [ ] Chaos engineering tests completed
- [ ] Security penetration testing done
- [ ] Performance benchmarks met

---

**NO MOCK DATA POLICY:**
This application is designed for production use with real infrastructure. Mock data is only allowed in:
1. Unit tests (using testcontainers or proper mocking frameworks)
2. Demo/sandbox mode (clearly labeled and isolated)
3. Local development (with explicit opt-in)

**Production code must NEVER return mock data to users.**

Violation of this policy should be caught by:
- Pre-commit hooks detecting mock patterns
- CI/CD pipeline checks
- Code review checklist
- Runtime monitoring for mock data signatures

## Running Services

```bash
# Start all services
./scripts/local-dev.sh start

# View logs
./scripts/local-dev.sh logs monitoring-service

# Health check
./scripts/health-check.sh
```

## Task Dependencies

```
Task 0.1 ──┬─────────────────┐
           │                 │
Task 0.2 ──┼──► Task 0.3 ───► Task 0.4 ──► Task 0.5 ──► Task 0.6 ──► Task 0.7 ──► Task 0.8 ✅
           │                 │                                              │
           └─────────────────┴──────────────────────────────────────────────┘
                                    ▲
                                    │
                               Task 0.9, 0.10, 0.11 (future)
```

## Progress Summary

| Phase | Tasks | Completed | In Progress | Pending |
|-------|-------|-----------|-------------|---------|
| Phase 0 | 11 | 10 | 0 | 1 |
| Overall | 11 | 10 (91%) | 0 (0%) | 1 (9%) |

## Files Created for Task 0.8

```
services/monitoring-service/
├── config.py                    # Pydantic settings
├── main.py                      # FastAPI app (Port 8009)
├── models.py                    # SQLAlchemy models
├── models_alerts.py             # Alert models
├── schemas.py                   # Pydantic schemas
├── database.py                   # DB connection
├── requirements.txt             # Dependencies
├── Dockerfile                   # Container config
├── README.md                    # Documentation
├── alembic/versions/__init__.py
├── api/__init__.py
├── api/v1/__init__.py
├── api/v1/alerts.py             # Alert endpoints
├── api/v1/metrics.py            # Metric endpoints
├── api/v1/health.py             # Health endpoints
├── api/v1/rules.py              # Rule endpoints
├── services/__init__.py
├── services/collector.py         # Metric collection
├── services/alerting.py          # Alert evaluation
├── services/anomaly_detection.py # ML detection
├── services/notification.py      # Notifications
└── workers/__init__.py
    └── celery_app.py             # Background workers

services/frontend/src/components/monitoring/
├── __init__.py
├── AlertList.tsx                # Alert dashboard
├── MetricsChart.tsx             # Time-series charts
├── ServiceHealth.tsx            # Service health grid
└── index.ts

services/frontend/src/pages/
└── Monitoring.tsx               # Dashboard page
```

---

*Last Updated: 2026-02-05T06:36:00Z*
