from pathlib import Path

from fastapi.testclient import TestClient

from experttwin.app import create_app
from experttwin.config import Settings


def test_api_smoke_create_ingest_fingerprint_chat(runtime_dir: Path):
    app = create_app(Settings(data_dir=runtime_dir))
    with TestClient(app) as client:
        empty_summary = client.get("/api/portfolio-summary")
        assert empty_summary.status_code == 200
        assert empty_summary.json() == {
            "expert_count": 0,
            "source_count": 0,
            "decision_count": 0,
            "projects": [],
        }
        assert client.get("/health").json()["status"] == "ok"
        expert_response = client.post(
            "/api/experts",
            json={"name": "Asha", "description": "Telemetry architect"},
        )
        assert expert_response.status_code == 201
        expert_id = expert_response.json()["id"]

        upload = client.post(
            f"/api/experts/{expert_id}/sources",
            data={"title": "Telemetry ADR", "source_type": "document"},
            files={
                "file": (
                    "telemetry.txt",
                    (
                        "We chose Azure Data Explorer over Synapse for telemetry because "
                        "fast Kusto queries support incident response. The risk is retention cost. "
                        "The result improved investigation latency."
                    ),
                    "text/plain",
                )
            },
        )
        assert upload.status_code == 201, upload.text
        assert upload.json()["decisions"]

        summary = client.get("/api/portfolio-summary")
        assert summary.status_code == 200
        assert summary.json() == {
            "expert_count": 1,
            "source_count": 1,
            "decision_count": 1,
            "projects": [],
        }

        fingerprint = client.get(f"/api/experts/{expert_id}/fingerprint")
        assert fingerprint.status_code == 200
        fingerprint_payload = fingerprint.json()
        assert fingerprint_payload["decision_count"] == 0
        assert fingerprint_payload["expert_attributed_decision_count"] == 0
        assert fingerprint_payload["contextual_decision_count"] >= 1

        chat = client.post(
            f"/api/experts/{expert_id}/chat",
            json={"question": "Azure Data Explorer vs Synapse for telemetry?", "top_k": 3},
        )
        assert chat.status_code == 200
        payload = chat.json()
        assert payload["citations"]
        assert payload["citations"][0]["attribution_status"] == "contextual"
        assert payload["citations"][0]["decision_confidence"] is not None
        assert payload["expert_attributed_citation_count"] == 0
        assert payload["contextual_citation_count"] >= 1
        assert payload["simulation_notice"] == "AI Clone"
        assert payload["evidence_strength"] == "limited"


def test_local_recording_error_is_actionable(runtime_dir: Path):
    app = create_app(Settings(data_dir=runtime_dir))
    with TestClient(app) as client:
        expert_id = client.post("/api/experts", json={"name": "Asha"}).json()["id"]
        response = client.post(
            f"/api/experts/{expert_id}/sources",
            data={"source_type": "meeting-recording"},
            files={"file": ("meeting.mp3", b"not-real-audio", "audio/mpeg")},
        )
        assert response.status_code == 422
        assert "TXT transcript" in response.json()["detail"]
