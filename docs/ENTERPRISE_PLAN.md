# TalkToInfra — Enterprise Readiness Plan

> Based on market research (Reddit, G2, Capterra, OWASP, CSA, Five Eyes guidance),
> real incident reports, and production deployment patterns from companies running
> AI agents in enterprise environments (2025–2026).

## 0. Why Enterprise Readiness Matters Now

| Source | Signal |
|--------|--------|
| **88% of orgs** reported AI-agent security incidents in 2025–2026 (Gravitee) | Most teams deploy agents faster than they secure them |
| **Only 14.4%** got full security/IT approval before production (Gravitee) | Shadow AI is the norm |
| **EU AI Act** high-risk enforcement begins **August 2026** | Regulatory clock is ticking |
| **Five Eyes** joint guidance (May 2026): agents must have cryptographic identity, least-privilege, and immutable audit trails | International baseline forming |
| Reddit r/devops, r/sre: "AI agents create incidents faster than we can fix them" | Trust is the bottleneck |

**TalkToInfra's gap today:** Strong foundation (closed action catalog, 3-tier safety gate,
in-cluster agent). Missing the enterprise layer: identity, audit, compliance, multi-tenancy,
production deployment, and governance.

---

## 1. Reddit / Practitioner Pain Points — Infrastructure AI Tools

Sourced from Reddit (r/devops, r/sre, r/kubernetes, r/aws), G2/Capterra reviews,
and incident post-mortems published in 2025–2026.

| # | Pain Point | Source Signal | TalkToInfra Impact |
|---|------------|---------------|-------------------|
| 1 | **"No single pane of glass"** — 8+ CLIs daily, context-switching hell | Reddit r/devops, DEV.to | Core value prop — but must actually deliver all connectors reliably |
| 2 | **"AI broke production at 3 AM"** — resource explosion, over-optimization, silent security holes | AI incident writeups (May 2026) | Safety gate is the defense, but **token budgets, rate limits, and circuit breakers** are missing |
| 3 | **"I don't trust what the agent will do"** — over-permissioned credentials, no visibility | Reddit r/sre, LinkedIn posts | **Policy-as-code (OPA)** and **immutable audit trails** are table stakes |
| 4 | **"Our CISO blocked AI agents entirely"** — no SSO, no audit, no compliance evidence | G2 enterprise reviews | SSO + audit log streaming + SOC 2 evidence must ship before enterprise sales |
| 5 | **"Hardcoded decisions don't scale"** — 47 deployment scripts, tribal knowledge | DEV.to, Medium | RAG over runbooks helps, but **agent memory** and **topology learning** need to work |
| 6 | **"Data leakage fear stops adoption"** — secrets in prompts, PII to public LLMs | TunedTools, Reddit | PII redactor exists; but **on-prem-only mode** and **Vault integration** are missing |
| 7 | **"Agents are great locally, terrible system-wide"** — no understanding of blast radius | Incident post-mortems | **Dependency graphs** and **blast-radius analysis** needed before destructive ops |
| 8 | **"Pipeline is flaky, I don't trust the signals"** — CI/CD unreliability | Reddit r/QualityAssurance (72% negative sentiment on CI) | Agent reliability monitoring, heartbeat with SLAs, cost tracking |
| 9 | **"Over-zealous safety guards block everything"** — binary allow/deny, no tiered autonomy | Autonomous SRE Experiment | 3-tier gate exists, but **autonomy maturity model** (Intern→Principal) needed |
| 10 | **"Shadow AI — agents deployed without approval"** — no inventory, no governance | IBM, Gravitee reports | **Agent registry + supply chain verification** needed |

---

## 2. Enterprise Requirements — Phased Roadmap

### Phase 0 — Foundation (Current)
- [x] In-cluster agent (zero-trust, outbound-only)
- [x] Closed action catalog (31 typed actions, schema-validated)
- [x] 3-tier safety gate (read/mutate/destructive + session approval memory)
- [x] PII redactor
- [x] Multi-LLM support (OpenAI, Anthropic, Ollama)
- [x] CLI + Web UI
- [x] API key auth (basic)

### Phase 1 — Identity & Access (Weeks 1–3)

