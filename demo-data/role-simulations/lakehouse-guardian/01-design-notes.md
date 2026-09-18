SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Lakehouse Guardian — Design proposal and review notes

A fictional data-engineering project ingesting product telemetry into bronze, silver, and curated layers with quality, lineage, and replay controls.

[2026-09-15 09:00] Hrishikesh Mohile (Principal Software Engineering Manager): Define trust gates for curated telemetry. I prefer Block publication when freshness, completeness, or reconciliation misses its SLO rather than Publish whenever the pipeline reports success. Constraint: Critical dashboards refresh every 15 minutes. Risk: Strict gates can delay partially useful data. Measured outcome: Synthetic bad-data publication dropped from 11 cases to 0.
[2026-09-15 10:28] Manish Patil (Senior Software Engineer): Make schema migration backward compatible. I prefer Dual-read old and new product-category fields during one release window rather than Rename the field in one deployment. Constraint: The transition lasts seven days. Risk: Temporary dual fields increase complexity. Measured outcome: The synthetic migration completed without failed consumer jobs.
[2026-09-15 11:56] Siya Sharma (Software Engineer): Distinguish missing metrics from zero. I prefer Render missing as unknown and zero as a measured value rather than Coerce missing values to zero. Constraint: Aggregations preserve null semantics. Risk: Downstream calculations need explicit handling. Measured outcome: All 18 synthetic null-semantics tests passed.
