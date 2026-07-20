import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.fetchers.base import Job
from src.scorer import score_job

SAMPLE_JOB = Job(
    id="",
    title="Engineering Manager, Climate Software",
    company="Acme",
    location="Remote",
    description="Lead a team building solar forecasting tools.",
    url="https://example.com/1",
    date_posted="2026-01-01",
    source="greenhouse",
)


def make_client(score=8, reasoning="Strong match on leadership and climate domain."):
    payload = json.dumps({"score": score, "reasoning": reasoning})
    text_block = SimpleNamespace(type="text", text=payload)
    response = SimpleNamespace(content=[text_block])

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_score_job_returns_parsed_result():
    client = make_client(score=9, reasoning="Excellent leadership and domain fit.")

    result = score_job(client, "claude-opus-4-8", "resume text", SAMPLE_JOB)

    assert result == {"score": 9, "reasoning": "Excellent leadership and domain fit."}


def test_score_job_sends_resume_and_job_details_in_prompt():
    client = make_client()

    score_job(client, "claude-opus-4-8", "ANONYMIZED RESUME TEXT", SAMPLE_JOB)

    _, kwargs = client.messages.create.call_args
    user_content = kwargs["messages"][0]["content"]
    assert "ANONYMIZED RESUME TEXT" in user_content
    assert SAMPLE_JOB.title in user_content
    assert SAMPLE_JOB.company in user_content


def test_score_job_uses_requested_model():
    client = make_client()

    score_job(client, "claude-opus-4-8", "resume text", SAMPLE_JOB)

    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"


def test_score_job_requests_structured_json_output():
    client = make_client()

    score_job(client, "claude-opus-4-8", "resume text", SAMPLE_JOB)

    _, kwargs = client.messages.create.call_args
    assert kwargs["output_config"]["format"]["type"] == "json_schema"


def test_score_job_system_prompt_instructs_gender_neutral_evaluation():
    client = make_client()

    score_job(client, "claude-opus-4-8", "resume text", SAMPLE_JOB)

    _, kwargs = client.messages.create.call_args
    assert "gender" in kwargs["system"].lower()
