"""Isolated real HTTP/MySQL acceptance of airspace policy and authoritative launch gate."""
import argparse
import importlib.util
import json
import math
import pathlib
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('airspace_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
helpers = listing.helpers
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
PREFIX = 'as_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


def check(name, condition):
    assert condition, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def ids(values):
    return ','.join(quote(value) for value in values) if values else "''"


def equivalent(left, right):
    # MySQL binary JSON can change the last floating-point bit on a round trip.
    # Preserve all keys/strings/timestamps/booleans exactly; tolerate <1ns/1e-9deg numerics.
    if isinstance(left, float) and isinstance(right, (float, int)):
        return math.isclose(left, right, rel_tol=0, abs_tol=1e-9)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equivalent(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equivalent(a, b) for a, b in zip(left, right))
    return left == right


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    base = 'http://127.0.0.1:5173/java-api'
    zones, stations, aircraft, tasks, orders, plans, users, tokens = [], [], [], [], [], [], [], []
    admin = None
    trigger = 'verify_' + PREFIX

    def request(path, body=None, expected=200, method=None, token=None):
        _, result = api(base, path, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert result.get('code') == expected, (path, result.get('code'), result.get('msg'))
        return result.get('data')

    def task(suffix, altitude=60):
        value = request('/sky/tasks', {'title': PREFIX + '_' + suffix, 'type': 'environment',
            'startStationId': stations[0], 'endStationId': stations[1], 'payload': 1, 'passengers': 0,
            'speed': 10, 'cruiseAltitude': altitude, 'reason': PREFIX})
        tasks.append(value)
        return value

    def action(value, name, resource=None, expected=200):
        return request('/sky/tasks/' + value + '/' + name, {'aircraftId': resource, 'reason': PREFIX}, expected)

    def state(value):
        return mysql('SELECT status FROM st_task WHERE id=' + quote(value) + ';')

    zone_input = {'name': PREFIX + '_no_fly', 'type': 'no_fly', 'west': 120.191, 'east': 120.192,
        'south': 30.214, 'north': 30.216, 'minAltitude': 0, 'maxAltitude': 120,
        'startsAt': None, 'endsAt': None, 'enabled': True, 'reason': PREFIX}

    def change(value, **patch):
        body = dict(zone_input, **patch)
        request('/sky/airspace/zones/' + value, body, method='PUT')
        return body

    def validate(value, departure=None):
        return request('/sky/airspace/validate', {'taskId': value, 'departureAt': departure})

    def plan(value):
        result = request('/sky/dispatch/plans', {'tasks': [{'taskId': value, 'priority': 1}], 'aircraftIds': [aircraft[0]]})
        plans.append(result['id'])
        return result

    def create_viewer():
        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(row['roleId'] for row in roles['rows'] if row['roleKey'] == 'sky_viewer')
        username, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'Az!3'
        request('/system/user', {'userName': username, 'nickName': username, 'password': password,
            'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [role], 'postIds': []})
        _, found = api(base, '/system/user/list?userName=' + username, token=admin)
        users.append(next(row['userId'] for row in found['rows'] if row['userName'] == username))
        token = listing.login_as(base, username, password)
        tokens.append(token)
        return token

    try:
        check('dedicated MySQL endpoint is 3307', mysql('SELECT @@port;') == '3307')
        _, denied = api(base, '/sky/airspace/zones')
        check('anonymous cannot read zones', denied.get('code') == 401)
        admin = helpers.login(base)
        tokens.append(admin)
        baseline_tasks = mysql("SELECT id,status,COALESCE(aircraft_id,'') FROM st_task ORDER BY id;")
        for index in range(2):
            stations.append(request('/sky/stations', {'name': PREFIX + '_s' + str(index), 'type': 'logistics',
                'longitude': 120.19 + index * .003, 'latitude': 30.215, 'status': 'enabled'}))
            aircraft.append(request('/sky/aircraft', {'name': PREFIX + '_a' + str(index), 'type': 'cargo',
                'model': 'airspace-test', 'longitude': 120.19, 'latitude': 30.215,
                'battery': 100, 'payloadCapacity': 20, 'seats': 0}))
        first = task('patrol')
        pending = task('pending')
        for label, patch in (
            ('reversed longitude', {'west': 120.193, 'east': 120.19}),
            ('reversed latitude', {'south': 30.22, 'north': 30.21}),
            ('reversed height', {'minAltitude': 121, 'maxAltitude': 120}),
            ('reversed time', {'startsAt': '2026-10-20T10:00:00', 'endsAt': '2026-10-20T09:00:00'}),
            ('invalid limit floor', {'type': 'height_limit', 'minAltitude': 5}),
        ):
            before = mysql('SELECT COUNT(*) FROM st_airspace_zone;')
            request('/sky/airspace/zones', dict(zone_input, **patch), expected=409)
            check(label + ' rejected without writing rule', mysql('SELECT COUNT(*) FROM st_airspace_zone;') == before)
        _, invalid = api(base, '/sky/airspace/zones', 'POST', dict(zone_input, name=''), admin)
        check('blank region name rejected', invalid.get('code') != 200)
        zone = request('/sky/airspace/zones', zone_input)
        zones.append(zone)
        blocked = validate(first)
        check('continuous crossing reports zone phase and clipped points', not blocked['allowed']
            and len(blocked['violations']) == 1 and blocked['violations'][0]['phase'] == 'cruise'
            and blocked['violations'][0]['zoneId'] == zone and blocked['violations'][0]['from']['altitude'] == 60)
        snapshot = request('/sky/snapshot')
        live_zone = next(value for value in snapshot['airspaceZones'] if value['id'] == zone)
        check('snapshot carries actual active rule for digital twin', live_zone['activeNow'] is True)
        saved_row = next(value for value in request('/sky/airspace/checks') if value['taskId'] == first)
        saved_detail = request('/sky/airspace/checks/' + saved_row['id'])
        if not equivalent(saved_detail['result'], blocked):
            REPORT['snapshotComparison'] = {'response': blocked, 'stored': saved_detail['result']}
        check('manual check preserves geometry time and decision evidence', equivalent(saved_detail['result'], blocked))
        action(first, 'assign', aircraft[0])
        before_aircraft = mysql('SELECT status,longitude,latitude,altitude,battery FROM st_aircraft WHERE id=' + quote(aircraft[0]) + ';')
        action(first, 'start', expected=409)
        check('task entry cannot launch through no-fly zone', state(first) == 'assigned'
            and mysql('SELECT COUNT(*) FROM st_track WHERE task_id=' + quote(first) + ';') == '0')
        check('launch denial leaves aircraft unchanged', before_aircraft == mysql('SELECT status,longitude,latitude,altitude,battery FROM st_aircraft WHERE id=' + quote(aircraft[0]) + ';'))
        records = request('/sky/airspace/checks')
        check('denial record survives outer launch transaction rollback', any(row['taskId'] == first and row['entry'] == 'start' and not row['allowed'] for row in records))
        # Same gate must also apply through the order service and original task API.
        order = request('/sky/logistics/orders', {'cargoName': PREFIX + '_medicine', 'weight': 1,
            'startStationId': stations[0], 'endStationId': stations[1], 'deadlineMinutes': 30, 'reason': PREFIX})
        orders.append(order)
        detail = request('/sky/logistics/orders/' + order)
        logistics_task = detail['taskId']
        tasks.append(logistics_task)
        request('/sky/logistics/orders/' + order + '/assign', {'aircraftId': aircraft[1], 'reason': PREFIX})
        request('/sky/logistics/orders/' + order + '/start', {'reason': PREFIX}, expected=409)
        action(logistics_task, 'start', expected=409)
        check('order and task entry both enforce same launch gate', state(logistics_task) == 'assigned'
            and mysql('SELECT COUNT(*) FROM st_track WHERE task_id=' + quote(logistics_task) + ';') == '0')
        action(logistics_task, 'cancel')
        action(first, 'cancel')
        blocked_plan = plan(pending)
        check('optimizer excludes airspace-violating task', blocked_plan['result']['optimized']['assignedCount'] == 0
            and any('禁飞' in reason for reason in blocked_plan['result']['decisions'][0]['candidates'][0]['reasons']))
        change(zone, enabled=False)
        check('disabled zone allows same route', validate(pending)['allowed'])
        stale_plan = plan(pending)
        check('disabled rule permits optimized assignment preview', stale_plan['result']['optimized']['assignedCount'] == 1)
        change(zone)
        request('/sky/dispatch/plans/' + stale_plan['id'] + '/confirm', {'reason': PREFIX}, expected=409)
        check('new rule after preview prevents entire batch confirmation', state(pending) == 'created'
            and mysql('SELECT status FROM st_dispatch_plan WHERE id=' + quote(stale_plan['id']) + ';') == 'proposed')
        # Check the same route with a ceiling exactly at, then below, business altitude.
        change(zone, type='height_limit', maxAltitude=60)
        check('height limit equality is legal despite display lift', validate(pending)['allowed'])
        change(zone, type='height_limit', maxAltitude=59)
        check('business altitude over ceiling rejected', not validate(pending)['allowed'])
        now = datetime.fromisoformat(validate(pending)['checkedAt'])
        future = (now + timedelta(days=1)).isoformat(timespec='seconds')
        change(zone, startsAt=future)
        check('future region inactive for current flight', validate(pending)['allowed'])
        check('future departure sees future no-fly region', not validate(pending, future)['allowed'])
        change(zone, endsAt=(now + timedelta(seconds=3)).isoformat(timespec='seconds'))
        check('zone ending before crossing allows flight', validate(pending)['allowed'])
        change(zone, name=PREFIX + '_renamed')
        old = request('/sky/airspace/checks/' + saved_row['id'])
        check('old evidence keeps original zone name and rule version', equivalent(old['result'], blocked))
        read_only = create_viewer()
        request('/sky/airspace/zones', token=read_only)
        request('/sky/airspace/checks/' + saved_row['id'], token=read_only)
        request('/sky/airspace/zones', zone_input, expected=403, token=read_only)
        request('/sky/airspace/zones/' + zone, zone_input, expected=403, method='PUT', token=read_only)
        request('/sky/airspace/validate', {'taskId': pending}, expected=403, token=read_only)
        check('viewer reads evidence but cannot manage or validate', True)
        # Concurrency: both attempts see a blocked route; neither writes flight state.
        action(pending, 'assign', aircraft[0])
        def start(_):
            return api(base, '/sky/tasks/' + pending + '/start', 'POST', {'reason': PREFIX}, admin)[1]['code']
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(start, [0, 1]))
        check('parallel starts cannot bypass blocked route', codes == [409, 409] and state(pending) == 'assigned')
        change(zone, enabled=False)
        action(pending, 'start')
        check('same assigned task can start after policy disabled', state(pending) == 'executing'
            and int(mysql('SELECT COUNT(*) FROM st_track WHERE task_id=' + quote(pending) + ';')) >= 1)
        action(pending, 'cancel')
        # Policy writes, revision changes and audit must be atomic.
        previous_count = mysql('SELECT COUNT(*) FROM st_airspace_zone;')
        previous_revision = mysql('SELECT revision FROM st_airspace_policy WHERE id=1;')
        mysql(f"""DELIMITER //
            CREATE TRIGGER {trigger} BEFORE INSERT ON st_audit FOR EACH ROW
            BEGIN IF NEW.action='airspace.zone.save' AND NEW.reason={quote(PREFIX + '_fault')}
            THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Scoped airspace audit failure'; END IF; END//
            DELIMITER ;
        """)
        try:
            _, rejected = api(base, '/sky/airspace/zones', 'POST', dict(zone_input, reason=PREFIX + '_fault'), admin)
            check('late rule-audit failure rolls back zone and revision', rejected.get('code') != 200
                and mysql('SELECT COUNT(*) FROM st_airspace_zone;') == previous_count
                and mysql('SELECT revision FROM st_airspace_policy WHERE id=1;') == previous_revision)
        finally:
            mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
        if args.restart:
            for operation in ['stop', 'start']:
                with (ROOT / 'logs' / ('airspace-restart-' + operation + '.log')).open('w', encoding='utf-8') as output:
                    run = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts' / (operation + '.ps1')), '-Service', 'backend'], stdout=output,
                        stderr=subprocess.STDOUT, timeout=110)
                assert run.returncode == 0, 'Backend restart failed'
            check('restart preserves rules and independent denial evidence', any(row['id'] == zone for row in request('/sky/airspace/zones'))
                and equivalent(request('/sky/airspace/checks/' + saved_row['id'])['result'], blocked))
        REPORT['uiFixture'] = {'zones': [dict(live_zone)], 'result': blocked,
            'tasks': [value for value in snapshot['tasks'] if value['id'] == first],
            'aircraft': [value for value in snapshot['aircraft'] if value['id'] in aircraft],
            'stations': [value for value in snapshot['stations'] if value['id'] in stations]}
        existing = mysql("SELECT id,status,COALESCE(aircraft_id,'') FROM st_task WHERE id NOT IN (" + ids(tasks) + ') ORDER BY id;')
        check('original user task state preserved', existing == baseline_tasks)
        REPORT['passed'] = True
    except Exception as error:
        REPORT['error'] = str(error)
        raise
    finally:
        try:
            if admin:
                for value in tasks:
                    if state(value) in ('assigned', 'executing'):
                        action(value, 'cancel')
                mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
                check_ids = mysql('SELECT id FROM st_airspace_check WHERE task_id IN (' + ids(tasks) + ');').splitlines()
                mysql(f"DELETE FROM st_audit WHERE entity_id IN ({ids(tasks + orders + zones + stations + aircraft + plans + check_ids)}); "
                    f"DELETE FROM st_traffic_check WHERE task_id IN ({ids(tasks)}); "
                    f"DELETE FROM st_airspace_check WHERE task_id IN ({ids(tasks)}); DELETE FROM st_dispatch_plan WHERE id IN ({ids(plans)}); "
                    f"DELETE FROM st_track WHERE task_id IN ({ids(tasks)}); DELETE FROM st_report WHERE task_id IN ({ids(tasks)}); "
                    f"DELETE FROM st_event WHERE task_id IN ({ids(tasks)}); DELETE FROM st_logistics_order WHERE id IN ({ids(orders)}); "
                    f"DELETE FROM st_task WHERE id IN ({ids(tasks)}); DELETE FROM st_aircraft WHERE id IN ({ids(aircraft)}); "
                    f"DELETE FROM st_station WHERE id IN ({ids(stations)}); DELETE FROM st_airspace_zone WHERE id IN ({ids(zones)});")
                # A revision may advance during tests; never rewind the live policy version.
                REPORT['cleanup'] = {}
                for label, table, key, values in (
                    ('zones', 'st_airspace_zone', 'id', zones), ('checks', 'st_airspace_check', 'task_id', tasks),
                    ('tasks', 'st_task', 'id', tasks), ('aircraft', 'st_aircraft', 'id', aircraft),
                    ('stations', 'st_station', 'id', stations), ('plans', 'st_dispatch_plan', 'id', plans),
                    ('orders', 'st_logistics_order', 'id', orders),
                    ('audits', 'st_audit', 'entity_id', tasks + orders + zones + stations + aircraft + plans + check_ids)):
                    REPORT['cleanup'][label] = int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({ids(values)});'))
                for user in users:
                    api(base, '/system/user/' + str(user), 'DELETE', token=admin)
                REPORT['cleanup']['activeUsers'] = int(mysql(f"SELECT COUNT(*) FROM sys_user WHERE user_id IN ({','.join(map(str, users)) or '-1'}) AND del_flag='0';"))
                REPORT['cleanup']['triggers'] = int(mysql("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME=" + quote(trigger) + ';'))
                if any(REPORT['cleanup'].values()):
                    REPORT['passed'] = False
                for token in reversed(tokens):
                    api(base, '/logout', 'POST', token=token)
        finally:
            (ROOT / 'logs/airspace-verification.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Report: ruoyi/logs/airspace-verification.json', flush=True)
    assert REPORT['passed'], 'Airspace verification failed'


if __name__ == '__main__':
    main()
