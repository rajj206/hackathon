import json
import sqlite3
import uuid
from pathlib import Path

from .models import DecisionRecord, Expert, PortfolioSummary, Source, utc_now


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS experts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    expert_id TEXT NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    simulation INTEGER NOT NULL DEFAULT 0,
                    simulation_namespace TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    page_or_segment TEXT NOT NULL,
                    timestamp TEXT,
                    author TEXT,
                    speaker_role TEXT,
                    comment_id TEXT,
                    anchor_text TEXT,
                    parent_comment_id TEXT,
                    parent_author TEXT,
                    parent_text TEXT
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    expert_id TEXT NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sources_expert ON sources(expert_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_expert ON decisions(expert_id);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(segments)").fetchall()
            }
            for name in (
                "author",
                "speaker_role",
                "comment_id",
                "anchor_text",
                "parent_comment_id",
                "parent_author",
                "parent_text",
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE segments ADD COLUMN {name} TEXT")
            source_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sources)").fetchall()
            }
            if "simulation" not in source_columns:
                connection.execute(
                    "ALTER TABLE sources ADD COLUMN simulation INTEGER NOT NULL DEFAULT 0"
                )
            if "simulation_namespace" not in source_columns:
                connection.execute("ALTER TABLE sources ADD COLUMN simulation_namespace TEXT")

    def create_expert(self, name: str, description: str = "") -> Expert:
        expert = Expert(
            id=str(uuid.uuid4()),
            name=name.strip(),
            description=description.strip(),
            created_at=utc_now(),
        )
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO experts(id,name,description,created_at) VALUES(?,?,?,?)",
                (expert.id, expert.name, expert.description, expert.created_at.isoformat()),
            )
        return expert

    def get_expert(self, expert_id: str) -> Expert | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM experts WHERE id=?", (expert_id,)).fetchone()
        return Expert.model_validate(dict(row)) if row else None

    def list_experts(self) -> list[Expert]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM experts ORDER BY created_at DESC").fetchall()
        return [Expert.model_validate(dict(row)) for row in rows]

    def get_portfolio_summary(self) -> PortfolioSummary:
        with self.connect() as connection:
            counts = connection.execute(
                """SELECT
                       (SELECT COUNT(*) FROM experts) AS expert_count,
                       (SELECT COUNT(*) FROM sources) AS source_count,
                       (SELECT COUNT(*) FROM decisions) AS decision_count"""
            ).fetchone()
            source_titles = connection.execute(
                """SELECT DISTINCT title
                   FROM sources
                   WHERE simulation=1
                   ORDER BY title"""
            ).fetchall()
        projects = sorted(
            {
                row["title"].split(" — ", 1)[0]
                for row in source_titles
                if " — " in row["title"]
            }
        )
        return PortfolioSummary(
            expert_count=counts["expert_count"],
            source_count=counts["source_count"],
            decision_count=counts["decision_count"],
            projects=projects,
        )

    def create_source(
        self,
        expert_id: str,
        title: str,
        filename: str,
        source_type: str,
        *,
        simulation: bool = False,
        simulation_namespace: str | None = None,
    ) -> Source:
        source = Source(
            id=str(uuid.uuid4()),
            expert_id=expert_id,
            title=title.strip(),
            filename=filename,
            source_type=source_type,
            status="processing",
            simulation=simulation,
            simulation_namespace=simulation_namespace,
            created_at=utc_now(),
        )
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO sources(
                       id,expert_id,title,filename,source_type,status,error,
                       simulation,simulation_namespace,created_at
                   )
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    source.id,
                    source.expert_id,
                    source.title,
                    source.filename,
                    source.source_type,
                    source.status,
                    None,
                    int(source.simulation),
                    source.simulation_namespace,
                    source.created_at.isoformat(),
                ),
            )
        return source

    def update_source(self, source_id: str, status: str, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE sources SET status=?, error=? WHERE id=?", (status, error, source_id)
            )

    def get_source(self, source_id: str) -> Source | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT s.*, COUNT(d.id) AS decision_count
                   FROM sources s LEFT JOIN decisions d ON d.source_id=s.id
                   WHERE s.id=? GROUP BY s.id""",
                (source_id,),
            ).fetchone()
        return Source.model_validate(dict(row)) if row else None

    def list_sources(self, expert_id: str) -> list[Source]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT s.*, COUNT(d.id) AS decision_count
                   FROM sources s LEFT JOIN decisions d ON d.source_id=s.id
                   WHERE s.expert_id=? GROUP BY s.id ORDER BY s.created_at DESC""",
                (expert_id,),
            ).fetchall()
        return [Source.model_validate(dict(row)) for row in rows]

    def store_segments(self, source_id: str, segments: list) -> None:
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO segments(
                       source_id,text,page_or_segment,timestamp,author,speaker_role
                       ,comment_id,anchor_text
                       ,parent_comment_id,parent_author,parent_text
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        source_id,
                        segment.text,
                        segment.page_or_segment,
                        segment.timestamp,
                        segment.author,
                        segment.speaker_role,
                        segment.comment_id,
                        segment.anchor_text,
                        segment.parent_comment_id,
                        segment.parent_author,
                        segment.parent_text,
                    )
                    for segment in segments
                ],
            )

    def store_decisions(self, decisions: list[DecisionRecord]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO decisions(id,expert_id,source_id,payload,created_at)
                   VALUES(?,?,?,?,?)""",
                [
                    (
                        item.id,
                        item.expert_id,
                        item.source_id,
                        item.model_dump_json(),
                        item.created_at.isoformat(),
                    )
                    for item in decisions
                ],
            )

    def list_decisions(self, expert_id: str) -> list[DecisionRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM decisions WHERE expert_id=? ORDER BY created_at DESC",
                (expert_id,),
            ).fetchall()
        return [DecisionRecord.model_validate(json.loads(row["payload"])) for row in rows]
