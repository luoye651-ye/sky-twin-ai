"""Real Java/MySQL evidence workflow acceptance. Synthetic PNGs are labelled simulation.
All fixtures use one unique prefix; no business endpoint is mocked.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import struct
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import zlib
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('environment_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
h = listing.helpers
api, mysql, quote = h.api, h.mysql, h.sql_value
PREFIX = 'ev_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


def png(color):
    # Entirely synthetic acceptance image, not environmental inference evidence.
    width, height = 1600, 1000
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    raw = b''.join(b'\0' + bytes(color) * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def check(name, ok):
    assert ok, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def ids(values):
    return ','.join(map(quote, values)) or "''"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart', action='store_true')
    parser.add_argument('--ui', action='store_true')
    args = parser.parse_args()
    base = 'http://127.0.0.1:5173/java-api'
    admin = None
    tokens, users, aircraft, stations, tasks, discoveries, plans, zones = [], [], [], [], [], [], [], []
    trigger = 'verify_' + PREFIX
    before_image, after_image = png((30, 120, 170)), png((40, 160, 120))

    def req(path, body=None, expected=200, method=None, token=None):
        _, result = api(base, path, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert result.get('code') == expected, (path, result.get('code'), result.get('msg'))
        return result.get('data')

    def upload(path, body, image=before_image, expected=200, token=None):
        boundary = 'env_' + uuid.uuid4().hex
        payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="input"\r\nContent-Type: application/json\r\n\r\n'.encode()
            + json.dumps(body).encode() + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="simulation-fixture.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
            + image + f'\r\n--{boundary}--\r\n'.encode())
        request = urllib.request.Request(base + path, data=payload, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary, 'Authorization': 'Bearer ' + (token or admin)}, method='POST')
        try: response = urllib.request.urlopen(request, timeout=25)
        except urllib.error.HTTPError as e: response = e
        with response: result = json.loads(response.read().decode())
        assert result.get('code') == expected, (path, result.get('code'), result.get('msg'))
        return result.get('data')

    def image_get(discovery, after=False, token=None):
        request = urllib.request.Request(base + '/sky/environment/discoveries/' + discovery + '/image?after=' + str(after).lower(), headers={'Authorization': 'Bearer ' + (token or admin)})
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read(), response.headers

    def body(task_id, suffix):
        return {'requestId': str(uuid.uuid4()), 'taskId': task_id, 'title': PREFIX + '_' + suffix, 'longitude': 120.19, 'latitude': 30.216,
            'observedAt': datetime.now(timezone.utc).isoformat(), 'imageSource': 'simulation', 'annotations': [{'x': .2, 'y': .2, 'width': .5, 'height': .5, 'note': 'Synthetic manual annotation, not AI'}]}

    def detail(discovery):
        return req('/sky/environment/discoveries/' + discovery)

    def review(discovery, decision='confirm', expected=200):
        return req('/sky/environment/discoveries/' + discovery + '/review', {'decision': decision, 'severity': 'high', 'reason': PREFIX}, expected)

    def response(discovery, expected=200, reason=PREFIX):
        return req('/sky/environment/discoveries/' + discovery + '/responses', {'startStationId': stations[0], 'endStationId': stations[1], 'reason': reason}, expected)

    def close(discovery, expected=200, image=after_image):
        return upload('/sky/environment/discoveries/' + discovery + '/close', {'resolution': PREFIX + '：人工提交仿真清理结果，不代表真实作业'}, image, expected)

    def action(task, command, resource=None, expected=200):
        return req('/sky/tasks/' + task + '/' + command, {'aircraftId': resource, 'reason': PREFIX}, expected)

    def wait(predicate, seconds, description):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate(): return
            time.sleep(.5)
        raise AssertionError('Timeout: ' + description)

    def task_state(task):
        return mysql('SELECT status FROM st_task WHERE id=' + quote(task) + ';')

    def viewer():
        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(r['roleId'] for r in roles['rows'] if r['roleKey'] == 'sky_viewer')
        name, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'Az!3'
        req('/system/user', {'userName': name, 'nickName': name, 'password': password, 'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [role], 'postIds': []})
        _, found = api(base, '/system/user/list?userName=' + name, token=admin)
        users.append(next(r['userId'] for r in found['rows'] if r['userName'] == name))
        token = listing.login_as(base, name, password); tokens.append(token)
        return token

    try:
        check('dedicated MySQL 3307 only', mysql('SELECT @@port;') == '3307')
        _, denied = api(base, '/sky/environment/discoveries')
        check('anonymous cannot access environmental evidence', denied.get('code') == 401)
        admin = h.login(base); tokens.append(admin)
        baseline = mysql("SELECT id,status,COALESCE(aircraft_id,''),duration_seconds FROM st_task ORDER BY id;")
        for i, lon in enumerate([120.187, 120.193]):
            stations.append(req('/sky/stations', {'name': PREFIX + '_station_' + str(i), 'type': 'takeoff', 'longitude': lon, 'latitude': 30.215, 'status': 'enabled'}))
        resource = req('/sky/aircraft', {'name': PREFIX + '_scout', 'type': 'drone', 'model': 'environment-test', 'longitude': 120.187, 'latitude': 30.215, 'battery': 100, 'payloadCapacity': 2, 'seats': 0}); aircraft.append(resource)
        source = req('/sky/tasks', {'title': PREFIX + '_patrol', 'type': 'environment', 'startStationId': stations[0], 'endStationId': stations[1], 'payload': 0, 'passengers': 0, 'speed': 10, 'cruiseAltitude': 80, 'reason': PREFIX}); tasks.append(source)
        upload('/sky/environment/discoveries', body(source, 'not_executed'), expected=409)
        check('unexecuted patrol cannot submit evidence', mysql('SELECT COUNT(*) FROM st_env_discovery WHERE task_id=' + quote(source) + ';') == '0')
        action(source, 'assign', resource); action(source, 'start')
        input_body = body(source, 'main')
        for suffix, image in [('fake', b'<svg>not PNG</svg>'), ('empty', b''), ('oversize', b'x' * (2 * 1024 * 1024 + 1))]:
            upload('/sky/environment/discoveries', body(source, suffix), image, 400)
        check('invalid image content empty image and byte limits enforced server-side', True)
        bad_box = body(source, 'outside'); bad_box['annotations'][0]['x'] = .9
        upload('/sky/environment/discoveries', bad_box, expected=400)
        bad_time = body(source, 'future'); bad_time['observedAt'] = '2099-01-01T00:00:00Z'
        upload('/sky/environment/discoveries', bad_time, expected=400)
        check('box geometry and capture timestamp validated', True)
        fault_input = body(source, 'create_fault')
        mysql(f"""DELIMITER $$
