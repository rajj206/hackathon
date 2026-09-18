import json
import sqlite3
import uuid
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from experttwin.app import create_app
from experttwin.config import Settings
from experttwin.db import Database
from experttwin.models import DecisionRecord
from experttwin.parsers import parse_file
from experttwin.role_simulations import (
    LEGACY_NAMESPACE,
    LEGACY_NAMESPACES,
    ROSTER,
    SIMULATION_NAMESPACE,
    SIMULATION_NOTICE,
    seed,
)
from experttwin.services import FingerprintService

BASE_CORPUS = Path("demo-data/role-simulations")
CORPUS = BASE_CORPUS / "northstar-mixed"
PROJECT_DIRS = [
    CORPUS,
    BASE_CORPUS / "atlas-commerce",
    BASE_CORPUS / "lakehouse-guardian",
    BASE_CORPUS / "release-pulse",
]
TEXT_ARTIFACTS = [
    "02-group-chat.txt",
    "03-architecture-review-transcript.txt",
    "04-architecture-review-audio-script.txt",
    "05-incident-report.md",
    "06-revised-adr.md",
    "07-measured-outcome.md",
]
REQUIRED_ARTIFACTS = [
    "01-initial-design-review.docx",
    *TEXT_ARTIFACTS,
    "04-architecture-review.wav",
    "manifest.json",
]


def test_all_role_simulation_files_are_labeled_and_complete():
    files = sorted(
        path
        for path in BASE_CORPUS.glob("*.json")
        if path.name != "portfolio-manifest.json"
    )
    assert len(files) == 11
    records = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    assert {record["evidence_author"] for record in records} == set(ROSTER)
    assert all(record["notice"] == SIMULATION_NOTICE for record in records)

    assert all((CORPUS / name).is_file() for name in REQUIRED_ARTIFACTS)
    for name in TEXT_ARTIFACTS:
        assert SIMULATION_NOTICE in (CORPUS / name).read_text(encoding="utf-8")
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["notice"] == SIMULATION_NOTICE
    assert manifest["simulation_namespace"] == LEGACY_NAMESPACES[0]
    assert len(manifest["artifacts"]) == 7
    portfolio = json.loads(
        (BASE_CORPUS / "portfolio-manifest.json").read_text(encoding="utf-8")
    )
    assert portfolio["notice"] == SIMULATION_NOTICE
    assert len(portfolio["projects"]) == 4
    for project_dir in PROJECT_DIRS[1:]:
        project_manifest = json.loads(
            (project_dir / "manifest.json").read_text(encoding="utf-8")
        )
        assert project_manifest["notice"] == SIMULATION_NOTICE
        assert len(project_manifest["artifacts"]) == 4
        assert {
            decision["evidence_author"]
            for decision in project_manifest["decisions"]
        } == set(ROSTER)
        for artifact in project_manifest["artifacts"]:
            content = (project_dir / artifact["filename"]).read_text(encoding="utf-8")
            assert SIMULATION_NOTICE in content

    body = "\n".join(
        segment.text
        for segment in parse_file(CORPUS / "01-initial-design-review.docx")
        if segment.comment_id is None
    )
    assert SIMULATION_NOTICE in body


def test_mixed_docx_has_threaded_attribution_for_all_profiles():
    segments = parse_file(CORPUS / "01-initial-design-review.docx")
    comments = [segment for segment in segments if segment.comment_id]
    assert len(comments) == 12
    assert {comment.author for comment in comments} == set(ROSTER)
    assert sum(comment.parent_comment_id is not None for comment in comments) == 6
    assert all(SIMULATION_NOTICE in comment.text for comment in comments)
    for name in ROSTER:
        selected = [
            segment
            for segment in parse_file(
                CORPUS / "01-initial-design-review.docx", reviewer_name=name
            )
            if segment.comment_id
        ]
        assert selected
        assert all(segment.author == name for segment in selected)


def test_mixed_transcripts_cover_all_speakers_and_wav_is_valid():
    for filename in ("02-group-chat.txt", "03-architecture-review-transcript.txt"):
        turns = [
            segment for segment in parse_file(CORPUS / filename) if segment.author
        ]
        assert {turn.author for turn in turns} == set(ROSTER)
        assert all(turn.speaker_role == ROSTER[turn.author] for turn in turns)
        assert all(SIMULATION_NOTICE in turn.text for turn in turns)
    architecture_text = (CORPUS / "03-architecture-review-transcript.txt").read_text(
        encoding="utf-8"
    )
    for decision_word in ("Accepted:", "Rejected:", "Refined:"):
        assert decision_word in architecture_text

    script = (CORPUS / "04-architecture-review-audio-script.txt").read_text(
        encoding="utf-8"
    )
    assert all(name in script for name in ROSTER)
    with wave.open(str(CORPUS / "04-architecture-review.wav"), "rb") as recording:
        assert recording.getnchannels() == 1
        assert recording.getsampwidth() == 2
        assert recording.getframerate() == 22050
        assert 5 < recording.getnframes() / recording.getframerate() < 120


