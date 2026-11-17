"""Authenticated owner-scoped AI workbench routes, mounted on the existing Agent app."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from workbench_store import ArtifactStore, ArtifactConflict
from workbench_service import WorkbenchService, CASES, measurements
from workbench_knowledge import index_document, MAX_FILE, scoped_search, search_documents


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class RunInput(Input):
    request_id: str
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal['live', 'demo'] = 'demo'
    external_allowed: bool = False
    source_kind: Literal['none', 'task', 'event', 'analysis'] = 'none'
    source_id: str = ''
    compare_id: str = ''
    parent_id: str = ''

    @model_validator(mode='after')
    def valid(self):
        self.request_id = str(UUID(self.request_id))
        self.question = self.question.strip()
        if not self.question or re.search(r'eyJ[\w-]+\.[\w-]+\.[\w-]+|\bsk-[A-Za-z0-9_-]{16,}', self.question):
            raise ValueError('问题为空或疑似含凭证')
        for ident in (self.source_id, self.compare_id, self.parent_id):
            if ident and not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', ident):
                raise ValueError('记录编号无效')
        if self.source_kind != 'none' and not self.source_id:
            raise ValueError('请填写所选记录编号')
        if self.mode == 'live' and not self.external_allowed:
            raise ValueError('真实分析会向外部模型发送问题及所选业务/知识证据，请先明确授权')
        return self


class Action(Input):
    revision: int = Field(ge=1)
    external_allowed: bool = False


class Preview(Action):
    task_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator('task_ids')
    @classmethod
    def ids(cls, value):
        if len(set(value)) != len(value) or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', v) for v in value):
            raise ValueError('任务编号无效或重复')
        return value


class Reconcile(Action):
    plan_id: str = ''

    @field_validator('plan_id')
    @classmethod
    def plan(cls, value):
        if value and not re.fullmatch(r'DP-[a-f0-9]{32}', value):
            raise ValueError('方案编号无效')
        return value


class Evaluation(Input):
    request_id: str
    evaluation_mode: Literal['retrieval', 'agent'] = 'retrieval'
    case_ids: list[str] = Field(min_length=1, max_length=16)
    variants: list[str] = Field(min_length=1, max_length=2)
    external_allowed: bool = False
    model_profile: Literal['primary', 'secondary'] = 'primary'
    prompt_profile: Literal['standard', 'structured'] = 'standard'

    @model_validator(mode='after')
    def valid(self):
        self.request_id = str(UUID(self.request_id))
        if len(set(self.case_ids)) != len(self.case_ids) or not set(self.case_ids).issubset({c['id'] for c in CASES}):
            raise ValueError('评测用例无效')
        allowed = {'semantic', 'hybrid'} if self.evaluation_mode == 'retrieval' else {'baseline', 'rag'}
        if len(set(self.variants)) != len(self.variants) or not set(self.variants).issubset(allowed):
            raise ValueError('评测方案无效')
        if self.evaluation_mode == 'retrieval' and any(not c.get('section') for c in CASES if c['id'] in self.case_ids):
            raise ValueError('检索评测仅接受带章节标注的用例')
        if self.evaluation_mode == 'agent' and (not self.external_allowed or len(self.case_ids) > 4):
            raise ValueError('真实Agent评测每次最多4条，需明确授权外部模型调用')
        if self.model_profile == 'secondary' and not os.environ.get('SKYTWIN_EVAL_MODEL_SECONDARY', '').strip():
            raise ValueError('尚未在服务端配置第二模型，不自动更换提供方')
        return self


def attach_workbench(app, authenticate, *, store=None, service_factory=WorkbenchService, demo_only=False):
    router = APIRouter(prefix='/workbench')

    def service():
        if not hasattr(app.state, 'workbench'):
            artifacts = store or ArtifactStore(os.environ.get('SKYTWIN_ARTIFACT_DB', str(Path(__file__).parent/'.runtime/workbench.sqlite')))
            artifacts.recover()
            app.state.workbench = service_factory(artifacts)
        return app.state.workbench

    async def principal(request: Request):
        origin = request.headers.get('origin')
        from chat_service import ALLOWED_ORIGINS
        allowed_origins = {'http://127.0.0.1:5180','http://localhost:5180'} if demo_only else ALLOWED_ORIGINS
        if origin and origin not in allowed_origins:
            raise HTTPException(403, '不允许的页面来源')
        return await authenticate(request.headers.get('authorization'))

    def operate(identity):
        if not {'sky:operate', '*:*:*'}.intersection(getattr(identity, 'permissions', ())):
            raise HTTPException(403, '此操作需要sky:operate权限')

    def live_allowed():
        if demo_only:
            raise HTTPException(403, '此为独立样例环境，禁止外部模型和真实Java业务请求')

    @router.get('/config')
    async def config(identity=Depends(principal)):
        return {'demo_only': demo_only, 'daily_runs': 30, 'daily_model_attempts': 60, 'concurrent_jobs': 2,
                'secondary_model_configured': bool(os.environ.get('SKYTWIN_EVAL_MODEL_SECONDARY','').strip())}

    @app.exception_handler(ArtifactConflict)
    async def conflict(_request, error):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': str(error)}, 409)

    def owned(identity, ident):
        try:
            return service().store.get(identity.user_id, ident)
        except KeyError:
            raise HTTPException(404, '运行记录不存在') from None

    @router.get('/runs')
    async def runs(page: int = 1, identity=Depends(principal)):
        if not 1 <= page <= 100000:
            raise HTTPException(422, '页码无效')
        return service().store.runs(identity.user_id, page)

    @router.get('/runs/{ident}')
    async def detail(ident: str, identity=Depends(principal)):
        row = owned(identity, ident)
        row['metrics'] = measurements(row)
        return row

    @router.post('/runs')
    async def create(value: RunInput, identity=Depends(principal)):
        work = service()
        if value.mode == 'live':
            live_allowed()
            operate(identity)
        if value.parent_id:
            owned(identity, value.parent_id)
        previous = work.store.existing_request(identity.user_id, value.request_id, 'workflow', value.model_dump())
        if previous:
            return work.store.get(identity.user_id, previous['id'])
        work.admit(identity.user_id)
        row, fresh = work.store.create_run(identity.user_id, value.request_id, 'workflow', value.model_dump())
        if fresh:
            work.store.claim(identity.user_id, row['id'], row['revision'], {'pending'})
            work.start(identity.user_id, row['id'], identity.token)
        return work.store.get(identity.user_id, row['id'])

    @router.post('/runs/{ident}/resume')
    async def resume(ident: str, value: Action, identity=Depends(principal)):
        work = service()
        row = owned(identity, ident)
        if row['kind'] not in ('workflow','evaluation'):
            raise HTTPException(409,'此类记录只能在原对话入口重新发送，不能从工作台自动恢复')
        if row['checkpoint'].get('step') == 'preview':
            raise ArtifactConflict('预览写入状态不确定，必须先核对Java历史并关联方案；不能重发')
        live = row['input'].get('mode') == 'live' or row['input'].get('evaluation_mode') == 'agent'
        if live:
            live_allowed()
            operate(identity)
            if not value.external_allowed:
                raise HTTPException(422, '恢复可能重发一次只读模型请求，需要重新授权')
        work.admit(identity.user_id)
        work.store.claim(identity.user_id, ident, value.revision, {'interrupted', 'failed', 'cancelled'})
        work.start(identity.user_id, ident, identity.token)
        return work.store.get(identity.user_id, ident)

    @router.post('/runs/{ident}/cancel')
    async def cancel(ident: str, value: Action, identity=Depends(principal)):
        owned(identity, ident)
        await service().cancel(identity.user_id, ident, value.revision)
        return owned(identity, ident)

    @router.post('/runs/{ident}/preview')
    async def preview(ident: str, value: Preview, identity=Depends(principal)):
        live_allowed()
        operate(identity)
        owned(identity, ident)
        try:
            await service().preview(identity.user_id, ident, value.revision, [dict(taskId=v, priority=1) for v in value.task_ids], identity.token)
        except ArtifactConflict:
            raise
        except Exception:
            raise HTTPException(409, '预览未完成，请刷新运行状态；结果不确定时先核对Java调度历史') from None
        return owned(identity, ident)

    @router.post('/runs/{ident}/reconcile')
    async def reconcile(ident: str, value: Reconcile, identity=Depends(principal)):
        live_allowed()
        owned(identity, ident)
        try:
            await service().reconcile(identity.user_id, ident, value.revision, identity.token, value.plan_id)
        except (ValueError, KeyError) as error:
            raise HTTPException(409, str(error)) from None
        return owned(identity, ident)

    @router.get('/cases')
    async def cases(identity=Depends(principal)):
        return CASES

    @router.post('/evaluations')
    async def evaluation(value: Evaluation, identity=Depends(principal)):
        work = service()
        if value.evaluation_mode == 'agent':
            live_allowed()
            operate(identity)
        previous = work.store.existing_request(identity.user_id, value.request_id, 'evaluation', value.model_dump())
        if previous:
            return work.store.get(identity.user_id, previous['id'])
        work.admit(identity.user_id)
        row, fresh = work.store.create_run(identity.user_id, value.request_id, 'evaluation', value.model_dump())
        if fresh:
            work.store.claim(identity.user_id, row['id'], row['revision'], {'pending'})
            work.start(identity.user_id, row['id'], identity.token)
        return work.store.get(identity.user_id, row['id'])

    @router.get('/documents')
    async def documents(identity=Depends(principal)):
        return service().store.documents(identity.user_id)

    @router.post('/documents')
    async def upload(file: UploadFile = File(...), document_id: str = Form(''), identity=Depends(principal)):
        operate(identity)
        work = service()
        if document_id and not re.fullmatch(r'KD-[a-f0-9]{32}', document_id):
            raise HTTPException(422, '文档编号无效')
        data = await file.read(MAX_FILE+1)
        name = (file.filename or '').replace('\\', '/').split('/')[-1][:150]
        if not data or len(data) > MAX_FILE or Path(name).suffix.lower() not in ('.txt', '.md', '.docx', '.pdf'):
            raise HTTPException(422, '请选择2MiB以内的TXT/Markdown/DOCX/文字PDF')
        work.admit(identity.user_id)
        try:
            ident, version = work.store.add_document(identity.user_id, name, data, document_id or None)
        except KeyError:
            raise HTTPException(404, '文档不存在') from None
        key = ident+'-'+str(version)
        task = asyncio.create_task(asyncio.to_thread(index_document, work.store, ident, version, name, data))
        work.jobs[key] = (identity.user_id, task)
        task.add_done_callback(lambda _done: work.jobs.pop(key, None))
        return dict(id=ident, version=version, status='indexing')

    @router.delete('/documents/{ident}')
    async def delete_document(ident: str, identity=Depends(principal)):
        operate(identity)
        try:
            service().store.delete_document(identity.user_id, ident)
        except KeyError:
            raise HTTPException(404, '文档不存在') from None
        return {'deleted': True}

    @router.get('/documents/search')
    async def search(q: str, identity=Depends(principal)):
        if not 1 <= len(q.strip()) <= 1000:
            raise HTTPException(422, '请输入1～1000字符')
        return await asyncio.to_thread(search_documents, service().store, identity.user_id, q)

    async def shutdown():
        if hasattr(app.state, 'workbench'):
            work = app.state.workbench
            tasks = [task for _uid, task in work.jobs.values()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    original_lifespan = app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(current_app):
        async with original_lifespan(current_app):
            try:
                yield
            finally:
                await shutdown()
    app.router.lifespan_context = lifespan

    @router.post('/reset')
    async def reset(identity=Depends(principal)):
        if not demo_only:
            raise HTTPException(403, '只有独立样例环境允许重置自己的演示记录')
        work = service()
        work.admit(identity.user_id)
        with work.store.connect() as db:
            db.execute('DELETE FROM ai_span WHERE run_id IN (SELECT id FROM ai_run WHERE owner=?)', (identity.user_id,))
            db.execute('DELETE FROM ai_run WHERE owner=?', (identity.user_id,))
            db.execute('DELETE FROM ai_document WHERE owner=?', (identity.user_id,))
        return {'reset': True, 'scope': 'current_owner_ai_artifacts_only'}

    app.include_router(router)
    return service