CREATE TRIGGER {trigger} BEFORE INSERT ON st_audit FOR EACH ROW BEGIN
IF NEW.action='environment.create' AND EXISTS(SELECT 1 FROM st_env_discovery d WHERE d.id=NEW.entity_id AND d.title={quote(fault_input['title'])})
THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='environment upload verification fault'; END IF; END$$
DELIMITER ;
""")
        upload('/sky/environment/discoveries', fault_input, expected=500)
        check('late upload audit failure rolls back image and discovery together', mysql('SELECT COUNT(*) FROM st_env_discovery WHERE request_id=' + quote(fault_input['requestId']) + ';') == '0')
        mysql('DROP TRIGGER ' + trigger + ';')
        main_discovery = upload('/sky/environment/discoveries', input_body)['id']; discoveries.append(main_discovery)
        saved = detail(main_discovery)
        check('upload persists provenance human annotation and source task without AI confidence', saved['status'] == 'pending_review' and saved['analysisSource'] == 'manual_annotation' and 'confidence' not in saved and saved['taskId'] == source)
        raw, headers = image_get(main_discovery)
        check('authorized image endpoint preserves exact evidence SHA256 and nosniff', raw == before_image and hashlib.sha256(raw).hexdigest() == saved['imageSha256'] and headers['X-Content-Type-Options'] == 'nosniff' and 'no-store' in headers['Cache-Control'])
        retry = upload('/sky/environment/discoveries', input_body)
        check('identical upload retry is idempotent', retry['id'] == main_discovery and mysql('SELECT COUNT(*) FROM st_env_discovery WHERE request_id=' + quote(input_body['requestId']) + ';') == '1')
        changed = dict(input_body, title=PREFIX + '_changed')
        upload('/sky/environment/discoveries', changed, expected=409)
        check('submission id cannot be reused for changed content', detail(main_discovery)['title'] == input_body['title'])
        concurrent = body(source, 'concurrent_upload')
        with ThreadPoolExecutor(2) as pool:
            copies = list(pool.map(lambda _: upload('/sky/environment/discoveries', concurrent), range(2)))
        discoveries.append(copies[0]['id'])
        check('parallel identical uploads produce one discovery', copies[0]['id'] == copies[1]['id'])
        rejected = review(copies[0]['id'], 'reject')
        response(copies[0]['id'], 409)
        check('rejection generates no event or response task', rejected['status'] == 'rejected' and rejected['eventId'] is None)
        response(main_discovery, 409); close(main_discovery, 409)
        check('unreviewed discovery cannot dispatch or close', not detail(main_discovery)['responses'])
        read_only = viewer()
        req('/sky/environment/discoveries', token=read_only); req('/sky/environment/discoveries/' + main_discovery, token=read_only)
        viewer_image, _ = image_get(main_discovery, token=read_only)
        upload('/sky/environment/discoveries', body(source, 'viewer'), expected=403, token=read_only)
        req('/sky/environment/discoveries/' + main_discovery + '/review', {'decision': 'confirm', 'severity': 'high', 'reason': PREFIX}, 403, token=read_only)
        req('/sky/environment/discoveries/' + main_discovery + '/responses', {'startStationId': stations[0], 'endStationId': stations[1], 'reason': PREFIX}, 403, token=read_only)
        upload('/sky/environment/discoveries/' + main_discovery + '/close', {'resolution': PREFIX}, after_image, 403, token=read_only)
        check('viewer can inspect evidence but cannot submit or review', viewer_image == before_image)
        mysql(f"""DELIMITER $$
