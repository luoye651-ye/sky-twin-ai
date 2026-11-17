"""Offline fake-model tests: real LangChain loop, no provider calls or real token."""
import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from mcp.client.stdio import StdioServerParameters
from pydantic import Field

from aircraft_agent import AgentRunError, build_agent, run_question
from sky_client import SkyReadError
from test_sky_client import ROW

DATA = {"source": "java", "simulation": True, "count": 1, "aircraft": [ROW]}


class ToolCallingFake(FakeMessagesListChatModel):
    seen_payloads: list[str] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        assert [t.name for t in tools] in (["list_aircraft"], ["list_aircraft", "list_dispatch_tasks", "preview_dispatch", "locate_on_map", "query_business", "read_business_record"])
        schema = tools[0].args_schema.model_json_schema()
        assert schema.get("properties", {}) == {}  # No token or arbitrary URL parameter.
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen_payloads.append(repr(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def call_message(*ids):
    return AIMessage(content="", tool_calls=[
        {"name": "list_aircraft", "args": {}, "id": ident, "type": "tool_call"}
        for ident in ids
    ])


class AircraftAgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.identity = patch("aircraft_agent.get_platform_token", return_value="offline-fixture-token")
        self.identity.start()
        self.addCleanup(self.identity.stop)

    async def test_real_langchain_loop_calls_mcp_and_summarizes(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="样例飞机电量90.0%。")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA) as query:
            result = await run_question("查询飞机", model=model)
        query.assert_awaited_once_with("offline-fixture-token")
        self.assertEqual((result.mcp_calls, result.tool_messages, result.aircraft_count), (1, 1, 1))
        self.assertIn("90.0", result.text)
        self.assertNotIn("offline-fixture-token", " ".join(model.seen_payloads))
        self.assertIn("fixture-A1", " ".join(model.seen_payloads))

    async def test_repeated_and_parallel_tools_query_once(self):
        model = ToolCallingFake(responses=[call_message("one", "two"), call_message("three"), AIMessage(content="查询完成")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA) as query:
            result = await run_question("查询", model=model)
        query.assert_awaited_once()
        self.assertEqual(result.tool_messages, 3)

    async def test_auth_failure_blocks_fabricated_answer(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="错误地声称有4架")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, side_effect=SkyReadError("登录已失效")):
            with self.assertRaisesRegex(AgentRunError, "登录已失效"):
                await run_question("查询", model=model)

    async def test_unexpected_error_does_not_leak_raw_exception(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="失败")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, side_effect=RuntimeError("private-test-value")):
            with self.assertRaises(AgentRunError) as error:
                await run_question("查询", model=model)
        self.assertNotIn("private-test-value", str(error.exception))

    async def test_no_tool_is_not_a_successful_query(self):
        model = ToolCallingFake(responses=[AIMessage(content="我查询了4架飞机且已起飞")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock) as query:
            with self.assertRaisesRegex(AgentRunError, "没有完成只读查询"):
                await run_question("起飞", model=model)
        query.assert_not_awaited()

    async def test_missing_token_fails_before_model_creation(self):
        with patch("aircraft_agent.get_platform_token", side_effect=SkyReadError("未配置令牌")), patch("aircraft_agent.create_llm") as create:
            with self.assertRaisesRegex(AgentRunError, "未配置令牌"):
                await run_question("查询")
        create.assert_not_called()

    async def test_empty_and_long_input_rejected_before_token(self):
        with patch("aircraft_agent.get_platform_token") as token:
            for question in ("   ", "a" * 2001):
                with self.assertRaises(AgentRunError):
                    await run_question(question)
        token.assert_not_called()

    async def test_timeout_is_bounded(self):
        async def slow_query(_):
            await asyncio.sleep(10)
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="完成")])
        with patch("aircraft_agent.query_mcp", side_effect=slow_query):
            with self.assertRaisesRegex(AgentRunError, "超时"):
                await run_question("查询", model=model, timeout_seconds=0.1)

    async def test_empty_fleet_is_success(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="当前没有登记飞机")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value={**DATA, "count": 0, "aircraft": []}):
            result = await run_question("查询", model=model)
        self.assertEqual(result.aircraft_count, 0)

    async def test_no_tools_can_write(self):
        graph, trace = build_agent(ToolCallingFake(responses=[]), "fixture")
        self.assertEqual(trace.mcp_calls, 0)
        self.assertIn("tools", graph.nodes)

    async def test_infinite_tool_loop_is_bounded(self):
        model = ToolCallingFake(responses=[call_message("one")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA) as query:
            with self.assertRaisesRegex(AgentRunError, "循环限制"):
                await run_question("查询", model=model)
        query.assert_awaited_once()

    async def test_truncated_answer_is_not_presented_as_complete(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="未完成", response_metadata={"finish_reason": "length"})])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA):
            with self.assertRaisesRegex(AgentRunError, "截断"):
                await run_question("查询", model=model)

    async def test_blank_final_answer_is_rejected(self):
        model = ToolCallingFake(responses=[call_message("one"), AIMessage(content="")])
        with patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA):
            with self.assertRaisesRegex(AgentRunError, "有效的最终回答"):
                await run_question("查询", model=model)

    async def test_model_configuration_error_is_sanitized(self):
        with patch("aircraft_agent.create_llm", side_effect=RuntimeError("private-provider-value")):
            with self.assertRaises(AgentRunError) as error:
                await run_question("查询")
        self.assertNotIn("private-provider-value", str(error.exception))

    async def test_langchain_through_real_stdio_with_fixture_server(self):
        # Real MCP framing/child lifecycle; only the Java adapter is replaced by a fixture.
        # Do not inherit any provider/platform credentials into this child.
        code = (
            "import mcp_server; "
            f"mcp_server.get_aircraft=lambda: {json.dumps([ROW], ensure_ascii=True)}; "
            "mcp_server.server.run(transport='stdio')"
        )
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-u", "-c", code],
            cwd=str(Path(__file__).resolve().parent),
            env={"SKYTWIN_TOKEN": "offline-fixture-token", "PYTHONUTF8": "1"},
        )
        model = ToolCallingFake(responses=[call_message("stdio"), AIMessage(content="这是协议测试样例，不是真实飞机。")])
        with patch("mcp_smoke.server_parameters", return_value=parameters):
            result = await run_question("查询", model=model, timeout_seconds=30)
        self.assertEqual((result.aircraft_count, result.mcp_calls), (1, 1))


if __name__ == "__main__":
    unittest.main()
