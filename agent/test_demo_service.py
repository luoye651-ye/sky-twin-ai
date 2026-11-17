import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from demo_service import create_demo_app


class DemoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        settings=root/'credentials.json';settings.write_text(json.dumps({'password':'fixture-demo-password-only'}))
        self.app=create_demo_app(settings,root/'sample.sqlite')
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://127.0.0.1')
        self.addAsyncCleanup(self.client.aclose)
        response=await self.client.post('/login',json={'username':'demo','password':'fixture-demo-password-only'})
        self.token=response.json()['token'];self.headers={'Authorization':'Bearer '+self.token,'Origin':'http://127.0.0.1:5180'}

    async def test_separate_login_and_empty_business_snapshot(self):
        self.assertTrue(self.token.startswith('demo_'))
        response=await self.client.get('/sky/snapshot',headers=self.headers)
        self.assertEqual(response.json()['data']['tasks'],[])
        self.assertEqual((await self.client.get('/getInfo',headers={'Authorization':'Bearer production-token'})).status_code,401)

    async def test_external_calls_and_java_preview_are_blocked_before_execution(self):
        with patch('workbench_service.run_question',side_effect=AssertionError('external forbidden')), patch('workbench_service.DispatchSession.request',side_effect=AssertionError('java forbidden')):
            body={'request_id':str(uuid4()),'question':'live test','mode':'live','external_allowed':True}
            self.assertEqual((await self.client.post('/workbench/runs',json=body,headers=self.headers)).status_code,403)
            self.assertEqual((await self.client.post('/workbench/runs/AR-fixture/preview',json={'revision':1,'task_ids':['T1']},headers=self.headers)).status_code,403)
            self.assertEqual((await self.client.post('/workbench/evaluations',json={'request_id':str(uuid4()),'evaluation_mode':'agent','case_ids':['R01'],'variants':['rag'],'external_allowed':True},headers=self.headers)).status_code,403)

    async def test_demo_run_and_reset_never_touch_other_account(self):
        created=await self.client.post('/workbench/runs',json={'request_id':str(uuid4()),'question':'demo','mode':'demo'},headers=self.headers)
        self.assertEqual(created.status_code,200)
        work=self.app.state.workbench
        await asyncio.gather(*(task for _uid,task in work.jobs.values()))
        other,_=work.store.create_run(2,str(uuid4()),'workflow',{'mode':'fixture'})
        response=await self.client.post('/workbench/reset',headers=self.headers)
        self.assertTrue(response.json()['reset'])
        self.assertEqual(work.store.runs(1)['total'],0)
        self.assertEqual(work.store.get(2,other['id'])['owner'],2)

    async def test_logout_revokes_only_demo_session(self):
        await self.client.post('/logout',headers=self.headers)
        self.assertEqual((await self.client.get('/workbench/runs',headers=self.headers)).status_code,401)


if __name__=='__main__':unittest.main()
