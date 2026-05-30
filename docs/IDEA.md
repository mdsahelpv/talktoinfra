# TalkToInfra — AI-Native Infrastructure Copilot

## The Big Idea

TalkToInfra is an open-source AI agent that lets IT/DevOps teams talk to their entire infrastructure in natural language. It sits **inside your network** as a lightweight agent, connects to everything (K8s, cloud, on-prem, AD, DNS, firewalls, monitoring), and answers questions or executes actions through conversation.

> **"Is my K8s cluster healthy?" → "Where is the AD server?" → "What's the IP of the DNS server?" → "Restart that pod."**

---

## 1. Market Landscape — Who's Already Here

### Established Open-Source Competitors

| Project | Focus | Stars | Language | Write Ops | Notes |
|---|---|---|---|---|---|
| **Siclaw** | Read-only K8s/SRE diagnostics, deep investigation | ~200 | TS | No | Strongest OSS project. 4-phase investigation, team collaboration, MCP extensible. Read-only by design. |
| **KubeIntellect** | K8s multi-agent RCA + diagnostics | ~3 | Python | HITL-gated | New. LangGraph multi-agent. HITL for destructive ops. CLI + API. |
| **SRE-Agent** | K8s + Prometheus + ArgoCD diagnostics | New | Python | Yes (scoped) | 28 tools, incident memory, hot-swap LLMs. Read + limited write. |
| **kubectl-ai (Google)** | Natural language K8s CLI assistant | Active | Go | Yes | Google-backed kubectl plugin. Reads context, translates intent to commands. |
| **k8sgpt** | K8s analysis + plain-English explanations | Popular | Go | No | Scans cluster, explains issues. Patterns-based + LLM. Read-only. |
| **PIPER** | Terminal-first DevOps copilot | New | TS | HITL-gated | Safety-first: LLM picks from a closed action catalog, never writes shell. |
| **DojOps** | AI IaC generator (Terraform, K8s, CI/CD) | New | TS | Yes | Config generation focused. 32 specialist agents. Not real-time infra query. |
| **InsideOut** | Cloud infra design + Terraform generation | New | (skill) | Yes | AWS/GCP architecture from conversation. Terraform generation. |
| **InfraSquad** | Multi-agent cloud architecture debate + IaC | New | Python | No (generates only) | Agents debate architecture, generate Terraform, security scan. |
| **AwsInfraAgent** | AWS natural language management | ~205 | Go | Yes (PoC) | AWS-only. Terraform-like state tracking. Dry-run mode. |
| **AgentOS** | Drag-drop DevOps workflow builder | New | - | Yes | Runbook mode, monitor mode, agent swarm mode. Archestra security. |
| **Kubernaut** | K8s alert → automated remediation | ~16 | Go | Yes | Tekton/Ansible remediation, OPA policies, audit trails. |
| **TalkOps** | Multi-agent DevOps automation | New | Python | Yes (gated) | LangGraph, A2A protocol, MCP tools. PR-based approval. |
| **Cluster-Whisperer** | K8s natural language Q&A + vector DB | New | TS | Yes | Vector DB of cluster knowledge. MCP server. Semantic bridge pattern. |
| **K8gentS** | K8s RCA + HITL remediation via Slack | New | Python | Yes (HITL) | OPA Gatekeeper sandbox. Confidence scoring. Slack approval. |
| **Kuborg** | Agentic CLI for K8s plain English | New | TS | Yes | kubectl as tool. 20 iteration agentic loop. Autocomplete. |
| **DevOps AI Toolkit** | Platform engineering + AI | New | - | Yes | MCP-based. Semantic search, policy management. |

### Commercial / SaaS Competitors

