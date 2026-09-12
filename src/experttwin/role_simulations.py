"""Seed deterministic, offline-only Project Northstar role simulations."""

import argparse
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from experttwin.db import Database
from experttwin.models import DecisionRecord
from experttwin.roster import AUTHORIZED_ROSTER

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT / "data" / "experttwin.db"
DEFAULT_CORPUS = ROOT / "demo-data" / "role-simulations" / "northstar-mixed"
SIMULATION_NAMESPACE = "northstar-role-sim-mixed-v2"
LEGACY_NAMESPACE = "northstar-role-sim-v1"
SIMULATION_NOTICE = (
    "SYNTHETIC ROLE-BASED SIMULATION — NOT BASED ON THESE EMPLOYEES' "
    "ACTUAL BEHAVIOR OR WORK HISTORY."
)
PROFILE_NOTICE = SIMULATION_NOTICE
SEED_TIME = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
ID_NAMESPACE = uuid.UUID("b62e14fc-7f74-4d63-a2db-2cbb2dcefd1f")
ROSTER = {profile.name: profile.role for profile in AUTHORIZED_ROSTER}


@dataclass(frozen=True)
class SeedReport:
    database_path: Path
    backup_path: Path | None
    source_count: int
    segment_count: int
    decision_count: int
    per_profile: dict[str, dict[str, int]]


def _stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, f"{SIMULATION_NAMESPACE}:{kind}:{value}"))


def _has_seeded_namespace(database_path: Path) -> bool:
    if not database_path.is_file():
        return False
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "sources" not in tables:
            return False
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(sources)").fetchall()
        }
        if "simulation_namespace" not in columns:
            return False
        return bool(
            connection.execute(
                "SELECT 1 FROM sources WHERE simulation_namespace=? LIMIT 1",
                (SIMULATION_NAMESPACE,),
            ).fetchone()
        )


def _backup_before_first_mutation(database_path: Path) -> Path | None:
    if not database_path.is_file() or _has_seeded_namespace(database_path):
        return None
    backup_dir = database_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"{database_path.stem}.pre-{SIMULATION_NAMESPACE}.{stamp}.db"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / (
            f"{database_path.stem}.pre-{SIMULATION_NAMESPACE}.{stamp}.{counter}.db"
        )
        counter += 1
    with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)
    return backup_path


def _load_corpus(corpus_dir: Path) -> dict:
    manifest_path = corpus_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("notice") != SIMULATION_NOTICE:
        raise ValueError("The mixed-corpus manifest is missing the required notice.")
    if manifest.get("simulation_namespace") != SIMULATION_NAMESPACE:
        raise ValueError("The mixed-corpus manifest has an unexpected namespace.")
    artifacts = manifest.get("artifacts", [])
    if len(artifacts) != 7:
        raise ValueError(f"Expected 7 mixed artifacts, found {len(artifacts)}.")
    for artifact in artifacts:
        path = corpus_dir / artifact["filename"]
        if not path.is_file():
            raise ValueError(f"Missing mixed artifact: {path.name}")
    decisions = manifest.get("decisions", [])
    names = {decision.get("evidence_author") for decision in decisions}
    if names != set(ROSTER):
        raise ValueError("Mixed-corpus decisions do not match the authorized roster.")
    for decision in decisions:
        name = decision["evidence_author"]
        if decision.get("evidence_role") != ROSTER[name]:
            raise ValueError(f"{name}: role does not match the authorized roster.")
    counts = {name: 0 for name in ROSTER}
    for decision in decisions:
        counts[decision["evidence_author"]] += 1
    if any(count < 3 for count in counts.values()):
        raise ValueError("Every profile must have at least three attributable decisions.")
    return manifest