| Requirement | Details | Priority |
|-------------|---------|----------|
| **SSO (SAML 2.0 + OIDC)** | Okta, Azure AD/Microsoft Entra, Google Workspace, OneLogin | P0 |
| **SCIM 2.0** | Automated user provisioning/deprovisioning; attribute mapping docs | P0 |
| **RBAC** | Admin, operator, viewer, auditor; action-level permissions; org-scoped | P0 |
| **Agent-level identity** | Every agent gets a cryptographic identity (JWT with short-lived creds, not shared API keys) | P0 |
| **MFA enforcement** | TOTP, WebAuthn; per-org policy | P1 |
| **Domain verification** | DNS TXT record to prove org ownership | P1 |

**Reddit pain point addressed:** *"No SSO? Our security team won't even evaluate it."*

### Phase 2 — Audit & Observability (Weeks 4–6)

| Requirement | Details | Priority |
|-------------|---------|----------|
| **Immutable audit trail** | Cryptographically chained (hash-linked) log of every: tool call, decision, approval, denial, policy change | P0 |
| **SIEM streaming** | Webhook + syslog export to Splunk, Datadog, Panther, Elastic, Microsoft Sentinel | P0 |
| **Distributed tracing** | OpenTelemetry instrumentation for every agent invocation; correlation IDs across orchestrator ↔ agent | P0 |
| **Cost tracking** | Per-session, per-user, per-org token consumption; budget alerts; anomaly detection on spend spikes | P1 |
| **Performance baselines** | Task completion time, error rate, latency; deviation-based alerting | P1 |
| **Heartbeat SLA** | Agent health check with 30-second granularity; auto-restart on missed heartbeats | P1 |

**Reddit pain point addressed:** *"Can you prove what your agent did at 3:14 AM Tuesday?"*

### Phase 3 — Governance & Policy (Weeks 7–10)

| Requirement | Details | Priority |
|-------------|---------|----------|
| **OPA policy engine** | Every tool call passes Rego policy before execution; policies stored in Git (GitOps) | P0 |
| **Policy categories** | Tool access (which agent can call which tool), argument constraints (SELECT-only, no DELETE), rate limits, data scope | P0 |
| **Content-aware guardrails** | Inspect prompt/tool arguments for PII/PHI/restricted data leakage | P0 |
| **Autonomy maturity model** | Intern (read-only) → Junior (suggest + HITL) → Senior (execute in guardrails) → Principal (autonomous domain) | P1 |
| **Approval flows** | Slack/MS Teams/email approval integration; configurable approver groups per action tier | P1 |
| **Policy review cadence** | Quarterly automated permission review; drift detection | P1 |

**Reddit pain point addressed:** *"I need to say 'agents can read pods but never delete namespaces' — without writing code."*

### Phase 4 — Deployment & Reliability (Weeks 11–14)

| Requirement | Details | Priority |
|-------------|---------|----------|
| **Helm charts** | Least-privilege RBAC (namespace-scoped ServiceAccount), NetworkPolicy (default-deny), PodSecurityPolicy, mTLS via Istio | P0 |
| **KEDA autoscaling** | Queue-depth-based HPA for agent workers; not CPU-based | P0 |
| **PostgreSQL checkpointing** | LangGraph state persistence across container restarts; SQLAlchemy migrations | P0 |
| **Multi-region failover** | Active-passive with automated DNS failover; RTO < 5 min, RPO < 1 min | P1 |
| **Backup/restore** | Automated backup of audit logs, agent state, session data; documented DR plan | P1 |
| **Circuit breakers** | LLM API rate-limit handling, cost cap enforcement, max iterations per task (hard cap of 10) | P1 |

**Reddit pain point addressed:** *"Agent crashed the orchestrator at 3 AM — no HA, no failover."*

### Phase 5 — Compliance & Certifications (Weeks 15–18)

| Requirement | Details | Priority |
|-------------|---------|----------|
| **SOC 2 Type II evidence** | Control mappings: access control, change management, data protection, availability | P0 |
| **EU AI Act compliance** | High-risk system documentation, risk classification, human oversight evidence, transparency reports | P0 |
| **Data Processing Agreement (DPA)** | Signed DPA template + subprocessors list (which LLM providers see user data) | P0 |
| **Data residency** | Configurable data storage region; agent can run fully on-prem with no egress | P0 |
| **Air-gapped support** | Zero internet dependency; local Ollama + local vector DB + local policy enforcement | P1 |
| **Penetration testing** | Annual independent pentest covering: prompt injection, privilege escalation, data exfiltration | P1 |
| **Buyer assurance brief** | Single PDF covering architecture, security controls, compliance mapping, SLA commitments | P1 |

**Reddit pain point addressed:** *"Our CISO said no agents in production until we have SOC 2 evidence."*

