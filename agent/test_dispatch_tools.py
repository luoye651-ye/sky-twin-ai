"""Real LangChain tool loop + isolated Java HTTP responses; no paid calls or business changes."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from langchain_core.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

from aircraft_agent import run_question, AgentRunError
from dispatch_tools import DispatchSession
from sky_client import SkyReadError
from test_aircraft_agent import DATA, call_message

PLAN = 'DP-' + 'a' * 32
ROWS = [{'id': 'T-1', 'title': '配送', 'status': 'created', 'type': 'logistics'},
        {'id': 'T-2', 'title': '已完成', 'status': 'completed', 'type': 'logistics'}]
SELECTION = [{'taskId': 'T-1', 'priority': 1}]


class DispatchFake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        assert [tool.name for tool in tools] == ['list_aircraft', 'list_dispatch_tasks', 'preview_dispatch', 'locate_on_map', 'query_business', 'read_business_record']
        for tool in tools:
            assert 'token' not in tool.args_schema.model_json_schema().get('properties', {})
        return self


def call(name, args=None):
    return AIMessage(content='', tool_calls=[{'name': name, 'args': args or {}, 'id': name, 'type': 'tool_call'}])


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_filters_and_caches_tasks(self):
        session = DispatchSession('fixture-token')
        session.request = AsyncMock(return_value=ROWS)
        first, second = await asyncio.gather(session.list_tasks(), session.list_tasks())
        self.assertEqual(first, second)
        self.assertEqual(first['count'], 1)
        session.request.assert_awaited_once_with('GET', '/sky/tasks')

    async def test_requires_query_and_rejects_unknown_duplicate_and_oversized(self):
        session = DispatchSession('fixture-token')
        session.request = AsyncMock()
        with self.assertRaises(SkyReadError):
            await session.preview(SELECTION)
        session.tasks = ROWS[:1]
        for selection in ([], SELECTION * 2, [{'taskId': 'unknown', 'priority': 1}], SELECTION * 21):
            with self.assertRaises(SkyReadError):
                await session.preview(selection)
        session.request.assert_not_awaited()

    async def test_one_preview_no_assignment_and_repeat_reuses(self):
        session = DispatchSession('fixture-token')
        session.tasks = ROWS[:1]
        session.request = AsyncMock(return_value={'id': PLAN, 'status': 'proposed', 'result': {}})
        first, second = await asyncio.gather(session.preview(SELECTION), session.preview(SELECTION))
        self.assertEqual(first, second)
        session.request.assert_awaited_once_with('POST', '/sky/dispatch/plans', {'tasks': SELECTION})
        with self.assertRaises(SkyReadError):
            await session.preview([{'taskId': 'T-1', 'priority': 3}])

    async def test_uncertain_post_never_retried(self):
        session = DispatchSession('fixture-token')
        session.tasks = ROWS[:1]
        session.request = AsyncMock(side_effect=SkyReadError('超时'))
        for _ in range(2):
            with self.assertRaises(SkyReadError):
                await session.preview(SELECTION)
        self.assertEqual(session.request.await_count, 1)

    async def test_http_permissions_business_errors_and_credentials_sanitized(self):
        for status, body in ((403, {}), (200, {'code': 403}), (200, {'code': True}), (200, {})):
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.request.return_value = httpx.Response(status, json=body)
            with patch('dispatch_tools.httpx.AsyncClient', return_value=client):
                with self.assertRaises(SkyReadError) as failure:
                    await DispatchSession('fixture-secret').request('GET', '/sky/tasks')
            self.assertNotIn('fixture-secret', str(failure.exception))

    async def test_real_graph_returns_only_server_plan_id_and_no_false_execution(self):
        model = DispatchFake(responses=[call_message('aircraft'), call('list_dispatch_tasks'),
            call('preview_dispatch', {'tasks': SELECTION}), AIMessage(content='我已起飞')])
        async def java(_self, method, path, body=None):
            if method == 'GET' and path == '/sky/tasks':
                return ROWS
            self.assertEqual((method, path, body), ('POST', '/sky/dispatch/plans', {'tasks': SELECTION}))
            return {'id': PLAN, 'status': 'proposed', 'result': {}}
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock, return_value=DATA), patch.object(DispatchSession, 'request', java):
            answer = await run_question('为待分配配送任务生成方案', model=model, platform_token='fixture-token')
        self.assertEqual(answer.dispatch_plan_id, PLAN)
        self.assertIn('尚未分配或起飞', answer.text)
        self.assertNotIn('我已起飞', answer.text)

    async def test_failure_cannot_become_successful_plan(self):
        model = DispatchFake(responses=[call('list_dispatch_tasks'), AIMessage(content='成功')])
        with patch.object(DispatchSession, 'request', AsyncMock(side_effect=SkyReadError('没有权限'))):
            with self.assertRaisesRegex(AgentRunError, '没有权限'):
                await run_question('生成方案', model=model, platform_token='fixture-token')

    async def test_preview_loads_aircraft_when_model_omits_prerequisite(self):
        model = DispatchFake(responses=[call('list_dispatch_tasks'),
            call('preview_dispatch', {'tasks': SELECTION}), AIMessage(content='请审查方案')])
        request = AsyncMock(side_effect=[ROWS, {'id': PLAN, 'status': 'proposed', 'result': {}}])
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock, return_value=DATA) as aircraft, \
                patch.object(DispatchSession, 'request', request):
            answer = await run_question('只为指定任务生成预览', model=model, platform_token='fixture-token')
        aircraft.assert_awaited_once_with('fixture-token')
        self.assertEqual(answer.dispatch_plan_id, PLAN)
        self.assertEqual(answer.mcp_calls, 1)
        self.assertEqual(request.await_args_list[-1].args,
            ('POST', '/sky/dispatch/plans', {'tasks': SELECTION}))

    async def test_automatic_aircraft_read_failure_never_posts_preview(self):
        model = DispatchFake(responses=[call('list_dispatch_tasks'),
            call('preview_dispatch', {'tasks': SELECTION}), AIMessage(content='已生成')])
        request = AsyncMock(return_value=ROWS)
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock,
                   side_effect=SkyReadError('飞行器查询无权限')) as aircraft, \
                patch.object(DispatchSession, 'request', request):
            with self.assertRaisesRegex(AgentRunError, '飞行器查询无权限'):
                await run_question('生成预览', model=model, platform_token='fixture-token')
        aircraft.assert_awaited_once_with('fixture-token')
        request.assert_awaited_once_with('GET', '/sky/tasks')

    async def test_automatic_aircraft_read_still_rejects_unknown_resource(self):
        model = DispatchFake(responses=[call('list_dispatch_tasks'),
            call('preview_dispatch', {'tasks': SELECTION, 'aircraft_ids': ['unknown']}),
            AIMessage(content='已生成')])
        request = AsyncMock(return_value=ROWS)
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock, return_value=DATA), \
                patch.object(DispatchSession, 'request', request):
            with self.assertRaisesRegex(AgentRunError, '真实飞行器编号'):
                await run_question('生成预览', model=model, platform_token='fixture-token')
        request.assert_awaited_once_with('GET', '/sky/tasks')

    async def test_parallel_aircraft_and_repeated_previews_share_one_read_and_post(self):
        parallel = AIMessage(content='', tool_calls=[
            {'name': 'list_aircraft', 'args': {}, 'id': 'aircraft', 'type': 'tool_call'},
            *[{'name': 'preview_dispatch', 'args': {'tasks': SELECTION},
               'id': f'preview-{i}', 'type': 'tool_call'} for i in range(2)]])
        model = DispatchFake(responses=[call('list_dispatch_tasks'), parallel, AIMessage(content='请审查')])
        request = AsyncMock(side_effect=[ROWS, {'id': PLAN, 'status': 'proposed', 'result': {}}])
        async def query(_token):
            await asyncio.sleep(0)
            return DATA
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock, side_effect=query) as aircraft, \
                patch.object(DispatchSession, 'request', request):
            answer = await run_question('生成一个方案', model=model, platform_token='fixture-token')
        aircraft.assert_awaited_once_with('fixture-token')
        self.assertEqual(request.await_count, 2)
        self.assertEqual(answer.dispatch_plan_id, PLAN)

    async def test_auto_reads_still_reject_unknown_or_completed_task(self):
        selection = [{'taskId': 'T-2', 'priority': 1}]
        model = DispatchFake(responses=[call('preview_dispatch', {'tasks': selection}),
            AIMessage(content='成功')])
        request = AsyncMock(return_value=ROWS)
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock, return_value=DATA), \
                patch.object(DispatchSession, 'request', request):
            with self.assertRaisesRegex(AgentRunError, '未查询到的待分配任务'):
                await run_question('生成预览', model=model, platform_token='fixture-token')
        request.assert_awaited_once_with('GET', '/sky/tasks')

    async def test_title_lookup_can_preview_after_refreshing_pending_ids(self):
        model = DispatchFake(responses=[call('query_business',
            {'kind': 'tasks', 'keyword': '配送', 'state': 'created'}),
            call('preview_dispatch', {'tasks': SELECTION}), AIMessage(content='请审查')])
        request = AsyncMock(side_effect=[{'rows': ROWS[:1]}, ROWS,
            {'id': PLAN, 'status': 'proposed', 'result': {}}])
        with patch('aircraft_agent.query_mcp', new_callable=AsyncMock, return_value=DATA) as aircraft, \
                patch.object(DispatchSession, 'request', request):
            answer = await run_question('按唯一标题生成预览', model=model, platform_token='fixture-token')
        aircraft.assert_awaited_once_with('fixture-token')
        self.assertEqual(request.await_count, 3)
        self.assertEqual(request.await_args_list[1].args, ('GET', '/sky/tasks'))
        self.assertEqual(request.await_args_list[2].args,
            ('POST', '/sky/dispatch/plans', {'tasks': SELECTION}))
        self.assertEqual(answer.dispatch_plan_id, PLAN)
