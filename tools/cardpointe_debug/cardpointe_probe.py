#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

from _report import (
    append_section,
    dump_json,
    format_exception,
    make_report_path,
    redact_env_snapshot,
    redact_headers,
    write_http_attempt,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class Probe:
    USER_AGENT = "cardpointe-probe/0.1"

    def __init__(self) -> None:
        self.base_url = os.getenv("CARDPOINTE_BASE_URL", "https://bolt-uat.cardpointe.com").rstrip("/")
        self.alt_base_url = os.getenv("CARDPOINTE_ALT_BASE_URL", "https://bolt-terminal-uat.cardpointe.com").rstrip("/")
        self.timeout = int(os.getenv("CARDPOINTE_TIMEOUT", "30"))
        self.verify = os.getenv("CARDPOINTE_VERIFY_TLS", "true").strip().lower() not in {"0", "false", "no"}

        self.merchid = os.getenv("CARDPOINTE_MERCHID", "800000009875")
        self.deviceid = os.getenv("CARDPOINTE_DEVICEID", "C047UG43720996")
        self.orderid = os.getenv("CARDPOINTE_ORDERID", "00001-002-0003")
        self.amount = os.getenv("CARDPOINTE_AMOUNT", "1.00")
        self.currency = os.getenv("CARDPOINTE_CURRENCY", "USD")

        self.api_key = os.getenv("CARDPOINTE_API_KEY", "")
        self.bearer_token = os.getenv("CARDPOINTE_BEARER_TOKEN", "")
        self.oauth_token_url = os.getenv("CARDPOINTE_OAUTH_TOKEN_URL", "")
        self.client_id = os.getenv("CARDPOINTE_CLIENT_ID", "")
        self.client_secret = os.getenv("CARDPOINTE_CLIENT_SECRET", "")
        self.oauth_grant_type = os.getenv("CARDPOINTE_OAUTH_GRANT_TYPE", "client_credentials")

        self.report_path = make_report_path(Path(__file__).resolve().parent)
        self.session = requests.Session()
        self.oauth_cached_token: Optional[str] = None

        append_section(
            self.report_path,
            "Probe Run Started",
            dump_json(
                {
                    "cwd": os.getcwd(),
                    "report_path": str(self.report_path),
                    "env": redact_env_snapshot(
                        {
                            "CARDPOINTE_BASE_URL": self.base_url,
                            "CARDPOINTE_ALT_BASE_URL": self.alt_base_url,
                            "CARDPOINTE_MERCHID": self.merchid,
                            "CARDPOINTE_DEVICEID": self.deviceid,
                            "CARDPOINTE_ORDERID": self.orderid,
                            "CARDPOINTE_AMOUNT": self.amount,
                            "CARDPOINTE_CURRENCY": self.currency,
                            "CARDPOINTE_API_KEY": self.api_key,
                            "CARDPOINTE_BEARER_TOKEN": self.bearer_token,
                            "CARDPOINTE_OAUTH_TOKEN_URL": self.oauth_token_url,
                            "CARDPOINTE_CLIENT_ID": self.client_id,
                            "CARDPOINTE_CLIENT_SECRET": self.client_secret,
                            "CARDPOINTE_OAUTH_GRANT_TYPE": self.oauth_grant_type,
                            "CARDPOINTE_VERIFY_TLS": str(self.verify).lower(),
                            "CARDPOINTE_TIMEOUT": str(self.timeout),
                        }
                    ),
                }
            ),
        )

    def sale_payload(self) -> Dict[str, str]:
        return {
            "amount": self.amount,
            "currency": self.currency,
            "merchid": self.merchid,
            "orderid": self.orderid,
            "capture": "y",
            "deviceid": self.deviceid,
        }

    def _request(
        self,
        *,
        test_name: str,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[requests.Response], Optional[Exception]]:
        req_headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        if payload is not None:
            req_headers["Content-Type"] = "application/json"
        if headers:
            req_headers.update(headers)

        resp = None
        err = None
        try:
            resp = self.session.request(
                method=method,
                url=url,
                headers=req_headers,
                json=payload,
                data=data,
                timeout=self.timeout,
                verify=self.verify,
            )
            body = resp.text
            write_http_attempt(
                self.report_path,
                test_name=test_name,
                method=method,
                url=url,
                request_headers=req_headers,
                payload=payload,
                timeout=self.timeout,
                verify=self.verify,
                response_status=resp.status_code,
                response_headers=dict(resp.headers),
                response_body=body,
            )
            print(f"[{test_name}] {method} {url} -> {resp.status_code}")
        except Exception as exc:  # noqa: BLE001
            err = exc
            stack = format_exception()
            write_http_attempt(
                self.report_path,
                test_name=test_name,
                method=method,
                url=url,
                request_headers=req_headers,
                payload=payload,
                timeout=self.timeout,
                verify=self.verify,
                error_stack=stack,
            )
            print(f"[{test_name}] {method} {url} -> ERROR: {exc.__class__.__name__}: {exc}")
        return resp, err

    def ping(self) -> None:
        for label, base in (("primary", self.base_url), ("alt", self.alt_base_url)):
            self._request(test_name=f"ping_{label}", method="GET", url=f"{base}/")

    def sale_noauth(self, base_url: Optional[str] = None, test_name: str = "sale_noauth") -> None:
        base = (base_url or self.base_url).rstrip("/")
        self._request(
            test_name=test_name,
            method="POST",
            url=f"{base}/api/v2/connectedterminal/sale",
            payload=self.sale_payload(),
        )

    def sale_apikey(self) -> None:
        if not self.api_key:
            print("[sale_apikey] skipped: CARDPOINTE_API_KEY not set")
            append_section(self.report_path, "sale_apikey", "Skipped: CARDPOINTE_API_KEY not set")
            return

        self._request(
            test_name="sale_apikey_raw",
            method="POST",
            url=f"{self.base_url}/api/v2/connectedterminal/sale",
            headers={"Authorization": self.api_key},
            payload=self.sale_payload(),
        )
        self._request(
            test_name="sale_apikey_bearer",
            method="POST",
            url=f"{self.base_url}/api/v2/connectedterminal/sale",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload=self.sale_payload(),
        )

    def sale_bearer(self) -> None:
        if not self.bearer_token:
            print("[sale_bearer] skipped: CARDPOINTE_BEARER_TOKEN not set")
            append_section(self.report_path, "sale_bearer", "Skipped: CARDPOINTE_BEARER_TOKEN not set")
            return

        self._request(
            test_name="sale_bearer",
            method="POST",
            url=f"{self.base_url}/api/v2/connectedterminal/sale",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            payload=self.sale_payload(),
        )

    def oauth_token(self) -> Optional[str]:
        if self.oauth_cached_token:
            return self.oauth_cached_token

        if not (self.oauth_token_url and self.client_id and self.client_secret):
            print("[oauth_token] skipped: missing CARDPOINTE_OAUTH_TOKEN_URL/CLIENT_ID/CLIENT_SECRET")
            append_section(
                self.report_path,
                "oauth_token",
                "Skipped: missing CARDPOINTE_OAUTH_TOKEN_URL/CLIENT_ID/CLIENT_SECRET",
            )
            return None

        resp, err = self._request(
            test_name="oauth_token",
            method="POST",
            url=self.oauth_token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": self.oauth_grant_type,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if err or resp is None:
            return None

        token = None
        try:
            parsed = resp.json()
            token = parsed.get("access_token")
            append_section(self.report_path, "oauth_token_parsed", dump_json({"keys": sorted(parsed.keys())}))
        except Exception:  # noqa: BLE001
            append_section(self.report_path, "oauth_token_parsed", "Response was not valid JSON")

        if token:
            self.oauth_cached_token = token
            print("[oauth_token] token acquired (redacted)")
            return token

        print("[oauth_token] no access_token in response")
        return None

    def sale_oauth(self) -> None:
        token = self.oauth_token()
        if not token:
            print("[sale_oauth] skipped: oauth token unavailable")
            append_section(self.report_path, "sale_oauth", "Skipped: oauth token unavailable")
            return

        self._request(
            test_name="sale_oauth",
            method="POST",
            url=f"{self.base_url}/api/v2/connectedterminal/sale",
            headers={"Authorization": f"Bearer {token}"},
            payload=self.sale_payload(),
        )

    def compare_hosts(self) -> None:
        self.sale_noauth(base_url=self.base_url, test_name="compare_hosts_primary_sale_noauth")
        self.sale_noauth(base_url=self.alt_base_url, test_name="compare_hosts_alt_sale_noauth")

    def full(self) -> None:
        self.ping()
        self.sale_noauth()
        self.sale_apikey()
        self.oauth_token()
        self.sale_oauth()
        self.compare_hosts()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CardPointe Integrated Terminal API troubleshooting probe")
    sub = parser.add_subparsers(dest="command", required=True)

    for cmd in [
        "ping",
        "sale_noauth",
        "sale_apikey",
        "sale_bearer",
        "oauth_token",
        "sale_oauth",
        "compare_hosts",
        "full",
    ]:
        sub.add_parser(cmd)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    probe = Probe()

    if args.command == "ping":
        probe.ping()
    elif args.command == "sale_noauth":
        probe.sale_noauth()
    elif args.command == "sale_apikey":
        probe.sale_apikey()
    elif args.command == "sale_bearer":
        probe.sale_bearer()
    elif args.command == "oauth_token":
        probe.oauth_token()
    elif args.command == "sale_oauth":
        probe.sale_oauth()
    elif args.command == "compare_hosts":
        probe.compare_hosts()
    elif args.command == "full":
        probe.full()

    print(f"Report written to: {probe.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
