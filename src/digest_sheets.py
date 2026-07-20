import json

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER = ["Date Found", "Score", "Company", "Title", "Location", "Reasoning", "Link"]


def _open_sheet(service_account_json: str, sheet_id: str):
    creds = Credentials.from_service_account_info(json.loads(service_account_json), scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1

    if not sheet.get_all_values():
        sheet.append_row(HEADER)

    return sheet


def append_matches(service_account_json: str, sheet_id: str, found_date: str, matches: list[dict]):
    if not matches:
        return

    sheet = _open_sheet(service_account_json, sheet_id)
    rows = []
    for m in matches:
        job = m["job"]
        rows.append([found_date, m["score"], job.company, job.title, job.location, m["reasoning"], job.url])

    sheet.append_rows(rows)
