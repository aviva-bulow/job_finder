from src.anonymize import anonymize_resume

SAMPLE_RESUME = r"""
\documentclass{article}
\begin{document}
\contact{Aviva Bulow Mehlow}{\text{aviva@terrene.solutions}}{github.com/aviva-bulow}{linkedin.com/in/aviva-bulow}

A technical leader with a decade of experience.

% \contact{\huge{Aviva Bulow}}{\text{aviva.bulow@gmail.com}}{+1(720)473-3836}{github.com/aviva-bulow}{linkedin.com/in/aviva-bulow}
\end{document}
"""


def test_strips_name_from_contact_command():
    result = anonymize_resume(SAMPLE_RESUME)
    assert "Aviva" not in result
    assert "Bulow" not in result
    assert "Candidate" in result


def test_strips_email_addresses():
    result = anonymize_resume(SAMPLE_RESUME)
    assert "aviva@terrene.solutions" not in result
    assert "aviva.bulow@gmail.com" not in result


def test_strips_github_and_linkedin_handles():
    result = anonymize_resume(SAMPLE_RESUME)
    assert "aviva-bulow" not in result


def test_drops_commented_lines_entirely():
    result = anonymize_resume(SAMPLE_RESUME)
    assert "720" not in result


def test_preserves_non_identifying_content():
    result = anonymize_resume(SAMPLE_RESUME)
    assert "technical leader" in result
