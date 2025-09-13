from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

__all__ = ["slugify", "parse_date", "in_date_range"]


def slugify(value: str, max_length: int = 80) -> str:
    if not isinstance(value, str):
        value = str(value or "")
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    if max_length and max_length > 0:
        value = value[:max_length].rstrip("-")
    return value


def _parse_relative_date(s: str, now: Optional[datetime] = None) -> Optional[datetime]:
    if not s:
        return None
    text = s.strip().lower()
    now = now or datetime.now(timezone.utc)

    if text == "today":
        return now
    if text == "yesterday":
        return now - timedelta(days=1)

    m = re.search(r"(\d+)\s*(day|days|d)\s*ago", text)
    if m:
        return now - timedelta(days=int(m.group(1)))

    m = re.search(r"(\d+)\s*(week|weeks|w)\s*ago", text)
    if m:
        return now - timedelta(weeks=int(m.group(1)))

    m = re.search(r"(\d+)\s*(month|months|mo)\s*ago", text)
    if m:
        return now - timedelta(days=30 * int(m.group(1)))

    m = re.search(r"(\d+)\s*(year|years|y)\s*ago", text)
    if m:
        return now - timedelta(days=365 * int(m.group(1)))

    return None


def _try_strptime_formats(s: str, fmts: Iterable[str]) -> Optional[datetime]:
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def parse_date(
    s: str,
    *,
    prefer_dayfirst: bool = False,
    now: Optional[datetime] = None,
) -> Optional[str]:
    if not s or not str(s).strip():
        return None

    raw = str(s).strip()

    rel = _parse_relative_date(raw, now=now)
    if rel:
        return rel.date().isoformat()

    cleaned = re.sub(r"[,\u00A0]", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    month_names = [
        "%b %d %Y", "%b %d, %Y", "%B %d %Y", "%B %d, %Y",
        "%d %b %Y", "%d %B %Y", "%Y %b %d", "%Y %B %d",
        "%b %Y", "%B %Y",
    ]

    dt = _try_strptime_formats(cleaned, month_names)
    if dt:
        return dt.date().isoformat()

    if prefer_dayfirst:
        ordered = [
            "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
            "%m-%d-%Y", "%m/%d/%Y", "%m.%d.%Y",
        ]
    else:
        ordered = [
            "%m-%d-%Y", "%m/%d/%Y", "%m.%d.%Y",
            "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        ]

    dt = _try_strptime_formats(cleaned, ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"] + ordered)
    if dt:
        return dt.date().isoformat()

    try:
        iso = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if iso.tzinfo is None:
            iso = iso.replace(tzinfo=timezone.utc)
        return iso.date().isoformat()
    except ValueError:
        pass

    token = re.search(r"(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})", cleaned)
    if token:
        dt = _try_strptime_formats(token.group(1), ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"])
        if dt:
            return dt.date().isoformat()

    token = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b", cleaned)
    if token:
        guess = " ".join(token.groups())
        dt = _try_strptime_formats(guess, ["%b %d %Y", "%B %d %Y"])
        if dt:
            return dt.date().isoformat()

    return None


def in_date_range(
    date_iso: Optional[str],
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
) -> bool:
    if not date_iso:
        return False
    try:
        d = datetime.strptime(date_iso, "%Y-%m-%d").date()
    except ValueError:
        return False

    s = None
    e = None
    if start_iso:
        try:
            s = datetime.strptime(start_iso, "%Y-%m-%d").date()
        except ValueError:
            s = None
    if end_iso:
        try:
            e = datetime.strptime(end_iso, "%Y-%m-%d").date()
        except ValueError:
            e = None

    if s and d < s:
        return False
    if e and d > e:
        return False
    return True
