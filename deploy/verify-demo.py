"""Exercise the actual loopback sample gateway, auth, indexing and local eval; never LLM/Java."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import httpx

ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'tmp/workbench-demo-verification.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--after-restart',action='store_true');args=parser.parse_args()
    settings=json.loads((ROOT/'agent/.runtime/demo/credentials.json').read_text(encoding='utf-8-sig'))
    checks=[]
    def check(ok,name):
        if not ok: raise AssertionError(name)
        checks.append(name)
    with httpx.Client(base_url='http://127.0.0.1:5180',timeout=30,trust_env=False,follow_redirects=True) as client:
        for path in ('/','/ai-workbench','/index.html'):
            reply=client.get(path);check(reply.status_code==200 and 'name="skytwin-demo" content="isolated"' in reply.text,'isolated HTML marker '+path)
        check(client.get('/agent-api/workbench/runs').status_code==401,'anonymous sample records rejected')
        login=client.post('/java-api/login',json={'username':'demo','password':settings['password']}).json()
        check(login.get('code')==200,'sample normal login succeeded')
        token=login['token'];client.headers.update({'Authorization':'Bearer '+token,'Origin':'http://127.0.0.1:5180'})
        check(client.get('/agent-api/workbench/config').json()['demo_only'],'server enforces sample mode')
        check(client.get('/java-api/sky/snapshot').json()['data']['tasks']==[],'no production task dataset in sample')
        if args.after_restart:
            report=json.loads(OUTPUT.read_text(encoding='utf-8'))
            row=client.get('/agent-api/workbench/runs/'+report['workflow_id']).json()
            digest=hashlib.sha256(json.dumps(row['checkpoint'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            check(row['status']=='awaiting_review' and digest==report['checkpoint_sha256'] and [s['id'] for s in row['spans']]==report['span_ids'],'workflow checkpoints and exact span IDs survive process restart')
            evaluation=client.get('/agent-api/workbench/runs/'+report['evaluation_id']).json()
            check(len(evaluation['checkpoint']['rows'])==6,'evaluation results survive process restart')
            report['after_restart_checks']=checks
        else:
            check(client.post('/agent-api/workbench/runs',json={'request_id':str(uuid4()),'question':'不得发出真实调用','mode':'live','external_allowed':True}).status_code==403,'real model calls forbidden in sample')
            check(client.post('/agent-api/workbench/runs/AR-example/preview',json={'revision':1,'task_ids':['T1']}).status_code==403,'Java preview forbidden in sample')
            request_id=str(uuid4())
            payload={'request_id':request_id,'question':'展示独立演示流程','mode':'demo'}
            run=client.post('/agent-api/workbench/runs',json=payload).json();ident=run['id']
            check(client.post('/agent-api/workbench/runs',json=payload).json()['id']==ident,'duplicate request reuses durable run')
            def wait_run(run_id):
                for _ in range(150):
                    row=client.get('/agent-api/workbench/runs/'+run_id).json()
                    if row['status'] not in ('running','pending'):return row
                    time.sleep(.1)
                raise AssertionError('run did not finish within local acceptance timeout')
            row=wait_run(ident)
            check(row['status']=='awaiting_review' and '独立合成样例' in row['checkpoint']['answer']['text'],'synthetic workflow is explicitly labeled')
            check(row['metrics']['model_calls']==0 and row['metrics']['tool_calls']==0,'sample has zero model/tool calls')
            original='独立演示巡检操作规范：发现疑似漂浮物后，必须人工复核图片来源、坐标和采集时间。任何自动化流程不得自动起飞或宣称真实清理完成。'
            upload=client.post('/agent-api/workbench/documents',files={'file':('public-demo-rules.md',original.encode(),'text/markdown')})
            check(upload.status_code==200,'actual multipart document accepted')
            document=upload.json();doc_id=document['id']
            def wait_document(version):
                for _ in range(150):
                    rows=client.get('/agent-api/workbench/documents').json()
                    found=next(r for r in rows if r['id']==doc_id and r['version']==version)
                    if found['status']!='indexing':return found
                    time.sleep(.1)
                raise AssertionError('local document indexing timeout')
            check(wait_document(1)['status']=='ready','actual CPU embedding completed')
            hits=client.get('/agent-api/workbench/documents/search',params={'q':'发现疑似漂浮物后必须人工复核哪些信息？'}).json()
            check(any(h.get('source')=='uploaded/'+doc_id for h in hits),'owner document retrieved with real embedding')
            updated='独立演示维修规程：维修完成后保留原电量，不能凭空恢复到100%。由人工填写维修说明和恢复原因。'
            upload=client.post('/agent-api/workbench/documents',data={'document_id':doc_id},files={'file':('public-demo-rules.md',updated.encode(),'text/markdown')})
            check(upload.json()['version']==2 and wait_document(2)['status']=='ready','new document version indexed')
            rows=client.get('/agent-api/workbench/documents').json()
            check(next(r for r in rows if r['id']==doc_id and r['version']==1)['status']=='superseded','old document immediately excluded')
            check(client.delete('/agent-api/workbench/documents/'+doc_id).status_code==200,'document deletion succeeded')
            hits=client.get('/agent-api/workbench/documents/search',params={'q':'独立演示维修规程'}).json()
            check(not any(h.get('source')=='uploaded/'+doc_id for h in hits),'deleted document no longer retrieved')
            evaluation=client.post('/agent-api/workbench/evaluations',json={'request_id':str(uuid4()),'evaluation_mode':'retrieval','case_ids':['R01','R03','R06'],'variants':['semantic','hybrid']}).json()
            result=wait_run(evaluation['id'])
            check(result['status']=='completed' and len(result['checkpoint']['rows'])==6,'actual local evaluation produced both variants')
            check(result['metrics']['model_calls']==0,'retrieval evaluation has zero external calls')
            report={'date':datetime.now(timezone(timedelta(hours=8))).date().isoformat(),'scope':'actual isolated sample HTTP/gateway/CPU retrieval, not real Java/model/browser acceptance',
                    'workflow_id':ident,'evaluation_id':evaluation['id'],'checks':checks,
                    'checkpoint_sha256':hashlib.sha256(json.dumps(row['checkpoint'],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                    'span_ids':[s['id'] for s in row['spans']],
                    'evaluation_rows':result['checkpoint']['rows'],'external_model_calls':0,'production_business_writes':0}
        check('Admin-Token' not in client.cookies,'sample HTTP client did not use production auth cookie')
        report['last_verified_at_utc']=datetime.now(timezone.utc).isoformat()
        OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(checks),'after_restart':args.after_restart,'report':str(OUTPUT.relative_to(ROOT))},ensure_ascii=False))


if __name__=='__main__':main()
