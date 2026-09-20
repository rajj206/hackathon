# ExpertTwin

ExpertTwin is a local-first hackathon MVP that preserves **engineering decision
judgment** from supplied documents and meeting history. It extracts auditable decision
records, derives an Engineering Decision Fingerprint, retrieves relevant evidence, and
answers questions with citations and explicit uncertainty.

The authorized roster demo is always labeled **SYNTHETIC ROLE-BASED SIMULATION — NOT
BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.** Synthetic statements are
fictional role-archetype evidence, not real behavior or unsupported impersonation.

## What works

- Create and select experts in a lightweight web app.
- Upload TXT, Markdown, PDF, DOCX, and PPTX documents.
- Parse bracketed named-speaker TXT chat/meeting transcripts into attributed turns,
  preserving timestamp, optional role, and multiline continuation text.
- Preserve DOCX body text and ingest only Word review comments authored by the selected
  expert (case-insensitive), with comment ID, date, and anchor/nearby text when available.
- Resolve threaded Word replies through `commentsExtended.xml`, retaining the parent
  reviewer/comment as context without treating it as the selected expert's own judgment.
- Upload TXT meeting transcripts as normal evidence.
- Upload audio/video through an explicit transcription provider.
- Extract structured decisions with expert, choice, alternatives, rationale, constraints,
  risks, outcome, source evidence/location, timestamp, tags, and confidence.
- Derive fingerprint categories from decision records: preferences, tradeoffs, risk posture,
  technology criteria, troubleshooting, operations, and outcome-backed lessons.
- Build fingerprint patterns only from records explicitly attributed to the selected
  expert. Unattributed body-derived records remain searchable grounding context and are
  visibly labeled as context, never as the expert's own view.
- Combine lexical overlap with a local TF-IDF/cosine semantic score.
- Rank the strongest evidence-backed AI Clones for a technology or engineering problem
  using one cross-team relevance scale and attributable citations.
- Answer with source-backed evidence separated from inferred patterns, citations, and an
  insufficient-evidence response when retrieval has no support.
- Run fully offline with SQLite and deterministic extraction.
- Optionally use Azure OpenAI and Azure AI Speech.

## Architecture

```text
Browser / REST API
       │
    FastAPI
       │
  composition root (experttwin.app)
       ├── parsers → evidence segments
       ├── DecisionExtractor (heuristic | Azure OpenAI)
       ├── SQLite decision/evidence store
       ├── FingerprintService (decision records only)
       ├── RetrievalService (lexical + local TF-IDF cosine)
       ├── ExpertFinderService (cross-team evidence ranking)
       ├── Answerer (local | Azure OpenAI)
       └── Transcriber (actionable local error | Azure Speech)
```

## Windows PowerShell setup

Requires Python 3.11.

