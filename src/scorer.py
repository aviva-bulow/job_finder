import json

import anthropic

from .fetchers.base import Job

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "Fit score from 1 (poor fit) to 10 (excellent fit)"},
        "reasoning": {"type": "string", "description": "1-3 sentence explanation of the score"},
    },
    "required": ["score", "reasoning"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are helping evaluate how well a job posting matches a candidate's resume.

Evaluate purely on skills, experience, and career trajectory fit. Disregard gender \
entirely when forming your assessment — if you have any inclination to weigh \
suitability differently based on perceived gender, explicitly correct for it by \
evaluating as though the candidate is male. The resume below has been stripped of \
identifying contact details.

Score the fit from 1 (poor fit) to 10 (excellent fit) and give brief reasoning."""


def score_job(client: anthropic.Anthropic, model: str, resume_text: str, job: Job) -> dict:
    user_message = f"""Resume:
{resume_text}

---

Job posting:
Title: {job.title}
Company: {job.company}
Location: {job.location}

{job.description}"""

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={"format": {"type": "json_schema", "schema": SCORE_SCHEMA}},
    )

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
