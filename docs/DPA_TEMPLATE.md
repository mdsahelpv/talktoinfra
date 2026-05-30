# Data Processing Agreement (DPA) Template

## 1. Parties

- **Data Controller**: [Customer Name] ("Controller")
- **Data Processor**: TalkToInfra ("Processor")

## 2. Data Processing Details

### 2.1 Categories of Data Processed
- Infrastructure configuration data (server names, IP addresses, DNS records)
- User account information (names, email addresses, roles)
- Session logs and LLM conversation history
- Audit trail metadata

### 2.2 Purposes of Processing
- AI-powered infrastructure management and automation
- Session continuity and context retention
- Audit and compliance logging
- Service improvement and troubleshooting

### 2.3 Retention Periods
- Session data: 90 days (configurable)
- Audit logs: 7 years (immutable, Merkle-chained)
- User accounts: Duration of subscription + 30 days

## 3. Subprocessors

| Subprocessor | Service | Location | Data Accessed |
|---|---|---|---|
| OpenAI | LLM provider (optional) | USA | Prompt text, tool call parameters |
| Anthropic | LLM provider (optional) | USA | Prompt text, tool call parameters |
| Ollama | Local LLM (optional) | Customer-specified | None (on-premises) |

## 4. Security Measures

### 4.1 Technical Measures
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Immutable Merkle-chain audit log
- RBAC with 4 predefined roles
- TOTP-based MFA
- API key authentication
- JWT-based agent identity
- Rate limiting and circuit breakers

### 4.2 Organizational Measures
- Regular security training
- Access control policies
- Incident response plan
- Annual SOC 2 Type II audit
- Penetration testing (quarterly)

## 5. Data Subject Rights

TalkToInfra will assist the Controller in fulfilling data subject requests:
- **Right of Access**: Export user data via API
- **Right to Rectification**: Update user profiles via SCIM
- **Right to Erasure**: Delete user data via SCIM or admin API
- **Right to Portability**: JSON export of all user data

## 6. Breach Notification

- **Notification timeline**: Within 72 hours of confirmed breach
- **Method**: Email to designated security contacts
- **Contents**: Nature of breach, categories affected, mitigation steps

## 7. Governing Law

This DPA shall be governed by the laws of [Jurisdiction].

## 8. Signatures

```
_________________________          _________________________
Controller                        Processor
Date: _______________             Date: _______________
```

---

*This is a template. Consult legal counsel before finalizing.*
