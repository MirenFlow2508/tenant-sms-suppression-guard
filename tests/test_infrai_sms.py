import httpx

from saas_sms_guard.infrai_sms import InfraiSmsClient


def test_send_retries_429_with_same_idempotency_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"ok": False, "error": {"message": "retry later"}})
        return httpx.Response(200, json={"ok": True, "data": {"message_id": "msg_42"}, "error": None, "metadata": {}})

    client = InfraiSmsClient(api_key="test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    result = client.send("+15550103030", "Your workspace is ready", "req-42")

    assert result == {"message_id": "msg_42"}
    assert [request.headers["Idempotency-Key"] for request in requests] == ["req-42", "req-42"]