```powershell
Set-Location C:\repos\LLM-Engineers-Handbook-azure
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn experttwin.app:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is at
<http://127.0.0.1:8000/docs>.

Local defaults make no network calls and require no Azure account. Data is stored in
`.\data\experttwin.db`; uploaded files are retained under `.\data\uploads`.

## Tests

```powershell
Set-Location C:\repos\LLM-Engineers-Handbook-azure
.\.venv\Scripts\Activate.ps1
pytest
ruff check .
```

Tests cover text parsing/ingestion, deterministic decision extraction, decision-derived
fingerprints, hybrid retrieval/citation metadata, an end-to-end API path, and the
actionable local recording error.

## Recording transcription

The default `TRANSCRIPTION_PROVIDER=local` intentionally does not pretend to transcribe
recordings. Local speech models are omitted because they are large and slow to install.
In local mode, audio/video upload returns an actionable error:

1. Upload a TXT transcript, or
2. Install Azure extras and configure Azure Speech.

```powershell
pip install -e ".[azure]"
$env:TRANSCRIPTION_PROVIDER = "azure-speech"
$env:AZURE_SPEECH_KEY = "<speech-resource-key>"
$env:AZURE_SPEECH_REGION = "<region>"
uvicorn experttwin.app:app --reload
```

WAV input can be passed directly to the Speech SDK. MP3/M4A/video and other compressed
formats require `ffmpeg` on `PATH` for conversion to mono 16 kHz WAV.

**Authentication accuracy:** this file-transcription adapter uses the Azure Speech SDK
with a Speech resource key and region. It does not claim passwordless support.

## Optional Azure OpenAI

Install the optional SDKs:

```powershell
pip install -e ".[azure]"
$env:EXTRACTOR_PROVIDER = "azure-openai"
$env:CHAT_PROVIDER = "azure-openai"
$env:WAR_ROOM_PROVIDER = "azure-openai"
$env:AZURE_OPENAI_ENDPOINT = "https://<resource>.openai.azure.com/"
$env:AZURE_OPENAI_CHAT_DEPLOYMENT = "gpt-5.6-sol"
$env:AZURE_OPENAI_API_VERSION = "2025-04-01-preview"
az login
uvicorn experttwin.app:app --reload
```

When `AZURE_OPENAI_API_KEY` is omitted, the adapter uses `DefaultAzureCredential`.
That enables developer authentication after `az login` and managed identity when hosted
on Azure. Assign the identity the appropriate Azure OpenAI user role. An API key remains
an optional compatibility setting; never commit it.

Embeddings are deliberately not required. The local hybrid retriever avoids an extra
deployment and per-token embedding cost. An Azure embedding adapter can be added later
behind the retrieval boundary if corpus size or ranking quality requires it.

Each War Room run retrieves at most two decisions per authorized profile and makes
exactly one strict-JSON Azure OpenAI generation call for the complete 11-person panel.
`WAR_ROOM_PROVIDER=disabled` returns an explicit 503 rather than a fabricated fallback.

## API summary

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/experts` | Create an expert |
| `GET` | `/api/experts` | List experts |
| `GET` | `/api/portfolio-summary` | Summarize projects, sources, decisions, and AI Clones |
| `POST` | `/api/expert-finder` | Rank AI Clones using attributable evidence |
| `POST` | `/api/experts/{id}/sources` | Upload and synchronously ingest a source |
| `GET` | `/api/experts/{id}/sources` | List ingestion status |
| `GET` | `/api/experts/{id}/decisions` | List structured decision records |
| `GET` | `/api/experts/{id}/fingerprint` | Derive the decision fingerprint |
| `POST` | `/api/experts/{id}/chat` | Ask an evidence-grounded question |
| `POST` | `/api/war-room` | Run one bounded, evidence-grounded 11-person panel |
| `GET` | `/health` | Health check |

Uploads are streamed to disk, filename-sanitized, extension-allowlisted, and limited by
`MAX_UPLOAD_MB` (25 MB by default). Ingestion failures are visible on the source record.
For a production multi-user service, add authentication, malware scanning, background
jobs, per-tenant authorization, and a concurrent database.

## Azure mapping and lowest-cost posture

| Need | MVP/local | Optional Azure mapping | Cost posture |
|---|---|---|---|
| Web/API compute | Uvicorn process | Azure Container Apps consumption | Configure minimum replicas 0 for scale-to-zero |
| Records | SQLite | Keep SQLite only for single replica; migrate to Azure SQL/Cosmos DB for concurrency | No database service in demo |
| Uploaded files | Local data directory | Azure Blob Storage | Consumption-based; add lifecycle policies |
| Decision extraction/chat | Deterministic local logic | Azure OpenAI small chat deployment | Paid, optional, token-based |
| Retrieval | In-process TF-IDF/cosine | Azure AI Search only if corpus/quality requires it | Avoids a paid search service in MVP |
| Transcription | TXT transcript | Azure AI Speech | Paid, optional, usage-based |
| Identity | None needed | Managed identity / DefaultAzureCredential | No stored OpenAI secret |

Actual Azure prices vary by region, model, tier, and date; verify with the Azure pricing
calculator before deployment. The cost floor is the fully local mode. The suggested
cloud posture keeps paid AI calls optional and uses scale-to-zero compute, but this
repository intentionally does not provision resources.

For a personal Azure subscription, start with strict budgets/alerts, a single resource
group, the smallest suitable model deployment, and Container Apps consumption with zero
minimum replicas. Keep all Azure features disabled until needed. Azure OpenAI model
availability and quota are subscription/region dependent.

See [`docs/azure-personal-subscription.md`](docs/azure-personal-subscription.md) for the
deferred deployment boundary, SQLite single-replica constraint, identity model, and
Pay-As-You-Go cost guardrails. The application does not need or accept a subscription ID.

## Personal GitHub repository

This directory is initialized as an independent Git repository and is ready to publish
to a personal GitHub account after review. No commit or remote is created automatically,
as requested.

```powershell
Set-Location C:\repos\LLM-Engineers-Handbook-azure
git status
git add .
git commit -m "Build local-first ExpertTwin Azure MVP"
gh repo create LLM-Engineers-Handbook-azure --private --source . --remote origin --push
```

