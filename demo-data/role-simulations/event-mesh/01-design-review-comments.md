SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Event Mesh — Threaded design review comments

A fictional event-driven platform combining Event Grid, Event Hubs, Cosmos DB, dead-letter handling, and replay-safe consumers.

[2026-09-20 09:15] Kumar Ritesh (Senior Software Engineer): We should make consumers idempotent and persist processing state separately from delivery. Demonstrated technologies: cosmos-db, event-grid. This addresses how to route high-volume events reliably while preserving ordering and replay from a application perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: All 6 million synthetic events were recovered without loss after a consumer outage.
[2026-09-20 11:40] Siya Sharma (Software Engineer): We should inject duplicates, gaps, poison events, reordering, and dead-letter recovery. Demonstrated technologies: cosmos-db, events. This addresses how to route high-volume events reliably while preserving ordering and replay from a quality perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: All 6 million synthetic events were recovered without loss after a consumer outage.
