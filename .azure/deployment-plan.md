# ExpertTwin Azure Deployment Plan

> **Status:** Deployed

Generated: 2026-09-20T18:07:06+05:30

---

## 1. Project Overview

**Goal:** Deploy evidence-backed expert discovery and the expanded nine-project synthetic
engineering portfolio for all 11 authorized AI Clones.

**Path:** Modify existing deployment

No Azure services will be created, deleted, resized, or exposed differently.

## 2. Requirements

| Attribute | Value |
|-----------|-------|
| Classification | Hackathon POC |
| Scale | Small; 0-1 Container App replicas |
| Budget | Cost-optimized; no SKU changes |
| Subscription | Visual Studio Enterprise Subscription (`c38f5047-f2db-4ed4-a415-c7eca00acbbe`) — confirmed |
| Location | East US — confirmed |

## 3. Components Detected

| Component | Type | Technology | Path |
|-----------|------|------------|------|
| ExpertTwin | Web UI and API | Python 3.11, FastAPI, HTML/CSS/JS | `src/experttwin` |
| Synthetic portfolio | Seed data | JSON, TXT, Markdown, DOCX, WAV | `demo-data/role-simulations` |
| Container image | Packaging | Docker | `Dockerfile` |
| Azure infrastructure | Existing IaC | Subscription-scoped Bicep | `infra` |

## 4. Recipe Selection

**Selected:** Bicep plus Azure Container Registry remote build

**Rationale:** The application already uses validated Bicep and an existing Container
Apps/ACR deployment. The update requires one immutable image, a Bicep what-if, and an
in-place Container App revision update.

## 5. Architecture

**Stack:** Existing Azure Container Apps Consumption deployment

| Component | Existing Azure Service | SKU/configuration |
|-----------|------------------------|-------------------|
| ExpertTwin | `ca-experttwin-dev-4449` | 0.5 vCPU, 1 GiB, 0-1 replicas |
| Container environment | `cae-experttwin-dev-4449` | Consumption |
| Image | `crexperttwindev4449` | ACR Basic |
| AI | `experttwin-hackathon-2026` | Existing Azure OpenAI deployment |
| Telemetry | Application Insights + Log Analytics | Existing workspace-based monitoring |
| Identity | System-assigned managed identity | Existing ACR and Azure OpenAI RBAC |

## 6. Provisioning Limit Checklist

This is an update-only deployment. It creates zero resources and does not change
replica, CPU, memory, or SKU limits.

| Resource type | Number to deploy | Total after deployment | Limit/quota | Notes |
|---------------|------------------|------------------------|-------------|-------|
| `Microsoft.App/managedEnvironments` | 0 | 1 | Not consumed by update | Existing environment is `Succeeded` |
| `Microsoft.App/containerApps` | 0 | 1 | Not consumed by revision | Existing app; max replicas remains 1 |
| `Microsoft.ContainerRegistry/registries` | 0 | 1 | Not consumed by image build | Existing Basic registry |
| Other supporting resources | 0 | 5 | Not consumed by update | Existing Key Vault, monitoring, and alerts |

**Status:** All update requirements are within limits; no quota increase is requested.

## 7. Execution Checklist

### Phase 1: Planning

- [x] Analyze workspace
- [x] Gather requirements
- [x] Confirm subscription and location with user
- [x] Prepare update-only resource inventory
- [x] Confirm zero additional quota consumption
- [x] Scan codebase
- [x] Select Bicep recipe
- [x] Preserve existing architecture
- [x] User approved this plan

### Phase 2: Execution

- [x] Retain existing infrastructure and managed identity
- [x] Verify application behavior locally
- [x] Select immutable image tag `experttwin:expert-finder-051a73e`
- [x] Compile existing Bicep successfully
- [x] Mark plan `Ready for Validation`

### Phase 3: Validation

- [x] Invoke azure-validate
- [x] All validation checks pass
  - [x] Core Bicep validation: CLI, authentication, build, ARM validation, and what-if
  - [x] Bicep linting
  - [x] Azure Policy validation
  - [x] Static managed-identity role assignment verification
