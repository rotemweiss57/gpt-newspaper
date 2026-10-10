import json

import pytest
from fastapi.testclient import TestClient

import backend.graph as graph_module
import backend.server as server
from backend.llm import get_chat_model


@pytest.fixture
def client(tmp_path, monkeypatch, fake_llm, fake_search):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(server, "get_chat_model", lambda *a, **k: fake_llm)
    monkeypatch.setattr(graph_module, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(server, "NewspaperContext", lambda model: graph_module.NewspaperContext(model=model, output_dir=str(tmp_path / "run")))
    return TestClient(server.app)


def test_config(client):
    body = client.get("/api/config").json()
    assert body["model"] and body["max_topics"] == server.MAX_TOPICS


def test_frontend_is_served(client):
    assert "GPT Newspaper" in client.get("/").text


def test_stream_endpoint(client, tmp_path):
    response = client.post("/api/newspaper", json={"topics": ["  quantum  "], "layout": "layout_2.html"})
    assert response.headers["content-type"] == "application/x-ndjson"
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["type"] == "progress" and events[0]["topic"] == "quantum"
    assert events[-1] == {"type": "done", "url": "/outputs/run/newspaper.html", "articles": 1}
    assert (tmp_path / "run" / "newspaper.html").exists()


def test_legacy_endpoint(client):
    assert client.post("/generate_newspaper", json={"topics": ["quantum"], "layout": "layout_1.html"}).json() == {
        "path": "/outputs/run/newspaper.html"
    }


def test_rejects_bad_input(client):
    assert client.post("/api/newspaper", json={"topics": [], "layout": "layout_1"}).status_code == 422
    assert client.post("/api/newspaper", json={"topics": [" "], "layout": "layout_1"}).status_code == 422
    assert client.post("/api/newspaper", json={"topics": ["x"], "layout": "layout_9"}).status_code == 422


def test_missing_tavily_key(client, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY")
    response = client.post("/api/newspaper", json={"topics": ["x"]})
    assert response.status_code == 400 and "TAVILY_API_KEY" in response.json()["detail"]


def test_unknown_model_provider(client, monkeypatch):
    monkeypatch.setattr(server, "get_chat_model", get_chat_model)
    response = client.post("/api/newspaper", json={"topics": ["x"], "model": "not-a-provider:foo"})
    assert response.status_code == 400 and "not-a-provider:foo" in response.json()["detail"]