CREATE TRIGGER {trigger} BEFORE INSERT ON st_audit FOR EACH ROW BEGIN
IF NEW.entity_id={quote(main_discovery)} AND NEW.action='environment.review'
THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='environment review verification fault'; END IF; END$$
DELIMITER ;
""")
        review(main_discovery, expected=500)
        check('late review audit failure cannot leave orphan event or reviewed status', detail(main_discovery)['status'] == 'pending_review' and detail(main_discovery)['eventId'] is None and mysql('SELECT COUNT(*) FROM st_event WHERE title=' + quote('河道漂浮物：' + input_body['title']) + ';') == '0')
        mysql('DROP TRIGGER ' + trigger + ';')
        with ThreadPoolExecutor(2) as pool:
            decisions = list(pool.map(lambda _: api(base, '/sky/environment/discoveries/' + main_discovery + '/review', 'POST', {'decision': 'confirm', 'severity': 'high', 'reason': PREFIX}, admin)[1], range(2)))
        check('parallel review creates exactly one event and audit', sorted(r.get('code') for r in decisions) == [200, 409] and mysql("SELECT COUNT(*) FROM st_audit WHERE entity_id=" + quote(main_discovery) + " AND action='environment.review';") == '1')
        event = detail(main_discovery)['eventId']
        req('/sky/events/' + str(event) + '/resolve', {'reason': PREFIX}, 409)
        check('generic event resolution cannot bypass environmental closure', mysql('SELECT status FROM st_event WHERE id=' + str(event) + ';') == 'open')
        snapshot = req('/sky/snapshot')
        linked_event = next(e for e in snapshot['events'] if e['id'] == event)
        check('snapshot exposes linked geographic incident without duplicating event state', linked_event['discoveryId'] == main_discovery and linked_event['longitude'] == input_body['longitude'])
        zone_body = {'name': PREFIX + '_barrier', 'type': 'no_fly', 'west': 120.1895, 'east': 120.1905, 'south': 30.2155, 'north': 30.2165, 'minAltitude': 0, 'maxAltitude': 120, 'startsAt': None, 'endsAt': None, 'enabled': True, 'reason': PREFIX}
        zones.append(req('/sky/airspace/zones', zone_body))
        response(main_discovery, 409)
        check('unsafe incident route cannot leave a partially created response task', detail(main_discovery)['status'] == 'confirmed' and not detail(main_discovery)['responses'] and mysql('SELECT COUNT(*) FROM st_task WHERE title=' + quote('环境侦察：' + input_body['title']) + ';') == '0')
        req('/sky/airspace/zones/' + zones[-1], dict(zone_body, enabled=False), method='PUT')
        mysql(f"""DELIMITER $$