def seed(database_path: Path, corpus_dir: Path = DEFAULT_CORPUS) -> SeedReport:
    database_path = database_path.resolve()
    corpus_dir = corpus_dir.resolve()
    manifest = _load_corpus(corpus_dir)
    backup_path = _backup_before_first_mutation(database_path)

    database = Database(database_path)
    database.initialize()
    expert_rows = database.list_experts()
    experts = {expert.name: expert for expert in expert_rows}
    duplicate_names = {
        name
        for name in ROSTER
        if sum(expert.name == name for expert in expert_rows) > 1
    }
    if duplicate_names:
        raise ValueError(f"Duplicate authorized profiles found: {sorted(duplicate_names)}")

    per_profile: dict[str, dict[str, int]] = {}
    expert_ids: dict[str, str] = {}
    with database.connect() as connection:
        for name, role in ROSTER.items():
            description = role
            expert = experts.get(name)
            if expert:
                expert_ids[name] = expert.id
                connection.execute(
                    "UPDATE experts SET description=? WHERE id=?",
                    (description, expert.id),
                )
            else:
                expert_id = _stable_id("expert", name)
                expert_ids[name] = expert_id
                connection.execute(
                    "INSERT INTO experts(id,name,description,created_at) VALUES(?,?,?,?)",
                    (expert_id, name, description, SEED_TIME.isoformat()),
                )

        connection.execute(
            "DELETE FROM sources WHERE simulation_namespace IN (?,?)",
            (SIMULATION_NAMESPACE, LEGACY_NAMESPACE),
        )

        decisions_by_artifact: dict[tuple[str, str], list[dict]] = {}
        for item in manifest["decisions"]:
            key = (item["evidence_author"], item["artifact"])
            decisions_by_artifact.setdefault(key, []).append(item)

        for name, role in ROSTER.items():
            decision_count = 0
            for artifact in manifest["artifacts"]:
                filename = artifact["filename"]
                source_id = _stable_id("source", f"{name}:{filename}")
                title = f"Project Northstar — {artifact['label']}"
                connection.execute(
                    """INSERT INTO sources(
                           id,expert_id,title,filename,source_type,status,error,
                           simulation,simulation_namespace,created_at
                       ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        source_id,
                        expert_ids[name],
                        title,
                        filename,
                        artifact["source_type"],
                        "ready",
                        None,
                        1,
                        SIMULATION_NAMESPACE,
                        SEED_TIME.isoformat(),
                    ),
                )
                source_decisions = decisions_by_artifact.get((name, filename), [])
                if not source_decisions:
                    connection.execute(
                        """INSERT INTO segments(
                               source_id,text,page_or_segment,timestamp,author,speaker_role,
                               comment_id,anchor_text,parent_comment_id,parent_author,parent_text
                           ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            source_id,
                            (
                                f"{SIMULATION_NOTICE} Project Northstar artifact context. "
                                "No statement from the selected profile is attributed in "
                                "this artifact."
                            ),
                            "synthetic artifact context",
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ),
                    )
                for index, item in enumerate(source_decisions, start=1):
                    connection.execute(
                        """INSERT INTO segments(
                               source_id,text,page_or_segment,timestamp,author,speaker_role,
                               comment_id,anchor_text,parent_comment_id,parent_author,parent_text
                           ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            source_id,
                            item["evidence_text"],
                            item["page_or_segment"],
                            item.get("timestamp"),
                            name,
                            role,
                            item.get("comment_id"),
                            item.get("anchor_text"),
                            item.get("parent_comment_id"),
                            item.get("parent_author"),
                            item.get("parent_text"),
                        ),
                    )
                    decision = DecisionRecord(
                        id=_stable_id("decision", f"{name}:{filename}:{index}"),
                        expert_id=expert_ids[name],
                        expert=name,
                        decision=item["decision"],
                        choice=item["choice"],
                        alternatives=item["alternatives"],
                        rationale=item["rationale"],
                        constraints=item["constraints"],
                        risks=item["risks"],
                        outcome=item["outcome"],
                        source_id=source_id,
                        source_title=title,
                        evidence_text=item["evidence_text"],
                        page_or_segment=item["page_or_segment"],
                        evidence_type=item["evidence_type"],
                        evidence_author=name,
                        evidence_role=role,
                        comment_id=item.get("comment_id"),
                        anchor_text=item.get("anchor_text"),
                        parent_comment_id=item.get("parent_comment_id"),
                        parent_author=item.get("parent_author"),
                        parent_text=item.get("parent_text"),
                        timestamp=item.get("timestamp"),
                        tags=item["tags"],
                        confidence=0.99,
                        simulation=True,
                        simulation_namespace=SIMULATION_NAMESPACE,
                        created_at=SEED_TIME,
                    )
                    connection.execute(
                        """INSERT INTO decisions(id,expert_id,source_id,payload,created_at)
                           VALUES(?,?,?,?,?)""",
                        (
                            decision.id,
                            expert_ids[name],
                            source_id,
                            decision.model_dump_json(),
                            decision.created_at.isoformat(),
                        ),
                    )
                    decision_count += 1
            per_profile[name] = {
                "sources": len(manifest["artifacts"]),
                "decisions": decision_count,
            }

        counts = connection.execute(
            """SELECT COUNT(DISTINCT s.id), COUNT(DISTINCT g.id), COUNT(DISTINCT d.id)
               FROM sources s
               LEFT JOIN segments g ON g.source_id=s.id
               LEFT JOIN decisions d ON d.source_id=s.id
               WHERE s.simulation_namespace=?""",
            (SIMULATION_NAMESPACE,),
        ).fetchone()

    return SeedReport(
        database_path=database_path,
        backup_path=backup_path,
        source_count=counts[0],
        segment_count=counts[1],
        decision_count=counts[2],
        per_profile=per_profile,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement; otherwise the database is not changed.",
    )
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("No action taken. Re-run with --execute for offline local seeding.")
    report = seed(args.database, args.corpus)
    print(f"Database: {report.database_path}")
    print(f"Backup: {report.backup_path or 'not created (namespace already seeded)'}")
    for name, counts in report.per_profile.items():
        print(f"{name}: {counts['sources']} source, {counts['decisions']} decisions")
    print(
        f"Totals: {report.source_count} sources, {report.segment_count} segments, "
        f"{report.decision_count} decisions"
    )


if __name__ == "__main__":
    main()
