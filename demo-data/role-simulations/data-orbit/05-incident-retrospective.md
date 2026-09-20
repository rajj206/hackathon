SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' ACTUAL BEHAVIOR OR WORK HISTORY.

# Project Data Orbit — Incident retrospective and outcomes

A fictional ETL platform using Azure Data Factory, Synapse, ADLS Gen2, and governed medallion-style data products.

[2026-09-19 09:15] Kumar Ritesh (Senior Software Engineer): We should expose pipeline state through stable APIs without coupling clients to ADF internals. Demonstrated technologies: adf. This addresses how to make high-volume ETL observable, replayable, and trustworthy from a application perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: A synthetic 18-terabyte replay completed with zero unexplained variance.
[2026-09-19 11:40] Siya Sharma (Software Engineer): We should test late, duplicate, malformed, missing, and schema-evolution boundaries. This addresses how to make high-volume ETL observable, replayable, and trustworthy from a quality perspective. Risk: A narrow implementation could optimize one component while hiding end-to-end failure. Measured outcome: A synthetic 18-terabyte replay completed with zero unexplained variance.
