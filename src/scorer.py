import json

import anthropic
from anthropic.types import TextBlockParam

from .fetchers.base import Job

BATCH_SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "0-based index of the job posting being scored",
                    },
                    "score": {
                        "type": "integer",
                        "description": "Fit score from 1 (poor fit) to 10 (excellent fit)",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "1-3 sentence explanation of the score",
                    },
                },
                "required": ["index", "score", "reasoning"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

SYSTEM_INSTRUCTIONS = """You are helping evaluate how well job postings match a candidate's resume.

Evaluate purely on skills, experience, and career trajectory fit. Disregard gender \
entirely when forming your assessment — if you have any inclination to weigh \
suitability differently based on perceived gender, explicitly correct for it by \
evaluating as though the candidate is male. The resume below has been stripped of \
identifying contact details.

You will be given a numbered list of job postings, each starting with its index in \
brackets like "[0]". Score each posting independently from 1 (poor fit) to 10 \
(excellent fit) with brief reasoning, and return exactly one result per posting in \
the "results" array, tagged with its index."""


def _build_batch_message(jobs: list[Job]) -> str:
    postings = [
        f"[{i}]\nTitle: {job.title}\nCompany: {job.company}\nLocation: {job.location}\n\n"
        f"{job.description}"
        for i, job in enumerate(jobs)
    ]
    return "\n\n---\n\n".join(postings)


def score_jobs_batch(
    client: anthropic.Anthropic, model: str, resume_text: str, jobs: list[Job]
) -> dict[int, dict]:
    # The system prompt + resume are identical across every batch in a run;
    # marking them as an explicit cache breakpoint means only the first
    # batch pays full price for that content, and later batches in the same
    # run read it back at a fraction of the cost. Only the job postings
    # (the messages content) vary per call, so they stay outside the cache.
    system: list[TextBlockParam] = [
        {
            "type": "text",
            "text": f"{SYSTEM_INSTRUCTIONS}\n\nResume:\n{resume_text}",
            "cache_control": {"type": "ephemeral"},
        }
    ]

    response = client.messages.create(
        model=model,
        max_tokens=512 + 200 * len(jobs),
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": _build_batch_message(jobs)}],
        output_config={"format": {"type": "json_schema", "schema": BATCH_SCORE_SCHEMA}},
    )

    text = next(block.text for block in response.content if block.type == "text")
    parsed = json.loads(text)
    return {
        item["index"]: {"score": item["score"], "reasoning": item["reasoning"]}
        for item in parsed["results"]
    }
