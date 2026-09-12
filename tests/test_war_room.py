import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from experttwin.app import create_app
from experttwin.config import Settings
from experttwin.db import Database
from experttwin.models import DecisionRecord
from experttwin.roster import AUTHORIZED_NAMES, AUTHORIZED_ROSTER, MANAGER_NAME
from experttwin.services import RetrievalService
from experttwin.war_room import (
    AzureOpenAIWarRoomOrchestrator,
    WarRoomGenerationError,
    WarRoomOrchestrator,
    WarRoomService,
    WarRoomValidationError,
)


def _populate_roster(database: Database) -> dict[str, list[str]]:
    decision_ids = {}
    for profile in reversed(AUTHORIZED_ROSTER):
        expert = database.create_expert(profile.name, profile.role)
        source = database.create_source(
            expert.id,
            f"War Room evidence for {profile.name}",
            "evidence.txt",
            "document",
        )
        database.update_source(source.id, "ready")
        decisions = []
        for index in range(3):
            decision_id = str(uuid.uuid4())
            decisions.append(
                DecisionRecord(
                    id=decision_id,
                    expert_id=expert.id,
                    expert=profile.name,
                    decision=f"Evaluate queue reliability option {index + 1}",
                    choice=f"Use bounded queue reliability option {index + 1}",
                    alternatives=["Use unbounded synchronous processing"],
                    rationale=["Bounded processing keeps recovery predictable"],
                    constraints=["One concise War Room recommendation"],
                    risks=["Backlog growth"],
                    outcome="Synthetic replay completed without data loss.",
                    source_id=source.id,
                    source_title=source.title,
                    evidence_text=(
                        f"{profile.name} selected bounded queue reliability option "
                        f"{index + 1} for predictable recovery."
                    ),
                    page_or_segment=f"decision {index + 1}",
                    evidence_author=profile.name,
                    evidence_role=profile.role,
                    confidence=0.9,
                )
            )
        database.store_decisions(decisions)
        decision_ids[profile.name] = [decision.id for decision in decisions]
    return decision_ids


def _valid_payload(decision_ids: dict[str, list[str]]) -> dict:
    messages = []
    for index, profile in enumerate(AUTHORIZED_ROSTER, start=1):
        ids = decision_ids[profile.name]
        message_type = "position"
        responds_to = None
        mentions = []
        if index == 1:
            message_type = "frame"
            mentions = ["Amrita Shanbhag", "Rajendra Kalepu"]
        elif profile.name == "Kumar Ritesh":
            message_type = "challenge"
            responds_to = "m2"
            mentions = ["Amrita Shanbhag"]
        elif profile.name == "Manish Patil":
            message_type = "refinement"
            responds_to = "m4"
            mentions = ["Kumar Ritesh"]
        messages.append(
            {
                "message_id": f"m{index}",
                "speaker": profile.name,
                "role": profile.role,
                "ai_clone": True,
                "text": (
                    (
                        "I disagree with the prior boundary: the evidence supports a bounded "
                        "queue only when readiness reports projection lag."
                        if message_type == "challenge"
                        else (
                            "Refining that challenge: retain the bounded queue and add "
                            "dependency-specific readiness plus backlog-age gates."
                            if message_type == "refinement"
                            else (
                                "The data perspective requires contract validity, freshness, "
                                "uniqueness, and reconciliation metrics."
                                if profile.name == "Rajendra Kalepu"
                                else (
                                    f"{profile.name} AI Clone recommends a bounded queue "
                                    "with explicit recovery evidence."
                                )
                            )
                        )
                    )
                    if ids
                    else "Evidence is insufficient for this AI Clone to recommend an option."
                ),
                "message_type": message_type,
                "responds_to": responds_to,
                "mentions": mentions,
                "evidence_strength": "strong" if ids else "insufficient",
                "citation_ids": [ids[-1]] if ids else [],
            }
        )
    return {
        "messages": messages,
        "final_decision": {
            "decision_owner": MANAGER_NAME,
            "recommendation": "Adopt a bounded queue behind measurable release gates.",
            "rationale_tradeoffs": [
                "It isolates command acceptance while accepting observable projection lag."
            ],
            "dissenting_views": [
                {
                    "name": "Vishwas Srivastava",
                    "view": "Keep the adapter boundary explicit to preserve reversibility.",
                }
            ],
            "risks_mitigations": [
                {
                    "risk": "Queue backlog can increase.",
                    "mitigation": "Alert on age and use replay-safe checkpoints.",
                }
            ],
            "action_items": [
                {
                    "owner": MANAGER_NAME,
                    "action": "Confirm the release gate and final go/no-go decision.",
                },
                {
                    "owner": "Tulika",
                    "action": "Run the bounded-concurrency recovery drill.",
                },
            ],
            "citation_ids": [
                decision_ids[MANAGER_NAME][-1],
                decision_ids["Tulika"][-1],
            ],
        },
    }


