import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.fetchers.base import Job
from src.scorer import score_jobs_batch

JOB_A = Job(
    id="",
    title="Engineering Manager, Climate Software",
    company="Acme",
    location="Remote",
    description="Lead a team building solar forecasting tools.",
    url="https://example.com/1",
    date_posted="2026-01-01",
    source="greenhouse",
)

JOB_B = Job(
    id="",
    title="Perception Engineer",
    company="Beta",
    location="Remote",
    description="Build computer vision models for methane detection.",
    url="https://example.com/2",
    date_posted="2026-01-01",
    source="greenhouse",
)


def make_client(results):
    payload = json.dumps({"results": results})
    text_block = SimpleNamespace(type="text", text=payload)
    response = SimpleNamespace(content=[text_block])

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_score_jobs_batch_returns_results_keyed_by_index():
    client = make_client(
        [
            {"index": 0, "score": 9, "reasoning": "Excellent leadership and domain fit."},
            {"index": 1, "score": 6, "reasoning": "Good technical fit."},
        ]
    )

    result = score_jobs_batch(client, "claude-opus-4-8", "resume text", [JOB_A, JOB_B])

    assert result == {
        0: {"score": 9, "reasoning": "Excellent leadership and domain fit."},
        1: {"score": 6, "reasoning": "Good technical fit."},
    }


def test_score_jobs_batch_handles_out_of_order_results():
    client = make_client(
        [
            {"index": 1, "score": 6, "reasoning": "Good technical fit."},
            {"index": 0, "score": 9, "reasoning": "Excellent leadership and domain fit."},
        ]
    )

    result = score_jobs_batch(client, "claude-opus-4-8", "resume text", [JOB_A, JOB_B])

    assert result[0]["score"] == 9
    assert result[1]["score"] == 6


def test_score_jobs_batch_sends_resume_and_all_job_details_in_prompt():
    client = make_client([{"index": 0, "score": 9, "reasoning": "fit"}])

    score_jobs_batch(client, "claude-opus-4-8", "ANONYMIZED RESUME TEXT", [JOB_A, JOB_B])

    _, kwargs = client.messages.create.call_args
    user_content = kwargs["messages"][0]["content"]
    assert JOB_A.title in user_content
    assert JOB_B.title in user_content
    assert "ANONYMIZED RESUME TEXT" not in user_content


def test_score_jobs_batch_caches_system_prompt_and_resume():
    client = make_client([{"index": 0, "score": 9, "reasoning": "fit"}])

    score_jobs_batch(client, "claude-opus-4-8", "ANONYMIZED RESUME TEXT", [JOB_A, JOB_B])

    _, kwargs = client.messages.create.call_args
    system_blocks = kwargs["system"]
    assert "ANONYMIZED RESUME TEXT" in system_blocks[0]["text"]
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_score_jobs_batch_uses_requested_model():
    client = make_client([{"index": 0, "score": 9, "reasoning": "fit"}])

    score_jobs_batch(client, "claude-opus-4-8", "resume text", [JOB_A])

    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"


def test_score_jobs_batch_requests_structured_json_output():
    client = make_client([{"index": 0, "score": 9, "reasoning": "fit"}])

    score_jobs_batch(client, "claude-opus-4-8", "resume text", [JOB_A])

    _, kwargs = client.messages.create.call_args
    assert kwargs["output_config"]["format"]["type"] == "json_schema"


def test_score_jobs_batch_system_prompt_instructs_gender_neutral_evaluation():
    client = make_client([{"index": 0, "score": 9, "reasoning": "fit"}])

    score_jobs_batch(client, "claude-opus-4-8", "resume text", [JOB_A])

    _, kwargs = client.messages.create.call_args
    assert "gender" in kwargs["system"][0]["text"].lower()
