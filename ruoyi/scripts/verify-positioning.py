"""Real local Java/MySQL acceptance. Only uniquely marked fixtures are mutated/removed.
Optional browser uses real APIs, isolated cookies and no user browser profile.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import time
import urllib.request
from urllib.parse import urlencode
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('position_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
helpers = listing.helpers
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
PREFIX = 'ps_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


def check(name, ok):
    assert ok, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def sql_ids(values):
    return ','.join(quote(x) for x in values) or "''"


def iso(offset=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart', action='store_true')
    parser.add_argument('--ui', action='store_true')
    args = parser.parse_args()
    base = 'http://127.0.0.1:5173/java-api'
    admin = None
    aircraft, stations, tasks, plans, users, tokens = [], [], [], [], [], []
    device = PREFIX + '_terminal'
    trigger = 'verify_' + PREFIX
    path = '/sky/positioning/devices/' + device

    def req(url, body=None, method=None, expected=200, token=None):
        _, result = api(base, url, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert result.get('code') == expected, (url, result.get('code'), result.get('msg'))
        return result.get('data')

    def mode(enabled):
        return req(path + '/mode', {'enabled': enabled, 'reason': PREFIX})

    def current():
        return next(x for x in req('/sky/positioning/devices') if x['id'] == device)

    def sample(seq, **patch):
        return dict({'sessionId': current()['sessionId'], 'sequence': seq, 'sampledAt': iso(),
            'longitude': 120.19, 'latitude': 30.215, 'altitude': 240, 'fixValid': True}, **patch)

    def ingest(body, expected=200):
        return req(path + '/samples', body, expected=expected)

    def history(after=0, limit=1000, accepted=True, **patch):
        params = dict({'from': iso(-3600), 'to': iso(3600), 'after': after, 'limit': limit,
            'acceptedOnly': str(accepted).lower()}, **patch)
        return req(path + '/samples?' + urlencode(params))

    def action(task, name, expected=200):
        return req('/sky/tasks/' + task + '/' + name, {'aircraftId': aircraft[0], 'reason': PREFIX}, expected=expected)

    def plan(task):
        p = req('/sky/dispatch/plans', {'tasks': [{'taskId': task, 'priority': 1}], 'aircraftIds': [aircraft[0]]})
        plans.append(p['id'])
        return p

    def viewer():
        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(x['roleId'] for x in roles['rows'] if x['roleKey'] == 'sky_viewer')
        name, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'Az!3'
        req('/system/user', {'userName': name, 'nickName': name, 'password': password, 'deptId': 100,
            'status': '0', 'sex': '0', 'roleIds': [role], 'postIds': []})
        _, found = api(base, '/system/user/list?userName=' + name, token=admin)
        users.append(next(x['userId'] for x in found['rows'] if x['userName'] == name))
        value = listing.login_as(base, name, password)
        tokens.append(value)
        return value

    try:
        check('only dedicated MySQL 3307 used', mysql('SELECT @@port;') == '3307')
        _, denied = api(base, '/sky/positioning/devices')
        check('anonymous positioning read rejected', denied.get('code') == 401)
        admin = helpers.login(base)
        tokens.append(admin)
        baseline = mysql("SELECT id,status,COALESCE(aircraft_id,'') FROM st_task ORDER BY id;")
        baseline_aircraft = mysql('SELECT id,status,longitude,latitude,altitude,battery FROM st_aircraft ORDER BY id;')
        a_input = {'name': PREFIX + '_aircraft', 'type': 'cargo', 'model': 'Positioning-test',
            'longitude': 120.19, 'latitude': 30.215, 'battery': 100, 'payloadCapacity': 20, 'seats': 0}
        aircraft.append(req('/sky/aircraft', a_input))
        for i in range(2):
            stations.append(req('/sky/stations', {'name': PREFIX + '_s' + str(i), 'type': 'logistics',
                'longitude': 120.19 + i * .003, 'latitude': 30.215, 'status': 'enabled'}))
        for i in range(2):
            tasks.append(req('/sky/tasks', {'title': PREFIX + '_task' + str(i), 'type': 'environment',
                'startStationId': stations[0], 'endStationId': stations[1], 'payload': 1, 'passengers': 0,
                'speed': 10, 'cruiseAltitude': 60, 'reason': PREFIX}))
        req('/sky/positioning/devices', {'id': device, 'name': PREFIX, 'aircraftId': aircraft[0]})
        req('/sky/positioning/devices', {'id': device + 'x', 'name': PREFIX, 'aircraftId': aircraft[0]}, expected=409)
        check('one immutable binding per aircraft', len([x for x in req('/sky/positioning/devices') if x['aircraftId'] == aircraft[0]]) == 1)
        action(tasks[0], 'assign')
        req(path + '/mode', {'enabled': True, 'reason': PREFIX}, expected=409)
        check('assigned aircraft cannot enable external positioning', not current()['enabled'])
        action(tasks[0], 'cancel')
        stale_plan = plan(tasks[1])
        check('disabled terminal permits normal dispatch preview', stale_plan['result']['optimized']['assignedCount'] == 1)
        enabled = mode(True)
        check('enable opens unique session with no fabricated latest fix', enabled['enabled'] and enabled['connectionState'] == 'waiting' and enabled['sampledAt'] is None)
        check('enable is idempotent without discarding session', mode(True)['sessionId'] == enabled['sessionId'])
        ingest(sample(0, sessionId='invalid-session'), expected=409)
        action(tasks[1], 'assign', expected=409)
        req('/sky/aircraft/' + aircraft[0], a_input, method='PUT', expected=409)
        req('/sky/aircraft/' + aircraft[0], method='DELETE', expected=409)
        check('active terminal blocks manual dispatch, editing and removal', mysql('SELECT status FROM st_task WHERE id=' + quote(tasks[1]) + ';') == 'created')
        excluded = plan(tasks[1])
        check('active terminal excluded from fleet optimization', excluded['result']['optimized']['assignedCount'] == 0)
        req('/sky/dispatch/plans/' + stale_plan['id'] + '/confirm', {'reason': PREFIX}, expected=409)
        check('old plan cannot bypass changed positioning mode', mysql('SELECT status FROM st_dispatch_plan WHERE id=' + quote(stale_plan['id']) + ';') == 'proposed')
        before = mysql('SELECT status,longitude,latitude,altitude FROM st_aircraft WHERE id=' + quote(aircraft[0]) + ';')
        first_body = sample(0, sampledAt=iso(-4), source='real_beidou')
        first = ingest(first_body)
        check('valid fix persisted with server enforced simulation source and height reference', first['accepted'] and first['source'] == 'simulated_terminal' and first['altitudeReference'] == 'relative_to_takeoff' and first['sampledAt'].endswith('Z'))
        check('device and sample link committed together', current()['latestSampleId'] == first['id'])
        duplicate = ingest(first_body)
        check('identical retry returns same immutable receipt', duplicate['duplicate'] and duplicate['id'] == first['id'] and mysql('SELECT COUNT(*) FROM st_position_sample WHERE device_id=' + quote(device) + ';') == '1')
        ingest(dict(first_body, altitude=241), expected=409)
        check('duplicate sequence with different content rejected', current()['latestSampleId'] == first['id'])
        snap = req('/sky/snapshot')
        displayed = next(x for x in snap['aircraft'] if x['id'] == aircraft[0])
        check('snapshot overlays accepted fix without overwriting task simulator state', displayed['altitude'] == 240 and displayed['positionSource'] == 'simulated_terminal' and displayed['positionDeviceId'] == device and mysql('SELECT status,longitude,latitude,altitude FROM st_aircraft WHERE id=' + quote(aircraft[0]) + ';') == before)
        request = urllib.request.Request(base + '/sky/stream', headers={'Authorization': 'Bearer ' + admin, 'Accept': 'text/event-stream'})
        with urllib.request.urlopen(request, timeout=15) as stream:
            streamed = None
            for line in stream:
                if line.startswith(b'data:'):
                    streamed = json.loads(line[5:]); break
        check('real SSE carries terminal positioning to digital twin', next(x for x in streamed['aircraft'] if x['id'] == aircraft[0])['positionSampledAt'] == first['sampledAt'])
        for i, (patch, verdict) in enumerate([
            ({'fixValid': False}, 'no_fix'), ({'sampledAt': iso(-60)}, 'stale_timestamp'),
            ({'sampledAt': iso(60)}, 'future_timestamp'), ({'longitude': 120.3}, 'position_jump'),
            ({'sampledAt': iso(-10)}, 'out_of_order_timestamp'),
        ], start=1):
            result = ingest(sample(i, **patch))
            check(verdict + ' retained as rejection without moving latest fix', not result['accepted'] and result['verdict'] == verdict and current()['latestSampleId'] == first['id'])
        result = ingest(sample(0, sampledAt=iso(), longitude=120.191), expected=409)
        # Use an unseen but lower sequence for the recorded out-of-order case.
        ingest(sample(10, fixValid=False))
        result = ingest(sample(8))
        check('unseen lower sequence rejected and retained', not result['accepted'] and result['verdict'] == 'out_of_order_sequence')
        for patch in [{'longitude': 181}, {'latitude': -91}, {'altitude': 10001}, {'sequence': -1}, {'sampledAt': '2026-10-19T00:00:00'}]:
            _, result = api(base, path + '/samples', 'POST', sample(11, **patch), admin)
            check('invalid contract rejected: ' + next(iter(patch)), result.get('code') != 200)
        # An identical pair racing must insert one sample, not two.
        concurrent = sample(11)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: ingest(concurrent), [0, 1]))
        check('parallel identical reports are idempotent under row lock', results[0]['id'] == results[1]['id'] and sum(bool(x['duplicate']) for x in results) == 1)
        good = next(x for x in results if x['accepted'])
        rejected_count = int(mysql('SELECT COUNT(*) FROM st_position_sample WHERE device_id=' + quote(device) + ' AND accepted=0;'))
        all_points = history(accepted=False)['rows']
        accepted_points = history()['rows']
        check('history contains only accepted samples by default', len(all_points) == rejected_count + len(accepted_points) and all(x['accepted'] for x in accepted_points))
        first_page = history(limit=1)
        next_page = history(after=first_page['nextCursor'], limit=1)
        check('cursor pagination is explicit and non-overlapping', first_page['hasMore'] and first_page['rows'][0]['id'] != next_page['rows'][0]['id'])
        check('end bound excludes exact sampled timestamp', not history(to=first['sampledAt'])['rows'])
        for patch in [{'limit': 1001}, {'after': -1}, {'from': iso(10), 'to': iso(-10)}, {'from': iso(-8*86400)}]:
            params = dict({'from': iso(-3600), 'to': iso(3600)}, **patch)
            _, result = api(base, path + '/samples?' + urlencode(params), token=admin)
            check('invalid query rejected: ' + next(iter(patch)), result.get('code') != 200)
        check('raw recent receipts include rejected sample evidence', any(not x['accepted'] for x in req(path + '/recent')))
        check('position samples cannot complete business tasks or create task tracks', mysql('SELECT status FROM st_task WHERE id=' + quote(tasks[1]) + ';') == 'created' and mysql('SELECT COUNT(*) FROM st_track WHERE aircraft_id=' + quote(aircraft[0]) + ';') == '0')
        viewer_token = viewer()
        req('/sky/positioning/devices', token=viewer_token)
        req(path + '/recent', token=viewer_token)
        for url, body in [('/sky/positioning/devices', {'id': device + 'v', 'name': PREFIX, 'aircraftId': aircraft[0]}), (path + '/mode', {'enabled': False, 'reason': PREFIX}), (path + '/samples', sample(12))]:
            req(url, body, token=viewer_token, expected=403)
        check('viewer can read but cannot bind, enable or report fixes', True)
        # Force failure after insert, while advancing latest pointer; transaction must undo both.
        previous = current()
        mysql(f"""DELIMITER //
            CREATE TRIGGER {trigger} BEFORE UPDATE ON st_position_device FOR EACH ROW
            BEGIN IF NEW.id={quote(device)} AND NEW.last_sequence=9999
            THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Scoped positioning rollback test'; END IF; END//
            DELIMITER ;
        """)
        _, failed = api(base, path + '/samples', 'POST', sample(9999), admin)
        check('late latest-pointer failure rolls sample insert and device update back', failed.get('code') != 200 and current()['lastSequence'] == previous['lastSequence'] and current()['latestSampleId'] == previous['latestSampleId'] and mysql('SELECT COUNT(*) FROM st_position_sample WHERE device_id=' + quote(device) + ' AND sequence_no=9999;') == '0')
        mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
        old_session = current()['sessionId']
        mode(False)
        disabled = next(x for x in req('/sky/snapshot')['aircraft'] if x['id'] == aircraft[0])
        check('disable restores original simulator position and keeps history', disabled['altitude'] == 0 and 'positionSource' not in disabled and len(history()['rows']) == len(accepted_points))
        ingest(dict(sample(12), sessionId=old_session), expected=409)
        renewed = mode(True)
        check('reenable rotates session and starts with no latest point', renewed['sessionId'] != old_session and renewed['latestSampleId'] is None)
        ingest(dict(sample(0), sessionId=old_session), expected=409)
        check('old delayed producer cannot write into new session', mysql('SELECT COUNT(*) FROM st_position_sample WHERE device_id=' + quote(device) + ' AND session_id=' + quote(renewed['sessionId']) + ';') == '0')
        ingest(sample(0, sampledAt=iso(-29)))
        check('accepted delayed fix is visibly stale, not online', current()['connectionState'] == 'stale')
        time.sleep(2)
        check('missing valid fixes becomes offline after 30 seconds', current()['connectionState'] == 'offline')
        if args.restart:
            saved = req(path + '/recent')
            for operation in ['stop', 'start']:
                with (ROOT / 'logs' / ('positioning-restart-' + operation + '.log')).open('w', encoding='utf-8') as output:
                    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts' / (operation + '.ps1')), '-Service', 'backend'], stdout=output, stderr=subprocess.STDOUT, timeout=110)
                assert result.returncode == 0, 'Project Java restart failed'
            check('Java restart preserves session and accepted/rejected receipts', current()['sessionId'] == renewed['sessionId'] and req(path + '/recent') == saved)
        mode(False)
        # Competing enable and assign serialize on the same aircraft lock.
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls = [pool.submit(api, base, path + '/mode', 'POST', {'enabled': True, 'reason': PREFIX}, admin), pool.submit(api, base, '/sky/tasks/' + tasks[1] + '/assign', 'POST', {'aircraftId': aircraft[0], 'reason': PREFIX}, admin)]
            codes = [x.result()[1]['code'] for x in calls]
        check('enable-versus-assign race has exactly one winner', sorted(codes) == [200, 409])
        if mysql('SELECT status FROM st_task WHERE id=' + quote(tasks[1]) + ';') == 'assigned': action(tasks[1], 'cancel')
        mode(False)
        if args.ui:
            ui_aircraft = req('/sky/aircraft', dict(a_input, name=PREFIX + '_ui_aircraft'))
            aircraft.append(ui_aircraft)
            environment = dict(os.environ, SKYTWIN_UI_PREFIX=PREFIX, SKYTWIN_UI_AIRCRAFT=ui_aircraft, SKYTWIN_UI_ADMIN_TOKEN=admin, SKYTWIN_UI_VIEWER_TOKEN=viewer_token)
            run = subprocess.run([helpers.RUNTIME['NodeExecutable'], str(ROOT / 'scripts/verify-positioning-ui.mjs')], cwd=ROOT.parent, env=environment, timeout=150)
            check('real browser workflow passes', run.returncode == 0)
        check('original user task states preserved', mysql("SELECT id,status,COALESCE(aircraft_id,'') FROM st_task WHERE id NOT IN (" + sql_ids(tasks) + ') ORDER BY id;') == baseline)
        check('original user aircraft states and coordinates preserved', mysql('SELECT id,status,longitude,latitude,altitude,battery FROM st_aircraft WHERE id NOT IN (' + sql_ids(aircraft) + ') ORDER BY id;') == baseline_aircraft)
        REPORT['passed'] = True
    except Exception as error:
        REPORT['error'] = str(error)
        raise
    finally:
        try:
            mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
            # Recover fixtures by exact unique prefix if an HTTP response was interrupted.
            own_aircraft = mysql('SELECT id FROM st_aircraft WHERE LEFT(name,' + str(len(PREFIX)) + ')=' + quote(PREFIX) + ';').splitlines()
            own_devices = mysql('SELECT id FROM st_position_device WHERE aircraft_id IN (' + sql_ids(own_aircraft) + ');').splitlines()
            check_ids = mysql('SELECT id FROM st_airspace_check WHERE task_id IN (' + sql_ids(tasks) + ');').splitlines()
            entities = own_aircraft + own_devices + stations + tasks + plans + check_ids
            mysql(f"""START TRANSACTION;
                SELECT id FROM st_task WHERE id IN ({sql_ids(tasks)}) ORDER BY id FOR UPDATE;
                DELETE FROM st_position_sample WHERE device_id IN ({sql_ids(own_devices)});
                DELETE FROM st_position_device WHERE id IN ({sql_ids(own_devices)});
                DELETE FROM st_audit WHERE entity_id IN ({sql_ids(entities)});
                DELETE FROM st_traffic_check WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_airspace_check WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_track WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_event WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_report WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_dispatch_plan WHERE id IN ({sql_ids(plans)});
                DELETE FROM st_task WHERE id IN ({sql_ids(tasks)});
                DELETE FROM st_aircraft WHERE id IN ({sql_ids(own_aircraft)});
                DELETE FROM st_station WHERE id IN ({sql_ids(stations)});
                COMMIT;
            """)
            for user in users:
                if admin: req('/system/user/' + str(user), method='DELETE')
            REPORT['cleanup'] = {}
            for label, table, key, values in [('devices','st_position_device','id',own_devices), ('samples','st_position_sample','device_id',own_devices), ('aircraft','st_aircraft','id',own_aircraft), ('stations','st_station','id',stations), ('tasks','st_task','id',tasks), ('plans','st_dispatch_plan','id',plans), ('audits','st_audit','entity_id',entities), ('airspaceChecks','st_airspace_check','id',check_ids)]:
                REPORT['cleanup'][label] = int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({sql_ids(values)});'))
            REPORT['cleanup']['triggers'] = int(mysql("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME=" + quote(trigger) + ';'))
            REPORT['cleanup']['activeUsers'] = int(mysql('SELECT COUNT(*) FROM sys_user WHERE user_id IN (' + (','.join(map(str, users)) or '-1') + ") AND del_flag='0';"))
            if any(REPORT['cleanup'].values()): REPORT['passed'] = False
            for token in reversed(tokens): api(base, '/logout', 'POST', token=token)
        finally:
            (ROOT / 'logs/positioning-verification.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Report: ruoyi/logs/positioning-verification.json', flush=True)
    assert REPORT['passed'], 'Positioning verification failed'


if __name__ == '__main__':
    main()
