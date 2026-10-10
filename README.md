# 🏥 Agentic AI — Healthcare Claim Finalization

> An autonomous multi-agent AI pipeline that processes, validates, adjudicates, and finalises health insurance claims end-to-end — deployed via a Jenkins CI/CD pipeline onto Red Hat OpenShift.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Agents](#agents)
- [Data Flow](#data-flow)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Running Tests](#running-tests)
- [Docker Build](#docker-build)
- [Jenkins CI/CD Pipeline](#jenkins-cicd-pipeline)
- [OpenShift Deployment](#openshift-deployment)
- [API Reference](#api-reference)
- [Security & HIPAA Compliance](#security--hipaa-compliance)
- [Configuration](#configuration)
- [Contributing](#contributing)

---

## Overview

Traditional claim processing relies on manual workflows that take days or weeks and are prone to coding errors, fraud, and compliance violations. This project demonstrates how **Agentic AI** — a network of specialised autonomous agents — can reduce claim cycle time from days to **seconds** while improving accuracy, auditability, and regulatory compliance.

### Key Capabilities

| Capability | Detail |
|---|---|
| **Autonomous processing** | 8 agents chain end-to-end without human intervention |
| **Short-circuit on failure** | Pipeline halts immediately on denial conditions |
| **Immutable audit trail** | Every agent action recorded with UTC timestamp |
| **HIPAA-aware** | PHI never logged; compliance checks built into pipeline |
| **Auto-scaling** | OpenShift HPA scales pods 3 → 10 on CPU/memory pressure |
| **Zero-downtime deploys** | Rolling updates with PodDisruptionBudget guarantee |

---

## Architecture

```
                        ┌──────────────────────────────────────────┐
                        │         OrchestratorAgent                │
                        │  (coordinates agents, manages audit log) │
                        └────────────────┬─────────────────────────┘
                                         │
          ┌──────────┬──────────┬────────┼────────┬──────────┬──────────┐
          ▼          ▼          ▼        ▼        ▼          ▼          ▼
     Ingestion  Eligibility  Coding  Fraud   Compliance  Adjudication  Finalize
      Agent      Agent       Agent   Agent    Agent        Agent        Agent
          │          │          │        │        │          │          │
     Parse &    Member      ICD-10   Score &   HIPAA /   Fee Schedule  Persist +
     Normalise  Coverage    CPT/HCPCS Watchlist  CMS NPI  Coinsurance  Notify EOB
```

### Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API Framework | FastAPI + Uvicorn |
| Containerisation | Docker (multi-stage) |
| CI/CD | Jenkins Declarative Pipeline |
| Container Platform | Red Hat OpenShift 4.x |
| Code Quality | SonarQube, flake8 |
| Security Scanning | Bandit (SAST), Safety (CVE), Trivy (image) |
| Test Framework | pytest + pytest-cov |

---

## Agents

### 1. `ClaimIngestionAgent`
Parses and normalises the raw claim JSON. Validates all required fields are present and converts types (e.g. `billed_amount` → `float`). Returns a typed `Claim` dataclass.

### 2. `EligibilityAgent`
Checks the `member_id` against the payer's coverage database. Denies the claim immediately if the member is not found or coverage has lapsed.

### 3. `MedicalCodingAgent`
Validates:
- **ICD-10** diagnosis codes (e.g. `I10`, `E11.9`, `Z00.00`)
- **CPT / HCPCS** procedure codes (e.g. `99213`, `99214`, `71046`)

Returns invalid codes in the denial payload so the provider can correct and resubmit.

### 4. `FraudDetectionAgent`
Scores the claim on three signals:

| Signal | Points |
|---|---|
| Billed amount > $10,000 | +40 |
| Procedure code count > 5 | +20 |
| Provider NPI on watchlist | +50 |

- Score **< 30** → LOW risk → continue
- Score **30–59** → MEDIUM risk → continue with flag
- Score **≥ 60** → HIGH risk → route to `PENDING_REVIEW` (SIU queue)

### 5. `ComplianceAgent`
Enforces:
- **HIPAA §164.514** — member identifier must be present
- **CMS NPI format** — must be exactly 10 digits

### 6. `AdjudicationAgent`
Applies the payer fee schedule per CPT code and calculates the approved payment:

```
approved_amount = sum(fee_schedule[cpt]) × coinsurance_rate (default 80%)
```

### 7. `ClaimFinalizationAgent`
- Persists the final claim record (DB write in production)
- Publishes a `ClaimFinalized` event to the message broker
- Triggers EOB (Explanation of Benefits) generation for the member

### 8. `OrchestratorAgent`
Sequences all agents and manages three exit paths:

| Path | Trigger | Final Status |
|---|---|---|
| Happy path | All checks pass | `FINALIZED` |
| Denial | Any hard-stop check fails | `DENIED` |
| Pending | High fraud score | `PENDING_REVIEW` |

---

## Data Flow

```
Raw Claim JSON
      │
      ▼
[1] ClaimIngestionAgent     → validate & normalise
      │
      ▼
[2] EligibilityAgent        → member active? ──(NO)──► DENIED
      │
      ▼
[3] MedicalCodingAgent      → codes valid?   ──(NO)──► DENIED
      │
      ▼
[4] FraudDetectionAgent     → risk score     ──(HIGH)─► PENDING_REVIEW
      │
      ▼
[5] ComplianceAgent         → HIPAA / CMS    ──(FAIL)─► DENIED
      │
      ▼
[6] AdjudicationAgent       → calculate payment
      │
      ▼
[7] ClaimFinalizationAgent  → persist + notify
      │
      ▼
   FINALIZED ✅
```

### Sample Input / Output

**Input:**
```json
{
  "claim_id": "CLM-2024-00123",
  "member_id": "M001",
  "provider_npi": "1234567890",
  "service_date": "2024-07-15",
  "diagnosis_codes": ["I10", "E11.9"],
  "procedure_codes": ["99214", "93000"],
  "billed_amount": 450.00
}
```

**Output:**
```json
{
  "claim_id": "CLM-2024-00123",
  "member_id": "M001",
  "status": "FINALIZED",
  "approved_amount": 244.00,
  "audit_trail": [
    { "timestamp": "2024-07-15T10:00:01Z", "agent": "ClaimIngestionAgent",   "action": "INGESTED" },
    { "timestamp": "2024-07-15T10:00:01Z", "agent": "EligibilityAgent",      "action": "ELIGIBILITY_CHECK" },
    { "timestamp": "2024-07-15T10:00:01Z", "agent": "MedicalCodingAgent",    "action": "CODE_VALIDATION" },
    { "timestamp": "2024-07-15T10:00:01Z", "agent": "FraudDetectionAgent",   "action": "FRAUD_SCORE" },
    { "timestamp": "2024-07-15T10:00:01Z", "agent": "ComplianceAgent",       "action": "COMPLIANCE_CHECK" },
    { "timestamp": "2024-07-15T10:00:02Z", "agent": "AdjudicationAgent",     "action": "ADJUDICATED" },
    { "timestamp": "2024-07-15T10:00:02Z", "agent": "ClaimFinalizationAgent","action": "FINALIZED" }
  ]
}
```

---

## Project Structure

```
healthcare-claim-agent/
├── agents/
│   ├── claim_orchestrator.py   # 8 agents + domain models (Claim, AgentResult)
│   └── api.py                  # FastAPI REST wrapper
├── tests/
│   └── test_claim_pipeline.py  # pytest unit tests (≥80% coverage enforced)
├── openshift/
│   ├── 00-namespace.yaml       # OpenShift project
│   ├── 01-rbac.yaml            # ServiceAccount + Role/RoleBinding
│   ├── 02-configmap-secret.yaml# App config & credentials
│   ├── 03-deployment.yaml      # Pod spec: probes, anti-affinity, SCC
│   ├── 04-service-route.yaml   # ClusterIP Service + HTTPS Route
│   └── 05-hpa-pdb.yaml         # HPA (3→10 pods) + PodDisruptionBudget
├── Dockerfile                  # Multi-stage, non-root UID 1001, OCP-ready
├── Jenkinsfile                 # 13-stage declarative pipeline
├── requirements.txt
└── README.md
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | ≥ 3.12 | Runtime |
| pip | latest | Package management |
| Docker | ≥ 24.x | Container build |
| Jenkins | ≥ 2.440 | CI/CD |
| OpenShift CLI (`oc`) | ≥ 4.14 | OCP deployment |
| Trivy | latest | Image scanning |
| SonarQube | ≥ 10.x | Code quality |

---

## Local Development

```bash
# 1. Clone the repository
git clone https://github.com/your-org/healthcare-claim-agent.git
cd healthcare-claim-agent

# 2. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov flake8 bandit

# 4. Run the orchestrator directly (uses the built-in sample claim)
python agents/claim_orchestrator.py

# 5. Start the FastAPI server
uvicorn agents.api:app --reload --port 8080

# 6. Open the interactive API docs
open http://localhost:8080/docs
```

---

## Running Tests

```bash
# Run all tests with coverage report
pytest tests/ -v --cov=agents --cov-report=term-missing

# Run a specific test
pytest tests/test_claim_pipeline.py::test_valid_claim_finalizes -v

# Enforce 80% coverage gate (used in Jenkins)
pytest tests/ --cov=agents --cov-fail-under=80
```

### Test Cases

| Test | Scenario | Expected |
|---|---|---|
| `test_valid_claim_finalizes` | All checks pass | `FINALIZED` |
| `test_ineligible_member_denied` | Unknown member ID | `DENIED` |
| `test_invalid_icd10_denied` | Bad diagnosis code | `DENIED` |
| `test_high_fraud_score_pending` | Provider on watchlist | `PENDING_REVIEW` |
| `test_missing_field_returns_error` | Incomplete payload | `error` key present |
| `test_approved_amount_is_80_percent` | 99214 = $210 × 80% | `$168.00` |

---

## Docker Build

```bash
# Build the image
docker build -t claim-finalization-agent:latest .

# Run locally
docker run -p 8080:8080 claim-finalization-agent:latest

# Scan for vulnerabilities
trivy image --severity HIGH,CRITICAL claim-finalization-agent:latest
```

> The image runs as **non-root UID 1001** with a **read-only filesystem** and all Linux capabilities dropped — compatible with OpenShift's `restricted` SCC.

---

## Jenkins CI/CD Pipeline

The [`Jenkinsfile`](Jenkinsfile) defines a **13-stage declarative pipeline**:

```
 Stage        │ Tool          │ Gate
──────────────┼───────────────┼──────────────────────────────────
 Checkout     │ git           │ —
 Setup Env    │ pip/venv      │ —
 Lint         │ flake8        │ Max line length 120
 Unit Tests   │ pytest-cov    │ ❌ fails if coverage < 80%
 SAST         │ Bandit        │ JSON report archived
 CVE Scan     │ Safety        │ checks requirements.txt
 SonarQube    │ sonar-scanner │ Project analysis
 Quality Gate │ SonarQube     │ ❌ blocks on gate failure
 Build Image  │ Docker        │ Multi-stage, labelled
 Image Scan   │ Trivy         │ HIGH/CRITICAL CVE report
 Push Image   │ Docker push   │ Only on main / release/*
 Deploy OCP   │ oc CLI        │ Rolling update + rollout wait
 Smoke Test   │ curl          │ ❌ fails if claim ≠ FINALIZED
```

### Required Jenkins Credentials

| Credential ID | Type | Used For |
|---|---|---|
| `registry-credentials` | Username/Password | Docker registry push |
| `openshift-sa-token` | Secret text | `oc login` to OCP cluster |
| `sonarqube-token` | Secret text | SonarQube analysis |

### Notifications

- ✅ **Success** → Slack `#claim-agent-deployments` (green)
- ❌ **Failure** → Slack + email to `platform-team@example.com` (red)

---

## OpenShift Deployment

### Apply All Manifests

```bash
# Login to your cluster
oc login https://api.ocp.example.com:6443 --token=<SA_TOKEN>

# Create the project
oc apply -f openshift/00-namespace.yaml

# Apply all manifests in order
oc apply -f openshift/

# Watch rollout
oc rollout status deployment/claim-finalization-agent -n healthcare-prod

# Get the public route URL
oc get route claim-finalization-agent -n healthcare-prod
```

### Manifests Overview

| File | Resource | Key Settings |
|---|---|---|
| `00-namespace.yaml` | Namespace | `healthcare-prod` |
| `01-rbac.yaml` | ServiceAccount + Role | Read-only on ConfigMaps/Secrets |
| `02-configmap-secret.yaml` | ConfigMap + Secret | App config; Vault-referenced passwords |
| `03-deployment.yaml` | Deployment | 3 replicas, UID 1001, readOnly FS, liveness/readiness/startup probes |
| `04-service-route.yaml` | Service + Route | ClusterIP; edge TLS termination; HTTPS redirect |
| `05-hpa-pdb.yaml` | HPA + PDB | Scale 3→10 on CPU>60% or Mem>70%; minAvailable: 2 |

### Verify Deployment

```bash
# Check pods are running
oc get pods -n healthcare-prod -l app=claim-finalization-agent

# Health check
curl -sf https://claim-agent.apps.ocp.example.com/health

# Submit a test claim
curl -X POST https://claim-agent.apps.ocp.example.com/claims/process \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "TEST-001",
    "member_id": "M001",
    "provider_npi": "1234567890",
    "service_date": "2024-01-01",
    "diagnosis_codes": ["I10"],
    "procedure_codes": ["99214"],
    "billed_amount": 210.0
  }'
```

---

## API Reference

### `GET /health`
Returns service liveness status.

```json
{ "status": "ok", "service": "claim-finalization-agent" }
```

### `POST /claims/process`
Submits a claim through the full agentic pipeline.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `claim_id` | string | ✅ | Unique claim identifier |
| `member_id` | string | ✅ | Payer member ID |
| `provider_npi` | string | ✅ | 10-digit NPI |
| `service_date` | string | ✅ | `YYYY-MM-DD` |
| `diagnosis_codes` | string[] | ✅ | ICD-10 codes |
| `procedure_codes` | string[] | ✅ | CPT / HCPCS codes |
| `billed_amount` | float | ✅ | Total billed in USD |

**Response statuses:**

| HTTP | Claim Status | Meaning |
|---|---|---|
| 200 | `FINALIZED` | Approved and payment calculated |
| 200 | `DENIED` | Failed a validation check |
| 200 | `PENDING_REVIEW` | High fraud risk — manual review queue |
| 422 | — | Missing required field |

### `GET /claims/{claim_id}/status`
Queries the persistence layer for a live claim status (production: backed by database).

---

## Security & HIPAA Compliance

| Control | Implementation |
|---|---|
| **PHI protection** | No PII/PHI in logs; only identifiers in audit trail |
| **Encryption in transit** | TLS 1.3 via OpenShift edge Route |
| **Encryption at rest** | AES-256 on DB volumes and PersistentVolumes |
| **Secrets management** | Kubernetes Secrets with Vault injection; never in source |
| **Least-privilege RBAC** | ServiceAccount can only read ConfigMaps/Secrets |
| **Non-root container** | UID 1001, `runAsNonRoot: true` |
| **Read-only filesystem** | `readOnlyRootFilesystem: true`; `/tmp` via emptyDir |
| **Capabilities** | `drop: [ALL]`; no privilege escalation |
| **Image provenance** | Trivy scans at build time; digest-pinned in prod |
| **Audit trail** | Immutable per-claim log: agent, action, UTC timestamp |

---

## Configuration

All configuration is injected via environment variables (from `ConfigMap` / `Secret`):

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `production` | Deployment environment |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `COINSURANCE_RATE` | `0.80` | Plan pays this fraction (0–1) |
| `FRAUD_THRESHOLD` | `60` | Score above which claim is PENDING |
| `MAX_BILLED_AMOUNT` | `50000` | Hard ceiling on billed amount |
| `DB_CONNECTION_STRING` | — | PostgreSQL connection string (Secret) |
| `BROKER_URL` | — | AMQP message broker URL (Secret) |

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/my-change`
2. Make your changes and ensure all tests pass: `pytest tests/ --cov=agents --cov-fail-under=80`
3. Run the linter: `flake8 agents/ --max-line-length=120`
4. Open a Pull Request against `main` — the Jenkins pipeline will run automatically

---

*Built with ❤️ using Agentic AI principles for autonomous healthcare operations.*
