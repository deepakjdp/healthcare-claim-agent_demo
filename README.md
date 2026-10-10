# 🏥 Agentic AI — Healthcare Claim Finalization

> An autonomous multi-agent AI pipeline that processes, validates, adjudicates, and finalises health insurance claims end-to-end — deployed via a Jenkins CI/CD pipeline onto Red Hat OpenShift.

---

## Table of Contents

- [Overview](#overview)
- [The Problem — Why Traditional Claim Processing Fails](#the-problem--why-traditional-claim-processing-fails)
- [Why Agentic AI?](#why-agentic-ai)
- [What Agentic AI Solves in This Application](#what-agentic-ai-solves-in-this-application)
- [How Agentic AI Works — Core Concepts](#how-agentic-ai-works--core-concepts)
- [Application Deep Dive](#application-deep-dive)
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

The US health insurance industry processes over **1.5 billion claims annually**. Despite this scale, most payers still rely on rule-engines and manual review queues that were designed in the 1990s. The result: slow payments, high administrative cost, rampant fraud, and frustrated patients and providers.

This project demonstrates how **Agentic AI** — a network of specialised autonomous AI agents — can fundamentally reimagine claim finalization. Each agent owns a single responsibility, reasons over domain knowledge, takes autonomous actions, and hands its result to the next agent — all without human intervention in the happy path.

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

## The Problem — Why Traditional Claim Processing Fails

### 1. Speed — Days, Not Seconds

Traditional claim adjudication involves a **serial hand-off chain** across multiple departments:

```
Claim Received → Data Entry → Eligibility Desk → Coding Review →
Fraud Unit → Adjudication Team → Payment Auth → EOB Mailing
```

Each hand-off can sit in a queue for hours or days. A simple office visit claim that should take seconds routinely takes **14–30 days** from submission to payment.

**Impact:**
- Providers wait months for reimbursement → cash flow pressure
- Members receive EOBs weeks after treatment → confusion and disputes
- Payers carry large accounts-payable balances → financial inefficiency

---

### 2. Accuracy — Errors Are Expensive

The human error rate in medical coding is estimated at **20–30%** of all claims. Common mistakes:

| Error Type | Example | Cost |
|---|---|---|
| Upcoding | Billing 99215 instead of 99213 | Overpayment + audit risk |
| Downcoding | Under-billing to avoid audits | Lost provider revenue |
| Unbundling | Billing separately what should be one code | Fraud / compliance violation |
| Wrong ICD-10 | Non-specific code used (Z00 instead of Z00.00) | Claim denial + rework |
| Duplicate claim | Same claim submitted twice | Duplicate payment |

Each denied claim costs a provider an average of **$25–$118** to rework and resubmit.

---

### 3. Fraud — A $100 Billion Problem

Healthcare fraud costs the US **$100 billion per year** (FBI estimate). Legacy rule-engines catch only the most obvious patterns. They cannot:

- Detect **subtle anomalies** in provider billing patterns over time
- Cross-reference claims against **multi-source watchlists** in real time
- Score **combinations of signals** (high billed + unusual codes + new provider)
- **Adapt** as fraudsters learn to stay just below rule thresholds

---

### 4. Compliance — HIPAA and CMS Complexity

Payers must simultaneously comply with:
- **HIPAA Privacy Rule** (§164.514) — PHI de-identification
- **HIPAA Security Rule** — safeguards for electronic PHI
- **CMS NPI Registry** — valid 10-digit National Provider Identifiers
- **ICD-10-CM** code sets (70,000+ codes, updated annually)
- **CPT** code sets (10,000+ codes, AMA-managed)
- **State-specific** prompt-payment laws (30–45 day windows)

Manual processes cannot consistently apply all these rules at scale.

---

### 5. Scalability — Volume Spikes Are Unpredictable

Claim volumes spike after:
- Natural disasters
- Flu seasons / pandemics
- Open enrollment periods
- Major policy changes

Static, monolithic adjudication systems have fixed capacity. When volume spikes, queues back up, SLAs are missed, and payers face regulatory penalties.

---

### The Status Quo — By the Numbers

| Metric | Industry Average (Manual) | Target with Agentic AI |
|---|---|---|
| Claim cycle time | 14–30 days | < 5 seconds |
| First-pass acceptance rate | 70–75% | > 95% |
| Cost per claim | $15–$25 | < $2 |
| Fraud detection rate | ~5% of fraudulent claims | > 40% flagged pre-payment |
| Compliance violation rate | ~15% of processed claims | < 1% |
| Scaling time under load | Hours (manual hire) | Seconds (HPA) |

---

## Why Agentic AI?

### What Is an AI Agent?

An AI agent is an autonomous software component that:

1. **Perceives** its environment (receives structured input)
2. **Reasons** using domain knowledge, rules, or a model
3. **Acts** — takes a decision, calls a tool, queries a system
4. **Reports** its result and transfers control to the next step

Unlike a simple function call, an agent can **adapt its behaviour** based on what it observes. It does not just execute a fixed rule — it applies judgment.

---

### Why NOT Traditional Approaches?

| Approach | Limitation |
|---|---|
| **Rule engines** (Drools, ILOG) | Cannot handle novel patterns; rules become unmanageable at scale (10,000+ rules in large payers) |
| **Monolithic adjudication systems** | Tightly coupled; a change to fraud logic requires a full system release |
| **RPA (Robotic Process Automation)** | Mimics human keystrokes; brittle to UI changes; no reasoning capability |
| **Single LLM call** | No specialisation; a single model trying to do eligibility + coding + fraud + compliance in one prompt is unreliable and untestable |
| **Microservices without orchestration** | Each service acts independently; no shared state; no coordinated decision pathway |

---

### Why Agentic AI IS the Right Fit

#### ✅ Separation of Concerns
Each agent is a **domain expert**. The `MedicalCodingAgent` only knows about ICD-10/CPT codes. The `FraudDetectionAgent` only knows about risk signals. This separation means each agent can be **tested, updated, and replaced independently**.

#### ✅ Composability
Agents are composed by the `OrchestratorAgent` into a pipeline. Adding a new check (e.g. a `DuplicateClaimAgent`) requires only inserting a new agent into the sequence — no changes to existing agents.

#### ✅ Explainability
Every agent records its action to an **immutable audit trail**. A compliance officer can see exactly which agent made which decision, at what time, and why — something opaque monoliths cannot provide.

#### ✅ Autonomous Adaptation
When the `FraudDetectionAgent` scores a claim as HIGH risk, it autonomously reroutes to `PENDING_REVIEW` without any human instruction. The system **self-routes** based on observed evidence.

#### ✅ Failure Isolation
If the `EligibilityAgent` fails (e.g. the coverage DB is down), only that stage fails. The orchestrator catches the error, records it, and routes the claim appropriately — it does not take down the entire system.

#### ✅ Scalability
Because each agent is a stateless function inside a containerised service, OpenShift's HPA can scale the entire pipeline horizontally under load — from 3 to 10 pods automatically — without any architectural changes.

---

## What Agentic AI Solves in This Application

| Problem (from above) | Agent That Solves It | How |
|---|---|---|
| **Slow manual hand-offs** | `OrchestratorAgent` | Sequences all 7 agents in < 1 second end-to-end |
| **ICD-10 / CPT coding errors** | `MedicalCodingAgent` | Validates every code against the full fee schedule before adjudication |
| **Eligibility disputes** | `EligibilityAgent` | Checks member coverage in real time before any work is done |
| **Pre-payment fraud** | `FraudDetectionAgent` | Scores 3 independent signals; routes HIGH risk before payment |
| **HIPAA / CMS violations** | `ComplianceAgent` | Enforces §164.514 and NPI format on every single claim |
| **Inaccurate payments** | `AdjudicationAgent` | Applies fee schedule + coinsurance formula deterministically |
| **No audit trail** | All agents | Every agent writes a timestamped entry to the claim's audit log |
| **Scalability spikes** | OpenShift HPA | Auto-scales pods from 3 → 10 within 60 seconds of CPU spike |
| **Slow compliance reporting** | `ClaimFinalizationAgent` | Publishes a `ClaimFinalized` event instantly to downstream systems |

---

## How Agentic AI Works — Core Concepts

### The Agent Contract

Every agent in this system implements the same interface:

```python
class SomeAgent:
    def run(self, claim: Claim) -> AgentResult:
        # 1. Observe: read what you need from the claim
        # 2. Reason:  apply domain logic
        # 3. Act:     mutate claim status / set denial reason / calculate amount
        # 4. Report:  return AgentResult(passed=True/False, payload={}, message="")
```

`AgentResult` is a simple value object:

```python
@dataclass
class AgentResult:
    agent_name: str   # which agent produced this
    passed: bool      # did this check pass?
    payload: Dict     # agent-specific output data
    message: str      # human-readable summary
```

This contract means every agent is independently unit-testable and the orchestrator does not need to know anything about what happens inside each agent.

---

### The Orchestrator Pattern

The `OrchestratorAgent` implements a **sequential pipeline with short-circuit evaluation**:

```python
for agent in [ingestion, eligibility, coding, fraud, compliance]:
    result = agent.run(claim)
    if not result.passed:
        return self._deny(claim)   # stop immediately

adjudication.run(claim)            # only reached if all checks passed
finalization.run(claim)            # final step: persist + notify
```

This is analogous to a **logical AND** across all checks — if any single check fails, the pipeline short-circuits. This prevents wasted computation and ensures a denied claim is never partially adjudicated.

---

### The Claim State Machine

The `Claim` object transitions through a defined set of states:

```
RECEIVED → VALIDATING → ADJUDICATING → APPROVED → FINALIZED
                │                          │
                └──────── DENIED ◄─────────┘
                               │
                          PENDING_REVIEW
```

State transitions are controlled exclusively by agents — no external code can set `claim.status` directly, ensuring the state machine is always consistent.

---

### The Audit Trail

Every agent calls `claim.add_audit(agent_name, action, detail)` before returning. The result is an immutable, append-only list of events on the claim object:

```json
[
  { "timestamp": "2024-07-15T10:00:01.123Z", "agent": "ClaimIngestionAgent",    "action": "INGESTED",          "detail": "Claim parsed and normalised" },
  { "timestamp": "2024-07-15T10:00:01.145Z", "agent": "EligibilityAgent",       "action": "ELIGIBILITY_CHECK", "detail": "Eligible=True" },
  { "timestamp": "2024-07-15T10:00:01.167Z", "agent": "MedicalCodingAgent",     "action": "CODE_VALIDATION",   "detail": "All codes valid" },
  { "timestamp": "2024-07-15T10:00:01.189Z", "agent": "FraudDetectionAgent",    "action": "FRAUD_SCORE",       "detail": "Score=0 Risk=LOW Flags=[]" },
  { "timestamp": "2024-07-15T10:00:01.201Z", "agent": "ComplianceAgent",        "action": "COMPLIANCE_CHECK",  "detail": "Passed" },
  { "timestamp": "2024-07-15T10:00:01.215Z", "agent": "AdjudicationAgent",      "action": "ADJUDICATED",       "detail": "Allowed=305.0 Approved=244.0 (80% coinsurance)" },
  { "timestamp": "2024-07-15T10:00:01.230Z", "agent": "ClaimFinalizationAgent", "action": "FINALIZED",         "detail": "Final status=FINALIZED Approved=$244.00" }
]
```

This trail is **the complete decision log** — fully explainable, auditable, and exportable to a compliance data warehouse.

---

## Application Deep Dive

### Domain Model

The application is built around two core dataclasses defined in [`agents/claim_orchestrator.py`](agents/claim_orchestrator.py):

#### `Claim`

The central domain object that flows through the entire pipeline. Every agent reads from and writes to this object.

```python
@dataclass
class Claim:
    claim_id:        str            # unique identifier (UUID or payer-assigned)
    member_id:       str            # insured member
    provider_npi:    str            # 10-digit National Provider Identifier
    service_date:    str            # ISO-8601 date of service
    diagnosis_codes: List[str]      # ICD-10-CM codes (1 primary + optional secondary)
    procedure_codes: List[str]      # CPT / HCPCS codes
    billed_amount:   float          # total amount billed by provider (USD)
    status:          ClaimStatus    # current pipeline state (enum)
    approved_amount: float          # calculated by AdjudicationAgent
    denial_reason:   Optional[str]  # set by first failing agent
    audit_trail:     List[Dict]     # append-only event log
```

#### `ClaimStatus` Enum

```python
class ClaimStatus(str, Enum):
    RECEIVED     = "RECEIVED"       # initial state on creation
    VALIDATING   = "VALIDATING"     # intermediate (reserved)
    ADJUDICATING = "ADJUDICATING"   # set by AdjudicationAgent on entry
    APPROVED     = "APPROVED"       # set by AdjudicationAgent on success
    DENIED       = "DENIED"         # set by any failing agent
    PENDING      = "PENDING_REVIEW" # set by FraudDetectionAgent on HIGH score
    FINALIZED    = "FINALIZED"      # terminal success state
```

#### `AgentResult`

A lightweight value object returned by every agent `run()` method:

```python
@dataclass
class AgentResult:
    agent_name: str        # e.g. "FraudDetectionAgent"
    passed:     bool       # False = pipeline should short-circuit
    payload:    Dict       # agent-specific data (scores, amounts, flags)
    message:    str        # human-readable outcome summary
```

---

### Fee Schedule & Adjudication Logic

The `AdjudicationAgent` uses a simplified fee schedule. In production this would be loaded from a database or external pricing API:

| CPT Code | Description | Allowed Amount |
|---|---|---|
| `99213` | Office visit — low complexity | $150.00 |
| `99214` | Office visit — moderate complexity | $210.00 |
| `99215` | Office visit — high complexity | $280.00 |
| `93000` | ECG with interpretation | $95.00 |
| `71046` | Chest X-ray (2 views) | $320.00 |

**Payment formula:**
```
allowed_amount  = Σ fee_schedule[cpt_code]   for each procedure code
approved_amount = allowed_amount × coinsurance_rate   (default: 0.80)
member_liability = allowed_amount × (1 - coinsurance_rate)   (default: 0.20)
```

**Example** — claim with `99214` + `93000`:
```
allowed_amount  = $210.00 + $95.00 = $305.00
approved_amount = $305.00 × 0.80  = $244.00   ← payer pays this
member_liability = $305.00 × 0.20  =  $61.00  ← member pays this
```

---

### Fraud Scoring Model

The `FraudDetectionAgent` uses a **weighted signal scoring model**:

```
fraud_score = 0

if billed_amount > $10,000:      score += 40
if len(procedure_codes) > 5:     score += 20
if provider_npi in watchlist:    score += 50

risk_level = LOW    (score  < 30)
           = MEDIUM (score 30–59)  → continue, flag for post-pay review
           = HIGH   (score ≥ 60)   → PENDING_REVIEW, stop pipeline
```

The model is intentionally simple in this demo. A production implementation would integrate with a machine learning model trained on historical claims, incorporating:
- Provider billing pattern deviation (Z-score vs. peer group)
- Member utilisation outliers
- Geographic anomalies
- Time-of-day / day-of-week signal
- Network / out-of-network mismatches

---

### REST API Layer

The [`agents/api.py`](agents/api.py) file wraps the orchestrator in a **FastAPI** application. FastAPI was chosen because:

- **Automatic OpenAPI docs** at `/docs` (Swagger UI) — useful for provider portals and integration testing
- **Pydantic validation** — request body is validated before it ever reaches the agent pipeline
- **Async-ready** — can be extended to async agents using `async def run()` with `await`
- **Lightweight** — minimal overhead; Uvicorn ASGI server handles thousands of concurrent requests

The three endpoints:

```
GET  /health                  → liveness probe (used by OpenShift readiness check)
POST /claims/process          → full agentic pipeline
GET  /claims/{claim_id}/status → persistence layer query
```

---

### Why Python 3.12?

| Feature | Benefit in This Codebase |
|---|---|
| `@dataclass` | Clean domain models (`Claim`, `AgentResult`) with no boilerplate |
| Type hints | Every agent `run()` is fully typed → better IDE support + static analysis |
| `Enum` (str) | `ClaimStatus` values serialise to JSON strings automatically |
| f-strings | Readable log messages in each agent |
| `match` statement (3.10+) | Available for future agent routing logic |
| Speed improvements (3.12) | ~5% interpreter speed improvement over 3.11 |

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
