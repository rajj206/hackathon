import json
from pathlib import Path
from types import SimpleNamespace

from experttwin import providers
from experttwin.config import Settings
from experttwin.db import Database
from experttwin.parsers import parse_file
from experttwin.providers import (
    AzureOpenAIDecisionExtractor,
    HeuristicDecisionExtractor,
    LocalUnavailableTranscriber,
)
from experttwin.services import FingerprintService, IngestionService


def test_dated_chat_turns_preserve_speaker_role_and_continuation(runtime_dir: Path):
    path = runtime_dir / "chat.txt"
    path.write_text(
        """
Synthetic transcript context.

[2026-07-04 09:05] Maya Rao (Engineering Manager): We chose the phased rollout
because recovery must be measured before expansion.
[2026-07-04 09:08] Daniel Kim (Senior SWE): I recommend immutable manifests.
They should include sequence ranges and record counts.
""".strip(),
        encoding="utf-8",
    )

    segments = parse_file(path)

    assert segments[0].page_or_segment == "transcript context"
    assert len(segments) == 3
    maya, daniel = segments[1:]
    assert maya.author == "Maya Rao"
    assert maya.speaker_role == "Engineering Manager"
    assert maya.timestamp == "2026-07-04 09:05"
    assert maya.page_or_segment == (
        "chat turn at 2026-07-04 09:05 — Maya Rao (Engineering Manager)"
    )
    assert "because recovery must be measured" in maya.text
    assert daniel.author == "Daniel Kim"
    assert "sequence ranges and record counts" in daniel.text


def test_meeting_turns_support_time_only_and_optional_role(runtime_dir: Path):
    path = runtime_dir / "meeting.txt"
    path.write_text(
        """
[00:00] Maya Rao: Start with the reliability gate.
[01:12] Luis Martinez (SWE II): I suggest backlog alerts.
Include oldest-batch age as a separate signal.
""".strip(),
        encoding="utf-8",
    )

    segments = parse_file(path)

    assert len(segments) == 2
    assert segments[0].author == "Maya Rao"
    assert segments[0].speaker_role is None
    assert segments[0].page_or_segment == "meeting turn at 00:00 — Maya Rao"
    assert segments[1].speaker_role == "SWE II"
    assert "oldest-batch age" in segments[1].text


def test_ordinary_txt_uses_existing_chunk_fallback(runtime_dir: Path):
    path = runtime_dir / "notes.txt"
    path.write_text("An ordinary note without named transcript turns.", encoding="utf-8")

    segments = parse_file(path)

    assert len(segments) == 1
    assert segments[0].page_or_segment == "segment 1"
    assert segments[0].author is None


def test_transcript_fingerprint_uses_only_selected_speaker(runtime_dir: Path):
    path = runtime_dir / "decisions.txt"
    path.write_text(
        """
[00:00] Maya Rao (Engineering Manager): We chose phased rollout because recovery is measurable.
[00:20] Daniel Kim (Senior SWE): I recommend immutable manifests because gaps are detectable.
""".strip(),
        encoding="utf-8",
    )
    database = Database(runtime_dir / "transcript.db")
    database.initialize()
    expert = database.create_expert("maya rao")

    result = IngestionService(
        database,
        HeuristicDecisionExtractor(),
        LocalUnavailableTranscriber(),
    ).ingest(expert.id, path, "Architecture meeting", "meeting-transcript")
    fingerprint = FingerprintService(database).derive(expert.id)

    assert len(result.decisions) == 2
    assert {decision.evidence_type for decision in result.decisions} == {"transcript_turn"}
    assert {decision.evidence_author for decision in result.decisions} == {
        "Maya Rao",
        "Daniel Kim",
    }
    assert fingerprint.total_decision_count == 2
    assert fingerprint.expert_attributed_decision_count == 1
    assert fingerprint.contextual_decision_count == 1
    assert all(
        "immutable manifests" not in pattern.pattern.lower()
        for pattern in fingerprint.recurring_preferences
    )


def test_azure_transcript_prompt_preserves_speaker_attribution(runtime_dir: Path, monkeypatch):
    path = runtime_dir / "meeting.txt"
    path.write_text(
        "[00:15] Priya Nair (Senior SWE): I recommend one ingress path.\n"
        "It reduces partial-success handling.",
        encoding="utf-8",
    )
    segment = parse_file(path)[0]
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        decision = {
            "decision": "Use one ingress path.",
            "choice": "One ingress path",
            "alternatives": [],
            "rationale": ["Reduces partial-success handling"],
            "constraints": [],
            "risks": [],
            "outcome": None,
            "tags": ["reliability"],
            "confidence": 0.8,
        }
        message = SimpleNamespace(content=json.dumps({"decisions": [decision]}))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(providers, "_azure_openai_client", lambda _settings: fake_client)
    extractor = AzureOpenAIDecisionExtractor(
        Settings(
            azure_openai_endpoint="https://example.invalid/",
            azure_openai_chat_deployment="test-deployment",
        )
    )

    decisions = extractor.extract("expert", "Maya Rao", "source", "Meeting", [segment])

    prompt = requests[0]["messages"][-1]["content"]
    assert "Evidence type: attributed transcript turn" in prompt
    assert "Speaker: Priya Nair (Senior SWE)" in prompt
    assert "Selected expert: Maya Rao" in prompt
    assert "Attribute statements only to the named speaker" in prompt
    assert "temperature" not in requests[0]
    assert decisions[0].evidence_type == "transcript_turn"
    assert decisions[0].evidence_author == "Priya Nair"
    assert decisions[0].evidence_role == "Senior SWE"
    assert "Attributed transcript statement by Priya Nair (Senior SWE)" in (
        decisions[0].evidence_text
    )
    ui_script = Path("src/experttwin/static/app.js").read_text(encoding="utf-8")
    assert "Attributed context" in ui_script
    assert "evidence_role" in ui_script
