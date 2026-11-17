"""Authenticated loopback chat API. Never use a global platform identity for Web calls."""
import asyncio
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
import re
import time
from uuid import UUID

import httpx
import anyio
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from aircraft_agent import AgentRunError, run_question
from conversation_store import ConversationStore
from rag import AGENT_DIR, KnowledgeError, corpus, get_index, search_knowledge

ALLOWED_ORIGINS = {"http://127.0.0.1:5173", "http://localhost:5173"}


@dataclass
class Principal:
    user_id: int
    token: str = field(repr=False)
    permissions: tuple[str, ...] = ()


async def platform_identity(authorization: str | None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "请先登录平台。")
    token = authorization[7:]
    if not token or len(token) > 8192 or not token.isascii() or not token.isprintable() or any(c.isspace() for c in token):
        raise HTTPException(401, "登录身份无效，请重新登录。")
    try:
        async with httpx.AsyncClient(timeout=8, trust_env=False, follow_redirects=False) as client:
            response = await client.get("http://127.0.0.1:8081/getInfo", headers={"Authorization": authorization})
        if response.status_code in (401, 403):
            raise HTTPException(response.status_code, "登录已失效或权限不足，请重新登录。")
        if response.status_code != 200:
            raise HTTPException(503, "Java身份校验服务暂不可用。")
        data = response.json()
        if not isinstance(data, dict) or type(data.get("code")) is not int:
            raise ValueError("schema")
        if data["code"] in (401, 403):
            raise HTTPException(data["code"], "登录已失效或权限不足，请重新登录。")
        if data["code"] != 200:
            raise HTTPException(503, "Java身份校验未完成。")
        permissions = data.get("permissions")
        if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
            raise ValueError("permissions")
        if not {"sky:read", "*:*:*"}.intersection(permissions):
            raise HTTPException(403, "此账号没有sky:read权限。")
        user_id = data["user"]["userId"]
        if type(user_id) is not int or user_id < 1:
            raise ValueError("identity")
        return Principal(user_id, token, tuple(permissions))
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        raise HTTPException(503, "无法校验平台身份，请检查Java服务。") from None


def ensure_ready():
    index = get_index()
    if corpus()[1] != index.manifest:
        raise KnowledgeError("项目知识已变化，请核对文档后重建索引。")
    # Do not expose keys in the health response or create a provider request.
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key is None:
        key = dotenv_values(AGENT_DIR / ".env").get("DEEPSEEK_API_KEY")
    if not key or not key.strip():
        raise KnowledgeError("DeepSeek配置尚未就绪，请在本机配置API Key。")


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=2000)
    request_id: str
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def clean_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("empty")
        if re.search(r"eyJ[\w-]+\.[\w-]+\.[\w-]+|\bsk-[A-Za-z0-9_-]{16,}", value):
            raise ValueError("credential-like text")
        return value

    @field_validator("request_id", "conversation_id")
    @classmethod
    def uuid_id(cls, value):
        return str(UUID(value)) if value is not None else None


