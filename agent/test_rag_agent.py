"""Real LangChain graph, scripted model responses; no paid model or business calls."""
import unittest
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import AIMessage

from aircraft_agent import AgentRunError, run_question
from test_aircraft_agent import DATA, ToolCallingFake, call_message

HIT = {
    "chunk_id": "fixture-knowledge", "source": "agent/knowledge/airspace.md", "section": "测试规则",
    "line_start": 3, "line_end": 6, "text": "测试规则：恰好等于限高允许通过。", "score": 0.9,
    "code_references": ["AirspaceEngine.java"],
}


class RAGFake(ToolCallingFake):
    def bind_tools(self, tools, **kwargs):
        assert [t.name for t in tools] == ["list_aircraft", "search_knowledge"]
        assert tools[0].args_schema.model_json_schema().get("properties", {}) == {}
        assert set(tools[1].args_schema.model_json_schema()["properties"]) == {"query"}
        return self


def search_call(query="限高", ident="search"):
    return AIMessage(content="", tool_calls=[{"name": "search_knowledge", "args": {"query": query}, "id": ident, "type": "tool_call"}])


class RAGAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_knowledge_only_does_not_need_platform_token(self):
        model = RAGFake(responses=[search_call(), AIMessage(content="恰好等于限高允许通过。[K1]")])
        with patch("aircraft_agent.get_platform_token", side_effect=AssertionError("must not read token")), patch("aircraft_agent.query_mcp", new_callable=AsyncMock) as mcp:
            answer = await run_question("规则是什么", model=model, knowledge=lambda q: [HIT])
        mcp.assert_not_awaited()
        self.assertEqual((answer.mcp_calls, answer.knowledge_calls, answer.aircraft_count), (0, 1, None))
        self.assertEqual(answer.sources[0]["source"], HIT["source"])
        self.assertEqual(answer.sources[0]["text"], HIT["text"])
        self.assertIn("测试规则", " ".join(model.seen_payloads))

    async def test_mixed_question_uses_both_tools(self):
        model = RAGFake(responses=[call_message("aircraft"), search_call(), AIMessage(content="样例飞机存在；限高规则见[K1]。")])
        with patch("aircraft_agent.get_platform_token", return_value="fixture-local-token"), patch("aircraft_agent.query_mcp", new_callable=AsyncMock, return_value=DATA) as mcp:
            answer = await run_question("查询飞机和限高规则", model=model, knowledge=lambda q: [HIT])
        mcp.assert_awaited_once_with("fixture-local-token")
        self.assertEqual((answer.mcp_calls, answer.knowledge_calls), (1, 1))
        self.assertNotIn("fixture-local-token", " ".join(model.seen_payloads))

    async def test_no_evidence_overrides_model_fabrication(self):
        model = RAGFake(responses=[search_call("无关问题"), AIMessage(content="编造的规则[K99]")])
        answer = await run_question("无关问题", model=model, knowledge=lambda q: [])
        self.assertIn("没有找到", answer.text)
        self.assertNotIn("编造", answer.text)
        self.assertEqual(answer.sources, [])

    async def test_missing_and_fabricated_citations_rejected(self):
        for text in ("限高允许通过", "限高允许通过[K99]", "限高允许通过[K1][K99]"):
            model = RAGFake(responses=[search_call(), AIMessage(content=text)])
            with self.assertRaisesRegex(AgentRunError, "引用"):
                await run_question("规则", model=model, knowledge=lambda q: [HIT])

    async def test_retrieval_exception_sanitized(self):
        model = RAGFake(responses=[search_call(), AIMessage(content="规则[K1]")])
        with self.assertRaises(AgentRunError) as error:
            await run_question("规则", model=model, knowledge=Mock(side_effect=RuntimeError("private-local-path")))
        self.assertNotIn("private-local-path", str(error.exception))

    async def test_repeated_search_is_cached_and_citation_stable(self):
        model = RAGFake(responses=[search_call(ident="one"), search_call(ident="two"), AIMessage(content="规则[K1]")])
        lookup = Mock(return_value=[HIT])
        answer = await run_question("规则", model=model, knowledge=lookup)
        lookup.assert_called_once_with("限高")
        self.assertEqual((answer.knowledge_calls, len(answer.sources)), (1, 1))

    async def test_search_budget_is_enforced(self):
        model = RAGFake(responses=[*[search_call(query=str(i), ident=str(i)) for i in range(4)], AIMessage(content="规则[K1]")])
        with self.assertRaisesRegex(AgentRunError, "最多检索3次"):
            await run_question("规则", model=model, knowledge=lambda q: [HIT])

    async def test_aircraft_auth_failure_not_replaced_by_knowledge(self):
        model = RAGFake(responses=[call_message("one"), search_call(), AIMessage(content="规则[K1]")])
        with patch("aircraft_agent.get_platform_token", side_effect=RuntimeError("private-token")):
            with self.assertRaises(AgentRunError) as error:
                await run_question("飞机和规则", model=model, knowledge=lambda q: [HIT])
        self.assertNotIn("private-token", str(error.exception))


if __name__ == "__main__":
    unittest.main()
