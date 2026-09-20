"""Build synthetic Azure engineering evidence for every authorized AI Clone."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

from experttwin.role_simulations import ROSTER, SIMULATION_NOTICE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo-data" / "role-simulations"

ARTIFACTS = [
    {
        "filename": "01-design-review-comments.md",
        "label": "Threaded design review comments",
        "source_type": "document",
        "evidence_type": "review_comment",
    },
    {
        "filename": "02-engineering-chat-transcript.txt",
        "label": "Engineering chat transcript",
        "source_type": "meeting-transcript",
        "evidence_type": "transcript_turn",
    },
    {
        "filename": "03-architecture-meeting-transcript.txt",
        "label": "Architecture meeting transcript",
        "source_type": "meeting-transcript",
        "evidence_type": "transcript_turn",
    },
    {
        "filename": "04-audio-review-transcript.txt",
        "label": "Audio architecture review transcript",
        "source_type": "meeting-transcript",
        "evidence_type": "transcript_turn",
    },
    {
        "filename": "05-incident-retrospective.md",
        "label": "Incident retrospective and outcomes",
        "source_type": "document",
        "evidence_type": "document",
    },
]

PEOPLE = {
    "Hrishikesh Mohile": {
        "specialty": "management",
        "lens": "architecture governance, delivery risk, ownership, and measurable outcomes",
        "tags": ["architecture-review", "governance", "risk", "azure"],
    },
    "Amrita Shanbhag": {
        "specialty": "application",
        "lens": "C#, .NET, REST API reliability, idempotency, and App Service",
        "tags": ["c#", "dotnet", "rest-api", "app-service"],
    },
    "Devarakonda Sathish": {
        "specialty": "data",
        "lens": "ADF orchestration, Synapse pipelines, ETL contracts, and Event Hubs",
        "tags": ["adf", "synapse", "etl", "event-hubs"],
    },
    "Kumar Ritesh": {
        "specialty": "application",
        "lens": "C# services, REST API performance, Cosmos DB, and event-driven integration",
        "tags": ["c#", "rest-api", "cosmos-db", "event-grid"],
    },
    "Manish Patil": {
        "specialty": "platform",
        "lens": "DevOps, CI/CD, Bicep, App Service, VM operations, and rollback",
        "tags": ["devops", "ci-cd", "bicep", "app-service", "vm"],
    },
    "Nishikant Lambat": {
        "specialty": "quality",
        "lens": "contract testing, failure injection, ETL quality, and release automation",
        "tags": ["testing", "api-contract", "data-quality", "automation"],
    },
    "Rajendra Kalepu": {
        "specialty": "data",
        "lens": "ADF, Synapse, ADLS Gen2, Kusto, ETL replay, lineage, and reconciliation",
        "tags": ["adf", "synapse", "adls-gen2", "kusto", "etl", "replay"],
    },
    "Satyajit Sahu": {
        "specialty": "application",
        "lens": "C# implementation, REST API state, operational UX, and diagnostics",
        "tags": ["c#", "rest-api", "diagnostics", "implementation"],
    },
    "Siya Sharma": {
        "specialty": "quality",
        "lens": "secure APIs, Cosmos DB validation, accessibility, and edge-case testing",
        "tags": ["security", "rest-api", "cosmos-db", "testing"],
    },
    "Tulika": {
        "specialty": "platform",
        "lens": "DevOps automation, Event Hub consumers, scaling, queues, and VM recovery",
        "tags": ["devops", "event-hubs", "autoscaling", "vm", "recovery"],
    },
    "Vishwas Srivastava": {
        "specialty": "architecture",
        "lens": "Azure architecture, Event Grid, Event Hubs, Cosmos DB, and reversible design",
        "tags": ["azure-architecture", "event-grid", "event-hubs", "cosmos-db"],
    },
}

PROJECTS = {
    "api-foundry": {
        "scenario": "Project API Foundry",
        "summary": (
            "A fictional C# and .NET modernization program for versioned REST APIs on "
            "Azure App Service with Cosmos DB and managed identity."
        ),
        "technologies": ["c#", "dotnet", "rest-api", "app-service", "cosmos-db"],
        "challenge": "modernize customer APIs without breaking clients or weakening reliability",
        "outcome": "Synthetic API p95 fell 41% while all contract and rollback checks passed.",
        "actions": {
            "management": "gate API releases on compatibility, reliability, and accountable risk owners",
            "application": "use versioned C# REST API contracts, idempotent commands, and explicit failure responses",
            "data": "choose Cosmos DB partition keys from access patterns and validate change-feed replay",
            "platform": "deploy through App Service slots with managed identity and automated rollback",
            "quality": "run consumer contract, authorization, concurrency, and failure-path tests",
            "architecture": "keep domain behavior independent from HTTP, persistence, and Azure SDK types",
        },
    },
    "data-orbit": {
        "scenario": "Project Data Orbit",
        "summary": (
            "A fictional ETL platform using Azure Data Factory, Synapse, ADLS Gen2, "
            "and governed medallion-style data products."
        ),
        "technologies": ["adf", "synapse", "etl", "adls-gen2", "data-quality"],
        "challenge": "make high-volume ETL observable, replayable, and trustworthy",
        "outcome": "A synthetic 18-terabyte replay completed with zero unexplained variance.",
        "actions": {
            "management": "publish data only after freshness, ownership, quality, and cost gates pass",
            "application": "expose pipeline state through stable APIs without coupling clients to ADF internals",
            "data": "checkpoint ADF by source data, preserve bronze in ADLS Gen2, and reconcile Synapse outputs",
            "platform": "promote ADF and Synapse configuration through parameterized CI/CD environments",
            "quality": "test late, duplicate, malformed, missing, and schema-evolution boundaries",
            "architecture": "separate storage contracts, orchestration, and compute so each remains replaceable",
        },
    },
    "event-mesh": {
        "scenario": "Project Event Mesh",
        "summary": (
            "A fictional event-driven platform combining Event Grid, Event Hubs, "
            "Cosmos DB, dead-letter handling, and replay-safe consumers."
        ),
        "technologies": ["event-grid", "event-hubs", "cosmos-db", "replay", "events"],
        "challenge": "route high-volume events reliably while preserving ordering and replay",
        "outcome": "All 6 million synthetic events were recovered without loss after a consumer outage.",
        "actions": {
            "management": "assign owners for event contracts, replay, cost, and operational readiness",
            "application": "make consumers idempotent and persist processing state separately from delivery",
            "data": "retain immutable event envelopes with sequence, schema, and lineage metadata",
            "platform": "scale Event Hubs consumers from lag while bounding partitions and retry pressure",
            "quality": "inject duplicates, gaps, poison events, reordering, and dead-letter recovery",
            "architecture": "use Event Grid for notification and Event Hubs for ordered high-volume streams",
        },
    },
    "kusto-command": {
        "scenario": "Project Kusto Command",
        "summary": (
            "A fictional observability program using Kusto for telemetry, incident "
            "investigation, operational dashboards, and governed retention."
        ),
        "technologies": ["kusto", "telemetry", "event-hubs", "observability", "kql"],
        "challenge": "turn application and pipeline telemetry into fast, trustworthy diagnosis",
        "outcome": "Synthetic mean time to isolate a failure dropped from 47 to 9 minutes.",
        "actions": {
            "management": "define service health around customer impact and named diagnostic ownership",
            "application": "emit correlated structured telemetry with stable dimensions and safe cardinality",
            "data": "ingest Event Hub telemetry into Kusto with update policies and reconciliation checks",
            "platform": "standardize Kusto dashboards, alerts, retention, and diagnostic settings through IaC",
            "quality": "validate missing signals, alert thresholds, KQL results, and incident timelines",
            "architecture": "separate operational Kusto workloads from governed analytical data products",
        },
    },
    "cloud-foundation": {
        "scenario": "Project Cloud Foundation",
        "summary": (
            "A fictional Azure platform program spanning App Service, virtual machines, "
            "networking, identity, infrastructure as code, and disaster recovery."
        ),
        "technologies": ["azure", "app-service", "vm", "devops", "bicep", "identity"],
        "challenge": "operate mixed PaaS and VM workloads with secure, repeatable recovery",
        "outcome": "Every synthetic regional and VM recovery exercise met its stated recovery target.",
        "actions": {
            "management": "require workload owners, recovery objectives, cost bounds, and exception expiry",
            "application": "externalize configuration and use managed identity across App Service workloads",
            "data": "protect state with tested backups, immutable checkpoints, and recovery reconciliation",
            "platform": "provision App Service, VMs, networking, monitoring, and RBAC through reviewed Bicep",
            "quality": "test identity loss, network isolation, VM restart, backup restore, and regional failover",
            "architecture": "prefer managed Azure services while isolating justified VM dependencies",
        },
    },
}


def build_project(slug: str, project: dict, project_index: int) -> None:
    project_dir = OUTPUT / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    rendered = {artifact["filename"]: [] for artifact in ARTIFACTS}
    decisions = []
    for person_index, (name, role) in enumerate(ROSTER.items()):
        profile = PEOPLE[name]
        artifact = ARTIFACTS[(person_index + project_index) % len(ARTIFACTS)]
        timestamp = (
            f"2026-09-{18 + project_index} {9 + person_index // 4:02d}:{person_index * 5 % 60:02d}"
        )
        action = project["actions"][profile["specialty"]]
        choice = action.capitalize()
        specialty = profile["specialty"].replace("-", " ")
        decision = f"{choice} for {project['scenario']}"
        rationale = f"This addresses how to {project['challenge']} from a {specialty} perspective."
        constraint = "The design must remain testable, observable, least-privilege, and reversible."
        risk = (
            "A narrow implementation could optimize one component while hiding end-to-end failure."
        )
        action_text = action.lower().replace("-", " ")
        action_technologies = {
            technology
            for technology in set(project["technologies"] + profile["tags"])
            if technology.lower().replace("-", " ") in action_text
        }
        profile_technologies = set(project["technologies"]) & set(profile["tags"])
        relevant_technologies = sorted(action_technologies | profile_technologies)
        technology_context = (
            f" Demonstrated technologies: {', '.join(relevant_technologies)}."
            if relevant_technologies
            else ""
        )
        evidence = (
            f"{SIMULATION_NOTICE}\n{name}: In {project['scenario']}, I recommend we "
            f"{action}.{technology_context} Rationale: {rationale} "
            f"Constraint: {constraint} Outcome: {project['outcome']}"
        )
        line = (
            f"[{timestamp}] {name} ({role}): We should {action}.{technology_context} "
            f"{rationale} Risk: {risk} Measured outcome: "
            f"{project['outcome']}"
        )
        rendered[artifact["filename"]].append(line)
        item = {
            "artifact": artifact["filename"],
            "evidence_author": name,
            "evidence_role": role,
            "evidence_type": artifact["evidence_type"],
            "evidence_text": evidence,
            "page_or_segment": f"{artifact['label']} at {timestamp} — {name} ({role})",
            "timestamp": timestamp,
            "decision": decision,
            "choice": choice,
            "alternatives": ["Adopt the platform defaults without an evidence or recovery gate"],
            "rationale": [rationale],
            "constraints": [constraint],
            "risks": [risk],
            "outcome": project["outcome"],
            "tags": sorted({profile["specialty"], *relevant_technologies}),
        }
        if artifact["evidence_type"] == "review_comment":
            item.update(
                {
                    "comment_id": f"{slug[:3].upper()}-{person_index + 1:02d}",
                    "anchor_text": project["challenge"],
                    "parent_comment_id": "ARCH-ROOT",
                    "parent_author": "Architecture proposal",
                    "parent_text": project["summary"],
                }
            )
        decisions.append(item)

    for artifact in ARTIFACTS:
        heading = (
            "Synthetic transcript from a fictional audio architecture review."
            if artifact["filename"] == "04-audio-review-transcript.txt"
            else project["summary"]
        )
        lines = [
            SIMULATION_NOTICE,
            "",
            f"# {project['scenario']} — {artifact['label']}",
            "",
            heading,
            "",
            *rendered[artifact["filename"]],
            "",
        ]
        (project_dir / artifact["filename"]).write_text("\n".join(lines), encoding="utf-8")

    manifest = {
        "notice": SIMULATION_NOTICE,
        "scenario": project["scenario"],
        "summary": project["summary"],
        "artifacts": [
            {key: value for key, value in artifact.items() if key != "evidence_type"}
            for artifact in ARTIFACTS
        ],
        "decisions": decisions,
    }
    (project_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    if set(PEOPLE) != set(ROSTER):
        raise ValueError("Capability profiles must cover the authorized roster.")
    for project_index, (slug, project) in enumerate(PROJECTS.items()):
        build_project(slug, project, project_index)
        print(OUTPUT / slug)


if __name__ == "__main__":
    main()
