# SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Northstar ADR-004 — Revised Offline-Tolerant Event Flow

## Status
Accepted for the fictional hackathon demonstration only.

## Challenges that changed the draft
The design review identified replay ambiguity, missing row-level lineage, stale dashboard
visibility, dependency coupling, and an under-specified recovery gate. The synthetic
incident then demonstrated that total request latency could remain healthy while projection
freshness degraded.

## Revised decision
Use one validated command boundary, idempotency keys, a bounded durable projection queue,
versioned event envelopes, quarantine reason codes, source-batch lineage, optimistic
concurrency, dependency-specific readiness, and explicit freshness telemetry.

## Rejected alternatives
- Synchronous fan-out to every read model.
- Last-writer-wins updates for offline edits.
- Unbounded worker concurrency.
- A single unconditional health endpoint.

## Consequences and risks
The queue introduces observable lag and requires replay operations. Version conflicts need
an explicit user path. These costs are accepted because the components remain replaceable
and the entire exercise runs offline without Azure services.
