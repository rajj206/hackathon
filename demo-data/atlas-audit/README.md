# AtlasAudit Synthetic Demo Corpus

> **SYNTHETIC FICTIONAL HACKATHON DATA.** AtlasAudit, Contoso Engineering, all
> people, discussions, metrics, incidents, and decisions in this folder are invented for
> demonstration. They do not describe real Microsoft, Contoso, customer, or employee activity.

This compact corpus demonstrates how an engineering decision evolves from proposal,
through review challenges and an incident, to a measured outcome. Create/select the
fictional expert **Maya Rao**. Her Word review replies are the explicitly attributed
judgment used for the fingerprint. Other document content remains contextual evidence.

## Recommended ingestion order

| Order | File | Exact upload title | Source type |
|---|---|---|---|
| 1 | `01-initial-design-review.docx` | `AtlasAudit Initial Design Review` | `document` |
| 2 | `02-design-challenge-chat.txt` | `AtlasAudit Design Challenge Chat` | `meeting-transcript` |
| 3 | `03-architecture-review-transcript.txt` | `AtlasAudit Architecture Review Meeting` | `meeting-transcript` |
| 4 | `05-incident-report.md` | `AtlasAudit Export Lag Incident` | `document` |
| 5 | `06-revised-adr.md` | `AtlasAudit ADR-007 Revision` | `document` |
| 6 | `07-three-month-outcome.md` | `AtlasAudit Three-Month Outcome` | `document` |

The optional `04-architecture-review.wav` is a synthetic spoken abridgement of the meeting,
with speaker names spoken aloud. Upload it as `meeting-recording` only when an explicit
transcription provider is configured. Do not upload both the WAV and transcript in the
same demo unless duplicate evidence is intentional.

**Audio status:** generated locally with Windows SAPI and validated as a RIFF/WAVE file.
The text used to render it is retained in `04-audio-recording-script.txt`.

## Demo facts

- Peak design target: 80,000 events/second; sustained target: 25,000 events/second.
- Pilot constraint: six weeks, personal Pay-As-You-Go-friendly resource posture.
- Final hot path: Event Hubs to Azure Data Explorer, with 14-day hot retention.
- Tamper evidence: hourly immutable Parquet exports plus hash-chain manifests.
- Synapse serverless: deferred for the core incident path; retained as an optional
  cross-domain analytics tool.
- Reliability gate: p95 searchable latency below 90 seconds and query p95 below 5 seconds.
- Synthetic incident: immutable export lagged 47 minutes; no event loss.
- Three-month outcome: 76,000 events/second peak, 42-second searchable p95, 2.8-second
  query p95, and 37% lower hot-retention cost than the 30-day baseline.

## Word review structure

The initial DOCX contains ten comments: five root challenges from Daniel, Priya, Luis,
Aisha, and Ethan, plus five threaded replies by Maya Rao. Maya accepts three suggestions,
rejects one dual-write proposal, and refines one retention proposal. Expected explicitly
Maya-attributed evidence: **11 segments** — 5 threaded DOCX replies, 4 named chat turns,
and 2 named architecture-meeting turns.

## Optional local-only ingestion

The helper uses deterministic local extraction and cannot spend Azure tokens:

```powershell
Set-Location C:\repos\LLM-Engineers-Handbook-azure
.\.venv\Scripts\python.exe scripts\ingest_atlas_demo.py --execute
```

It intentionally skips the WAV. Use `--data-dir` to select a separate demo database.
Nothing is ingested unless `--execute` is supplied.

## Suggested judge questions

1. Why did Maya choose Azure Data Explorer instead of Synapse for the incident path?
2. What did Maya accept, reject, or refine during review?
3. How did the export-lag incident change the reliability controls?
4. Did the measured outcome validate the 14-day retention decision?
5. Where is Synapse still appropriate, and where is evidence insufficient?