| Product | Focus | Key Differentiator |
|---|---|---|
| **Pulumi Neo** | AI infrastructure agent for Pulumi | Deep IaC integration, enterprise governance |
| **Docker Gordon** | Container workflow AI agent | Environment-aware, built into Docker Desktop |
| **Praxis** | Universal DevOps AI agent | Multi-agent, Slack-native, MCP extensible |
| **Atmos AI** | Infra-aware AI for Atmos stacks | Deep IaC understanding, 7 LLM providers |
| **SwiftDeploy** | Deployment harness for AI agents | DevOps harness, Terraform management |
| **Spacelift Intent** | AI IaC provisioning | Deterministic, compliance-focused |
| **Atmosly Copilot** | K8s troubleshooting AI | Natural language to kubectl/PromQL |

### Key Takeaway

**No single OSS project connects *all* infrastructure types (K8s + cloud + on-prem + AD + DNS + networking) in one agent.** Most are:
- K8s-only (kubectl-ai, KubeIntellect, K8gentS, Kuborg)
- Cloud-only (InsideOut, AwsInfraAgent, InfraSquad)
- IaC generation only (DojOps, TerraBot)
- Read-only diagnostics (Siclaw, k8sgpt)

**TalkToInfra's differentiator:** A single agent that speaks to **everything** in your hybrid infrastructure — K8s, AWS, Azure, GCP, on-prem VMs, AD, DNS, databases, load balancers, firewalls — with read + HITL-gated write operations.

---

## 2. Real Pain Points (Sourced from Reddit, DEV, Medium, Industry Reports)

### Pain 1: "I run the same 10 kubectl commands 50 times a day"
> "Developers usually run the same commands again and again before they can even explain the incident clearly." — DEV.to

Engineers waste 30-60 minutes per incident running the same diagnostic commands manually. The cognitive load of remembering syntax across (kubectl, aws, az, gcloud, dig, nslookup, systemctl, journalctl) is enormous.

### Pain 2: "K8s doesn't fail loudly — it fails indirectly"
> "A pod crashes, but the real issue sits in a missing secret. A service is healthy, but traffic never reaches it." — Medium

The gap between raw signals and root cause is where most time is lost. Engineers need to correlate events, logs, metrics, and resource states — across different systems — to build a coherent picture.

### Pain 3: "Context switching between 5+ tools is exhausting"
> "I'm jumping between kubectl, AWS console, Grafana, Slack, and runbooks. Each tool has its own syntax, its own auth, its own UI." — Reddit

Infrastructure tools are fragmented. An engineer managing hybrid infra might use 8+ different CLIs/consoles daily. No single pane of glass.

### Pain 4: "On-call at 3 AM with someone else's infrastructure"
> "The worst is getting paged for something you didn't set up. You don't know the topology, the naming conventions, or where to look first." — DEV.to

Tribal knowledge is the biggest bottleneck. New team members take months to learn infrastructure topology. Runbooks go out of date.

### Pain 5: "AI writes plausible Terraform — then it breaks in production"
> "The LLM suggested deleting the kube-system namespace to 'clear up resource contention.'" — Medium

Blind trust in AI-generated infrastructure code is dangerous. AI-generated IAM policies are syntactically perfect but wildly over-permissioned. Resource limits get "optimized" to insane values.

### Pain 6: "LLMs hallucinate API versions and non-existent flags"
> "AI suggested extensions/v1beta1 for an Ingress — deprecated years ago." — Production Guide

LLMs trained on outdated data suggest deprecated or non-existent API versions, flags, and resource names.

### Pain 7: "Data leakage fear stops adoption"
> "If you send your raw secrets or PII to a public endpoint, you're creating a bigger problem than a failing pod." — TunedTools

Infrastructure data is sensitive. Teams need on-prem/local LLM options and redaction layers.

### Pain 8: "Our 47 deployment scripts don't scale"
> "I wasn't automating. I was hardcoding decisions." — DEV.to

Hardcoded scripts for every workflow don't scale. Teams need adaptive orchestration, not more scripts.

### Pain 9: "Junior engineers can't debug production"
> "Kubernetes debugging relies on experience we don't have yet." — Junior engineer on Reddit

