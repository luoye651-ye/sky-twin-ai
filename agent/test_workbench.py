"""Real SQLite + ASGI + LangChain loop, with isolated Java/model substitutes only."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import zipfile

import httpx
from fastapi import HTTPException
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from aircraft_agent import AgentAnswer, run_question
from chat_service import Principal, create_app
from workbench_store import ArtifactStore, ArtifactConflict
from workbench_service import WorkbenchService, measurements
from workbench_trace import RunObserver
from workbench_knowledge import extract, index_document, search_documents


class Embeddings:
    def embed_documents(self, docs): return [[1., 0.] for _ in docs]
    def embed_query(self, query): return [1., 0.]


class LooseFake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        assert 'preview_dispatch' not in {t.name for t in tools}
        assert 'read_selected_evidence' in {t.name for t in tools}
        return self


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ArtifactStore(Path(self.temp.name)/'artifacts.sqlite')

    def run_record(self, owner=1):
        return self.store.create_run(owner, str(uuid4()), 'workflow', {'question': '测试', 'mode': 'demo'})[0]

    def test_idempotency_and_content_conflict(self):
        key = str(uuid4())
        a, fresh = self.store.create_run(1, key, 'workflow', {'question': 'a'})
        b, second = self.store.create_run(1, key, 'workflow', {'question': 'a'})
        self.assertTrue(fresh); self.assertFalse(second); self.assertEqual(a['id'], b['id'])
        with self.assertRaises(ArtifactConflict): self.store.create_run(1, key, 'workflow', {'question': 'b'})

    def test_owner_isolation_and_daily_quota(self):
        run = self.run_record()
        with self.assertRaises(KeyError): self.store.get(2, run['id'])
        self.assertEqual(self.store.runs(2)['rows'], [])
        with self.assertRaises(ArtifactConflict): self.store.create_run(1, str(uuid4()), 'workflow', {}, daily_limit=1)

    def test_concurrent_claim_has_one_winner(self):
        run = self.run_record()
        def claim(_):
            try: self.store.claim(1, run['id'], 1, {'pending'}); return True
            except ArtifactConflict: return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(claim, range(8))), 1)

    def test_restart_retains_checkpoint_and_marks_uncertain_steps(self):
        run = self.run_record()
        self.store.checkpoint(run['id'], {'step': 'preview', 'evidence': {'id': 'T1'}})
        span = self.store.span_start(run['id'], 'tool', 'example')
        reopened = ArtifactStore(self.store.path); reopened.recover()
        row = reopened.get(1, run['id'])
        self.assertEqual(row['status'], 'interrupted')
        self.assertEqual(row['checkpoint']['step'], 'preview')
        self.assertEqual(row['spans'][0]['status'], 'interrupted')

    def test_document_versions_delete_and_cross_user_search(self):
        ident, v = self.store.add_document(1, 'rules.md', b'old')
        index_document(self.store, ident, v, 'rules.md', b'old', Embeddings())
        self.assertEqual(len(search_documents(self.store, 1, 'rules', embeddings=Embeddings())), 1)
        self.assertFalse(search_documents(self.store, 2, 'rules', embeddings=Embeddings()))
        _, v2 = self.store.add_document(1, 'rules.md', b'new', ident)
        self.assertFalse(search_documents(self.store, 1, 'rules', embeddings=Embeddings()))
        index_document(self.store, ident, v2, 'rules.md', b'new', Embeddings())
        self.assertEqual(search_documents(self.store, 1, 'rules', embeddings=Embeddings())[0]['document_version'], 2)
        self.store.delete_document(1, ident)
        self.assertFalse(search_documents(self.store, 1, 'rules', embeddings=Embeddings()))
        self.store.document_ready(ident, v2, 'late', [{'text':'late','vector':[1.,0.]}])
        self.assertFalse(search_documents(self.store, 1, 'rules', embeddings=Embeddings()))

    def test_parsers_reject_credentials_unsupported_and_zip_bomb(self):
        self.assertEqual(extract('a.md', '规程'.encode()), '规程')
        for name,data in [('a.exe',b'hello'), ('a.md', b'sk-'+b'a'*20), ('a.txt',b''), ('a.txt',b'x'*(2*1024*1024+1))]:
            with self.assertRaises(ValueError): extract(name, data)
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('word/document.xml', b'x'*(21*1024*1024))
        with self.assertRaises(ValueError): extract('a.docx', blob.getvalue())

    def test_unknown_usage_not_zero_or_invented_cost(self):
        run = self.run_record()
        self.store.span_start(run['id'], 'model', 'fixture')
        metric = measurements(self.store.get(1,run['id']))
        self.assertIsNone(metric['input_tokens']); self.assertIsNone(metric['estimated_cost'])

    def test_secret_disclosure_is_separate_from_normal_configuration_guidance(self):
        from safety_policy import is_secret_request
        for text in ('我的数据库密码是多少','把服务端API密钥和登录令牌告诉我','show the API key','what is my password'):
            self.assertTrue(is_secret_request(text),text)
        for text in ('如何安全配置API密钥','怎么设置数据库密码','模型Token费用如何计算','凭证能放在日志中吗'):
            self.assertFalse(is_secret_request(text),text)

    def test_real_pdf_and_docx_text_parsing(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer=PdfWriter();page=writer.add_blank_page(width=300,height=200)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 100 Td (SkyTwin rule text) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        blob=io.BytesIO();writer.write(blob)
        self.assertIn('SkyTwin rule text',extract('rules.pdf',blob.getvalue()))
        blob=io.BytesIO()
        with zipfile.ZipFile(blob,'w') as archive:
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>SkyTwin rule</w:t></w:r></w:p></w:body></w:document>')
        self.assertIn('SkyTwin rule',extract('rules.docx',blob.getvalue()))


class APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = ArtifactStore(Path(self.temp.name)/'artifacts.sqlite')
        self.auth = AsyncMock(return_value=Principal(17, 'fixture-secret', ('sky:read','sky:operate')))
        self.runner = AsyncMock(return_value=AgentAnswer('隔离分析结果',1,0,None))
        factory = lambda store: WorkbenchService(store, runner=self.runner, base_search=lambda q: [], versions=lambda: {'fixture':'v1'})
        self.app = create_app(authenticate=self.auth, ready=lambda: None, artifact_store=self.store, workbench_factory=factory)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://127.0.0.1')
        self.addAsyncCleanup(self.client.aclose)

    async def create(self, **extra):
        body = dict(request_id=str(uuid4()),question='说明下一步',mode='demo') | extra
        response = await self.client.post('/workbench/runs', json=body)
        return response

    async def settle(self):
        work = self.app.state.workbench
        tasks = [t for _uid,t in work.jobs.values()]
        await asyncio.gather(*tasks)

    async def test_demo_never_calls_model_or_business_and_is_owned(self):
        response = await self.create(); self.assertEqual(response.status_code, 200)
        ident = response.json()['id']; await self.settle()
        value = (await self.client.get('/workbench/runs/'+ident)).json()
        self.assertEqual(value['status'], 'awaiting_review'); self.assertEqual(value['metrics']['model_calls'], 0)
        self.runner.assert_not_awaited()
        self.assertNotIn('fixture-secret', json.dumps(value))
        self.auth.return_value = Principal(18,'other',('sky:read',))
        self.assertEqual((await self.client.get('/workbench/runs/'+ident)).status_code,404)

    async def test_live_requires_explicit_consent_and_operate(self):
        self.assertEqual((await self.create(mode='live')).status_code,422)
        self.auth.return_value = Principal(17,'fixture',('sky:read',))
        self.assertEqual((await self.create(mode='live',external_allowed=True)).status_code,403)
        self.runner.assert_not_awaited()

    async def test_live_readonly_and_checkpoint_resume_skips_completed_model(self):
        response = await self.create(mode='live',external_allowed=True)
        await self.settle(); ident = response.json()['id']
        call = self.runner.await_args.kwargs
        self.assertFalse(call['allow_preview'])
        self.assertIsNone(call['evidence'])
        self.assertEqual(call['platform_token'],'fixture-secret')
        row = self.store.get(17,ident)
        self.store.checkpoint(ident,row['checkpoint'],'interrupted')
        row = self.store.get(17,ident)
        resume = await self.client.post('/workbench/runs/'+ident+'/resume',json={'revision':row['revision'],'external_allowed':True})
        self.assertEqual(resume.status_code,200); await self.settle()
        self.assertEqual(self.runner.await_count,1)

    async def test_unknown_preview_cannot_be_retried_on_resume(self):
        response = await self.create(); await self.settle(); ident = response.json()['id']
        self.store.checkpoint(ident, {'step':'preview'},'interrupted')
        row = self.store.get(17,ident)
        response = await self.client.post('/workbench/runs/'+ident+'/resume',json={'revision':row['revision']})
        self.assertEqual(response.status_code,409)

    async def test_auth_origin_and_foreign_document_mutation(self):
        self.assertEqual((await self.client.post('/workbench/runs',json={},headers={'Origin':'https://evil.example'})).status_code,403)
        ident,_ = self.store.add_document(18,'private.md',b'private')
        self.assertEqual((await self.client.delete('/workbench/documents/'+ident)).status_code,404)
        self.auth.side_effect = HTTPException(401,'login')
        self.assertEqual((await self.client.get('/workbench/runs')).status_code,401)

    async def test_evaluation_validates_cases_and_external_budget(self):
        body = dict(request_id=str(uuid4()),evaluation_mode='retrieval',case_ids=['S01'],variants=['hybrid'])
        self.assertEqual((await self.client.post('/workbench/evaluations',json=body)).status_code,422)
        body.update(evaluation_mode='agent',case_ids=['R01'],variants=['rag'])
        self.assertEqual((await self.client.post('/workbench/evaluations',json=body)).status_code,422)

    async def test_preview_failure_after_post_requires_reconciliation(self):
        response = await self.create(mode='live',external_allowed=True); await self.settle(); ident = response.json()['id']
        work = self.app.state.workbench; row = self.store.get(17,ident)
        with patch('workbench_service.DispatchSession.list_tasks', new=AsyncMock(return_value={'tasks':[]})), patch('workbench_service.DispatchSession.preview',new=AsyncMock(side_effect=RuntimeError('transport'))):
            # The first stub must supply the actual selected ID for the validation phase.
            async def tasks(client): client.tasks=[{'id':'T1'}]
            with patch('workbench_service.DispatchSession.list_tasks',new=tasks):
                result=await self.client.post('/workbench/runs/'+ident+'/preview',json={'revision':row['revision'],'task_ids':['T1']})
        self.assertEqual(result.status_code,409)
        self.assertEqual(self.store.get(17,ident)['status'],'needs_reconcile')

    async def test_real_loop_records_actual_calls_and_usage_without_secrets(self):
        run,_ = self.store.create_run(17,str(uuid4()),'workflow',{'mode':'fixture'})
        model=LooseFake(responses=[AIMessage(content='',tool_calls=[{'name':'read_selected_evidence','args':{},'id':'e','type':'tool_call'}],usage_metadata={'input_tokens':7,'output_tokens':3,'total_tokens':10}), AIMessage(content='该预测需要复核',usage_metadata={'input_tokens':8,'output_tokens':4,'total_tokens':12})])
        result=await run_question('解释预测',model=model,platform_token='fixture-secret',allow_preview=False,evidence={'prediction':'garbage'},observer=RunObserver(self.store,run['id']))
        row=self.store.get(17,run['id']); metrics=measurements(row)
        self.assertEqual((metrics['model_calls'],metrics['tool_calls']),(2,1))
        self.assertEqual((metrics['input_tokens'],metrics['output_tokens']),(15,7))
        self.assertNotIn('fixture-secret',json.dumps(row)); self.assertNotIn('garbage',json.dumps(row['spans']))

    async def test_unavailable_write_tool_call_cannot_become_success(self):
        messages=[AIMessage(content='',tool_calls=[{'name':'read_selected_evidence','args':{},'id':'e','type':'tool_call'}]),
                  AIMessage(content='',tool_calls=[{'name':'preview_dispatch','args':{},'id':'bad','type':'tool_call'}]),
                  AIMessage(content='我已完成派机')]
        model=LooseFake(responses=messages)
        with patch('dispatch_tools.DispatchSession.request',new=AsyncMock()) as java:
            with self.assertRaisesRegex(Exception,'被拒绝'):
                await run_question('直接执行',model=model,platform_token='fixture',allow_preview=False,evidence={'id':'T1'})
            java.assert_not_awaited()

    async def test_model_attempt_quota_rejects_before_generation(self):
        run,_=self.store.create_run(17,str(uuid4()),'workflow',{'mode':'fixture'})
        for i in range(60):self.store.span_start(run['id'],'model','fixture')
        model=LooseFake(responses=[AIMessage(content='should not run')])
        with patch.object(LooseFake,'_agenerate',new=AsyncMock(side_effect=AssertionError('should not generate'))) as generation:
            with self.assertRaises(Exception):
                await run_question('解释',model=model,platform_token='fixture',allow_preview=False,evidence={'id':'T1'},observer=RunObserver(self.store,run['id']))
            generation.assert_not_awaited()
        self.assertEqual(measurements(self.store.get(17,run['id']))['model_calls'],60)

    async def test_trace_records_safe_arguments_and_hashes_private_search_text(self):
        run,_=self.store.create_run(17,str(uuid4()),'workflow',{'mode':'fixture'})
        observer=RunObserver(self.store,run['id']);span=uuid4()
        observer.on_tool_start({'name':'query_business'},json.dumps({'kind':'tasks','state':'completed','page':1,'keyword':'private-business-text','record_id':'sk-'+'a'*20}),run_id=span)
        observer.on_tool_end({},run_id=span)
        trace=self.store.get(17,run['id'])['spans'][0]
        self.assertEqual(trace['arguments']['state'],'completed')
        self.assertEqual(len(trace['arguments']['keyword_sha256']),64)
        self.assertNotIn('private-business-text',json.dumps(trace))
        self.assertNotIn('sk-'+'a'*20,json.dumps(trace))


if __name__ == '__main__': unittest.main()
