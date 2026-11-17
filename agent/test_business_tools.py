import unittest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from dispatch_tools import DispatchSession
from sky_client import SkyReadError
from aircraft_agent import run_question
from test_dispatch_tools import DispatchFake, call


class BusinessToolsTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_pagination_and_cache_never_write(self):
        session=DispatchSession('fixture-token')
        session.request=AsyncMock(return_value={'rows':[{'id':'T-old','title':'历史任务','status':'completed'}], 'total':1,'page':1,'size':20})
        first=await session.business('tasks',state='completed')
        second=await session.business('tasks',state='completed')
        self.assertEqual(first['data'],second['data'])
        session.request.assert_awaited_once()
        self.assertEqual(session.request.await_args.args[0],'GET')
        self.assertIn('state=completed',session.request.await_args.args[1])
        self.assertEqual(session.business_tasks[0]['id'],'T-old')

    async def test_only_allowlisted_kinds_ids_and_bounded_queries(self):
        session=DispatchSession('fixture-token');session.request=AsyncMock(return_value={'rows':[],'total':0})
        for kind,id_value in [('credentials',None),('task','../config'),('report','x'*41)]:
            with self.assertRaises(SkyReadError):await session.business(kind,record_id=id_value)
        session.request.assert_not_awaited()
        for page in range(1,4):await session.business('tasks',page=page)
        with self.assertRaises(SkyReadError):await session.business('tasks',page=4)
        self.assertEqual(session.request.await_count,3)

    async def test_completed_task_can_be_located_after_actual_lookup(self):
        model=DispatchFake(responses=[call('query_business',{'kind':'tasks','state':'completed'}),
            call('locate_on_map',{'kind':'task','entity_id':'T-old'}),AIMessage(content='请查看历史任务航线')])
        with patch.object(DispatchSession,'request',AsyncMock(return_value={'rows':[{'id':'T-old','title':'历史任务','status':'completed'}],'total':1})):
            answer=await run_question('定位已完成任务',model=model,platform_token='fixture-token')
        self.assertEqual(answer.map_targets,[{'kind':'task','id':'T-old','label':'历史任务'}])

    async def test_report_draft_reads_server_evidence_without_save_tool(self):
        model=DispatchFake(responses=[call('read_business_record',{'kind':'report','record_id':'OR-fixture'}),AIMessage(content='草稿：本地仿真任务已完成；不能证明实机飞行。')])
        with patch.object(DispatchSession,'request',AsyncMock(return_value={'id':'OR-fixture','status':'draft','snapshot':{'status':'completed','trackCount':10}})) as request:
            answer=await run_question('根据报告起草摘要',model=model,platform_token='fixture-token')
        request.assert_awaited_once_with('GET','/sky/operations/records/report/OR-fixture')
        self.assertIn('草稿',answer.text)
        self.assertIsNone(answer.dispatch_plan_id)

    async def test_oversized_report_is_not_silently_sent(self):
        session=DispatchSession('fixture-token');session.request=AsyncMock(return_value={'content':'x'*30001})
        with self.assertRaisesRegex(SkyReadError,'过大'):await session.business('report',record_id='OR-fixture')
