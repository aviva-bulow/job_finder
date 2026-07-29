from unittest.mock import MagicMock, patch

from src.digest_sheets import append_matches
from src.fetchers.base import Job

JOB = Job(
    id="",
    title="Engineering Manager, Climate Software",
    company="Acme",
    location="Remote",
    description="Lead a team building solar forecasting tools.",
    url="https://example.com/1",
    date_posted="2026-01-15",
    source="greenhouse",
)


def _mock_sheet(existing_values=None):
    sheet = MagicMock()
    sheet.get_all_values.return_value = existing_values or []
    client = MagicMock()
    client.open_by_key.return_value.sheet1 = sheet
    return sheet, client


def test_append_matches_includes_date_posted_column():
    sheet, client = _mock_sheet()

    with patch("src.digest_sheets.Credentials.from_service_account_info"), patch(
        "src.digest_sheets.gspread.authorize", return_value=client
    ):
        append_matches(
            '{"type": "service_account"}',
            "sheet-id",
            "2026-01-20",
            [{"job": JOB, "score": 9, "reasoning": "Great fit."}],
        )

    header_row = sheet.append_row.call_args[0][0]
    assert header_row == [
        "Date Found",
        "Date Posted",
        "Score",
        "Company",
        "Title",
        "Location",
        "Reasoning",
        "Link",
    ]

    data_rows = sheet.append_rows.call_args[0][0]
    assert data_rows == [
        ["2026-01-20", "2026-01-15", 9, "Acme", "Engineering Manager, Climate Software",
         "Remote", "Great fit.", "https://example.com/1"]
    ]