Change `--private` to `--public` only if all uploaded demo data and future commits are
safe to publish. Runtime data, `.env`, test artifacts, and virtual environments are
ignored. This hackathon repository intentionally contains no CI/CD, build pipeline, or
release automation; run the documented validation commands manually.

## Deliberate omissions

- **ZenML:** synchronous stages are simpler and more transparent for this cohesive MVP.
- **SageMaker:** replaced by optional Azure OpenAI; no endpoint fleet is needed.
- **MongoDB/Qdrant:** SQLite and local scoring are sufficient for a personal demo corpus.
- **Fine-tuning/preference training:** the goal is explainable judgment preservation,
  not style imitation or model cloning.
- **GPU/local embedding model:** avoids heavyweight downloads and demo hardware risk.
- **Azure AI Search:** useful at larger scale, but unnecessary fixed complexity/cost here.

These are conscious hackathon boundaries, not placeholders. Provider interfaces and the
composition root preserve upgrade paths without burdening offline tests.

## Example evidence

Upload a short ADR such as:

> We chose Azure Data Explorer over Synapse for high-volume telemetry because Kusto
> queries and ingestion latency fit incident response. The risk was retention cost, so
> we limited hot retention. The result improved investigation time.

Then ask: **Azure Data Explorer vs Synapse for telemetry?**

The local response cites the uploaded source/location, separates extracted evidence from
fingerprint inference, and qualifies uncertainty.

## Synthetic hackathon portfolio

`demo-data/role-simulations/northstar-mixed` contains a DOCX with threaded review
comments, group chat, architecture transcript, WAV rendition and script, incident report,
revised ADR, outcome retrospective, and deterministic manifest.

The portfolio also includes eight fictional projects with distinct software, data,
event-driven, observability, and platform-engineering scenarios:

- **Project Atlas Commerce:** checkout, payments, inventory, API resilience, security,
  accessibility, and customer-impact measures.
- **Project Lakehouse Guardian:** telemetry ingestion, schema evolution, late data,
  quality gates, lineage, reconciliation, compaction, and deterministic replay.
- **Project Release Pulse:** progressive delivery, health probes, database migration,
  fault injection, release metrics, rollback UX, worker draining, and latency budgets.
- **Project API Foundry:** C#, .NET, REST APIs, App Service, Cosmos DB, compatibility,
  managed identity, deployment slots, and contract testing.
- **Project Data Orbit:** ADF, Synapse, ETL, ADLS Gen2, data quality, lineage, replay,
  environment promotion, and governed publication.
- **Project Event Mesh:** Event Grid, Event Hubs, Cosmos DB, idempotent consumers,
  ordering, dead-letter recovery, scaling, and replay.
- **Project Kusto Command:** Kusto, KQL, Event Hub telemetry, observability, alerting,
  retention, diagnostic correlation, and incident investigation.
- **Project Cloud Foundation:** App Service, VMs, Bicep, networking, managed identity,
  CI/CD, backup restoration, regional recovery, and operational governance.

The expanded projects contain threaded review comments, engineering chats, architecture
meeting transcripts, transcripts from fictional audio reviews, incidents, retrospectives,
and measured outcomes. All content is explicitly labeled as synthetic and supplies at
least one attributable decision for every authorized AI Clone. Seed the complete
44-source and 12-decision-per-profile portfolio without network or Azure provider calls:

```powershell
python scripts\seed_role_simulations.py --execute --database data\experttwin.db
```

The first portfolio mutation backs up an existing database under `data\backups`.
Reruns replace only `engineering-portfolio-role-sim-v4`; the first run also removes
superseded Northstar namespaces. Unrelated sources remain unchanged.

For an ephemeral hosted demo, set `SEED_ROLE_SIMULATIONS=true`. Application startup then
uses the same idempotent seeder and `ROLE_SIMULATIONS_CORPUS_DIR`; startup fails visibly
instead of serving an empty roster if the packaged synthetic corpus is unavailable.

`demo-data/atlas-audit` contains a fully fictional, internally consistent demonstration
covering design review, threaded Word comments, chat, architecture review, an incident,
a revised ADR, and a three-month outcome. Follow its README for exact upload order and
titles. The included helper can ingest text/document artifacts locally only after an
explicit `--execute`; it forces heuristic/local providers and cannot spend Azure tokens.

## Project notes

- `assessment.md` maps reusable handbook architecture and AWS-to-Azure changes.
- `migration-status.md` records the migration workflow state.
- No upstream repository files were modified.
- No copyrighted PDF text is included.
