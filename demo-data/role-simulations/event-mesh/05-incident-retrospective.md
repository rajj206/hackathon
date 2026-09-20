SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Event Mesh — Incident retrospective and outcomes

A fictional event-driven platform combining Event Grid, Event Hubs, Cosmos DB, dead-letter handling, and replay-safe consumers.

[2026-09-20 09:10] Devarakonda Sathish (Data Engineer): We should retain immutable event envelopes with sequence, schema, and lineage metadata. Demonstrated technologies: event-hubs. This addresses how to route high-volume events reliably while preserving ordering and replay from a data perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: All 6 million synthetic events were recovered without loss after a consumer outage.
[2026-09-20 10:35] Satyajit Sahu (Software Engineering): We should make consumers idempotent and persist processing state separately from delivery. This addresses how to route high-volume events reliably while preserving ordering and replay from a application perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: All 6 million synthetic events were recovered without loss after a consumer outage.