Standardized troubleshooting knowledge isn't accessible to newer team members. Every incident requires a senior engineer.

### Pain 10: "Security agents become infinite blockers"
> "Security agent demanded two-person approval workflows — for a 2-node homelab." — Autonomous SRE Experiment

Over-zealous safety guards block legitimate work. Teams need tiered autonomy, not binary allow/deny.

---

## 3. TalkToInfra — Our Position

### Vision
**One conversation to manage everything.** The IT team talks to a single AI agent that understands their entire hybrid infrastructure — Kubernetes, cloud, on-prem, networking, identity, databases, and observability.

### Core Differentiators

| Dimension | Others | TalkToInfra |
|---|---|---|
| **Infrastructure Coverage** | K8s-only or cloud-only | Hybrid: K8s + cloud + on-prem + AD/DNS + networking + DB + monitoring |
| **Write Operations** | Often none or limited | Yes — tiered HITL gates (read/mutate/destructive) |
| **Deployment Model** | Cloud API or CLI tool | **In-cluster agent** inside your network — no data leaves |
| **LLM Choice** | Usually 1-2 providers | Plugable: OpenAI, Anthropic, Ollama (local), Azure, Bedrock |
| **Safety Model** | Prompt-based or none | **Deterministic gate**: LLM proposes, schema validates, code executes |
| **Action Catalog** | Free-form shell execution | **Closed typed action catalog** (like PIPER) — LLM cannot run arbitrary commands |
| **Memory** | Stateless sessions | Persistent incident memory + RAG over runbooks |
| **Interface** | CLI-only | CLI + Web UI + Slack bot |

### Philosophy

1. **The LLM proposes; deterministic code disposes.** The LLM never writes shell. It picks from a typed action catalog.
2. **Read by default, write by consent.** Read-only tools execute immediately. Mutations pause for approval. Destructive actions require fresh confirmation every time.
3. **Your infra, your data.** Agent runs in your network. LLM queries go to your chosen provider (local Ollama supported).
4. **Cover everything, deeply.** Start with K8s + DNS + AD + cloud. Grow to all infrastructure types.
5. **Build memory.** The agent learns your topology, past incidents, naming conventions, and runbooks over time.

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                               │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐                        │
│   │   CLI    │   │  Web UI  │   │  Slack   │                        │
│   │ (rich)   │   │(dashboard)│   │  (bot)   │                        │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘                        │
│        │              │              │                               │
└────────┼──────────────┼──────────────┼───────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AI ORCHESTRATOR                                 │
│                              │                                        │
│              ┌───────────────┴───────────────┐                       │
│              │        LLM Router              │                       │
│              │  OpenAI / Anthropic / Ollama   │                       │
│              │  Azure / Bedrock / Custom      │                       │
│              └───────────────┬───────────────┘                       │
│                              │                                        │
│              ┌───────────────┴───────────────┐                       │
│              │    Agent Engine (LangGraph)    │                       │
│              │  ┌─────────────────────────┐  │                       │
│              │  │   Supervisor Agent      │  │                       │
│              │  │  - Intent classification│  │                       │
│              │  │  - Task decomposition   │  │                       │
│              │  │  - Agent routing        │  │                       │
│              │  └──────────┬──────────────┘  │                       │
│              │             │                  │                       │
│              │  ┌──────────┼──────────────┐  │                       │
│              │  │          │              │  │                       │
│              │  ▼          ▼              ▼  │                       │
│              │ ┌──────┐ ┌──────┐ ┌────────┐ │                       │
│              │ │ K8s  │ │Cloud │ │Network │ │                       │
│              │ │Agent │ │Agent │ │ Agent  │ │                       │
│              │ └──┬───┘ └──┬───┘ └───┬────┘ │                       │
│              │    │        │         │      │                        │
│              │    ▼        ▼         ▼      │                        │
│              │ ┌─────────────────────────┐  │                       │
│              │ │   Safety Gate           │  │                       │
│              │ │  - Read: auto-execute   │  │                       │
│              │ │  - Mutate: HITL approve │  │                       │
│              │ │  - Destructive: fresh   │  │                       │
│              │ │    confirm every time   │  │                       │
│              │ └─────────────────────────┘  │                       │
│              └──────────────────────────────┘                       │
│                              │                                        │
└──────────────────────────────┼────────────────────────────────────────┘
                               │
