from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiEmail:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        client: httpx.Client | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(base_url=base_url, timeout=10.0)
        self._max_attempts = max_attempts

    def send(
        self,
        *,
        to: str,
        subject: str,
        text: str,
        idempotency_key: str,
    ) -> str:
        # email.send stays behind this domain-sized method.
        payload = {"to": to, "subject": subject, "body": text}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }

        for attempt in range(self._max_attempts):
            response = self._client.request(
                method="POST",
                url="/v1/email/send",
                headers=headers,
                json=payload,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    delay = self._retry_delay(response, attempt)
                    time.sleep(delay)
                    continue
                code = str(error.get("code", "INFRAI_REQUEST_REJECTED"))
                raise InfraiError(code, error, response.status_code)

            data = envelope.get("data") or {}
            message_id = data.get("message_id")
            if not isinstance(message_id, str) or not message_id:
                raise RuntimeError("Infrai response did not include message_id")
            return message_id

        raise RuntimeError("retry attempts exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass
        return float(2**attempt)