CREATE TRIGGER {trigger} BEFORE INSERT ON st_audit FOR EACH ROW BEGIN
IF NEW.entity_id={quote(main_discovery)} AND NEW.action='environment.respond' AND NEW.reason={quote(PREFIX + '_fault')}
THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='environment response verification fault'; END IF; END$$
DELIMITER ;
""")
        response(main_discovery, 500, PREFIX + '_fault')
        check('late response audit failure rolls back task route association and incident state', not detail(main_discovery)['responses'] and detail(main_discovery)['status'] == 'confirmed' and mysql('SELECT COUNT(*) FROM st_task WHERE title=' + quote('环境侦察：' + input_body['title']) + ';') == '0')
        mysql('DROP TRIGGER ' + trigger + ';')
        with ThreadPoolExecutor(2) as pool:
            created = list(pool.map(lambda _: api(base, '/sky/environment/discoveries/' + main_discovery + '/responses', 'POST', {'startStationId': stations[0], 'endStationId': stations[1], 'reason': PREFIX}, admin)[1], range(2)))
        check('parallel response creation cannot duplicate an active mission', sorted(r.get('code') for r in created) == [200, 409] and len(detail(main_discovery)['responses']) == 1)
        first_response = detail(main_discovery)['responses'][0]['taskId']; tasks.append(first_response)
        route = req('/sky/tasks/' + first_response + '/route')['plan']
        check('response has frozen aerial event waypoint and severity priority floor', route['revision'] == 2 and any(abs(p['longitude'] - input_body['longitude']) < 1e-8 and abs(p['latitude'] - input_body['latitude']) < 1e-8 and p['altitude'] == 80 for p in route['points']) and detail(main_discovery)['responses'][0]['priority'] == 3)
        req('/sky/tasks/' + first_response + '/route', {'expectedRevision': 2, 'waypoints': [], 'reason': PREFIX}, 409, method='PUT')
        check('generic route editor cannot remove required incident visit', req('/sky/tasks/' + first_response + '/route')['plan']['revision'] == 2)
        action(first_response, 'cancel'); close(main_discovery, 409)
        check('cancelled response does not qualify as successful treatment', detail(main_discovery)['afterSha256'] is None)
        response(main_discovery)
        current = detail(main_discovery)['responses'][-1]['taskId']; tasks.append(current)
        check('retry keeps cancelled attempt history', len(detail(main_discovery)['responses']) == 2 and detail(main_discovery)['responses'][0]['taskStatus'] == 'cancelled')
        # Scoped negative fixture: forged completion without telemetry MUST NOT be enough.
        mysql('UPDATE st_task SET status=\'completed\' WHERE id=' + quote(current) + ';')
        close(main_discovery, 409)
        mysql('UPDATE st_task SET status=\'created\' WHERE id=' + quote(current) + ';')
        check('completion flag without an actual aerial visit is insufficient to close', detail(main_discovery)['status'] == 'in_response')
        wait(lambda: task_state(source) == 'completed', 35, 'source patrol completion')
        dispatch = req('/sky/dispatch/plans', {'tasks': [{'taskId': current, 'priority': 1}], 'aircraftIds': [resource]}); plans.append(dispatch['id'])
        check('optimizer enforces reviewed incident priority even when caller asks for lower priority', dispatch['result']['assignments'][0]['priority'] == 3)
        req('/sky/dispatch/plans/' + dispatch['id'] + '/confirm', {'reason': PREFIX})
        action(current, 'start'); close(main_discovery, 409)
        check('executing reconnaissance cannot be prematurely closed', detail(main_discovery)['status'] == 'in_response')
        if args.restart:
            for operation in ['stop', 'start']:
                with (ROOT / 'logs' / ('environment-restart-' + operation + '.log')).open('w', encoding='utf-8') as output:
                    run = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts' / (operation + '.ps1')), '-Service', 'backend'], stdout=output, stderr=subprocess.STDOUT, timeout=110)
                assert run.returncode == 0
            check('restart preserves evidence hashes event and active response linkage', detail(main_discovery)['imageSha256'] == saved['imageSha256'] and detail(main_discovery)['eventId'] == event and detail(main_discovery)['responses'][-1]['taskId'] == current)
        print('INFO: waiting for real Java reconnaissance completion', flush=True)
        wait(lambda: task_state(current) == 'completed', 55, 'response completion')
        close(main_discovery, 409, before_image)
        check('closure requires a distinct post-treatment image', detail(main_discovery)['afterSha256'] is None)
        mysql(f"""DELIMITER $$
