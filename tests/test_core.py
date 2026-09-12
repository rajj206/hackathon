import uuid
from pathlib import Path

from experttwin.db import Database
from experttwin.models import DecisionRecord, ParsedSegment
from experttwin.parsers import parse_file
from experttwin.providers import HeuristicDecisionExtractor, LocalUnavailableTranscriber
from experttwin.services import (
    ChatService,
    FingerprintService,
    IngestionService,
    RetrievalService,
)

TEXT = """
We chose Azure Data Explorer over Synapse for high-volume telemetry because Kusto
queries and ingestion latency fit the incident-response workflow. The main risk was
cost at high retention, so the budget required short hot retention.

The result reduced dashboard latency and improved on-call investigation time.
""".strip()


def test_txt_parser_and_heuristic_extraction(runtime_dir: Path):
    source = runtime_dir / "decision.txt"
    source.write_text(TEXT, encoding="utf-8")
    segments = parse_file(source)
    assert segments[0].page_or_segment == "segment 1"

    decisions = HeuristicDecisionExtractor().extract(
        "expert-1", "Asha", "source-1", "Telemetry ADR", segments
    )
    assert decisions
    assert "Synapse" in decisions[0].alternatives[0]
    assert decisions[0].rationale
    assert decisions[0].source_title == "Telemetry ADR"


def test_ingestion_fingerprint_and_retrieval(runtime_dir: Path):
    db = Database(runtime_dir / "test.db")
    db.initialize()
    expert = db.create_expert("Asha", "Data platform lead")
    source = runtime_dir / "telemetry.md"
    source.write_text(TEXT, encoding="utf-8")
    result = IngestionService(
        db, HeuristicDecisionExtractor(), LocalUnavailableTranscriber()
    ).ingest(expert.id, source, "Telemetry ADR")

    assert result.source.status == "ready"
    assert result.source.decision_count >= 1
    fingerprint = FingerprintService(db).derive(expert.id)
    assert fingerprint.decision_count == 0
    assert fingerprint.expert_attributed_decision_count == 0
    assert fingerprint.contextual_decision_count >= 1
    assert fingerprint.total_decision_count >= 1
    assert fingerprint.recurring_preferences == []

    matches = RetrievalService(db).search(expert.id, "ADX vs Synapse telemetry", 3)
    assert matches
    assert matches[0][0].source_title == "Telemetry ADR"
    assert matches[0][0].page_or_segment == "segment 1"


def test_no_decision_for_generic_summary():
    segments = [
        ParsedSegment(
            text="This document lists the team members and meeting agenda.", page_or_segment="1"
        )
    ]
    decisions = HeuristicDecisionExtractor().extract("e", "Asha", "s", "Agenda", segments)
    assert decisions == []


def test_fingerprint_uses_only_explicit_expert_attribution(runtime_dir: Path):
    database = Database(runtime_dir / "provenance.db")
    database.initialize()
    expert = database.create_expert("Asha")
    source = database.create_source(expert.id, "Architecture notes", "notes.txt", "document")
    body = DecisionRecord(
        id=str(uuid.uuid4()),
        expert_id=expert.id,
        expert=expert.name,
        decision="The document says to use an archival lake for statutory history.",
        choice="Use an archival lake",
        source_id=source.id,
        source_title=source.title,
        evidence_text="Archival lake storage supports statutory history.",
        page_or_segment="section 1",
        confidence=0.8,
    )
    attributed = DecisionRecord(
        id=str(uuid.uuid4()),
        expert_id=expert.id,
        expert=expert.name,
        decision="Use queued ingestion for incident telemetry.",
        choice="Use queued ingestion",
        source_id=source.id,
        source_title=source.title,
        evidence_text="Review comment: Use queued ingestion for incident telemetry.",
        page_or_segment="Word comment 4",
        evidence_type="review_comment",
        evidence_author="aShA",
        comment_id="4",
        confidence=0.9,
    )
    database.store_decisions([body, attributed])

    fingerprint = FingerprintService(database).derive(expert.id)

    assert fingerprint.decision_count == 1
    assert fingerprint.total_decision_count == 2
    assert fingerprint.expert_attributed_decision_count == 1
    assert fingerprint.contextual_decision_count == 1
    patterns = [pattern.pattern for pattern in fingerprint.recurring_preferences]
    assert patterns == ["Use queued ingestion"]
    assert all("archival lake" not in pattern.lower() for pattern in patterns)

    chat = ChatService(RetrievalService(database), FingerprintService(database))
    contextual_response = chat.answer(expert.id, "statutory archival history", top_k=1)
    assert contextual_response.citations[0].attribution_status == "contextual"
    assert contextual_response.expert_attributed_citation_count == 0
    assert contextual_response.contextual_citation_count == 1
    assert "CONTEXTUAL DOCUMENT CONTENT" in contextual_response.answer

    attributed_response = chat.answer(expert.id, "queued incident telemetry", top_k=1)
    assert attributed_response.citations[0].attribution_status == "expert_attributed"
    assert attributed_response.expert_attributed_citation_count == 1
    assert attributed_response.contextual_citation_count == 0
    assert "EXPERT-ATTRIBUTED JUDGMENT" in attributed_response.answer
