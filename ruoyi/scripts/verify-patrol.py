"""Real fixed-model inference acceptance; preserves the completed demo result.

No fake predictions, dataset changes, training or task/event writes. Optional UI
test uses a temporary viewer and cleans it up; credentials never enter reports.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('patrol_helpers', ROOT / 'ruoyi/scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
h = listing.helpers
BASE = 'http://127.0.0.1:5173/java-api'
PATH = '/sky/patrol-evaluation'
REPORT = {'passed': False, 'checks': [], 'source': 'Real Java, MySQL 3307, CUDA, pinned model and HAIDA test; no mocked responses'}
DEFAULT_AUTH = object()


def check(name, condition):
    assert condition, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', action='store_true')
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    token = h.login(BASE)
    viewer_id = None
    viewer_token = None
    def req(path, body=None, expected=200, auth=DEFAULT_AUTH):
        _, value = h.api(BASE, PATH + path, 'POST' if body is not None else 'GET', body, token if auth is DEFAULT_AUTH else auth)
        assert value['code'] == expected, (path, value['code'], value.get('msg'))
        return value.get('data')
    def image(run, item, kind, auth=token):
        request = urllib.request.Request(BASE + PATH + f'/runs/{run}/images/{item}?kind={kind}', headers={'Authorization': 'Bearer ' + auth})
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read(), response.headers
    def business():
        return h.mysql("SELECT id,status,COALESCE(aircraft_id,'') FROM st_task ORDER BY id;") + '\n' + h.mysql("SELECT id,status FROM st_event ORDER BY id;") + '\n' + h.mysql("SELECT id,status FROM st_aircraft ORDER BY id;")
    try:
        check('dedicated MySQL 3307', h.mysql('SELECT @@port;') == '3307')
        req('/runs', expected=401, auth=None)
        check('anonymous denied', True)
        cfg = req('/config')
        check('pinned model and random sample bounds configured', cfg['ready'] and cfg['imageCount'] == 132 and cfg['sampleMin'] == 1 and cfg['sampleMax'] == 132 and cfg['confidence'] == .25)
        baseline = business()
        marker = str(uuid.uuid4())
        with ThreadPoolExecutor(max_workers=4) as pool:
            starts = list(pool.map(lambda _: req('/runs', {'requestId': marker}), range(4)))
        run_id = starts[0]['id']
        REPORT['runId'] = run_id
        count = starts[0]['imageCount']
        check('server chooses and persists a count from 1 to 132', 1 <= count <= 132 and all(v['imageCount'] == count for v in starts))
        check('concurrent same-request submissions create one job', len({v['id'] for v in starts}) == 1 and sum(not v['reused'] for v in starts) == 1)
        other_marker = str(uuid.uuid4())
        other = req('/runs', {'requestId': other_marker})
        check('different request cannot start a second active GPU job', other['id'] == run_id and other['reused'])
        req('/runs', {'requestId': '../../bad'}, expected=500)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            run = req('/runs/' + run_id)
            if run['status'] in ('completed', 'failed'):
                break
            print('PROGRESS:', run['stage'], run['processed'], flush=True)
            time.sleep(3)
        check('real evaluator completes exactly the planned random count', run['status'] == 'completed' and run['processed'] == count and run['imageCount'] == count)
        report = run['report']
        check('model and dataset provenance match pinned configuration', report['modelSha256'] == cfg['modelSha256'] and report['datasetSha256'] == cfg['datasetSha256'] and report['split'] == 'test')
        output = ROOT / 'ai/runs/patrol' / run_id
        raw = (output / 'report.json').read_bytes()
        check('persisted report SHA matches actual immutable output', hashlib.sha256(raw).hexdigest() == run['reportSha256'] and json.loads(raw) == report)
        rows = report['rows']
        check('all image IDs unique and counts consistent', len(rows) == len({r['id'] for r in rows}) == count and all(r['tp'] + r['fp'] == r['predictionCount'] and r['tp'] + r['fn'] == r['truthCount'] for r in rows))
        manifest = json.loads((ROOT/'ai/data/haida-yolo/manifest.json').read_text(encoding='utf-8'))
        pool = {r['id']:r for r in manifest['records'] if r['split'] == 'test'}
        import random
        expected_ids = sorted(r['id'] for r in random.Random(run_id).sample(sorted(pool.values(),key=lambda r:r['id']),count))
        check('sample is reproducible, unique and drawn before inference', [r['id'] for r in rows] == expected_ids and report['samplingSeed'] == run_id and report['poolImageCount'] == 132 and report['protocolVersion'] == 'haida-patrol-random-v2')
        check('annotations correspond to sampled originals', all(r['truthCount'] == len(pool[r['id']]['boxes']) for r in rows))
        selected = (output/'selected-images.txt').read_text(encoding='utf-8').splitlines()
        check('validator actually receives only selected image paths', sorted(Path(p).stem for p in selected) == expected_ids)
        # Independent implementation, not importing production matching code.
        for row in rows:
            used = set()
            for prediction in sorted(row['predictions'],key=lambda p:-p['confidence']):
                a = prediction['box']
                scores = []
                for index, truth in enumerate(row['truths']):
                    if index in used or truth['classId'] != prediction['classId']: continue
                    b = truth['box']
                    area = max(0,min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])) * max(0,min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]))
                    scores.append((area/(a[2]*a[3]+b[2]*b[3]-area),index))
                score,index = max(scores,default=(0,-1))
                correct = index >= 0 and score >= .5
                assert prediction['correct'] == correct
                if correct:
                    used.add(index)
                    assert abs(prediction['matchedIou']-score) < 1e-9
                else: assert prediction['matchedIou'] is None
            assert row['tp'] == len(used)
        check('independent one-to-one IoU matching reproduces all TP/FP/FN', True)
        check('totals and undefined-denominator metrics are honest', all(sum(r[k] for r in rows) == report[k] for k in ('tp','fp','fn')) and all(r['precision'] is None if not r['predictionCount'] else abs(r['precision'] - r['tp']/r['predictionCount']) < 1e-10 for r in rows))
        check('fixed protocol and valid mAP values', report['confidence'] == .25 and report['matchIou'] == .5 and report['imgsz'] == 640 and 0 <= report['map5095'] <= report['map50'] <= 1)
        for kind in ('predicted', 'truth', 'original'):
            check(kind + ' images complete', len(list((output/kind).glob('*.jpg'))) == count)
            data, headers = image(run_id, rows[0]['id'], kind)
            check(kind + ' authenticated JPEG endpoint', data[:2] == b'\xff\xd8' and headers['Content-Type'] == 'image/jpeg' and headers['X-Content-Type-Options'] == 'nosniff' and 'no-store' in headers['Cache-Control'])
        req(f'/runs/{run_id}/images/{rows[0]["id"]}?kind=unknown', expected=409)
        req(f'/runs/{run_id}/images/data99999_1?kind=predicted', expected=409)
        req(f'/runs/{run_id}/images/{rows[0]["id"]}?kind=predicted', expected=401, auth=None)
        check('invalid image kind and unrelated image rejected', True)
        check('completed request replay remains idempotent', req('/runs', {'requestId': marker})['id'] == run_id)
        check('coalesced request replay after completion also remains idempotent', req('/runs', {'requestId': other_marker})['id'] == run_id)
        check('no task/event/aircraft status changed', baseline == business())
        if args.restart:
            fixture = str(uuid.uuid4())
            h.mysql("INSERT INTO st_patrol_eval(id,request_id,status,stage,model_name,model_sha256,dataset_sha256,created_by) VALUES(" + ','.join(h.sql_value(x) for x in [fixture, str(uuid.uuid4()), 'queued','queued',cfg['modelName'],cfg['modelSha256'],cfg['datasetSha256'],'acceptance']) + ');')
            try:
                for action in ('stop','start'):
                    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/f'ruoyi/scripts/{action}.ps1'),'-Service','backend'],check=True)
                token = h.login(BASE)
                check('restart marks interrupted fixture failed, never completed', req('/runs/'+fixture)['status'] == 'failed')
                check('completed report survives restart', req('/runs/'+run_id)['reportSha256'] == run['reportSha256'])
            finally:
                h.mysql('DELETE FROM st_patrol_eval WHERE id=' + h.sql_value(fixture) + " AND created_by='acceptance';")
        _, roles = h.api(BASE, '/system/role/list?pageNum=1&pageSize=100',token=token)
        role = next(r['roleId'] for r in roles['rows'] if r['roleKey'] == 'sky_viewer')
        name, password = 'pv_' + uuid.uuid4().hex[:12], uuid.uuid4().hex[:12]+'Az!3'
        _, created = h.api(BASE,'/system/user','POST',{'userName':name,'nickName':name,'password':password,'deptId':100,'status':'0','sex':'0','roleIds':[role],'postIds':[]},token)
        assert created['code'] == 200
        _, users = h.api(BASE,'/system/user/list?userName='+name,token=token)
        viewer_id = next(u['userId'] for u in users['rows'] if u['userName'] == name)
        viewer_token = listing.login_as(BASE,name,password)
        req('/runs', {'requestId':str(uuid.uuid4())},expected=403,auth=viewer_token)
        check('viewer can read but cannot start GPU evaluation', req('/runs/'+run_id,auth=viewer_token)['status'] == 'completed')
        check('viewer can read protected image', image(run_id,rows[0]['id'],'predicted',viewer_token)[0][:2] == b'\xff\xd8')
        REPORT['metrics'] = {k:report[k] for k in ('modelName','modelSha256','imageCount','tp','fp','fn','precision','recall','map50','map5095','speedMs')}
        if args.ui:
            legacy = h.mysql("SELECT id FROM st_patrol_eval WHERE status='completed' AND JSON_UNQUOTE(JSON_EXTRACT(report_json,'$.protocolVersion'))='haida-test-v1' ORDER BY created_time LIMIT 1;")
            env = dict(os.environ,SKYTWIN_UI_ADMIN_TOKEN=token,SKYTWIN_UI_VIEWER_TOKEN=viewer_token,SKYTWIN_PATROL_RUN=run_id,SKYTWIN_PATROL_LEGACY_RUN=legacy)
            subprocess.run(['node',str(ROOT/'ruoyi/scripts/verify-patrol-ui.mjs')],env=env,cwd=ROOT,check=True)
        REPORT['passed'] = True
    finally:
        if viewer_id is not None:
            h.api(BASE,'/system/user/'+str(viewer_id),'DELETE',token=token)
        if viewer_token:
            h.api(BASE,'/logout','POST',token=viewer_token)
        h.api(BASE,'/logout','POST',token=token)
        destination = ROOT/'docs/verification/patrol-api.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
