from __future__ import annotations

import httpx
import pytest

from rescontre import (
    AuthenticationError,
    Client,
    Direction,
    RescontreAPIError,
    RescontreConfigurationError,
)

API_KEY = "a" * 64


def _mock_client(handler: httpx.MockTransport, *, api_key: str = API_KEY) -> Client:
    http = httpx.Client(base_url="http://test", transport=handler)
    return Client(base_url="http://test", api_key=api_key, http_client=http)


def test_end_to_end_happy_path() -> None:
    seen: list[tuple[str, str, dict | None, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = None
        if request.content:
            import json as _json

            body = _json.loads(request.content)
        seen.append(
            (
                request.method,
                request.url.path,
                body,
                request.headers.get("x-api-key"),
            )
        )

        if request.url.path == "/agents":
            return httpx.Response(200, json={"id": body["id"]})
        if request.url.path == "/servers":
            return httpx.Response(200, json={"id": body["id"]})
        if request.url.path == "/agreements":
            return httpx.Response(200, json={"agreement_id": "agr-1"})
        if request.url.path == "/internal/verify":
            return httpx.Response(
                200, json={"valid": True, "reason": None, "remaining_credit": 9_000_000}
            )
        if request.url.path == "/internal/settle":
            return httpx.Response(
                200,
                json={
                    "settled": True,
                    "commitment_id": "cmt-1",
                    "net_position": -1_000_000,
                    "commitments_until_settlement": 99,
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    with _mock_client(httpx.MockTransport(handler)) as c:
        c.register_agent("agent-1", "0xAAA")
        c.register_server("server-1", "0xBBB", ["/api/data"])
        c.create_agreement("agent-1", "server-1", credit_limit=10_000_000)

        v = c.verify("agent-1", "server-1", 1_000_000, "n-1")
        assert v.valid and v.remaining_credit == 9_000_000

        s = c.settle(
            "agent-1",
            "server-1",
            1_000_000,
            "n-1",
            "GET /api/data",
            direction=Direction.AgentToServer,
        )
        assert s.settled
        assert s.commitment_id == "cmt-1"

    paths = [p for _, p, _, _ in seen]
    assert paths == [
        "/agents",
        "/servers",
        "/agreements",
        "/internal/verify",
        "/internal/settle",
    ]

    settle_body = seen[-1][2]
    assert settle_body["direction"] == "AgentToServer"

    headers_by_path = {path: api_key for _, path, _, api_key in seen}
    assert headers_by_path["/internal/verify"] == API_KEY
    assert headers_by_path["/internal/settle"] == API_KEY
    # Public endpoints must NOT receive the API key header.
    assert headers_by_path["/agents"] is None
    assert headers_by_path["/servers"] is None
    assert headers_by_path["/agreements"] is None


def test_api_error_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "insufficient credit"})

    with _mock_client(httpx.MockTransport(handler)) as c:
        with pytest.raises(RescontreAPIError) as ei:
            c.verify("a", "s", 1, "n")
        assert ei.value.status_code == 400
        assert "insufficient credit" in str(ei.value)


def test_missing_api_key_raises_at_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESCONTRE_API_KEY", raising=False)
    with pytest.raises(RescontreConfigurationError) as ei:
        Client(base_url="http://test")
    msg = str(ei.value)
    assert "api_key" in msg
    assert "RESCONTRE_API_KEY" in msg


def test_api_key_picked_up_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESCONTRE_API_KEY", API_KEY)
    seen_keys: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_keys.append(request.headers.get("x-api-key"))
        return httpx.Response(
            200, json={"valid": True, "reason": None, "remaining_credit": 0}
        )

    http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    with Client(base_url="http://test", http_client=http) as c:
        c.verify("a", "s", 1, "n")

    assert seen_keys == [API_KEY]


def test_401_on_verify_raises_authentication_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    with _mock_client(httpx.MockTransport(handler)) as c:
        with pytest.raises(AuthenticationError) as ei:
            c.verify("a", "s", 1, "n")
        assert ei.value.status_code == 401
        assert "RESCONTRE_API_KEY" in str(ei.value)
        assert "/admin/keys" in str(ei.value)


def test_401_on_settle_raises_authentication_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    with _mock_client(httpx.MockTransport(handler)) as c:
        with pytest.raises(AuthenticationError):
            c.settle(
                "a",
                "s",
                1,
                "n",
                "GET /x",
                direction=Direction.AgentToServer,
            )
