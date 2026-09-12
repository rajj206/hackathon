# SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Northstar Synthetic Projection-Lag Incident

## Impact
For 17 fictional minutes, dashboard projections were up to 94 seconds behind while
command acceptance remained available. No real systems, people, or data were involved.

## Timeline
- 14:02 — A synthetic burst increased queue depth.
- 14:06 — The freshness indicator crossed its 60-second warning threshold.
- 14:09 — Operators used stage metrics to isolate an intentionally constrained worker.
- 14:19 — Bounded concurrency was raised from four to eight after a replay-safe checkpoint.

## Root cause
The exercise configured worker concurrency below the measured arrival rate. The queue,
idempotency keys, and deterministic checkpoints behaved as designed.

## Decisions
- Preserve command acceptance and drain the durable queue rather than bypass validation.
- Keep the stale-data warning visible and report queue age separately from request latency.
- Add a release gate requiring projection lag below two seconds p95 at 25,000 synthetic
  events per minute.

## Measured recovery
The fictional backlog drained in 6 minutes, no events were lost, and duplicate projection
count remained zero.