### Phase 6 — Multi-Tenant & Scale (Weeks 19–22)

| Requirement | Details | Priority |
|-------------|---------|----------|
| **Organization model** | Tenant-isolated data, audit logs, SSO config, RBAC policies per org | P0 |
| **Cross-tenant leak prevention** | Tenant ID in every metadata filter; integration test proving isolation | P0 |
| **API versioning** | Semantic versioning for REST/WebSocket APIs; deprecation policy (6-month migration window) | P1 |
| **Rate limiting** | Per-user, per-org, per-endpoint; configurable quotas | P1 |
| **Sandbox environments** | Test tenants with seeded data for enterprise evaluation | P1 |

**Reddit pain point addressed:** *"Multi-tenant? So my competitor can see my infra data? No thanks."*

---

## 3. Technical Architecture Changes

### 3.1 Agent Identity & Credential Chain

```
User (SSO/OIDC)
  → Orchestrator (validates JWT, scopes permissions via RBAC)
    → Agent (short-lived credential, cryptographically signed)
      → Tool call (OPA policy check → identity verified → execute)
        → Audit log (agent ID + user ID + action hash-chained)
```

**Current gap:** `verify_api_key` is a stub. Need full OIDC middleware.

### 3.2 Policy Enforcement Layer

```
User → Orchestrator
         → Intent classification
           → Agent selection
             → SAFETY GATE (tier check)
               → OPA POLICY (tool-level: which tools, what args, rate limits)
                 → EXECUTOR (sandboxed, timeout-enforced)
                   → AUDIT LOG (immutable, SIEM-streamed)
```

**New dependency:** Open Policy Agent (Rego) as embedded library or sidecar.

### 3.3 Immutable Audit Chain

```
block_1 = { event, timestamp, actor_hash, prev_hash: null, signature }
block_2 = { event, timestamp, actor_hash, prev_hash: sha256(block_1), signature }
block_3 = { event, timestamp, actor_hash, prev_hash: sha256(block_2), signature }
...
```

**Implementation:** Merkle-chain or rekor-style transparency log. SQLite for dev, PostgreSQL for prod.

### 3.4 Deployment Topology (Production)

```
                     ┌─────────────────┐
                     │   Load Balancer  │
                     │   (HAProxy/ALB)  │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
         │Orch v1  │    │Orch v2  │    │Orch v3  │
         │(us-east)│    │(us-west)│    │(eu-west)│
         └────┬────┘    └────┬────┘    └────┬────┘
              │              │              │
         ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
         │Postgres │    │Postgres │    │Postgres │
         │ (Sync)  │    │ (Async) │    │ (Async) │
         └─────────┘    └─────────┘    └─────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │  Agent (in-cluster, outbound-only) │
                    │  Connects to orchestrator          │
                    └─────────────────────────────────┘
```

---

## 4. Security Hardening Checklist

Based on OWASP Agentic Applications Top 10 (2025/2026), Five Eyes guidance, CSA AARM spec, and real-world incident patterns.

### 4.1 Pre-Production

- [ ] Every agent has a unique, cryptographically verifiable identity (not shared API keys)
- [ ] Short-lived credentials only (max 1 hour); rotated via Vault / External Secrets Operator
- [ ] OPA policy written and version-controlled for every tool category
- [ ] Penetration test completed: prompt injection, privilege escalation, data exfiltration, MCP server hijack
- [ ] Dependency scan: no known-vulnerable packages, no `:latest` images, signed attestations
- [ ] RBAC matrix documented: every role, its permissions, and default assignments

### 4.2 Runtime

- [ ] All tool calls pass through OPA policy check (not just at deployment time)
- [ ] Circuit breakers active: max 10 agent iterations per task, cost cap exceeded → halt
- [ ] Content-aware guardrails: tool arguments scanned for PII/secrets before reaching executor
- [ ] Memory lifecycle constraints: max 20K token context, auto-compaction; no unbounded data accumulation
- [ ] Agent tool execution sandboxed: no `shell=True`, no filesystem access, no network egress beyond allowlist
- [ ] mTLS enforced between all agent ↔ orchestrator, agent ↔ tool service communication

### 4.3 Post-Incident

- [ ] Immutable audit log exported to SIEM within 60 seconds
- [ ] Incident response playbook specific to AI-agent failures (not generic runbook)
- [ ] Post-mortem template includes: "was this a prompt injection, permission error, or hallucination?"
- [ ] Agent can be force-killed at the orchestrator level (kill switch for runaway agents)