┌──────────────────────────────┼────────────────────────────────────────┐
│                   INFRA AGENT (in-cluster)                            │
│                              │                                        │
│   ┌──────────┬──────────┬────┴────┬──────────┬──────────┐           │
│   │          │          │         │          │          │           │
│   ▼          ▼          ▼         ▼          ▼          ▼           │
│ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌────────┐      │
│ │ K8s  │ │ AWS  │ │Azure   │ │ On-  │ │ AD /   │ │ DNS /  │      │
│ │ API  │ │ API  │ │ API    │ │ Prem │ │ LDAP   │ │ Net-   │      │
│ │      │ │      │ │        │ │ SSH  │ │        │ │ work   │      │
│ └──────┘ └──────┘ └────────┘ └──────┘ └────────┘ └────────┘      │
│                                                                     │
│   ┌────────────────────────────────────────────────────────┐       │
│   │            Knowledge Store (Vector DB)                   │       │
│   │  - Runbooks / SOPs / Architecture docs                  │       │
│   │  - Incident history                                     │       │
│   │  - Topology / naming conventions                        │       │
│   └────────────────────────────────────────────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

#### AI Orchestrator (runs in your infra or cloud)
- **FastAPI** server with WebSocket support
- **LangGraph** state machine for multi-step reasoning
- **Action Catalog**: typed tools with Zod/Pydantic schemas
- **Safety Gate**: three-tier permission system (read/mutate/destructive)
- **LLM Router**: supports OpenAI, Anthropic, Ollama, Azure, Bedrock
- **Memory**: SQLite/PostgreSQL for sessions, Vector DB for RAG

#### Infra Agent (deployed in-cluster/on-prem)
- Lightweight Python/Go service with no external dependencies
- Pluggable "connectors" for each infrastructure type
- Communicates with orchestrator via secure WebSocket or gRPC
- Runs inside your network — no inbound ports required

#### Action Catalog (typed, gated, auditable)

| Category | Read Tools | Mutate Tools | Destructive Tools |
|---|---|---|---|
| **Kubernetes** | get pods, describe, logs, events, top | restart deployment, scale, apply manifest | delete namespace, drain node |
| **Cloud (AWS/Azure/GCP)** | list instances, describe VPC, get costs | start/stop instance, resize, tag | terminate instance, delete SG |
| **Networking** | dig, nslookup, ping, traceroute, port check | update firewall rule (staging) | — |
| **AD/LDAP** | search user, check status, group membership | unlock account, reset password | delete user, delete OU |
| **On-prem** | systemctl status, journalctl, disk usage, memory | restart service, clean logs | shutdown, package remove |
| **Databases** | query size, show connections, slow queries | kill connection, run migration | drop database |
| **Monitoring** | query Prometheus, check alerts, Grafana | silence alert, create dashboard | delete datasource |

---

## 5. Feature Roadmap

### MVP (Phase 1) — Read + Basic Write
- [ ] CLI interface (rich terminal with streaming)
- [ ] K8s connector: pod/service/deployment/event queries
- [ ] DNS/network connector: dig, nslookup, ping
- [ ] AD/LDAP connector: user search, status
- [ ] Cloud connector: AWS EC2 describe (one provider)
- [ ] Safety gate: read auto-execute, mutate HITL approval
- [ ] LLM integration: OpenAI + Ollama (local)
- [ ] Memory: SQLite session persistence
- [ ] Action catalog: typed tools with validation

