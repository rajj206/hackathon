"""Explicit, offline-only ingestion helper for the synthetic AtlasAudit corpus."""

import argparse
from pathlib import Path

from experttwin.config import Settings
from experttwin.db import Database
from experttwin.providers import HeuristicDecisionExtractor, LocalUnavailableTranscriber
from experttwin.services import IngestionService

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "demo-data" / "atlas-audit"
SOURCES = [
    ("01-initial-design-review.docx", "AtlasAudit Initial Design Review", "document"),
    ("02-design-challenge-chat.txt", "AtlasAudit Design Challenge Chat", "meeting-transcript"),
    (
        "03-architecture-review-transcript.txt",
        "AtlasAudit Architecture Review Meeting",
        "meeting-transcript",
    ),
    ("05-incident-report.md", "AtlasAudit Export Lag Incident", "document"),
    ("06-revised-adr.md", "AtlasAudit ADR-007 Revision", "document"),
    ("07-three-month-outcome.md", "AtlasAudit Three-Month Outcome", "document"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement; without it no database is created or changed.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "demo-data" / ".atlas-demo-runtime",
    )
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("No action taken. Re-run with --execute for offline local ingestion.")

    settings = Settings(
        data_dir=args.data_dir,
        extractor_provider="heuristic",
        chat_provider="local",
        transcription_provider="local",
    )
    settings.prepare()
    database = Database(settings.database_path)
    database.initialize()
    expert = next(
        (item for item in database.list_experts() if item.name.casefold() == "maya rao"),
        None,
    ) or database.create_expert(
        "Maya Rao",
        "Fictional AtlasAudit Engineering Manager",
    )
    ingestion = IngestionService(
        database,
        HeuristicDecisionExtractor(),
        LocalUnavailableTranscriber(),
    )
    total = 0
    for filename, title, source_type in SOURCES:
        result = ingestion.ingest(expert.id, CORPUS / filename, title, source_type)
        total += len(result.decisions)
        print(f"{title}: {len(result.decisions)} decisions")
    print(f"Offline ingestion complete: {total} decisions for {expert.name}")
    print(f"Database: {settings.database_path}")


if __name__ == "__main__":
    main()
