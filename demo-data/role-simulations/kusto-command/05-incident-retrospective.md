SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Kusto Command — Incident retrospective and outcomes

A fictional observability program using Kusto for telemetry, incident investigation, operational dashboards, and governed retention.

[2026-09-21 09:05] Amrita Shanbhag (Senior Software Engineer): We should emit correlated structured telemetry with stable dimensions and safe cardinality. Demonstrated technologies: telemetry. This addresses how to turn application and pipeline telemetry into fast, trustworthy diagnosis from a application perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: Synthetic mean time to isolate a failure dropped from 47 to 9 minutes.
[2026-09-21 10:30] Rajendra Kalepu (Senior Data Engineer): We should ingest Event Hub telemetry into Kusto with update policies and reconciliation checks. Demonstrated technologies: kusto, telemetry. This addresses how to turn application and pipeline telemetry into fast, trustworthy diagnosis from a data perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: Synthetic mean time to isolate a failure dropped from 47 to 9 minutes.