### Phase 2 — Multi-Agent + Write
- [ ] Supervisor agent with sub-agent routing
- [ ] Full write operations: restart pods, scale, modify firewall rules
- [ ] Web dashboard (real-time streaming)
- [ ] Slack bot integration
- [ ] K8s metrics (Prometheus connector)
- [ ] Cloud expand: Azure + GCP connectors
- [ ] Incident memory: Vector DB for past failures
- [ ] RAG: ingest runbooks, SOPs, architecture docs

### Phase 3 — Proactive + Autonomous
- [ ] Proactive monitoring: agent watches and alerts
- [ ] Auto-remediation for low-risk known issues
- [ ] Scheduled investigations (patrol mode)
- [ ] Team collaboration: shared sessions, approvals
- [ ] Multi-cluster / multi-account support
- [ ] Cost optimization recommendations
- [ ] Ansible/playbook integration
- [ ] Terraform generation from conversation

### Phase 4 — Enterprise
- [ ] RBAC / SSO / audit trail for compliance
- [ ] On-prem only mode (no external LLM calls)
- [ ] Custom skill/connector SDK
- [ ] MCP server (expose as tools to other AI agents)
- [ ] CI/CD integration (GitHub Actions, GitLab)
- [ ] PagerDuty / OpsGenie integration
- [ ] Helm chart deployment
- [ ] Multi-tenant (team isolation)

---

