import hashlib
import html
import re
from dataclasses import dataclass


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    date_posted: str
    source: str
    description_hash: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = job_id(self.company, self.url)
        if not self.description_hash:
            self.description_hash = description_hash(self.description)


def job_id(company: str, url: str) -> str:
    return hashlib.sha256(f"{company}|{url}".encode()).hexdigest()


def description_hash(description: str) -> str:
    normalized = re.sub(r"\s+", " ", description or "").strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def strip_html(raw: str) -> str:
    text = raw or ""
    # Some ATS postings store content that's been HTML-escaped twice (e.g.
    # pasted-from-Word text saved as literal "&lt;p&gt;...&lt;/p&gt;" instead
    # of real "<p>" tags) - unescape until stable so real tags are exposed,
    # rather than passing the escaped markup through as literal text.
    for _ in range(5):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
