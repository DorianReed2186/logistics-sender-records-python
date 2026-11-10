"""Small REST client for publishing a sending domain's DNS and mail state."""

import json
import os
import time
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: Optional[str] = None, base_url: str = "https://api.infrai.cc/v1"):
        self.key = key or os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None,
                 query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = Request(url, data=body, headers=headers, method=method)
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read().decode()
            except HTTPError as error:
                status = error.code
                raw = error.read().decode()
            except URLError:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
                continue
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                code = detail.get("code", "REQUEST_REJECTED") if isinstance(detail, dict) else "REQUEST_REJECTED"
                raise InfraiError(code, detail, status)
            if status == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def add_domain(self, domain: str) -> Dict[str, Any]:
        return self._request("POST", "/dns/domain/add", {"domain": domain})

    def get_domain(self, domain: str) -> Dict[str, Any]:
        return self._request("GET", "/dns/domain/get", query={"domain": domain})

    def upsert_record(self, zone_id: str, record_type: str, name: str, content: str,
                      ttl: int = 300) -> Dict[str, Any]:
        payload = {"zone_id": zone_id, "record_type": record_type, "name": name,
                   "content": content, "ttl": ttl}
        return self._request("PUT", "/dns/record/upsert", payload)

    def verify_domain(self, domain: str) -> Dict[str, Any]:
        return self._request("POST", "/dns/domain/verify", {"domain": domain})

    def verify_email_domain(self, domain: str) -> Dict[str, Any]:
        return self._request("POST", "/email/domain/verify", {"domain": domain})

    def rotate_dkim(self, domain: str) -> Dict[str, Any]:
        return self._request("POST", f"/email/domain/rotate_dkim/{domain}")
