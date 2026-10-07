import pytest
from fastapi.testclient import TestClient
from intelligence.main import app

client = TestClient(app)


def test_analyze_schema_validity():
    payload = {
        "investigation_id": "test-inv-uuid-001",
        "area_m2": 14500.5,
        "change_type": "construction",
        "confidence": 0.92,
        "overlap_percent": 0.35,
    }
    response = client.post("/intelligence/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # 1. Fingerprint has numeric floats (never strings like "94.0%")
    fp = data["fingerprint"]
    assert fp["fingerprint_id"].startswith("TEST-") or "UC-" in fp["fingerprint_id"]
    assert fp["change_type"] == "Construction"
    assert isinstance(fp["changed_area_m2"], float)
    assert fp["changed_area_m2"] == 14500.5
    assert isinstance(fp["confidence"], float)
    assert fp["confidence"] == 0.92

    # 2. Evidence graph contains nodes and edges
    assert "evidence_graph" in data
    graph = data["evidence_graph"]
    assert "nodes" in graph and len(graph["nodes"]) >= 4
    assert "edges" in graph and len(graph["edges"]) >= 3

    # 3. Grounded explanation with 4 distinct sections
    expl = data["explanation"]
    assert "text" in expl
    assert "[Observation]" in expl["text"]
    assert "[Prediction]" in expl["text"]
    assert "[Inference]" in expl["text"]
    assert "[Uncertainty & Statutory Notice]" in expl["text"]
    assert expl["status"] == "requires_human_verification"


def test_chat_grounding_and_fallback():
    payload = {
        "question": "Why was this area flagged?",
        "evidence_ids": ["EV-SAT-A", "EV-ML-B", "EV-GIS-C"],
        "fingerprint": {
            "fingerprint_id": "UC-2026-F981",
            "change_type": "excavation",
            "changed_area_m2": 18200.0,
        },
    }
    response = client.post("/intelligence/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    # Grounding checks: cites evidence and includes disclaimer
    assert "requires_human_verification" in data["status"]
    assert "EV-SAT-A" in data["answer"] or "EV-ML-B" in data["answer"] or "EV-GIS-C" in data["answer"] or "evidence" in data["answer"]
    # Never invent legal conclusions
    assert "illegal" not in data["answer"].lower() or "not establish" in data["answer"].lower()
    assert len(data["evidence_ids"]) > 0


def test_chat_assistant_alias():
    payload = {
        "question": "How large is the detected change footprint?",
        "evidence_ids": ["EV-01"],
        "fingerprint": {
            "changed_area_m2": 12000.0,
            "change_type": "construction",
        },
    }
    # Test that /assistant alias also works
    response = client.post("/intelligence/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "12,000" in data["answer"] or "12000" in data["answer"]
    assert data["status"] == "requires_human_verification"
