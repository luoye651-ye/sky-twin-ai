"""Explicit opt-in smoke: real paid LLM, fixture Java/MCP; never changes real tasks."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aircraft_agent import run_question
from dispatch_tools import DispatchSession


async def main():
    calls = []
    plan_id = 'DP-' + 'b' * 32
    async def java(_session, method, path, body=None):
        calls.append({'method': method, 'path': path, 'body': body})
        if method == 'GET' and path == '/sky/tasks':
            return [dict(id='FIXTURE-LOG-1', title='样例配送任务', type='logistics', status='created'),
                    dict(id='FIXTURE-ENV-1', title='样例巡检任务', type='environment', status='created')]
        if method == 'POST' and path == '/sky/dispatch/plans':
            return {'id': plan_id, 'status': 'proposed', 'result': {
                'assignments': [{'taskId': 'FIXTURE-LOG-1', 'aircraftId': 'FIXTURE-CARGO'}], 'decisions': []}}
        raise AssertionError('unapproved endpoint')
    fleet = {'source': 'java-fixture', 'simulation': True, 'count': 1, 'aircraft': [
        dict(id='FIXTURE-CARGO', name='样例货运机', type='cargo', status='idle', battery=100,
             payloadCapacity=20, seats=0, model='fixture')]}
    report = {'passed': False, 'real_model': True, 'java_and_mcp': 'isolated fixtures',
              'business_writes': 0, 'checks': {}}
    try:
        with patch.object(DispatchSession, 'request', java), patch('aircraft_agent.query_mcp', AsyncMock(return_value=fleet)):
            answer = await run_question('请为所有待分配的物流任务生成调度方案，优先级普通，先预览不要执行。',
                platform_token='isolated-fixture-identity', knowledge=lambda _q: [], timeout_seconds=90)
        posts = [call for call in calls if call['method'] == 'POST']
        report['checks'] = {
            'only_logistics_selected': len(posts) == 1 and posts[0]['body']['tasks'] == [{'taskId': 'FIXTURE-LOG-1', 'priority': 1}],
            'server_plan_id_returned': answer.dispatch_plan_id == plan_id,
            'not_executed_notice': '尚未分配或起飞' in answer.text,
            'no_assignment_or_flight_call': all(call['path'] in ('/sky/tasks', '/sky/dispatch/plans') for call in calls),
        }
        report['passed'] = all(report['checks'].values())
    except Exception:
        report['error'] = '模型或网络验收未完成；未执行真实业务操作。'
    target = Path(__file__).resolve().parents[1] / 'docs/verification/natural-dispatch-model.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--paid-model', action='store_true', required=True,
                        help='Explicitly enable a real model request that consumes API credits')
    parser.parse_args()
    raise SystemExit(asyncio.run(main()))
