from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


SECRET_KEYS = {
    "authorization",
    "cardpointe_api_key",
    "cardpointe_bearer_token",
    "cardpointe_client_secret",
}


def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def make_report_path(base_dir: Path) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return base_dir / f"RESULTS_{ts}.txt"


def _redact_auth(value: str) -> str:
    if not value:
        return "(redacted)"
    parts = value.split(" ", 1)
    if len(parts) == 2:
        return f"{parts[0]} ...(redacted)"
    return "...(redacted)"


def redact_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    clean = {}
    for key, value in (headers or {}).items():
        if key.lower() == "authorization":
            clean[key] = _redact_auth(str(value))
        else:
            clean[key] = value
    return clean


def redact_env_snapshot(env: Dict[str, str]) -> Dict[str, str]:
    cleaned = {}
    for key, value in env.items():
        if key.lower() in SECRET_KEYS:
            cleaned[key] = "...(redacted)" if value else ""
        else:
            cleaned[key] = value
    return cleaned


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def append_section(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{'=' * 88}\n")
        fh.write(f"[{now_iso()}] {title}\n")
        fh.write(f"{'=' * 88}\n")
        fh.write(body)
        fh.write("\n")


def format_exception() -> str:
    return traceback.format_exc()


def write_http_attempt(
    report_path: Path,
    *,
    test_name: str,
    method: str,
    url: str,
    request_headers: Dict[str, Any],
    payload: Optional[Dict[str, Any]],
    timeout: int,
    verify: bool,
    response_status: Optional[int] = None,
    response_headers: Optional[Dict[str, Any]] = None,
    response_body: Optional[str] = None,
    error_stack: Optional[str] = None,
) -> None:
    lines = [
        f"test: {test_name}",
        f"timestamp: {now_iso()}",
        f"request.method: {method}",
        f"request.url: {url}",
        "request.headers:",
        dump_json(redact_headers(request_headers)),
        "request.payload:",
        dump_json(payload or {}),
        f"request.timeout_seconds: {timeout}",
        f"request.verify_tls: {verify}",
        f"response.status_code: {response_status}",
        "response.headers:",
        dump_json(dict(response_headers or {})),
        "response.body_first_2000:",
        (response_body or "")[:2000],
    ]
    if error_stack:
        lines.extend(["exception.stacktrace:", error_stack])

    append_section(report_path, f"HTTP Attempt - {test_name}", "\n".join(lines))