def test_seeder_is_idempotent_attributable_offline_and_preserves_other_sources(
    runtime_dir: Path, monkeypatch
):
    database_path = runtime_dir / "experttwin.db"
    database = Database(database_path)
    database.initialize()
    existing = database.create_expert("Existing Approved Expert", "Approved evidence")
    approved = database.create_source(
        existing.id, "Approved source", "approved.txt", "document"
    )
    database.update_source(approved.id, "ready")
    legacy = database.create_source(
        existing.id,
        "Superseded simulation",
        "old.json",
        "document",
        simulation=True,
        simulation_namespace=LEGACY_NAMESPACE,
    )
    database.update_source(legacy.id, "ready")

    def azure_provider_must_not_run(*_args, **_kwargs):
        raise AssertionError("Azure provider was invoked by the offline seeder")

    monkeypatch.setattr(
        "experttwin.providers.AzureOpenAIAnswerer.__init__", azure_provider_must_not_run
    )
    monkeypatch.setattr(
        "experttwin.providers.AzureOpenAIDecisionExtractor.__init__",
        azure_provider_must_not_run,
    )
    monkeypatch.setattr(
        "experttwin.providers.AzureSpeechTranscriber.__init__",
        azure_provider_must_not_run,
    )

    first = seed(database_path)
    assert first.backup_path and first.backup_path.is_file()
    assert first.source_count == 209
    assert first.segment_count == 209
    assert first.decision_count == 77

    with sqlite3.connect(database_path) as connection:
        first_source_ids = {
            row[0]
            for row in connection.execute(
                "SELECT id FROM sources WHERE simulation_namespace=?",
                (SIMULATION_NAMESPACE,),
            )
        }
        first_decision_ids = {
            row[0]
            for row in connection.execute(
                """SELECT d.id FROM decisions d
                   JOIN sources s ON s.id=d.source_id
                   WHERE s.simulation_namespace=?""",
                (SIMULATION_NAMESPACE,),
            )
        }

    second = seed(database_path)
    assert second.backup_path is None
    assert second.source_count == first.source_count
    assert second.segment_count == first.segment_count
    assert second.decision_count == first.decision_count

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sources WHERE id=?", (approved.id,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM sources WHERE simulation_namespace=?",
            (LEGACY_NAMESPACE,),
        ).fetchone()[0] == 0
        assert {
            row[0]
            for row in connection.execute(
                "SELECT id FROM sources WHERE simulation_namespace=?",
                (SIMULATION_NAMESPACE,),
            )
        } == first_source_ids
        assert {
            row[0]
            for row in connection.execute(
                """SELECT d.id FROM decisions d
                   JOIN sources s ON s.id=d.source_id
                   WHERE s.simulation_namespace=?""",
                (SIMULATION_NAMESPACE,),
            )
        } == first_decision_ids

    seeded_database = Database(database_path)
    first_profile = next(
        item for item in seeded_database.list_experts() if item.name == next(iter(ROSTER))
    )
    unrelated = seeded_database.create_source(
        first_profile.id,
        "Unrelated approved source",
        "unrelated.txt",
        "document",
    )
    seeded_database.store_decisions(
        [
            DecisionRecord(
                id=str(uuid.uuid4()),
                expert_id=first_profile.id,
                expert=first_profile.name,
                decision="Unrelated non-simulation decision",
                choice="Keep unrelated approved evidence",
                source_id=unrelated.id,
                source_title=unrelated.title,
                evidence_text="This non-simulation record must not enter the role fingerprint.",
                page_or_segment="segment 1",
                evidence_author=first_profile.name,
                confidence=0.9,
            )
        ]
    )
    for name in ROSTER:
        expert = next(item for item in seeded_database.list_experts() if item.name == name)
        assert expert.description == ROSTER[name]
        sources = [
            source
            for source in seeded_database.list_sources(expert.id)
            if source.simulation_namespace == SIMULATION_NAMESPACE
        ]
        decisions = [
            decision
            for decision in seeded_database.list_decisions(expert.id)
            if decision.simulation_namespace == SIMULATION_NAMESPACE
        ]
        assert len(sources) == 19
        assert {source.source_type for source in sources} == {
            "document",
            "meeting-transcript",
            "meeting-recording",
        }
        assert {
            source.title.split(" — ", 1)[0] for source in sources
        } == {
            "Project Northstar",
            "Project Atlas Commerce",
            "Project Lakehouse Guardian",
            "Project Release Pulse",
        }
        assert len(decisions) == 7
        assert all(decision.evidence_author == name for decision in decisions)
        assert all(decision.simulation for decision in decisions)
        fingerprint = FingerprintService(seeded_database).derive(expert.id)
        assert fingerprint.decision_count == len(decisions)
        assert fingerprint.total_decision_count == len(decisions)
        assert fingerprint.contextual_decision_count == 0


def test_seeded_api_and_ui_keep_simulation_markers_internal(runtime_dir: Path):
    seed(runtime_dir / "experttwin.db")
    app = create_app(Settings(data_dir=runtime_dir))
    with TestClient(app) as client:
        html = client.get("/").text
        experts = client.get("/api/experts").json()
        selected = next(expert for expert in experts if expert["name"] == "Tulika")
        sources = client.get(f"/api/experts/{selected['id']}/sources").json()
        decisions = client.get(f"/api/experts/{selected['id']}/decisions").json()

    assert "AI Clone" in html
    assert "SYNTHETIC ROLE-BASED SIMULATION" not in html
    assert {expert["name"] for expert in experts} == set(ROSTER)
    assert "Maya Rao" not in {expert["name"] for expert in experts}
    assert len(sources) == 19
    assert all(source["simulation"] is True for source in sources)
    assert all(decision["simulation"] is True for decision in decisions)
