from fastapi.testclient import TestClient

from experttwin.app import create_app
from experttwin.config import Settings


def test_simple_two_column_workspace_has_critical_accessible_hooks(runtime_dir):
    app = create_app(Settings(data_dir=runtime_dir))
    with TestClient(app) as client:
        response = client.get("/")
        css = client.get("/static/style.css")
        script = client.get("/static/app.js")

    assert response.status_code == 200
    html = response.text
    for person in (
        "Hrishikesh Mohile",
        "Amrita Shanbhag",
        "Devarakonda Sathish",
        "Kumar Ritesh",
        "Manish Patil",
        "Nishikant Lambat",
        "Rajendra Kalepu",
        "Satyajit Sahu",
        "Siya Sharma",
        "Tulika",
        "Vishwas Srivastava",
    ):
        assert person in html
    for fictional_person in (
        "Maya Rao",
        "Daniel Kim",
        "Priya Nair",
        "Luis Martinez",
        "Aisha Khan",
        "Ethan Brooks",
    ):
        assert fictional_person not in html
    assert "Hrishikesh Mohile (AI Clone)" in html
    assert "Evidence-grounded AI employees" in html
    assert "synthetic demo scenario is separate" in html
    assert "SYNTHETIC ROLE-BASED SIMULATION" not in html
    assert "/static/style.css?v=minimal-ui-20260918-1" in html
    assert "/static/app.js?v=minimal-ui-20260918-1" in html
    assert "app-rail" not in html
    assert "evidence-panel" not in html
    for hook in (
        'id="expertSelect"',
        'id="uploadForm"',
        'id="messages"',
        'id="chatForm"',
        'id="fingerprintGrid"',
        'id="sourceList"',
        'id="decisionList"',
        'id="warRoomTab"',
        'id="warRoomForm"',
        'id="warRoomTopic"',
        'id="warRoomResult"',
        'role="tablist"',
        'aria-live="polite"',
    ):
        assert hook in html

    assert css.status_code == 200
    assert ":focus-visible" in css.text
    assert "@media (max-width: 900px)" in css.text
    assert "grid-template-columns: 296px minmax(0, 1fr)" in css.text
    assert "backdrop-filter" in css.text
    assert "@media (prefers-reduced-motion: reduce)" in css.text
    assert "https://" not in css.text

    assert script.status_code == 200
    assert "selectedExpert?.name" in script.text
    assert "(AI Clone)" in script.text
    assert "citationMarkup(citations)" in script.text
    assert "answer-evidence" in script.text
    assert "button.disabled = true" in script.text
    assert "escapeHtml" in script.text
    assert 'api("/api/war-room"' in script.text
    assert "Running one Azure call" in script.text
    assert "renderWarRoom(response)" in script.text
    assert "user-opening" in script.text
    assert "response.topic" in script.text
    assert "response.messages.map" in script.text
