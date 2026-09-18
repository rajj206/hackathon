"""Build additional deterministic synthetic engineering project corpora."""

from __future__ import annotations

import json
from pathlib import Path

from experttwin.role_simulations import ROSTER, SIMULATION_NOTICE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo-data" / "role-simulations"

ARTIFACTS = [
    {
        "filename": "01-design-notes.md",
        "label": "Design proposal and review notes",
        "source_type": "document",
    },
    {
        "filename": "02-engineering-chat.txt",
        "label": "Timestamped engineering group chat",
        "source_type": "meeting-transcript",
    },
    {
        "filename": "03-architecture-meeting-transcript.txt",
        "label": "Architecture decision meeting transcript",
        "source_type": "meeting-transcript",
    },
    {
        "filename": "04-incident-and-retrospective.md",
        "label": "Incident review and measured retrospective",
        "source_type": "document",
    },
]

PROJECTS = {
    "atlas-commerce": {
        "scenario": "Project Atlas Commerce",
        "summary": (
            "A fictional software-engineering project modernizing checkout, inventory, "
            "payments, and customer-facing APIs."
        ),
        "decisions": {
            "Hrishikesh Mohile": (
                "Gate the checkout migration on customer outcomes",
                "Release only after conversion, error-rate, and rollback rehearsals pass",
                ["Release by feature completion alone"],
                "Outcome gates keep the program focused on safe customer value",
                "Migration must remain reversible",
                "Schedule pressure could bypass a weak gate",
                "Synthetic checkout failures fell from 3.2% to 0.4%.",
                ["governance", "outcomes"],
            ),
            "Amrita Shanbhag": (
                "Make payment submission idempotent",
                "Require one idempotency key per checkout attempt",
                ["Trust clients not to retry"],
                "Network retries must not create duplicate charges",
                "Keys expire after 24 hours",
                "Reused keys with changed payloads must be rejected",
                "Duplicate synthetic charges fell from 38 to 0.",
                ["architecture", "reliability"],
            ),
            "Devarakonda Sathish": (
                "Publish versioned order events",
                "Use an immutable event envelope with schema version and event ID",
                ["Infer event shape from optional fields"],
                "Explicit contracts support replay and independent consumers",
                "Two schema versions must coexist",
                "Unknown versions can block consumers",
                "All 54 incompatible synthetic events were quarantined.",
                ["data-contract", "quality"],
            ),
            "Kumar Ritesh": (
                "Isolate inventory from checkout latency",
                "Reserve stock through an asynchronous command with a visible pending state",
                ["Call inventory synchronously in the checkout request"],
                "A bounded asynchronous boundary prevents one dependency from stalling checkout",
                "Reservation response target is two seconds",
                "Customers may briefly see a pending order",
                "Synthetic checkout p95 improved from 4.1 seconds to 1.2 seconds.",
                ["architecture", "performance"],
            ),
            "Manish Patil": (
                "Use a circuit breaker for the tax provider",
                "Open after five failures and return an explicit retryable response",
                ["Retry every request indefinitely"],
                "Fast failure protects threads and makes degradation visible",
                "Tax must never be silently estimated",
                "A sensitive threshold could reject recoverable calls",
                "Synthetic provider outages no longer exhausted the request pool.",
                ["reliability", "operations"],
            ),
            "Nishikant Lambat": (
                "Test checkout boundaries with executable examples",
                "Cover zero quantity, stock race, duplicate payment, and timeout cases",
                ["Test only the happy path"],
                "Concrete boundary cases clarify behavior before implementation",
                "Tests run without external payment calls",
                "Mocks may drift from provider behavior",
                "Checkout branch coverage increased from 68% to 93%.",
                ["testing", "clarification"],
            ),
            "Rajendra Kalepu": (
                "Reconcile orders, payments, and fulfillment daily",
                "Compare counts and amounts by order date and source batch",
                ["Compare only monthly finance totals"],
                "Fine-grained reconciliation localizes loss and duplication",
                "Late refunds remain separately pending",
                "Currency conversion can create expected variance",
                "Unexplained synthetic revenue variance dropped to zero.",
                ["data-quality", "lineage"],
            ),
            "Satyajit Sahu": (
                "Model checkout UI states explicitly",
                "Represent validating, reserving, paying, confirmed, and failed states",
                ["Use one loading flag"],
                "Explicit states prevent ambiguous customer messaging",
                "Refresh must restore the server state",
                "More states require broader tests",
                "All five synthetic states passed accessibility and recovery tests.",
                ["implementation", "testing"],
            ),
            "Siya Sharma": (
                "Protect customer notes from markup injection",
                "Render delivery notes as text and validate length at input",
                ["Allow arbitrary rich HTML"],
                "Text rendering removes an avoidable script-injection path",
                "Line breaks remain supported",
                "Customers lose rich formatting",
                "All 30 synthetic hostile-note cases were blocked.",
                ["security", "testing"],
            ),
            "Tulika": (
                "Bound checkout worker concurrency",
                "Process 16 reservations concurrently and expose queue age",
                ["Create an unbounded task per order"],
                "A fixed limit protects memory during demand spikes",
                "Peak synthetic load is 5,000 orders per minute",
                "A fixed value may underuse larger instances",
                "Memory remained below 420 MB during the peak replay.",
                ["operations", "performance"],
            ),
            "Vishwas Srivastava": (
                "Keep commerce domain logic provider-neutral",
                "Place payment, tax, and inventory clients behind domain ports",
                ["Use vendor SDK types in checkout handlers"],
                "Ports preserve testability and make provider replacement reversible",
                "The first release supports one provider per port",
                "Too many abstractions can slow delivery",
                "Offline integration coverage reached 91%.",
                ["architecture", "testing"],
            ),
        },
    },
    "lakehouse-guardian": {
        "scenario": "Project Lakehouse Guardian",
        "summary": (
            "A fictional data-engineering project ingesting product telemetry into bronze, "
            "silver, and curated layers with quality, lineage, and replay controls."
        ),
        "decisions": {
            "Hrishikesh Mohile": (
                "Define trust gates for curated telemetry",
                "Block publication when freshness, completeness, or reconciliation misses its SLO",
                ["Publish whenever the pipeline reports success"],
                "Consumers need trustworthy data rather than green jobs",
                "Critical dashboards refresh every 15 minutes",
                "Strict gates can delay partially useful data",
                "Synthetic bad-data publication dropped from 11 cases to 0.",
                ["governance", "data-quality"],
            ),
            "Amrita Shanbhag": (
                "Separate ingestion validation from transformation",
                "Validate the envelope before writing bronze and record reason codes",
                ["Mix validation into every transformation"],
                "One boundary produces consistent failures and simpler transforms",
                "Raw payload is retained for replay",
                "Overly strict rules may reject a new producer",
                "Invalid synthetic records were classified with 100% reason coverage.",
                ["architecture", "quality"],
            ),
            "Devarakonda Sathish": (
                "Use event-time watermarks",
                "Accept telemetry up to 20 minutes late and correct later arrivals separately",
                ["Aggregate only by processing time"],
                "A bounded watermark balances completeness and stable windows",
                "Devices can be offline temporarily",
                "Very late data requires correction logic",
                "Synthetic window completeness improved from 89% to 99.3%.",
                ["data-architecture", "quality"],
            ),
            "Kumar Ritesh": (
                "Expose data-product health by dependency",
                "Report source, bronze, silver, and serving readiness separately",
                ["Return one unconditional health result"],
                "Layer-specific health makes partial degradation diagnosable",
                "Health queries must finish in 500 milliseconds",
                "Expensive checks can overload the warehouse",
                "All 14 injected layer failures were correctly localized.",
                ["telemetry", "reliability"],
            ),
            "Manish Patil": (
                "Make schema migration backward compatible",
                "Dual-read old and new product-category fields during one release window",
                ["Rename the field in one deployment"],
                "Compatible readers prevent producer and consumer lockstep",
                "The transition lasts seven days",
                "Temporary dual fields increase complexity",
                "The synthetic migration completed without failed consumer jobs.",
                ["data-contract", "operations"],
            ),
            "Nishikant Lambat": (
                "Test every quality-rule boundary",
                "Parameterize null, duplicate, stale, malformed, and late-event cases",
                ["Use one invalid sample"],
                "Table-driven tests make missing boundaries visible",
                "Tests use a frozen event clock",
                "Overlapping rules may obscure the primary rejection reason",
                "Quality-rule branch coverage reached 96%.",
                ["testing", "data-quality"],
            ),
            "Rajendra Kalepu": (
                "Use data-derived replay checkpoints",
                "Checkpoint by source batch and maximum committed event sequence",
                ["Checkpoint by worker wall clock"],
                "Data-derived positions make recovery deterministic",
                "Sequences are monotonic within a source batch",
                "Malformed sequence gaps can halt progress",
                "A 3-million-event synthetic replay produced no omissions or duplicates.",
                ["data-architecture", "recovery"],
            ),
            "Satyajit Sahu": (
                "Show freshness and quality separately",
                "Display last successful load, event freshness, and quality status",
                ["Show one green pipeline badge"],
                "Distinct signals prevent a recent but invalid dataset appearing healthy",
                "The page must remain usable on mobile",
                "Additional indicators can overwhelm users",
                "Synthetic users identified the failing dimension in 28 of 30 trials.",
                ["implementation", "telemetry"],
            ),
            "Siya Sharma": (
                "Distinguish missing metrics from zero",
                "Render missing as unknown and zero as a measured value",
                ["Coerce missing values to zero"],
                "Unknown and zero lead to different operational decisions",
                "Aggregations preserve null semantics",
                "Downstream calculations need explicit handling",
                "All 18 synthetic null-semantics tests passed.",
                ["clarification", "testing"],
            ),
            "Tulika": (
                "Compact small files on a bounded schedule",
                "Compact only partitions above a file-count threshold",
                ["Compact every partition every hour"],
                "Threshold-based work reduces compute without ignoring fragmentation",
                "Hot partitions must remain queryable",
                "Compaction can contend with ingestion",
                "Synthetic scan file count fell by 78% with 31% less compute.",
                ["operations", "performance"],
            ),
            "Vishwas Srivastava": (
                "Separate storage contracts from compute engines",
                "Use open table contracts and adapters for query engines",
                ["Embed one engine's APIs throughout transformations"],
                "A portable boundary keeps platform choices reversible",
                "Performance-specific optimizations remain isolated",
                "Abstraction may hide useful engine features",
                "Two synthetic query adapters passed the same 42 contract tests.",
                ["architecture", "risk"],
            ),
        },
    },
    "release-pulse": {
        "scenario": "Project Release Pulse",
        "summary": (
            "A fictional platform-engineering project improving safe deployments, "
            "observability, incident response, and engineering feedback loops."
        ),
        "decisions": {
            "Hrishikesh Mohile": (
                "Use evidence-based production go/no-go reviews",
                "Require named owners for unresolved reliability and security risks",
                ["Approve through informal consensus"],
                "Visible ownership prevents critical risks from becoming assumptions",
                "Emergency rollback remains available",
                "Review overhead can slow low-risk releases",
                "All 9 synthetic launch risks had owners and evidence.",
                ["governance", "risk"],
            ),
            "Amrita Shanbhag": (
                "Use progressive delivery for API changes",
                "Route 5%, 25%, then 100% of traffic with automated health gates",
                ["Deploy to every instance immediately"],
                "Small exposure limits blast radius while preserving real signals",
                "Each stage observes ten minutes",
                "Low traffic may produce weak confidence",
                "Synthetic regression impact was limited to 4.7% of requests.",
                ["reliability", "deployment"],
            ),
            "Devarakonda Sathish": (
                "Version deployment telemetry contracts",
                "Publish immutable deployment and rollback events with correlation IDs",
                ["Parse free-form pipeline logs"],
                "Structured events support reliable trend and incident analysis",
                "No secret values enter telemetry",
                "Missing events can distort release metrics",
                "Synthetic release-event completeness reached 99.9%.",
                ["data-contract", "telemetry"],
            ),
            "Kumar Ritesh": (
                "Separate liveness from readiness",
                "Use liveness for process health and readiness for dependencies",
                ["Restart on every dependency outage"],
                "Dependency failures should remove traffic without causing restart loops",
                "Checks complete within 200 milliseconds",
                "Bad thresholds can flap instances",
                "All synthetic database outages drained traffic without restart storms.",
                ["reliability", "operations"],
            ),
            "Manish Patil": (
                "Use expand-migrate-contract for database releases",
                "Add, backfill, switch readers, then remove the old column",
                ["Rename the column in one step"],
                "Compatible schemas support rolling deployment and rollback",
                "Backfill must be resumable",
                "Dual-write defects can create divergence",
                "A synthetic 20-million-row migration completed with zero downtime.",
                ["architecture", "deployment"],
            ),
            "Nishikant Lambat": (
                "Add fault-injection release tests",
                "Exercise timeout, dependency loss, stale configuration, and rollback",
                ["Test only successful deployment"],
                "Failure paths are the highest-risk release behavior",
                "Tests must be deterministic",
                "Mocks may not capture platform timing",
                "The release suite detected all 12 injected regressions.",
                ["testing", "reliability"],
            ),
            "Rajendra Kalepu": (
                "Measure deployment quality beyond success rate",
                "Track change failure, rollback, recovery time, and escaped defects",
                ["Track successful pipeline runs only"],
                "A green pipeline does not prove a healthy release",
                "Metrics are aggregated without personal performance scoring",
                "Definitions can vary across services",
                "Synthetic escaped defects fell by 43% over six release cycles.",
                ["outcomes", "telemetry"],
            ),
            "Satyajit Sahu": (
                "Display deployment state explicitly",
                "Model queued, deploying, verifying, healthy, rolling back, and failed",
                ["Use one progress spinner"],
                "Explicit states tell operators what action is safe",
                "State comes from server events",
                "Out-of-order events can regress the display",
                "All six synthetic states passed UI recovery tests.",
                ["implementation", "operations"],
            ),
            "Siya Sharma": (
                "Make rollback controls accessible and safe",
                "Use a labeled action, confirmation summary, and live status region",
                ["Use an unlabeled icon button"],
                "Clear controls reduce mistakes during stressful incidents",
                "Keyboard-only operation is required",
                "Confirmation may slow an urgent rollback",
                "Synthetic accessibility checks reported no critical violations.",
                ["testing", "implementation"],
            ),
            "Tulika": (
                "Drain workers before deployment",
                "Stop intake and drain for up to 15 seconds before checkpointing",
                ["Terminate workers immediately", "Wait indefinitely"],
                "Bounded draining reduces interrupted work without blocking rollout",
                "Unfinished work remains replayable",
                "Long requests may execute again",
                "Fifty synthetic rolling restarts lost no work.",
                ["operations", "recovery"],
            ),
            "Vishwas Srivastava": (
                "Allocate the latency budget by component",
                "Budget ingress, application, dependency, and queue latency separately",
                ["Optimize only after total latency fails"],
                "Component budgets localize regressions before the SLO is breached",
                "End-to-end p95 target is 800 milliseconds",
                "Local optimization may miss the critical path",
                "Synthetic API p95 improved from 1.4 seconds to 690 milliseconds.",
                ["architecture", "performance"],
            ),
        },
    },
}