---

## 5. Compliance Framework Mapping

| Regulation | TalkToInfra Requirement | Evidence Needed |
|------------|------------------------|-----------------|
| **EU AI Act** (High-risk, Aug 2026) | Risk classification, human oversight, transparency, record-keeping | Risk assessment doc, audit logs, approval gates |
| **SOC 2 Type II** | Access control, change management, data protection, availability | SSO logs, OPA policy history, backup tests, uptime SLAs |
| **ISO 27001** | Information security management system | ISMS doc, risk register, incident response plan |
| **HIPAA** | BAA, PHI redaction, access controls, audit controls | PII redactor test results, signed BAAs, access reviews |
| **GDPR** | Data residency, deletion workflows, DPA, subprocessors list | Data processing records, deletion API, DPA template |
| **NIST AI RMF** | AI risk management, testing, monitoring | Model cards, red-teaming reports, continuous monitoring dash |
| **Five Eyes guidance** (May 2026) | Agent identity, least-privilege, immutable audit, human oversight | Cryptographic identity impl, OPA policies, audit chain, HITL gates |

---

## 6. Procurement Artifacts to Create

Based on CoreLine's procurement-ready framework and real enterprise security reviews:

| Artifact | Purpose | Owner |
|----------|---------|-------|
| **Buyer assurance brief** (1-page PDF) | First call — architecture, security, compliance snapshot | Product + Security |
| **Security one-pager** | Control mapping (SOC 2 / ISO 27001 crosswalk) | Security |
| **Data flow diagram** | Every place user data enters/leaves the system | Engineering |
| **DPA + subprocessors list** | Legal requirement for GDPR/HIPAA procurement | Legal |
| **SSO setup guide** (per IdP) | Okta, Entra ID, Google Workspace — step by step | Engineering |
| **RBAC matrix** | Every role, permission, scope — downloadable spreadsheet | Engineering |
| **Audit logging spec** | Fields, retention, streaming format, access controls | Engineering |
| **SLO/SLA documentation** | Uptime, latency, error budget, support response times | Operations |
| **Penetration test report** | Annual, covering OWASP Agentic Top 10 | Security |
| **Incident response playbook** | Agent-specific IR procedures, not generic | Operations |

---

## 7. Effort Estimate

| Phase | Weeks | Engineering Focus | External Dependencies |
|-------|-------|-------------------|----------------------|
| P1: Identity & Access | 3 | OIDC middleware, RBAC, SCIM stubs | WorkOS / Auth0 / Logto for SSO |
| P2: Audit & Observability | 3 | Immutable audit chain, OTel instrumentation, SIEM export | OpenTelemetry SDK, SIEM vendor |
| P3: Governance & Policy | 4 | OPA integration, content guardrails, maturity model | OPA/Rego, content scanner |
| P4: Deployment & Reliability | 4 | Helm charts, KEDA, PostgreSQL, circuit breakers | Kubernetes, KEDA, Istio |
| P5: Compliance & Certifications | 4 | SOC 2 evidence prep, pentest, buyer artifacts | External auditor, pentest firm |
| P6: Multi-Tenant & Scale | 4 | Org isolation, API versioning, rate limiting | — |
| **Total** | **22** | | |

**Team recommendation:** 2–3 backend engineers (Python/K8s), 1 security engineer (part-time), 1 SRE (part-time) for Phases 1–4. Add 1 legal/compliance resource for Phase 5.

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Prompt injection** via tool arguments | High | Critical | OPA content guardrails, output validation, sandboxed execution |
| **Data exfiltration** via agent tool calls | Medium | Critical | Allowlist egress, PII redactor, content-aware guardrails, immutable audit |
| **Agent privilege escalation** | Medium | High | Cryptographic agent identity, short-lived credentials, quarterly permission review |
| **Cost explosion** from runaway agent | Medium | High | Circuit breakers, token budgets, cost anomaly alerts, hard cap on iterations |
| **Compliance failure** (EU AI Act, SOC 2) | Medium | High | Phase 5 evidence prep, external audit, buyer assurance brief |
| **Multi-tenant data leak** | Low | Critical | Tenant ID in every query, integration test proving isolation |
| **LLM hallucination** causes production outage | High | High | Closed action catalog (no free-form execution), schema validation, tiered HITL |

---

*Last updated: May 2026. Review quarterly as regulations and threat landscape evolve.*
