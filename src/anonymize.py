import re

CONTACT_RE = re.compile(r"\\contact\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
GITHUB_RE = re.compile(r"github\.com/\S+")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/\S+")


def anonymize_resume(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.strip().startswith("%")]
    text = "\n".join(lines)

    contact_replacement = (
        r"\\contact{Candidate}{candidate@example.com}"
        r"{github.com/candidate}{linkedin.com/in/candidate}"
    )
    text = CONTACT_RE.sub(contact_replacement, text)
    text = EMAIL_RE.sub("[email]", text)
    text = GITHUB_RE.sub("[github]", text)
    text = LINKEDIN_RE.sub("[linkedin]", text)

    return text