def _retrieved_decision_ids(database: Database) -> dict[str, list[str]]:
    experts = {expert.name: expert for expert in database.list_experts()}
    retrieval = RetrievalService(database)
    return {
        profile.name: [
            decision.id
            for decision, _score in retrieval.search(
                experts[profile.name].id,
                "Should we use a bounded queue for reliability?",
                2,
            )
        ]
        for profile in AUTHORIZED_ROSTER
    }


class RecordingOrchestrator(WarRoomOrchestrator):
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        self.calls.append((system_prompt, user_prompt, schema))
        return self.payload


def test_war_room_uses_stable_roster_bounded_separate_evidence_and_one_call(runtime_dir):
    database = Database(runtime_dir / "war-room.db")
    database.initialize()
    _populate_roster(database)
    decision_ids = _retrieved_decision_ids(database)
    payload = _valid_payload(decision_ids)
    payload["messages"][0]["role"] = "Engineering Manager"
    payload["messages"][0]["mentions"] = [
        "Amrita Shanbhag AI Clone) — Senior Software Engineer — Participant 2. "
        "Rajendra Kalepu AI Clone) — Senior Data Engineer — Participant 8. "
        "Unknown prompt text"
    ]
    next(
        message for message in payload["messages"] if message["speaker"] == "Manish Patil"
    )["citation_ids"] = []
    payload["final_decision"]["citation_ids"] = [
        "".join(payload["final_decision"]["citation_ids"])
    ]
    orchestrator = RecordingOrchestrator(payload)
    service = WarRoomService(
        database,
        RetrievalService(database),
        orchestrator,
        prompt_budget=24000,
    )

    prompt, _citations, participant_citations = service.build_prompt(
        "Should we use a bounded queue for reliability?"
    )
    assert len(prompt) <= 24000
    assert list(participant_citations) == list(AUTHORIZED_NAMES)
    assert all(len(ids) == 2 for ids in participant_citations.values())
    assert prompt.index(MANAGER_NAME) < prompt.index("Amrita Shanbhag")
    for index, profile in enumerate(AUTHORIZED_ROSTER):
        block_start = prompt.index(f"PARTICIPANT: {profile.name} (AI Clone)")
        block_end = (
            prompt.index("PARTICIPANT:", block_start + 1)
            if index < len(AUTHORIZED_ROSTER) - 1
            else len(prompt)
        )
        block = prompt[block_start:block_end]
        assert participant_citations[profile.name]
        assert all(decision_id in block for decision_id in participant_citations[profile.name])

    response = service.run("Should we use a bounded queue for reliability?")
    assert len(orchestrator.calls) == 1
    assert [message.speaker for message in response.messages] == list(AUTHORIZED_NAMES)
    assert [message.role for message in response.messages] == [
        profile.role for profile in AUTHORIZED_ROSTER
    ]
    assert next(
        message for message in response.messages if message.speaker == "Manish Patil"
    ).citation_ids
    assert response.messages[0].mentions == ["Amrita Shanbhag", "Rajendra Kalepu"]
    assert len(response.final_decision.citation_ids) == 2
    assert all(message.ai_clone is True for message in response.messages)
    challenge = next(
        message for message in response.messages if message.message_type == "challenge"
    )
    refinement = next(
        message for message in response.messages if message.message_type == "refinement"
    )
    assert refinement.responds_to == challenge.message_id
    assert response.moderator == MANAGER_NAME
    assert response.final_decision.decision_owner == MANAGER_NAME
    assert response.citations


