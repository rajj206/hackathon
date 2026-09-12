# ADR-007: AtlasAudit Telemetry and Audit Storage — Revision 2

> **SYNTHETIC FICTIONAL HACKATHON DATA.** This ADR, organization, architecture,
> people, constraints, and measurements are invented for demonstration.

**Status:** Accepted for pilot
**Revised:** 2026-06-20 after the synthetic export-lag incident

## Decision

Use Event Hubs to Azure Data Explorer as the only operational ingestion path. Retain
14 days hot in ADX. Export immutable Parquet batches hourly to a 13-month archive with
source sequence ranges and hash-chain manifests. Keep Synapse serverless optional for
cross-domain analysis; do not synchronously dual-write the core audit stream.

## Reliability revision

The exporter is idempotent by batch and sequence range. It releases storage leases before
long backoff, applies jitter, dead-letters after eight attempts, and reconciles source
ranges every fifteen minutes. Page when oldest-unexported-batch age exceeds ten minutes.

## Rationale

ADX meets high-volume ingestion and Kusto incident-query needs with lower operating
complexity than coordinating ADX and Synapse writes. Fourteen hot days controls retention
cost. The immutable archive supplies tamper evidence and long retention. The revised
export controls address the observed failure mode without adding a second critical write.

## Alternatives

1. **Synapse as the primary operational store:** rejected for the pilot because incident
   query latency and ingestion operations did not meet the focused hot-path criteria.
2. **Synchronous ADX and Synapse dual-write:** rejected because partial success, schema
   coordination, and replay increase reliability and six-week delivery risk.
3. **Thirty-day ADX hot retention:** refined to 14 days after cost modeling; revisit if
   measured incident demand shows the shorter window is inadequate.

## Exit gates

Pass an 80,000 events-per-second burst; keep p95 searchable latency below 90 seconds and
query p95 below 5 seconds; recover archive freshness within 15 minutes after injected
failure; produce zero unexplained reconciliation gaps; remain below the agreed pilot cost cap.