- [x] Record validation proof
- [x] Set status to `Validated`

### Phase 4: Deployment

- [x] Invoke azure-deploy
- [x] Build image in existing ACR
- [x] Update existing Container App revision
- [x] Verify health, Expert Finder ranking, portfolio counts, and UI assets
- [x] Confirm existing RBAC assignments
- [x] Set status to `Deployed`

## 8. Functional Verification

- **Status:** Verified locally
- **Backend:** Full 35-test suite passed
- **UI:** Expert Finder HTML, CSS, JavaScript syntax, API, and accessibility tests passed
- **Data:** Portfolio seeding verified as idempotent with 484 sources and 132 decisions

## 9. Validation Proof

| Check | Command run | Result | Timestamp |
|-------|-------------|--------|-----------|
| Full application suite | `python -m pytest -q` | Pass: 35 tests | 2026-09-20T18:10:17+05:30 |
| Python build | `python -m compileall -q src scripts/build_capability_portfolio.py` | Pass | 2026-09-20T18:10:17+05:30 |
| Lint | `ruff check` on changed Python and tests | Pass | 2026-09-20T18:10:17+05:30 |
| JavaScript syntax | `node --check src/experttwin/static/app.js` | Pass | 2026-09-20T18:10:17+05:30 |
| Bicep core validation | `validate-deployment.ps1 -Scope sub -Location eastus -Subscription c38f5047-f2db-4ed4-a415-c7eca00acbbe` | Pass: CLI, auth, compile, ARM validation, and what-if | 2026-09-20T18:10:17+05:30 |
| Resource-level what-if review | `az deployment sub what-if ... --result-format ResourceIdOnly --no-pretty-print` | Pass: zero resource deletions; 8 deploy updates and 3 known unsupported RBAC analyses | 2026-09-20T18:10:17+05:30 |
| Bicep lint | `az bicep lint --file infra/main.bicep` | Pass with known non-blocking API type warnings | 2026-09-20T18:10:17+05:30 |
| Azure Policy | `az policy assignment list`; `az policy state list --resource <container-app-id>` | Pass: one assignment; zero Container App noncompliant states | 2026-09-20T18:10:17+05:30 |
| Static RBAC | Confirmed no changes to role assignment modules | Pass: resource-scoped AcrPull, Key Vault Secrets User, Cognitive Services OpenAI User | 2026-09-20T18:10:17+05:30 |

**Validated by:** azure-validate workflow

## 10. Files

| File | Purpose | Status |
|------|---------|--------|
| `.azure/deployment-plan.md` | Deployment source of truth | Complete |
| `Dockerfile` | Image build | Complete |
| `infra/main.bicep` and modules | Existing infrastructure | Complete |
| `infra/main.parameters.json` | Existing environment parameters | Complete |

## 11. Rollback

If health or data verification fails, reactivate the current healthy Container App
revision `ca-experttwin-dev-4449--0000010`. No data migration or destructive operation
is part of this deployment.

## 12. Deployment Verification

| Check | Result |
|-------|--------|
| ACR build | `cab` succeeded; digest `sha256:9f2f60f70eaef2aa5e1795e1b81cbb41fd3648f35c2953aa2c5c4fcfd5d0e4c4` |
| Container revision | `ca-experttwin-dev-4449--0000011` is healthy and receives 100% traffic |
| Health | `/health` returned `ok` in `azure-openai` mode |
| UI | `expert-finder-ui-20260920-1` assets, finder tab, nine project filters, and match routing are live |
| Roster and portfolio | 11 AI Clones, 9 projects, 484 sources, and 132 decisions |
| Expert Finder | Five domain queries returned ranked matches with three attributable citations each |
| Rich evidence | Verified 44 sources and 12 decisions for one profile, including review comments and transcript turns |
| ACR role | `AcrPull` confirmed at registry scope |
| Key Vault role | `Key Vault Secrets User` confirmed at vault scope |
| Azure OpenAI role | `Cognitive Services OpenAI User` confirmed at account scope |
