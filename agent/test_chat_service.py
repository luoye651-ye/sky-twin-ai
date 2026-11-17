"""Authenticated web API acceptance with fake Java identity/provider; never paid calls."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import HTTPException, Request

from aircraft_agent import AgentAnswer, AgentRunError, run_question
from chat_service import ChatInput, Principal, create_app, platform_identity
from test_aircraft_agent import DATA, ToolCallingFake, call_message
from langchain_core.messages import AIMessage


class PlatformIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, payload=None, status=200, error=None):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.side_effect = error
        client.get.return_value = httpx.Response(status, json=payload)
        with patch("chat_service.httpx.AsyncClient", return_value=client) as factory:
            result = await platform_identity("Bearer offline-token")
        factory.assert_called_once_with(timeout=8, trust_env=False, follow_redirects=False)
        client.get.assert_awaited_once_with("http://127.0.0.1:8081/getInfo", headers={"Authorization": "Bearer offline-token"})
        return result

    async def test_valid_read_permission(self):
        result = await self.call({"code": 200, "user": {"userId": 17}, "permissions": ["sky:read"]})
        self.assertEqual((result.user_id, result.token), (17, "offline-token"))
        self.assertNotIn("offline-token", repr(result))

    async def test_wildcard_permission(self):
        self.assertEqual((await self.call({"code": 200, "user": {"userId": 1}, "permissions": ["*:*:*"]})).user_id, 1)

    async def test_missing_and_invalid_headers(self):
        for value in (None, "", "offline-token", "Bearer ", "Bearer token\nvalue", "Bearer 中文"):
            with self.assertRaises(HTTPException) as error:
                await platform_identity(value)
            self.assertEqual(error.exception.status_code, 401)

    async def test_auth_business_codes_and_permissions(self):
        for payload, status, expected in (({"code": 401}, 200, 401), ({"code": 403}, 200, 403),
            ({}, 401, 401), ({}, 403, 403), ({"code": 200, "user": {"userId": 1}, "permissions": []}, 200, 403),
            ({"code": True}, 200, 503), ({"code": 200, "permissions": "sky:read"}, 200, 503)):
            with self.assertRaises(HTTPException) as error:
                await self.call(payload, status)
            self.assertEqual(error.exception.status_code, expected)

    async def test_network_errors_are_sanitized(self):
        with self.assertRaises(HTTPException) as error:
            await self.call(error=httpx.ConnectError("private-upstream-text"))
        self.assertNotIn("private-upstream-text", str(error.exception.detail))

    async def test_explicit_web_identity_never_falls_back_to_env(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="样例")])
        with patch("aircraft_agent.get_platform_token", side_effect=AssertionError("no global identity")), patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA) as query:
            await run_question("查询", model=model, platform_token="request-user-token")
        query.assert_awaited_once_with("request-user-token")
        self.assertNotIn("request-user-token", " ".join(model.seen_payloads))

    async def test_explicit_empty_token_fails_closed(self):
        with patch("aircraft_agent.get_platform_token") as fallback, patch("aircraft_agent.create_llm") as model:
            with self.assertRaises(AgentRunError):
                await run_question("查询", platform_token="")
        fallback.assert_not_called()
        model.assert_not_called()


class ChatAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.authenticate = AsyncMock(return_value=Principal(17, "request-identity"))
        self.runner = AsyncMock(return_value=AgentAnswer("只读样例答复", 1, 1, 4))
        self.app = create_app(authenticate=self.authenticate, ready=lambda: None, runner=self.runner, knowledge=lambda q: [])
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://127.0.0.1")
        self.addAsyncCleanup(self.client.aclose)
        self.body = {"question": "查询飞机", "request_id": str(uuid4())}

    async def post(self, body=None, headers=None):
        return await self.client.post("/chat", json=body if body is not None else self.body,
                                      headers=headers if headers is not None else {"Authorization": "Bearer fixture"})

    async def test_health_never_runs_model(self):
        response = await self.client.get("/health")
        self.assertTrue(response.json()["ready"])
        self.runner.assert_not_awaited()

    async def test_answer_stream_and_per_request_token(self):
        response = await self.post()
        self.assertEqual(response.status_code, 200)
        events = [json.loads(line) for line in response.text.splitlines()]
        self.assertEqual(events[-1]["data"]["aircraft_count"], 4)
        self.assertEqual(events[0]["type"], "progress")
        self.assertNotIn("request-identity", response.text)
        self.assertEqual(self.runner.await_args.kwargs["platform_token"], "request-identity")
        self.assertFalse(self.app.state.active)

    async def test_auth_rejection_before_runner(self):
        self.authenticate.side_effect = HTTPException(401, "请登录")
        self.assertEqual((await self.post()).status_code, 401)
        self.runner.assert_not_awaited()

    async def test_permission_rejection_before_runner(self):
        self.authenticate.side_effect = HTTPException(403, "权限不足")
        self.assertEqual((await self.post()).status_code, 403)
        self.runner.assert_not_awaited()

    async def test_untrusted_origin_blocked(self):
        response = await self.post(headers={"Origin": "https://untrusted.example"})
        self.assertEqual(response.status_code, 403)
        self.runner.assert_not_awaited()

    async def test_validation_does_not_echo_credentials(self):
        for body in ({**self.body, "question": " "}, {**self.body, "question": "x" * 2001},
                     {**self.body, "request_id": "bad-id"}, {**self.body, "platform_token": "private-test-token"},
                     {**self.body, "question": "sk-" + "a" * 30}):
            response = await self.post(body)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("private-test-token", response.text)
            self.assertNotIn("sk-" + "a" * 30, response.text)
        self.runner.assert_not_awaited()

    async def test_body_size_limit(self):
        response = await self.client.post("/chat", content="x" * 16001, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        self.runner.assert_not_awaited()

    async def test_cached_replay_does_not_repeat_paid_work(self):
        self.assertEqual((await self.post()).status_code, 200)
        self.assertEqual((await self.post()).status_code, 200)
        self.runner.assert_awaited_once()
        self.assertEqual(self.authenticate.await_count, 2)
        self.assertEqual((await self.post({**self.body, "question": "其他问题"})).status_code, 409)

    async def test_two_users_cannot_share_answer_cache(self):
        self.authenticate.side_effect = [Principal(17, "user-a"), Principal(18, "user-b")]
        await self.post(); await self.post()
        self.assertEqual(self.runner.await_count, 2)
        self.assertEqual([call.kwargs["platform_token"] for call in self.runner.await_args_list], ["user-a", "user-b"])

    async def test_rate_limit(self):
        for _ in range(6):
            self.assertEqual((await self.post({**self.body, "request_id": str(uuid4())})).status_code, 200)
        self.assertEqual((await self.post({**self.body, "request_id": str(uuid4())})).status_code, 429)
        self.assertEqual(self.runner.await_count, 6)

    async def test_same_user_concurrency_is_blocked(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def slow(*args, **kwargs):
            started.set(); await release.wait()
            return AgentAnswer("完成", 1, 1, 4)
        self.runner.side_effect = slow
        first = asyncio.create_task(self.post())
        await asyncio.wait_for(started.wait(), 5)
        try:
            self.assertEqual((await self.post({**self.body, "request_id": str(uuid4())})).status_code, 409)
        finally:
            release.set(); await first
        self.assertEqual(self.runner.await_count, 1)

    async def test_unexpected_runner_error_is_sanitized(self):
        self.runner.side_effect = RuntimeError("private-provider-error")
        response = await self.post()
        events = [json.loads(line) for line in response.text.splitlines()]
        self.assertEqual(events[-1]["type"], "error")
        self.assertNotIn("private-provider-error", response.text)
        self.assertFalse(self.app.state.active)

    async def test_preflight_failure_stops_before_runner(self):
        app = create_app(authenticate=self.authenticate, ready=lambda: (_ for _ in ()).throw(RuntimeError("private-local")), runner=self.runner)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as client:
            response = await client.post("/chat", json=self.body)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("private-local", response.text)
        self.runner.assert_not_awaited()

    async def test_closing_stream_cancels_runner_and_releases_user(self):
        started, cancelled = asyncio.Event(), asyncio.Event()
        async def slow(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        self.runner.side_effect = slow
        endpoint = next(route.endpoint for route in self.app.routes if route.path == "/chat")
        request = Request({"type": "http", "headers": [(b"authorization", b"Bearer fixture")]})
        response = await endpoint(ChatInput(**self.body), request)
        await anext(response.body_iterator)
        await asyncio.wait_for(started.wait(), 5)
        await response.body_iterator.aclose()
        self.assertTrue(cancelled.is_set())
        self.assertFalse(self.app.state.active)

    async def test_disconnect_before_first_frame_does_not_leak_admission(self):
        endpoint = next(route.endpoint for route in self.app.routes if route.path == "/chat")
        request = Request({"type": "http", "headers": [(b"authorization", b"Bearer fixture")]})
        response = await endpoint(ChatInput(**self.body), request)
        async def disconnected_send(message):
            raise OSError("offline client disconnect")
        async def receive():
            return {"type": "http.disconnect"}
        with self.assertRaises(Exception):
            await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, disconnected_send)
        self.assertFalse(self.app.state.active)
        self.runner.assert_not_awaited()

    async def test_global_concurrency_is_bounded(self):
        both_started, release = asyncio.Event(), asyncio.Event()
        calls = 0
        async def slow(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                both_started.set()
            await release.wait()
            return AgentAnswer("样例", 1, 0, None)
        self.authenticate.side_effect = [Principal(17, "a"), Principal(18, "b"), Principal(19, "c")]
        self.runner.side_effect = slow
        first = asyncio.create_task(self.post())
        second = asyncio.create_task(self.post())
        await asyncio.wait_for(both_started.wait(), 5)
        try:
            self.assertEqual((await self.post()).status_code, 429)
        finally:
            release.set(); await asyncio.gather(first, second)
        self.assertEqual(self.runner.await_count, 2)

    async def test_cached_answers_still_require_fresh_auth(self):
        await self.post()
        self.authenticate.side_effect = HTTPException(401, "expired")
        self.assertEqual((await self.post()).status_code, 401)
        self.runner.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