CREATE TRIGGER {trigger} BEFORE INSERT ON st_env_report FOR EACH ROW BEGIN
IF NEW.discovery_id={quote(main_discovery)} THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='environment report verification fault'; END IF; END$$
DELIMITER ;
""")
        close(main_discovery, 500)
        check('late report failure rolls back closure event after-image and close audit', detail(main_discovery)['status'] == 'in_response' and detail(main_discovery)['afterSha256'] is None and mysql('SELECT status FROM st_event WHERE id=' + str(event) + ';') == 'open' and mysql("SELECT COUNT(*) FROM st_audit WHERE entity_id=" + quote(main_discovery) + " AND action='environment.close';") == '0')
        mysql('DROP TRIGGER ' + trigger + ';')
        with ThreadPoolExecutor(2) as pool:
            # Capture business codes directly, avoiding an assertion in the expected losing request.
            def closing(_):
                try: return close(main_discovery), 200
                except AssertionError as error:
                    assert '409' in str(error), str(error)
                    return None, 409
            closed = list(pool.map(closing, range(2)))
        check('concurrent closure creates one report and resolves event exactly once', sorted(code for _, code in closed) == [200, 409] and mysql('SELECT COUNT(*) FROM st_env_report WHERE discovery_id=' + quote(main_discovery) + ';') == '1')
        final = detail(main_discovery)
        report = req('/sky/environment/reports/' + final['report']['id'])
        after_raw, _ = image_get(main_discovery, True)
        check('archived report freezes actual route tracks provenance reviewers and image hashes', final['status'] == 'closed' and after_raw == after_image and report['snapshot']['status'] == 'closed' and report['snapshot']['latestResponseRoute']['revision'] == 2 and bool(report['snapshot']['latestResponseTracks']) and '非AI识别' in report['content'] and saved['imageSha256'] in report['content'] and hashlib.sha256(after_image).hexdigest() in report['content'])
        close(main_discovery, 409)
        response(main_discovery, 409)
        check('closed evidence and report cannot be overwritten by repeated actions', req('/sky/environment/reports/' + final['report']['id']) == report)
        if args.ui:
            env = dict(os.environ, SKYTWIN_UI_PREFIX=PREFIX, SKYTWIN_UI_SOURCE=source, SKYTWIN_UI_AIRCRAFT=resource, SKYTWIN_UI_STATIONS=json.dumps(stations), SKYTWIN_UI_BEFORE=before_image.hex(), SKYTWIN_UI_AFTER=after_image.hex(), SKYTWIN_UI_ADMIN_TOKEN=admin, SKYTWIN_UI_VIEWER_TOKEN=read_only)
            bundled = pathlib.Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
            if bundled.exists(): env.setdefault('SKYTWIN_PLAYWRIGHT_MODULE', str(bundled))
            run = subprocess.run([h.RUNTIME['NodeExecutable'], str(ROOT / 'scripts/verify-environment-ui.mjs')], cwd=ROOT.parent, env=env, timeout=200)
            check('real browser complete evidence-to-report workflow passes', run.returncode == 0)
        REPORT['reportId'] = final['report']['id']
        check('original user tasks preserve status assignment and duration', mysql("SELECT id,status,COALESCE(aircraft_id,''),duration_seconds FROM st_task WHERE LOCATE(" + quote(PREFIX) + ',title)=0 ORDER BY id;') == baseline)
        REPORT['passed'] = True
    except Exception as error:
        REPORT['error'] = str(error)
        raise
    finally:
        try:
            mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
            tasks[:] = mysql('SELECT id FROM st_task WHERE LOCATE(' + quote(PREFIX) + ',title)>0;').splitlines()
            discoveries[:] = mysql('SELECT id FROM st_env_discovery WHERE LEFT(title,15)=' + quote(PREFIX) + ';').splitlines()
            plans[:] = mysql('SELECT id FROM st_dispatch_plan WHERE LOCATE(' + quote(PREFIX) + ',CAST(result_json AS CHAR))>0;').splitlines()
            checks = mysql('SELECT id FROM st_airspace_check WHERE task_id IN (' + ids(tasks) + ') OR LOCATE(' + quote(PREFIX) + ',task_title)>0;').splitlines()
            entities = tasks + discoveries + aircraft + stations + plans + zones + checks
            mysql(f"""START TRANSACTION;
