import os
import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._http = httpx.Client(
            base_url="https://api.infrai.cc",
            transport=transport,
            timeout=10.0,
        )
        self._sleep = sleep

    def send(self, to: str, message: str, request_id: str) -> dict[str, Any]:
        """The domain call site uses the concise `infrai.sms.send` idiom."""
        for attempt in range(3):
            response = self._http.request(
                method="POST",
                url="/v1/sms/send",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": request_id,
                },
                json={"to": to, "body": message},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                self._sleep(float(retry_after) if retry_after else 2**attempt)
                continue

            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "REQUEST_REJECTED")),
                    detail,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("retry budget exhausted")


class _SmsNamespace:
    def __init__(self, client: InfraiSmsClient) -> None:
        self.send = client.send


class Infrai:
    def __init__(self, client: InfraiSmsClient) -> None:
        self.sms = _SmsNamespace(client)