def test_war_room_explicitly_marks_participant_without_evidence(runtime_dir):
    database = Database(runtime_dir / "insufficient.db")
    database.initialize()
    _populate_roster(database)
    expert = next(
        item for item in database.list_experts() if item.name == "Siya Sharma"
    )
    with database.connect() as connection:
        connection.execute("DELETE FROM decisions WHERE expert_id=?", (expert.id,))
    decision_ids = _retrieved_decision_ids(database)
    orchestrator = RecordingOrchestrator(_valid_payload(decision_ids))
    response = WarRoomService(
        database, RetrievalService(database), orchestrator
    ).run("Should we use a bounded queue for reliability?")

    message = next(item for item in response.messages if item.speaker == "Siya Sharma")
    assert message.evidence_strength == "insufficient"
    assert message.citation_ids == []
    assert "Evidence is insufficient" in message.text
    assert len(orchestrator.calls) == 1


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (
            lambda payload: payload["messages"].pop(),
            "schema validation",
        ),
        (
            lambda payload: payload["messages"][0]["citation_ids"].__setitem__(
                0, "invented-id"
            ),
            "not retrieved",
        ),
        (
            lambda payload: payload["final_decision"]["action_items"].append(
                {"owner": "Unknown Person", "action": "Own an action."}
            ),
            "Unknown War Room action owner",
        ),
        (
            lambda payload: payload["messages"][1]["mentions"].append("Unknown Person"),
            "mentions unknown participant",
        ),
    ],
)
def test_war_room_rejects_invalid_structured_output(runtime_dir, mutation, expected):
    database = Database(runtime_dir / "invalid.db")
    database.initialize()
    _populate_roster(database)
    decision_ids = _retrieved_decision_ids(database)
    payload = _valid_payload(decision_ids)
    mutation(payload)
    orchestrator = RecordingOrchestrator(payload)
    service = WarRoomService(database, RetrievalService(database), orchestrator)

    with pytest.raises(WarRoomValidationError, match=expected):
        service.run("Should we use a bounded queue for reliability?")
    assert len(orchestrator.calls) == 1


def test_war_room_api_success_unavailable_and_validation_failure(runtime_dir):
    settings = Settings(data_dir=runtime_dir)
    database = Database(settings.database_path)
    database.initialize()
    _populate_roster(database)
    decision_ids = _retrieved_decision_ids(database)

    success_orchestrator = RecordingOrchestrator(_valid_payload(decision_ids))
    success_app = create_app(settings, war_room_orchestrator=success_orchestrator)
    with TestClient(success_app) as client:
        response = client.post(
            "/api/war-room",
            json={"topic": "Should we use a bounded queue for reliability?"},
        )
    assert response.status_code == 200
    assert len(response.json()["messages"]) == 11
    assert len(success_orchestrator.calls) == 1

    unavailable_app = create_app(settings)
    with TestClient(unavailable_app) as client:
        unavailable = client.post(
            "/api/war-room",
            json={"topic": "Should we use a bounded queue for reliability?"},
        )
    assert unavailable.status_code == 503
    assert "WAR_ROOM_PROVIDER" in unavailable.json()["detail"]

    invalid_payload = _valid_payload(decision_ids)
    invalid_payload["final_decision"]["citation_ids"] = ["hallucinated"]
    invalid_app = create_app(
        settings,
        war_room_orchestrator=RecordingOrchestrator(invalid_payload),
    )
    with TestClient(invalid_app) as client:
        invalid = client.post(
            "/api/war-room",
            json={"topic": "Should we use a bounded queue for reliability?"},
        )
    assert invalid.status_code == 502
    assert "unverified citation" in invalid.json()["detail"]

    with TestClient(success_app) as client:
        assert client.post("/api/war-room", json={"topic": "no"}).status_code == 422
        assert client.post(
            "/api/war-room", json={"topic": "x" * 2001}
        ).status_code == 422


def test_azure_orchestrator_uses_strict_json_schema_without_temperature():
    requests = []
    payload = {"participants": [], "final_decision": {}}

    class Completions:
        def create(self, **kwargs):
            requests.append(kwargs)
            message = SimpleNamespace(content=json.dumps(payload))
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    orchestrator = AzureOpenAIWarRoomOrchestrator.__new__(
        AzureOpenAIWarRoomOrchestrator
    )
    orchestrator.settings = Settings(
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_chat_deployment="gpt-5.6-sol",
        azure_openai_api_version="2025-04-01-preview",
    )
    orchestrator.client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    assert orchestrator.generate("system", "user", {"type": "object"}) == payload
    assert len(requests) == 1
    assert requests[0]["model"] == "gpt-5.6-sol"
    assert requests[0]["response_format"]["type"] == "json_schema"
    assert requests[0]["response_format"]["json_schema"]["strict"] is True
    assert "temperature" not in requests[0]


def test_azure_orchestrator_rejects_malformed_json():
    class Completions:
        def create(self, **_kwargs):
            message = SimpleNamespace(content="{not-json")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    orchestrator = AzureOpenAIWarRoomOrchestrator.__new__(
        AzureOpenAIWarRoomOrchestrator
    )
    orchestrator.settings = Settings(
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_chat_deployment="gpt-5.6-sol",
    )
    orchestrator.client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    with pytest.raises(WarRoomGenerationError, match="malformed JSON"):
        orchestrator.generate("system", "user", {"type": "object"})
