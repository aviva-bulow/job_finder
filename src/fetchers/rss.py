import xml.etree.ElementTree as ET

import requests

from .base import Job, strip_html

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def fetch(company: str, feed_url: str, timeout: int = 15) -> list[Job]:
    resp = requests.get(feed_url, timeout=timeout)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    items = root.findall(".//item")
    if items:
        return [_from_rss_item(company, item) for item in items]

    entries = root.findall(f".//{ATOM_NS}entry")
    return [_from_atom_entry(company, entry) for entry in entries]


def _text(el, tag):
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else ""


def _from_rss_item(company: str, item) -> Job:
    return Job(
        id="",
        title=_text(item, "title"),
        company=company,
        location="",
        description=strip_html(_text(item, "description")),
        url=_text(item, "link"),
        date_posted=_text(item, "pubDate"),
        source="rss",
    )


def _from_atom_entry(company: str, entry) -> Job:
    link_el = entry.find(f"{ATOM_NS}link")
    url = link_el.get("href", "") if link_el is not None else ""
    return Job(
        id="",
        title=_text(entry, f"{ATOM_NS}title"),
        company=company,
        location="",
        description=strip_html(_text(entry, f"{ATOM_NS}summary") or _text(entry, f"{ATOM_NS}content")),
        url=url,
        date_posted=_text(entry, f"{ATOM_NS}updated"),
        source="rss",
    )
