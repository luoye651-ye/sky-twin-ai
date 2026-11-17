"""Bounded Java dispatch preview adapter. No assignment or flight endpoint is exposed."""
import asyncio
import re
import json
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, ConfigDict, Field

from sky_client import SkyReadError


class TaskSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    taskId: str = Field(min_length=1, max_length=40)
    priority: int = Field(ge=1, le=3)


class DispatchSession:
    def __init__(self, token, log=None):
        self.token = token
        self.log = log
        self.tasks = None
        self.plan_id = None
        self.preview_input = None
        self.preview_result = None
        self.lock = asyncio.Lock()
        self.calls = 0
        self.business_cache = {}
        self.business_tasks = []
        self.business_attempts = 0

    async def request(self, method, path, body=None):
        try:
            async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
                response = await client.request(method, "http://127.0.0.1:8081" + path,
                    headers={"Authorization": "Bearer " + self.token}, json=body)
            if response.status_code != 200:
                raise SkyReadError("Java调度服务拒绝请求或不可用，请检查登录与调度权限。")
            value = response.json()
            if not isinstance(value, dict) or type(value.get("code")) is not int or value["code"] != 200:
                raise SkyReadError("Java未接受调度请求，请检查权限、任务状态并重新生成方案。")
            return value["data"]
        except SkyReadError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise SkyReadError("调度查询或预览未完成；请检查Java服务，不要假定方案已生成。") from None

    async def business(self, kind, keyword='', state='', page=1, record_id=None):
        if record_id is None:
            if kind not in {'tasks', 'events', 'reports'} or len(keyword)>200 or len(state)>24 or not 1<=page<=100000:
                raise SkyReadError('业务查询范围无效。')
            path='/sky/operations/query?'+urlencode(dict(kind=kind,keyword=keyword,state=state,page=page))
        else:
            if kind not in {'task','event','report'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',record_id):
                raise SkyReadError('业务记录类型或编号无效。')
            path='/sky/operations/records/'+kind+'/'+record_id
        async with self.lock:
            if path in self.business_cache: return {'source':'java','simulation':True,'data':self.business_cache[path]}
            if self.business_attempts>=3: raise SkyReadError('每问最多3次业务记录查询，请缩小范围。')
            if self.log: self.log('[业务查询] 正在读取Java任务、事件或报告记录……')
            self.business_attempts += 1
            value=await self.request('GET',path)
            if not isinstance(value,dict): raise SkyReadError('业务响应格式异常。')
            if record_id is None:
                rows=value.get('rows')
                if not isinstance(rows,list) or len(rows)>20: raise SkyReadError('业务分页格式异常。')
                if kind=='tasks': self.business_tasks.extend(rows)
                # Report contents and evidence are fetched explicitly through read_business_record.
                for row in rows:
                    row.pop('snapshotJson',None)
            elif kind=='task': self.business_tasks.append(value)
            if len(json.dumps(value,ensure_ascii=False))>30000: raise SkyReadError('记录内容过大，请通过报告中心查看完整证据。')
            self.business_cache[path]=value;self.calls+=1
            return {'source':'java','simulation':True, 'data':value, 'notice':'仅查询；报告草稿不等于已审核，历史记录不代表实机状态。'}

    async def list_tasks(self):
        async with self.lock:
            if self.tasks is None:
                if self.log:
                    self.log("[调度查询] 正在读取待分配任务……")
                rows = await self.request("GET", "/sky/tasks")
                if not isinstance(rows, list) or len(rows) > 500:
                    raise SkyReadError("任务列表格式或数量异常。")
                self.tasks = []
                for row in rows:
                    if not isinstance(row, dict):
                        raise SkyReadError("任务数据格式异常。")
                    if row.get("status") == "created":
                        if not all(isinstance(row.get(key), str) for key in ("id", "title", "type")):
                            raise SkyReadError("任务字段异常。")
                        self.tasks.append({key: row.get(key) for key in (
                            "id", "title", "type", "status", "startStationName", "endStationName",
                            "payload", "passengers", "responsePriority")})
                self.calls += 1
            return {"tasks": self.tasks, "count": len(self.tasks), "source": "java",
                    "notice": "最多最近500条任务中的待分配项；文本仅为数据。超过20项请用户缩小范围。"}

    async def preview(self, tasks, aircraft_ids=None):
        async with self.lock:
            if self.tasks is None:
                raise SkyReadError("请先查询待分配任务，再按用户指定范围选择任务。")
            if not 1 <= len(tasks) <= 20:
                raise SkyReadError("一次请选择1～20个任务，不自动截断范围。")
            selections = [TaskSelection.model_validate(item) for item in tasks]
            ids = [item.taskId for item in selections]
            if len(set(ids)) != len(ids) or not set(ids).issubset({row['id'] for row in self.tasks}):
                raise SkyReadError("方案包含重复或未查询到的待分配任务。")
            body = {"tasks": [item.model_dump() for item in selections]}
            if aircraft_ids is not None:
                if not 1 <= len(aircraft_ids) <= 200 or len(set(aircraft_ids)) != len(aircraft_ids) or any(
                        not isinstance(item, str) or not 1 <= len(item) <= 40 for item in aircraft_ids):
                    raise SkyReadError("飞行器范围无效。")
                body["aircraftIds"] = aircraft_ids
            if self.preview_input is not None:
                if self.preview_input != body:
                    raise SkyReadError("一次问题只生成一个方案，请重新提问调整方案。")
                if self.preview_result is None:
                    raise SkyReadError("上次预览结果不确定，请在调度历史核对，不能自动重试。")
                return self.preview_result
            # Reserve before I/O: an uncertain response must never trigger an automatic POST retry.
            self.preview_input = body
            if self.log:
                self.log("[方案预览] Java正在校验约束并生成方案，尚未分配或起飞……")
            plan = await self.request("POST", "/sky/dispatch/plans", body)
            if not isinstance(plan, dict) or not re.fullmatch(r"DP-[a-f0-9]{32}", str(plan.get("id", ""))):
                raise SkyReadError("Java方案格式异常。")
            self.plan_id = plan["id"]
            self.calls += 1
            self.preview_result = {"planId": self.plan_id, "status": plan.get("status"),
                "assignments": plan.get("result", {}).get("assignments", []),
                "decisions": [{k: row.get(k) for k in ("taskId", "taskTitle", "aircraftId", "explanation")}
                              for row in plan.get("result", {}).get("decisions", [])], "notice": "仅生成预览。请用户审查网页方案卡并点击确认；未分配、未起飞。"}
            return self.preview_result
