"""Explicit paid LLM verification with fixture Java data and real local RAG."""
import asyncio
import json
from unittest.mock import patch, AsyncMock
from aircraft_agent import run_question
from dispatch_tools import DispatchSession
from conversation_store import ConversationStore
from rag import ROOT, search_knowledge


async def main():
    posts=[]
    async def java(_session,method,path,body=None):
        if method=='GET' and path=='/sky/tasks':
            return [dict(id='WF-LOG-1',title='测试物流',type='logistics',status='created'),dict(id='WF-ENV-1',title='测试巡检',type='environment',status='created')]
        if method=='POST' and path=='/sky/dispatch/plans':
            posts.append(body)
            return dict(id='DP-'+str(len(posts))*32,status='proposed',result={})
        raise AssertionError('unexpected endpoint')
    fleet=dict(count=1,source='fixture',simulation=True,aircraft=[dict(id='WF-CARGO',name='样例货运机',type='cargo',status='idle',battery=100,payloadCapacity=20,seats=0,model='fixture')])
    store=ConversationStore();key=store.key(1,'fixture','session'); report={'passed':False,'java':'isolated fixture','real_llm':True,'business_writes':0,'checks':{}}
    try:
        with patch.object(DispatchSession,'request',java),patch('aircraft_agent.query_mcp',AsyncMock(return_value=fleet)):
            q='为所有待分配的物流任务生成普通优先级调度预览'
            first=await run_question(q,platform_token='fixture',knowledge=search_knowledge)
            store.append(key,q,first)
            second=await run_question('把刚才那批任务改成紧急，只生成预览',platform_token='fixture',knowledge=search_knowledge,history=store.history(key))
            third=await run_question('在地图上定位待分配任务WF-LOG-1',platform_token='fixture',knowledge=search_knowledge)
            fourth=await run_question('上传图片分析后会自动生成环境事件吗，位置从哪里来？请附依据',platform_token='fixture',knowledge=search_knowledge)
        report['checks']={
            'same_logistics_task_only':len(posts)==2 and all([item['taskId'] for item in body['tasks']]==['WF-LOG-1'] for body in posts),
            'followup_priority_changed':len(posts)==2 and posts[1]['tasks'][0]['priority']==3,
            'verified_task_map_target':any(item['kind']=='task' and item['id']=='WF-LOG-1' for item in third.map_targets),
            'rag_has_inspectable_evidence':bool(fourth.sources) and all(item.get('text') and item.get('version') for item in fourth.sources)}
        report['rag_answer']=fourth.text
        report['rag_sources']=[{key:hit[key] for key in ('source','section','text','version')} for hit in fourth.sources]
        report['passed']=all(report['checks'].values())
    except Exception:
        report['error']='真实模型验收未完成，未调用真实业务写接口'
    target=ROOT/'docs/verification/assistant-workflows.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--paid-model',action='store_true',required=True);parser.parse_args()
    raise SystemExit(asyncio.run(main()))