SELECT tick FROM st_traffic_clock WHERE id=1 FOR UPDATE;
SELECT id FROM st_task WHERE id IN ({ids(tasks)}) ORDER BY id FOR UPDATE;
DELETE FROM st_audit WHERE entity_id IN ({ids(entities)});
DELETE FROM st_env_report WHERE discovery_id IN ({ids(discoveries)});
DELETE FROM st_env_response WHERE discovery_id IN ({ids(discoveries)});
DELETE FROM st_env_discovery WHERE id IN ({ids(discoveries)});
DELETE FROM st_airspace_check WHERE id IN ({ids(checks)});
DELETE FROM st_traffic_check WHERE task_id IN ({ids(tasks)});
DELETE FROM st_dispatch_plan WHERE id IN ({ids(plans)});
DELETE FROM st_track WHERE task_id IN ({ids(tasks)});
DELETE FROM st_report WHERE task_id IN ({ids(tasks)});
DELETE FROM st_event WHERE task_id IN ({ids(tasks)});
DELETE FROM st_task WHERE id IN ({ids(tasks)});
DELETE FROM st_aircraft WHERE id IN ({ids(aircraft)});
DELETE FROM st_station WHERE id IN ({ids(stations)});
DELETE FROM st_airspace_zone WHERE id IN ({ids(zones)});
COMMIT;
""")
            for user in users:
                if admin: req('/system/user/' + str(user), method='DELETE')
            REPORT['cleanup'] = {}
            for name, table, key, values in [('discoveries','st_env_discovery','id',discoveries), ('responses','st_env_response','discovery_id',discoveries), ('reports','st_env_report','discovery_id',discoveries), ('tasks','st_task','id',tasks), ('aircraft','st_aircraft','id',aircraft), ('stations','st_station','id',stations), ('plans','st_dispatch_plan','id',plans), ('zones','st_airspace_zone','id',zones), ('checks','st_airspace_check','id',checks), ('audits','st_audit','entity_id',entities)]:
                REPORT['cleanup'][name] = int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({ids(values)});'))
            REPORT['cleanup']['activeUsers'] = int(mysql('SELECT COUNT(*) FROM sys_user WHERE user_id IN (' + (','.join(map(str, users)) or '-1') + ") AND del_flag='0';"))
            REPORT['cleanup']['triggers'] = int(mysql("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME=" + quote(trigger) + ';'))
            if any(REPORT['cleanup'].values()): REPORT['passed'] = False
            for token in reversed(tokens): api(base, '/logout', 'POST', token=token)
        finally:
            (ROOT / 'logs/environment-verification.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Report: ruoyi/logs/environment-verification.json', flush=True)
    assert REPORT['passed'], 'Environmental workflow verification failed'


if __name__ == '__main__':
    main()
