import hashlib
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


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()