def evidence_type(filename: str) -> str:
    return "transcript_turn" if filename.endswith(".txt") else "document"


def build_project(slug: str, project: dict) -> None:
    project_dir = OUTPUT / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    decisions = []
    rendered: dict[str, list[str]] = {item["filename"]: [] for item in ARTIFACTS}
    names = list(ROSTER)
    for index, name in enumerate(names):
        artifact = ARTIFACTS[index % len(ARTIFACTS)]
        (
            decision,
            choice,
            alternatives,
            rationale,
            constraints,
            risks,
            outcome,
            tags,
        ) = project["decisions"][name]
        day = 14 + list(PROJECTS).index(slug)
        hour = 9 + index // 4
        minute = (index * 7) % 60
        timestamp = f"2026-09-{day} {hour:02d}:{minute:02d}"
        location_kind = "chat turn" if artifact["filename"].startswith("02") else (
            "meeting turn" if artifact["filename"].startswith("03") else "section"
        )
        location = f"{location_kind} at {timestamp} — {name} ({ROSTER[name]})"
        evidence = (
            f"{SIMULATION_NOTICE}\n{name}: {decision}. Choice: {choice}. "
            f"Rationale: {rationale}. Outcome: {outcome}"
        )
        rendered[artifact["filename"]].append(
            f"[{timestamp}] {name} ({ROSTER[name]}): {decision}. "
            f"I prefer {choice} rather than {'; '.join(alternatives)}. "
            f"Constraint: {constraints}. Risk: {risks}. Measured outcome: {outcome}"
        )
        decisions.append(
            {
                "artifact": artifact["filename"],
                "evidence_author": name,
                "evidence_role": ROSTER[name],
                "evidence_type": evidence_type(artifact["filename"]),
                "evidence_text": evidence,
                "page_or_segment": location,
                "timestamp": timestamp,
                "decision": decision,
                "choice": choice,
                "alternatives": alternatives,
                "rationale": [rationale],
                "constraints": [constraints],
                "risks": [risks],
                "outcome": outcome,
                "tags": tags,
            }
        )

    for artifact in ARTIFACTS:
        filename = artifact["filename"]
        title = artifact["label"]
        lines = [
            SIMULATION_NOTICE,
            "",
            f"# {project['scenario']} — {title}",
            "",
            project["summary"],
            "",
            *rendered[filename],
            "",
        ]
        (project_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    manifest = {
        "notice": SIMULATION_NOTICE,
        "scenario": project["scenario"],
        "summary": project["summary"],
        "artifacts": ARTIFACTS,
        "decisions": decisions,
    }
    (project_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def main() -> None:
    if set(next(iter(PROJECTS.values()))["decisions"]) != set(ROSTER):
        raise ValueError("Project decisions must cover the authorized roster.")
    for slug, project in PROJECTS.items():
        if set(project["decisions"]) != set(ROSTER):
            raise ValueError(f"{slug}: decisions do not cover the authorized roster.")
        build_project(slug, project)
        print(OUTPUT / slug)


if __name__ == "__main__":
    main()
