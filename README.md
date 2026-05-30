# TalkToInfra

**AI-native infrastructure copilot** — talk to your infrastructure in natural language.

Ask questions about your Kubernetes clusters, cloud resources, Active Directory, DNS, servers, and databases. Get answers instantly. Execute approved changes with safety gates.

```bash
# Start chatting
pip install talktoinfra
talktoinfra chat

# Ask a single question
talktoinfra ask "Are there any failing pods in production?"

# Check system status
talktoinfra status
```

## Quick Start

### 1. Start the orchestrator
```bash
docker compose up orchestrator
```

### 2. Deploy the agent in your cluster
```bash
kubectl apply -f deploy/agent.yaml
```

### 3. Start chatting
```bash
talktoinfra chat
```

## Examples

| You ask | TalkToInfra does |
|---------|-----------------|
| "Are there any failing pods?" | `kubectl get pods --all-namespaces` → analyzes status |
| "What's the IP of the DNS server?" | `nslookup` or DNS API query |
| "Find user jdoe in AD" | LDAP search → returns user details |
| "Check disk on web-server-01" | SSH → `df -h` → returns usage |
| "Show me all EC2 instances" | AWS API → returns instance list |
| "Restart the payment-service" | Requires approval → `kubectl rollout restart` |

## Architecture

```
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐
│  CLI / Web  │────▶│  Orchestrator  │────▶│  Infra Agent     │
│  (you)      │     │  (LLM + Safety)│     │  (in-cluster)    │
└─────────────┘     └────────────────┘     └──────────────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────┐
                    │   K8s API  │  AWS/Azure  │  DNS  │  AD  │  SSH  │
                    └────────────┴─────────────┴───────┴──────┴───────┘
```

## Safety

Three-tier permission system:
- **READ**: Auto-execute (safe by definition)
- **MUTATE**: Requires session-level human approval
- **DESTRUCTIVE**: Requires fresh human approval every time

## LLM Providers

- OpenAI (GPT-4o)
- Anthropic (Claude)
- Ollama (fully local, no data leaves your network)

## License

Apache 2.0
