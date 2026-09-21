import asyncio
import json

from app import chatbot


def test_retrieve_normalizes_punctuation_and_returns_best_match():
    results = chatbot.retrieve("How do I REGISTER on Skill-India Digital?")

    assert results[0]["id"] == "learner_001"
    assert len(results) <= 3


def test_retrieve_supports_partial_keywords():
    results = chatbot.retrieve("I need help with course discovery")

    assert results[0]["id"] == "learner_004"


def test_load_knowledge_returns_empty_for_malformed_json(tmp_path):
    path = tmp_path / "knowledge.json"
    path.write_text("{bad json", encoding="utf-8")

    assert chatbot.load_knowledge(path) == []


def test_load_knowledge_returns_empty_for_non_array_json(tmp_path):
    path = tmp_path / "knowledge.json"
    path.write_text(json.dumps({"record": True}), encoding="utf-8")

    assert chatbot.load_knowledge(path) == []


def test_get_response_has_attribution_fields_without_context():
    response = asyncio.run(chatbot.get_response("something outside the knowledge base"))

    assert set(response) == {"answer", "source", "page", "category"}
    assert response["source"] is None
