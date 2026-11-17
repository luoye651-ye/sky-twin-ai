"""Separate, loopback-only sample server. Never authenticates against or calls Java."""
import asyncio
from collections import defaultdict, deque
import hmac
import json
import os
from pathlib import Path
import secrets
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from chat_service import BodyLimit, Principal
from workbench_api import attach_workbench
from workbench_store import ArtifactStore


def create_demo_app(settings_path, artifact_path):
    config = json.loads(Path(settings_path).read_text(encoding='utf-8-sig'))
    if not isinstance(config.get('password'), str) or len(config['password']) < 16:
        raise RuntimeError('独立演示密码必须至少16字符')
    app = FastAPI(title='SkyTwin Isolated Sample', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost'])
    sessions, attempts = {}, defaultdict(deque)

    async def identity(header):
        token = (header or '').removeprefix('Bearer ')
        expiry = sessions.get(token, 0)
        if expiry < time.monotonic():
            sessions.pop(token, None)
            raise HTTPException(401, '独立演示登录已过期')
        return Principal(1, token, ('sky:read','sky:operate'))

    class Login(BaseModel):
        model_config = ConfigDict(extra='ignore')
        username: str = Field(max_length=50)
        password: str = Field(max_length=100)

    @app.get('/captchaImage')
    async def captcha():
        return {'code':200,'captchaEnabled':False,'uuid':'','img':''}

    @app.post('/login')
    async def login(value: Login, request: Request):
        address = request.client.host if request.client else 'loopback'
        queue = attempts[address]
        now = time.monotonic()
        while queue and now-queue[0] > 60:
            queue.popleft()
        if len(queue) >= 6:
            raise HTTPException(429,'演示登录每分钟最多6次')
        queue.append(now)
        if not hmac.compare_digest(value.username, 'demo') or not hmac.compare_digest(value.password, config['password']):
            return {'code':401,'msg':'独立演示账号或密码不正确'}
        for key, expiry in list(sessions.items()):
            if expiry < now: sessions.pop(key, None)
        if len(sessions) >= 30:
            raise HTTPException(429,'演示会话数已达上限，请稍后再试')
        token = 'demo_' + secrets.token_urlsafe(32)
        sessions[token] = now+3600
        return {'code':200,'token':token}

    @app.get('/getInfo')
    async def info(request: Request):
        principal = await identity(request.headers.get('authorization'))
        return {'code':200,'user':{'userId':principal.user_id,'userName':'demo'},'permissions':list(principal.permissions)}

    def snapshot():
        return {'aircraft':[],'stations':[],'tasks':[],'airspaceZones':[],'events':[],'reports':[],'audit':[],
                'summary':{'aircraft':0,'executing':0,'completed':0,'openEvents':0},
                'simulation':{'enabled':True,'timeScale':1,'coordinateSystem':'WGS84','realFlight':False}}

    @app.get('/sky/snapshot')
    async def get_snapshot(request: Request):
        await identity(request.headers.get('authorization'))
        return {'code':200,'data':snapshot()}

    @app.get('/sky/stream')
    async def stream(request: Request):
        await identity(request.headers.get('authorization'))
        async def events():
            yield 'data: '+json.dumps(snapshot())+'\n\n'
            while not await request.is_disconnected():
                await asyncio.sleep(10)
                yield ': isolated sample heartbeat\n\n'
        return StreamingResponse(events(), media_type='text/event-stream', headers={'Cache-Control':'no-store'})

    @app.post('/logout')
    async def logout(request: Request):
        sessions.pop(request.headers.get('authorization','').removeprefix('Bearer '), None)
        return {'code':200}

    @app.get('/health')
    async def health():
        return {'ready':True,'demo_only':True,'message':'独立合成样例；禁止外部模型与Java业务请求'}

    attach_workbench(app, identity, store=ArtifactStore(artifact_path), demo_only=True)
    return app


def app_factory():
    root = Path(__file__).parent/'.runtime/demo'
    return create_demo_app(os.environ.get('SKYTWIN_DEMO_SETTINGS', str(root/'credentials.json')),
                           os.environ.get('SKYTWIN_ARTIFACT_DB', str(root/'artifacts.sqlite')))