## 6. Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| **Python** | Best AI/LLM ecosystem (LangChain, LangGraph, FastAPI). Rich infra libraries (kubernetes, boto3, azure-sdk, ldap3). |
| **LangGraph** | State machines handle multi-step reasoning with checkpointing, cycles, and HITL patterns. Better than CrewAI/AutoGen for infra workflows. |
| **Closed action catalog** | Prevents arbitrary command injection. LLM picks from a fixed set of typed tools. Deterministic validation before execution. (Like PIPER's approach.) |
| **In-cluster agent** | No inbound ports, no data exfiltration risk. Agent connects out to orchestrator. Follows zero-trust principles. |
| **Three-tier safety** | Read (auto) / Mutate (HITL, remembered per session) / Destructive (fresh confirm every time). Adult supervision where it matters. |
| **Multi-LLM support** | Not locked to one provider. Teams can use local Ollama for sensitive data, GPT-4 for complex reasoning, Claude for analysis. |
| **Vector DB for memory** | Past incidents, runbooks, and topology are semantically searchable. Agent learns from history. |
| **CLI-first** | Infra teams live in the terminal. CLI builds trust — you see every action before it runs. Web/Slack come after. |
| **SQLite first, PostgreSQL later** | Zero-dependency setup for teams to try. Production gets PostgreSQL for team-scale persistence. |

---

## 7. Critical Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **LLM hallucinates commands** | Closed action catalog + schema validation. LLM cannot invent tools. |
| **AI breaks production** | Tiered HITL gates. Read-only default. Destructive ops require fresh confirmation. |
| **Prompt injection** | Input sanitization, parameterized tool execution (never shell=True), secret redaction layer. |
| **Data leakage** | Agent runs in-cluster. Ollama for local LLM. Redaction of secrets/IPs before LLM calls. |
| **Context drift in multi-turn** | LangGraph checkpointing, session compression, explicit context windows. |
| **Token costs** | Local Ollama option. Tool output compaction. Prompt caching. Tiered model routing (cheap model for simple queries). |
| **Agent loops / infinite retries** | Hard cap on iterations (like Kube-AutoFix's 5 max). Circuit breakers. Escalation to human. |
| **Over-privileged agent credentials** | Namespace-locked (like Kube-AutoFix). Least-privilege IAM roles. RBAC scoped per connector. |

---

## 8. Comparison to Major Competitors

| Feature | **TalkToInfra** | Siclaw | KubeIntellect | SRE-Agent | kubectl-ai | PIPER | DojOps |
|---|---|---|---|---|---|---|---|
| K8s support | ✅ Deep | ✅ Deep | ✅ Deep | ✅ Deep | ✅ Deep | ✅ Basic | ⚠️ IaC only |
| Cloud (AWS/Azure/GCP) | ✅ All 3 | ⚠️ SSH only | ❌ | ❌ | ❌ | ⚠️ SSH only | ✅ IaC+ |
| On-prem (SSH) | ✅ Yes | ✅ Yes | ❌ | ❌ | ❌ | ✅ Yes | ❌ |
| AD/LDAP | ✅ Yes | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| DNS/Network | ✅ Yes | ❌ | ❌ | ❌ | ❌ | ✅ Yes | ❌ |
| Write operations | ✅ Tiered HITL | ❌ No | ✅ HITL | ✅ Scoped | ✅ Yes | ✅ HITL | ✅ Yes |
| Local LLM | ✅ Ollama | ❌ | ❌ | ⚠️ Partial | ❌ | ✅ Ollama | ✅ Ollama |
| In-cluster deploy | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ CLI plugin | ❌ CLI only | ❌ CLI only |
| Safe action catalog | ✅ Yes | N/A | ❌ Free-form | ❌ Free-form | ❌ Free-form | ✅ Yes | ⚠️ Partial |
| Incident memory | ✅ Vector DB | ⚠️ Basic | ❌ | ✅ SQLite | ❌ | ✅ PGlite | ❌ |
| Web UI | ✅ Dashboard | ✅ Full | ✅ Basic | ❌ CLI only | ❌ CLI only | ❌ TUI only | ✅ Dashboard |
| Team features | ✅ Shared | ✅ Full | ❌ | ❌ | ❌ | ❌ | ✅ Shared |
| License | **Apache 2.0** | Apache 2.0 | AGPL v3 | MIT | Apache 2.0 | MIT | AGPL v3 |

---

## 9. Getting Started (MVP Plan)

```bash
# 1. Clone the repo
git clone https://github.com/your-org/talktoinfra
cd talktoinfra

# 2. Deploy the in-cluster agent
helm install talktoinfra-agent ./charts/agent \
  --namespace talktoinfra \
  --set orchestrator.endpoint=https://orchestrator.example.com

# 3. Start the orchestrator
docker compose up -d

# 4. Start chatting
talktoinfra
> ℹ️ Connected to orchestrator. Ready.
> 🟢 K8s cluster: 12 nodes healthy
> 🟢 DNS server: 8.8.8.8 reachable
> 🟢 AD server: ad.company.com reachable
>
> You: Are there any failing pods?
> 🤖 Let me check...
> Found 1 pod in CrashLoopBackOff in namespace `production`:
>   - `payment-service-7d9f8c` restarted 6 times in 15 min
>   - Root cause: Missing ConfigMap `db-config`
>   - Fix: `kubectl create configmap db-config --from-literal=DB_HOST=postgres.internal`
>
>   Apply this fix? [y/N]
```

---

## 10. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Runtime** | Python 3.12+ | AI/ML ecosystem, rich infra SDKs |
| **API** | FastAPI + WebSocket | Async, auto-docs, real-time streaming |
| **Agent Framework** | LangGraph | State machines, HITL, checkpointing |
| **LLM Providers** | OpenAI, Anthropic, Ollama, Azure, Bedrock | Flexibility, local option |
| **Action Catalog** | Pydantic v2 | Schema validation, typed tools |
| **Vector DB** | Chroma / Qdrant / pgvector | RAG for runbooks, incident memory |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Session persistence |
| **Auth** | API keys + RBAC | Enterprise-ready |
| **Deployment** | Docker Compose / Helm | Easy dev, production K8s |
| **Connectors** | kubernetes, boto3, azure-identity, ldap3, dnspython | Official SDKs |
| **CLI** | Click + Rich | Beautiful terminal experience |
| **Web UI** | React + Vite + Tailwind | Dashboard for non-CLI users |
| **Safety** | Custom safety gate | Deterministic, not prompt-based |

---

*This is a living document. Updated as we learn and build.*
