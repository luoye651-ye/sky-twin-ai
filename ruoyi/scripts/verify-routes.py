"""Real local Java/MySQL route acceptance. All mutations use unique test fixtures."""
import argparse
import importlib.util
import json
import math
import os
import pathlib
import subprocess
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('route_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
helpers = listing.helpers
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
PREFIX = 'rt_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


def check(name, ok):
    assert ok, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def ids(values):
    return ','.join(quote(x) for x in values) or "''"


def same_point(a, b):
    return all(abs(a[key] - b[key]) < 1e-8 for key in ['longitude', 'latitude', 'altitude'])


def same_json(a, b):
    # MySQL binary JSON can round a floating-point last bit (observed 2e-15 seconds).
    # Keys, ordering, strings, revisions and integer durations remain strictly checked.
    if isinstance(a, float) and isinstance(b, (float, int)):
        return math.isclose(a, b, rel_tol=0, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_json(x, y) for x, y in zip(a, b))
    return a == b


def point_at(points, seconds):
    for a, b in zip(points, points[1:]):
        if seconds <= b['offsetSeconds'] + 1e-8:
            f = max(0, min(1, (seconds - a['offsetSeconds']) / (b['offsetSeconds'] - a['offsetSeconds'])))
            return {key: a[key] + (b[key] - a[key]) * f for key in ['longitude', 'latitude', 'altitude']}
    return points[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart', action='store_true')
    parser.add_argument('--ui', action='store_true')
    args = parser.parse_args()
    base = 'http://127.0.0.1:5173/java-api'
    admin = None
    tokens, users, aircraft, stations, tasks, orders, zones, plans = [], [], [], [], [], [], [], []
    trigger = 'verify_' + PREFIX
    via = [{'longitude': 120.19, 'latitude': 30.225}, {'longitude': 120.193, 'latitude': 30.225}]

    def req(path, body=None, expected=200, method=None, token=None):
        _, result = api(base, path, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert result.get('code') == expected, (path, result.get('code'), result.get('msg'))
        return result.get('data')

    def order(suffix):
        value = req('/sky/logistics/orders', {'cargoName': PREFIX + '_' + suffix, 'weight': 1,
            'startStationId': stations[0], 'endStationId': stations[1], 'deadlineMinutes': 30, 'reason': PREFIX})
        orders.append(value)
        detail = req('/sky/logistics/orders/' + value)
        tasks.append(detail['taskId'])
        return value, detail['taskId']

    def route(task):
        return req('/sky/tasks/' + task + '/route')

    def payload(task, points=None, revision=None, reason=None):
        return {'expectedRevision': route(task)['plan']['revision'] if revision is None else revision,
            'waypoints': via if points is None else points, 'reason': reason or PREFIX}

    def preview(task, body=None):
        return req('/sky/tasks/' + task + '/route/preview', body or payload(task))

    def save(task, body=None, expected=200):
        return req('/sky/tasks/' + task + '/route', body or payload(task), expected, 'PUT')

    def assign(task, resource):
        req('/sky/tasks/' + task + '/assign', {'aircraftId': resource, 'reason': PREFIX})

    def plan(task):
        value = req('/sky/dispatch/plans', {'tasks': [{'taskId': task, 'priority': 1}], 'aircraftIds': [aircraft[0]]})
        plans.append(value['id'])
        return value

    def viewer():
        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(x['roleId'] for x in roles['rows'] if x['roleKey'] == 'sky_viewer')
        name, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'Az!3'
        req('/system/user', {'userName': name, 'nickName': name, 'password': password,
            'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [role], 'postIds': []})
        _, found = api(base, '/system/user/list?userName=' + name, token=admin)
        users.append(next(x['userId'] for x in found['rows'] if x['userName'] == name))
        token = listing.login_as(base, name, password)
        tokens.append(token)
        return token

    try:
        check('dedicated MySQL 3307 only', mysql('SELECT @@port;') == '3307')
        _, denied = api(base, '/sky/tasks/missing/route')
        check('anonymous route access rejected', denied.get('code') == 401)
        admin = helpers.login(base)
        tokens.append(admin)
        baseline = mysql("SELECT id,status,COALESCE(aircraft_id,''),duration_seconds FROM st_task ORDER BY id;")
        for i in range(2):
            stations.append(req('/sky/stations', {'name': PREFIX + '_station_' + str(i), 'type': 'logistics', 'longitude': 120.19 + i * .003, 'latitude': 30.215, 'status': 'enabled'}))
            aircraft.append(req('/sky/aircraft', {'name': PREFIX + '_aircraft_' + str(i), 'type': 'cargo', 'model': 'route-test', 'longitude': 120.19, 'latitude': 30.215, 'battery': 100 if i == 0 else 26, 'payloadCapacity': 20, 'seats': 0}))
        first_order, task = order('main')
        original = route(task)['plan']
        check('new task stores frozen initial v1 route', original['revision'] == 1 and len(original['points']) == 4 and len(route(task)['versions']) == 1)
        zone_input = {'name': PREFIX + '_barrier', 'type': 'no_fly', 'west': 120.191, 'east': 120.192, 'south': 30.2147, 'north': 30.2153, 'minAltitude': 0, 'maxAltitude': 120, 'startsAt': None, 'endsAt': None, 'enabled': True, 'reason': PREFIX}
        zones.append(req('/sky/airspace/zones', zone_input))
        blocked = preview(task, payload(task, []))
        check('direct route blocked without draft persistence', not blocked['allowed'] and route(task)['plan']['revision'] == 1)
        save(task, payload(task, []), 409)
        check('unsafe save cannot overwrite original route or task duration', route(task)['plan']['revision'] == 1 and mysql('SELECT duration_seconds FROM st_task WHERE id=' + quote(task) + ';') == str(original['durationSeconds']))
        check('unsafe save evidence survives transaction rollback', any(x['taskId'] == task and x['entry'] == 'route_save' and not x['allowed'] for x in req('/sky/airspace/checks')))
        candidate = preview(task)
        check('manual detour avoids zone and recomputes full distance and duration', candidate['allowed'] and candidate['plan']['distanceMeters'] > original['distanceMeters'] * 5 and candidate['plan']['durationSeconds'] > original['durationSeconds'])
        check('preview has no route or audit writes', len(route(task)['versions']) == 1 and mysql("SELECT COUNT(*) FROM st_audit WHERE entity_id=" + quote(task) + " AND action='route.save';") == '0')
        saved = save(task)
        check('route and task duration commit atomically', saved['plan']['revision'] == 2 and mysql('SELECT duration_seconds FROM st_task WHERE id=' + quote(task) + ';') == str(saved['plan']['durationSeconds']))
        check('old version remains immutable after detour save', req('/sky/tasks/' + task + '/route/versions/1') == original)
        inspected = req('/sky/airspace/validate', {'taskId': task})
        check('launch validator reads full saved waypoint path', inspected['allowed'] and all(same_point(a, b) for a, b in zip(inspected['route'], saved['plan']['points'])) and len(inspected['route']) == 6)
        snapshot = req('/sky/snapshot')
        live = next(x for x in snapshot['tasks'] if x['id'] == task)
        check('snapshot publishes same path revision distance and elapsed time', live['routeRevision'] == 2 and len(live['routePoints']) == 6 and live['elapsedSeconds'] == 0)
        request = urllib.request.Request(base + '/sky/stream', headers={'Authorization': 'Bearer ' + admin, 'Accept': 'text/event-stream'})
        with urllib.request.urlopen(request, timeout=15) as stream:
            for line in stream:
                if line.startswith(b'data:'):
                    check('real SSE carries saved route geometry', next(x for x in json.loads(line[5:])['tasks'] if x['id'] == task)['routeRevision'] == 2)
                    break
        old_plan = plan(task)
        energy = old_plan['result']['assignments'][0]['expectedEnergy']
        check('optimizer scores updated route duration and energy', abs(energy - round(saved['plan']['durationSeconds'] * .08, 2)) < .001)
        longer = [{'longitude': p['longitude'], 'latitude': 30.226} for p in via]
        save(task, payload(task, longer))
        req('/sky/dispatch/plans/' + old_plan['id'] + '/confirm', {'reason': PREFIX}, 409)
        check('route change invalidates old dispatch confirmation', mysql('SELECT status FROM st_task WHERE id=' + quote(task) + ';') == 'created')
        save(task, payload(task, revision=2), 409)
        check('stale editor cannot overwrite newer route revision', route(task)['plan']['revision'] == 3)
        save(task)
        concurrent = [payload(task, via), payload(task, longer)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda body: api(base, '/sky/tasks/' + task + '/route', 'PUT', body, admin)[1]['code'], concurrent))
        check('parallel saves with same revision have one winner', sorted(results) == [200, 409] and route(task)['plan']['revision'] == 5)
        before_plan = route(task)['plan']
        preview(task)
        blocker = dict(zone_input, name=PREFIX + '_late_policy', west=120.189, east=120.194, south=30.224, north=30.227)
        late = req('/sky/airspace/zones', blocker)
        zones.append(late)
        save(task, expected=409)
        check('save rechecks rule changes made after preview', route(task)['plan']['revision'] == before_plan['revision'])
        req('/sky/airspace/zones/' + late, dict(blocker, enabled=False), method='PUT')
        # Invalid topology and DTO shape must not create revisions.
        for name, points in [('duplicate start', [{'longitude': 120.19, 'latitude': 30.215}]), ('overlong route', [{'longitude': 121, 'latitude': 31}]), ('too many points', via * 13), ('invalid coordinate', [{'longitude': 181, 'latitude': 30}])]:
            _, result = api(base, '/sky/tasks/' + task + '/route', 'PUT', payload(task, points), admin)
            check(name + ' rejected without revision change', result.get('code') != 200 and route(task)['plan']['revision'] == before_plan['revision'])
        # Fail only the route.save audit, after revision insert and duration update.
        fault = PREFIX + '_audit_fault'
        mysql(f"""DELIMITER //
            CREATE TRIGGER {trigger} BEFORE INSERT ON st_audit FOR EACH ROW
            BEGIN IF NEW.entity_id={quote(task)} AND NEW.action='route.save' AND NEW.reason={quote(fault)}
            THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Scoped route audit failure'; END IF; END//
            DELIMITER ;
        """)
        _, failed = api(base, '/sky/tasks/' + task + '/route', 'PUT', payload(task, reason=fault), admin)
        check('late audit failure rolls revision and duration back together', failed.get('code') != 200 and route(task)['plan'] == before_plan and mysql('SELECT duration_seconds FROM st_task WHERE id=' + quote(task) + ';') == str(before_plan['durationSeconds']))
        mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
        _, low_task = order('battery')
        assign(low_task, aircraft[1])
        very_long = [{'longitude': 120.19, 'latitude': 30.26}, {'longitude': 120.193, 'latitude': 30.26}]
        low = preview(low_task, payload(low_task, very_long))
        check('assigned aircraft battery reevaluated for longer detour', not low['allowed'] and any('电量' in x for x in low['constraints']))
        save(low_task, payload(low_task, very_long), 409)
        check('battery rejection preserves assigned task and original route', route(low_task)['plan']['revision'] == 1 and mysql('SELECT status FROM st_task WHERE id=' + quote(low_task) + ';') == 'assigned')
        deadline_order, deadline_task = order('deadline')
        mysql('UPDATE st_logistics_order SET deadline_at=DATE_ADD(NOW(3),INTERVAL 25 SECOND) WHERE id=' + quote(deadline_order) + ';')
        late_route = preview(deadline_task)
        check('unassigned order deadline checked against detour duration', not late_route['allowed'] and any('时限' in x for x in late_route['constraints']))
        save(deadline_task, expected=409)
        read_only = viewer()
        req('/sky/tasks/' + task + '/route', token=read_only)
        req('/sky/tasks/' + task + '/route/versions/1', token=read_only)
        req('/sky/tasks/' + task + '/route/preview', payload(task), 403, token=read_only)
        req('/sky/tasks/' + task + '/route', payload(task), 403, method='PUT', token=read_only)
        check('viewer can inspect routes and versions but cannot plan or save', True)
        final = save(task)['plan']
        readback = route(task)['plan']
        if readback != final:
            REPORT['roundtripDifference'] = {'response': final, 'readback': readback}
        check('saved response roundtrip preserves route within numeric tolerance', same_json(readback, final))
        final = readback
        assign(task, aircraft[0])
        req('/sky/tasks/' + task + '/start', {'reason': PREFIX})
        save(task, payload(task), 409)
        check('executing route cannot be edited', route(task)['plan']['revision'] == final['revision'])
        if args.restart:
            for operation in ['stop', 'start']:
                with (ROOT / 'logs' / ('routes-restart-' + operation + '.log')).open('w', encoding='utf-8') as output:
                    run = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts' / (operation + '.ps1')), '-Service', 'backend'], stdout=output, stderr=subprocess.STDOUT, timeout=110)
                assert run.returncode == 0, 'Backend restart failed'
            check('restart preserves executing route revision and geometry', route(task)['plan'] == final)
        print('INFO: waiting for Java to finish the real waypoint simulation', flush=True)
        end = time.monotonic() + 75
        while time.monotonic() < end:
            if mysql('SELECT status FROM st_task WHERE id=' + quote(task) + ';') == 'completed': break
            time.sleep(1)
        check('Java completes saved multi-waypoint task', mysql('SELECT status FROM st_task WHERE id=' + quote(task) + ';') == 'completed')
        tracks = req('/sky/tasks/' + task + '/tracks')
        check('every recorded point follows same timed route', all(same_point(t, point_at(final['points'], t['progress'] * final['durationSeconds'] / 100)) for t in tracks))
        check('fractional-time corners are explicitly preserved in tracks', all(any(same_point(t, corner) for t in tracks) for corner in final['points']))
        check('flight lands at fixed destination with completed progress', tracks[-1]['progress'] == 100 and same_point(tracks[-1], final['points'][-1]))
        req('/sky/logistics/orders/' + first_order + '/deliver', {'reason': PREFIX})
        check('detour delivery still uses original confirmation workflow', req('/sky/logistics/orders/' + first_order)['status'] == 'delivered')
        save(task, payload(task), 409)
        check('finished task retains immutable flown route', route(task)['plan'] == final)
        REPORT['trackCount'] = len(tracks)
        REPORT['flownPlan'] = final
        if args.ui:
            _, ui_task = order('ui_route')
            environment = dict(os.environ, SKYTWIN_UI_PREFIX=PREFIX, SKYTWIN_UI_TASK=ui_task, SKYTWIN_UI_ADMIN_TOKEN=admin, SKYTWIN_UI_VIEWER_TOKEN=read_only)
            run = subprocess.run([helpers.RUNTIME['NodeExecutable'], str(ROOT / 'scripts/verify-routes-ui.mjs')], cwd=ROOT.parent, env=environment, timeout=160)
            check('real browser waypoint editor passes', run.returncode == 0)
        check('original user task state and durations preserved', mysql("SELECT id,status,COALESCE(aircraft_id,''),duration_seconds FROM st_task WHERE id NOT IN (" + ids(tasks) + ') ORDER BY id;') == baseline)
        REPORT['passed'] = True
    except Exception as e:
        REPORT['error'] = str(e)
        raise
    finally:
        try:
            mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
            # Recover exact-prefix fixtures if a response failed after commit.
            own_orders = mysql('SELECT id,task_id FROM st_logistics_order WHERE LEFT(cargo_name,' + str(len(PREFIX)) + ')=' + quote(PREFIX) + ';').splitlines()
            for line in own_orders:
                order_id, task_id = line.split('\t')
                if order_id not in orders: orders.append(order_id)
                if task_id not in tasks: tasks.append(task_id)
            checks = mysql('SELECT id FROM st_airspace_check WHERE task_id IN (' + ids(tasks) + ');').splitlines()
            entities = orders + tasks + aircraft + stations + plans + zones + checks
            mysql(f"""START TRANSACTION;
                SELECT id FROM st_task WHERE id IN ({ids(tasks)}) ORDER BY id FOR UPDATE;
                DELETE FROM st_audit WHERE entity_id IN ({ids(entities)});
                DELETE FROM st_traffic_check WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_airspace_check WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_dispatch_plan WHERE id IN ({ids(plans)});
                DELETE FROM st_track WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_report WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_event WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_logistics_order WHERE id IN ({ids(orders)});
                DELETE FROM st_task WHERE id IN ({ids(tasks)});
                DELETE FROM st_aircraft WHERE id IN ({ids(aircraft)});
                DELETE FROM st_station WHERE id IN ({ids(stations)});
                DELETE FROM st_airspace_zone WHERE id IN ({ids(zones)});
                COMMIT;
            """)
            for user in users:
                if admin: req('/system/user/' + str(user), method='DELETE')
            REPORT['cleanup'] = {}
            for name, table, key, values in [('routes','st_task_route','task_id',tasks), ('dispatchSnapshots','st_dispatch_route_snapshot','plan_id',plans), ('tasks','st_task','id',tasks), ('orders','st_logistics_order','id',orders), ('aircraft','st_aircraft','id',aircraft), ('stations','st_station','id',stations), ('zones','st_airspace_zone','id',zones), ('plans','st_dispatch_plan','id',plans), ('checks','st_airspace_check','task_id',tasks), ('audits','st_audit','entity_id',entities)]:
                REPORT['cleanup'][name] = int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({ids(values)});'))
            REPORT['cleanup']['activeUsers'] = int(mysql('SELECT COUNT(*) FROM sys_user WHERE user_id IN (' + (','.join(map(str, users)) or '-1') + ") AND del_flag='0';"))
            REPORT['cleanup']['triggers'] = int(mysql("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME=" + quote(trigger) + ';'))
            if any(REPORT['cleanup'].values()): REPORT['passed'] = False
            for token in reversed(tokens): api(base, '/logout', 'POST', token=token)
        finally:
            (ROOT / 'logs/routes-verification.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Report: ruoyi/logs/routes-verification.json', flush=True)
    assert REPORT['passed'], 'Route verification failed'


if __name__ == '__main__':
    main()
