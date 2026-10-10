import json

import pytest
from fastapi.testclient import TestClient

import backend.server as server
import backend.setup as setup
from backend.config import NewspaperContext
from backend.llm import get_chat_model


@pytest.fixture
def client(outputs_dir, monkeypatch, fake_llm, fake_search):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")  # the default model's provider
    monkeypatch.setattr(setup, "get_chat_model", lambda *a, **k: fake_llm)
    contexts = []

    def make_context(**kwargs):
        contexts.append(NewspaperContext(**kwargs, output_dir=str(outputs_dir / f"run{len(contexts)}")))
        return contexts[-1]

    monkeypatch.setattr(setup, "NewspaperContext", make_context)
    client = TestClient(server.app)
    client.contexts = contexts
    return client


def read_events(response):
    return [json.loads(line) for line in response.text.splitlines()]


def test_config(client):
    body = client.get("/api/config").json()
    assert body["model"] and body["max_topics"] == server.MAX_TOPICS and body["version"]
    assert body["languages"]["he"] == "עברית"
    assert body["images"]["styles"]["photos"] == "News photos" and "ink" in body["images"]["styles"]
    # Reports which keys exist, never their values
    assert body["server_keys"]["tavily"] is True and body["server_keys"]["ollama"] is True
    assert "tvly-test" not in json.dumps(body)


def test_frontend_and_security_headers(client):
    response = client.get("/")
    assert "GPT Newspaper" in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert client.get("/static/scripts.js").headers["cache-control"] == "no-cache"


def test_stream_endpoint_and_archive(client):
    response = client.post(
        "/api/newspaper", json={"topics": ["  quantum  "], "layout": "layout_2.html", "language": "fr"}
    )
    assert response.headers["content-type"] == "application/x-ndjson"
    events = read_events(response)
    assert events[0]["type"] == "progress" and events[0]["topic"] == "quantum"
    assert events[-1] == {"type": "done", "url": "/outputs/run0/newspaper.html", "articles": 1, "failed": 0}
    assert client.contexts[-1].language == "French"

    page = client.get(events[-1]["url"])
    assert page.status_code == 200
    assert "script-src 'unsafe-inline'" in page.headers["content-security-policy"]

    [edition] = client.get("/api/editions").json()
    assert edition["url"] == "/outputs/run0/newspaper.html"
    # Illustrated by default (the server has an OpenAI key in this test)
    assert edition["topics"] == ["quantum"] and edition["image"] == "/outputs/run0/01-quantum.webp"


def test_news_photos_mode(client, fake_images):
    response = client.post("/api/newspaper", json={"topics": ["quantum"], "images": "photos"})
    assert read_events(response)[-1]["type"] == "done"
    assert client.contexts[-1].image_style is None and fake_images == []


def test_legacy_endpoint(client):
    response = client.post("/generate_newspaper", json={"topics": ["quantum"], "layout": "layout_1.html"})
    assert response.json() == {"path": "/outputs/run0/newspaper.html"}


def test_rejects_bad_input(client):
    for body in [
        {"topics": [], "layout": "layout_1"},
        {"topics": [" "]},
        {"topics": ["x"], "layout": "layout_9"},
        {"topics": ["x"] * 7},
        {"topics": ["x"], "language": "xx"},
        {"topics": ["x"], "model": "openai:gpt; rm -rf /"},
    ]:
        assert client.post("/api/newspaper", json=body).status_code == 422, body
    for body in [{"topics": ["x"], "images": "vaporwave"}]:
        assert client.post("/api/newspaper", json=body).status_code == 400, body


def test_validation_errors_never_echo_secrets(client):
    secret = "sk-" + "s" * 600  # too long, so it fails validation
    response = client.post("/api/newspaper", json={"topics": ["x"], "api_key": secret})
    assert response.status_code == 422 and secret not in response.text


def test_missing_tavily_key(client, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY")
    response = client.post("/api/newspaper", json={"topics": ["x"]})
    assert response.status_code == 400 and "Tavily API key" in response.json()["detail"]


def test_keys_from_the_ui_are_used_for_the_run(client, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post(
        "/api/newspaper",
        json={
            "topics": ["x"],
            "model": "anthropic:claude-sonnet-5-5",
            "api_key": " sk-ant-ui ",
            "tavily_api_key": "tvly-ui",
        },
    )
    assert read_events(response)[-1]["type"] == "done"
    context = client.contexts[-1]
    assert (context.api_key, context.tavily_api_key) == ("sk-ant-ui", "tvly-ui")
    assert "sk-ant-ui" not in repr(context)


def test_missing_model_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/api/newspaper", json={"topics": ["x"], "model": "anthropic:claude-sonnet-5-5"})
    assert response.status_code == 400 and "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_unknown_model_provider(client, monkeypatch):
    monkeypatch.setattr(setup, "get_chat_model", get_chat_model)
    response = client.post("/api/newspaper", json={"topics": ["x"], "model": "not-a-provider:foo"})
    assert response.status_code == 400 and "not-a-provider:foo" in response.json()["detail"]


def test_busy_newsroom(client, monkeypatch):
    monkeypatch.setattr(server.slots, "active", 10_000)
    assert client.post("/api/newspaper", json={"topics": ["x"]}).status_code == 429


def test_slots_are_released(client):
    client.post("/api/newspaper", json={"topics": ["x"]})
    assert server.slots.active == 0
