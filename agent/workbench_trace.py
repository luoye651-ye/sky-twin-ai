"""Record actual LangChain calls, never prompts, credentials or hidden reasoning."""
from langchain_core.callbacks import BaseCallbackHandler
import hashlib
import json
import re


class RunObserver(BaseCallbackHandler):
    raise_error = True
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id

    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kwargs):
        metadata = kwargs.get('metadata') or {}
        name = metadata.get('ls_model_name', 'configured-model')
        if re.search(r'\bsk-[A-Za-z0-9_-]{16,}|eyJ[\w-]+\.[\w-]+\.[\w-]+',str(name)):
            name = 'configured-model'
        self.store.span_start(self.run_id, 'model', name, run_id, parent_run_id)

    def on_llm_end(self, response, *, run_id, **kwargs):
        usage = None
        for generations in response.generations:
            for generation in generations:
                candidate = getattr(getattr(generation, 'message', None), 'usage_metadata', None)
                if candidate:
                    usage = candidate
        if usage is None:
            raw = (response.llm_output or {}).get('token_usage') or {}
            usage = dict(input_tokens=raw.get('prompt_tokens'), output_tokens=raw.get('completion_tokens'))
        self.store.span_end(run_id, summary='模型调用结束；正文不写入调用日志', usage=usage)

    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs):
        raw = kwargs.get('inputs')
        if not isinstance(raw, dict):
            try:
                raw = json.loads(input_str)
            except (ValueError, TypeError):
                raw = {}
        if not isinstance(raw, dict):
            raw = {}
        arguments = {}
        for key in ('kind', 'state', 'record_id', 'entity_id'):
            value = raw.get(key)
            if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,40}',value) and not re.match(r'sk-[A-Za-z0-9_-]{16,}',value):
                arguments[key] = value
        if type(raw.get('page')) is int:
            arguments['page'] = raw['page']
        # Query content may contain private text; retain only a stable digest for correlation.
        for key in ('query','keyword'):
            if isinstance(raw.get(key),str):
                arguments[key+'_sha256'] = hashlib.sha256(raw[key].encode()).hexdigest()
        self.store.span_start(self.run_id, 'tool', (serialized or {}).get('name', 'tool'), run_id, parent_run_id, arguments)

    def on_tool_end(self, output, *, run_id, **kwargs):
        # Tool artifacts can contain business evidence. Persist only type/length, never raw payload.
        self.store.span_end(run_id, summary=f'工具返回类型：{type(output).__name__}')

    def on_tool_error(self, error, *, run_id, **kwargs):
        self.store.span_end(run_id, 'failed', '工具调用失败；请查看运行结果中的安全错误信息')

    def on_llm_error(self, error, *, run_id, **kwargs):
        self.store.span_end(run_id, 'failed', '模型调用失败；原始错误未持久化')
