import requests


def fetch_resume_text(resume_url: str, timeout: int = 15) -> str:
    resp = requests.get(resume_url, timeout=timeout)
    resp.raise_for_status()
    return resp.text