class BodyLimit:
    """Cap request bodies before JSON parsing; no request content is logged."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        body_limit = 2 * 1024 * 1024 + 16000 if scope.get('path') in ('/workbench/documents','/vision-chat') else 16000
        try:
            if int(headers.get(b"content-length", b"0")) > body_limit:
                return await JSONResponse({"detail": "请求内容过大。"}, 413)(scope, receive, send)
        except ValueError:
            return await JSONResponse({"detail": "请求格式异常。"}, 400)(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > body_limit:
                raise HTTPException(413, "请求内容过大。")
            return message

        await self.app(scope, bounded_receive, send)


class ManagedStream(StreamingResponse):
    """Close the generator on every ASGI disconnect/send-error path, including pre-start."""
    def __init__(self, *args, on_close, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_close = on_close

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                with anyio.CancelScope(shield=True):
                    close = getattr(self.body_iterator, "aclose", None)
                    if close:
                        await close()
            finally:
                self.on_close()


def create_app(*, authenticate=platform_identity, ready=ensure_ready, runner=run_question, knowledge=search_knowledge,
               artifact_store=None, workbench_factory=None):
    app = FastAPI(title="SkyTwin Agent Dispatch Preview", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    active: dict[int, object] = {}
    rates = defaultdict(deque)
    cache = {}  # Bounded, ephemeral answer replay; never stores credentials or task state.
    conversations = ConversationStore()
    app.state.conversations = conversations
    app.state.active = active

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, _error):
        return JSONResponse({"detail": "问题须为1～2000字符、请求编号须为UUID；请勿输入密钥或令牌。"}, 422)

    @app.get("/health")
    async def health():
        try:
            await asyncio.to_thread(ready)
        except Exception:
            return JSONResponse({"ready": False, "message": "Agent模型或知识索引尚未就绪，请检查本机配置。"}, 503)
        return {"ready": True, "readOnly": False, "message": "助手及调度预览已就绪，分配需人工确认"}

    @app.post("/chat")
    async def chat(body: ChatInput, request: Request):
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            raise HTTPException(403, "不允许的页面来源。")
        identity = await authenticate(request.headers.get("authorization"))
        now = time.monotonic()
        for key, value in list(cache.items()):
            if now - value[0] > 600:
                cache.pop(key)
        conversation_key = conversations.key(identity.user_id, identity.token, body.conversation_id)
        key = (identity.user_id, conversation_key[1], body.request_id)
        question_hash = hashlib.sha256((body.question + "\n" + str(body.conversation_id)).encode()).hexdigest()
        if key in cache:
            if cache[key][1] != question_hash:
                raise HTTPException(409, "此请求编号已用于其他问题。")
            return StreamingResponse(iter([json.dumps(cache[key][2], ensure_ascii=False) + "\n"]),
                                     media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})
        if identity.user_id in active:
            raise HTTPException(409, "上一条问题仍在处理，请等待完成或停止等待后再试。")
        if len(active) >= 2:
            raise HTTPException(429, "助手繁忙，请稍后再试。")
        for user_id, times in list(rates.items()):
            while times and now - times[0] > 60:
                times.popleft()
            if not times and user_id not in active:
                rates.pop(user_id, None)
        if len(rates[identity.user_id]) >= 6:
            raise HTTPException(429, "每分钟最多提交6条问题，请稍后再试。")
        try:
            await asyncio.to_thread(ready)
        except Exception:
            raise HTTPException(503, "知识索引或模型配置未就绪，请检查Agent服务。") from None
        # No await between final admission and reservation: two same-user requests cannot race.
        if identity.user_id in active or len(active) >= 2:
            raise HTTPException(409, "已有问题正在处理，请稍后再试。")
        reservation = object()
        active[identity.user_id] = reservation
        rates[identity.user_id].append(now)

        def release():
            if active.get(identity.user_id) is reservation:
                active.pop(identity.user_id, None)

        async def events():
            queue = asyncio.Queue()

            async def execute():
                try:
                    context_options = {"history": conversations.history(conversation_key)} if body.conversation_id else {}
                    answer = await runner(body.question, **context_options, knowledge=knowledge, platform_token=identity.token,
                                          log=lambda message: queue.put_nowait({"type": "progress", "message": message}))
                    if body.conversation_id:
                        conversations.append(conversation_key, body.question, answer)
                    event = {"type": "answer", "data": asdict(answer)}
                    if len(cache) >= 100:
                        cache.pop(next(iter(cache)))
                    cache[key] = (time.monotonic(), question_hash, event)
                    queue.put_nowait(event)
                except AgentRunError as error:
                    queue.put_nowait({"type": "error", "message": str(error)})
                except Exception:
                    queue.put_nowait({"type": "error", "message": "助手暂时无法完成查询，请检查模型或本地服务。"})

            task = asyncio.create_task(execute())
            try:
                yield json.dumps({"type": "progress", "message": "已通过平台身份校验，正在理解问题……"}, ensure_ascii=False) + "\n"
                last_heartbeat = time.monotonic()
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    except TimeoutError:
                        if await request.is_disconnected():
                            break
                        if time.monotonic() - last_heartbeat >= 10:
                            yield '{"type":"heartbeat"}\n'
                            last_heartbeat = time.monotonic()
                        continue
                    yield json.dumps(event, ensure_ascii=False) + "\n"
                    if event["type"] in {"answer", "error"}:
                        break
            finally:
                release()
                if not task.done():
                    task.cancel()
                with anyio.CancelScope(shield=True):
                    await asyncio.gather(task, return_exceptions=True)

        return ManagedStream(events(), on_close=release, media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    from workbench_api import attach_workbench
    options = {'service_factory': workbench_factory} if workbench_factory else {}
    workbench = attach_workbench(app, authenticate, store=artifact_store, **options)
    from vision_chat import attach_vision_chat
    attach_vision_chat(app, authenticate, workbench)
    return app


app = create_app()
