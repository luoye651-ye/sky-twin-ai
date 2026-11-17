"""Real localhost Java/MySQL traffic acceptance, unique fixtures, no mocked business API."""
import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('traffic_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
h = listing.helpers
api, mysql, quote = h.api, h.mysql, h.sql_value
PREFIX = 'tf_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


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
    tokens, users, tasks, aircraft, stations, plans, zones, orders = [], [], [], [], [], [], [], []
    trigger = 'verify_' + PREFIX

    def req(path, body=None, expected=200, method=None, token=None):
        _, value = api(base, path, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert value.get('code') == expected, (path, value.get('code'), value.get('msg'))
        return value.get('data')

    def resource():
        value = req('/sky/aircraft', {'name': PREFIX + '_aircraft_' + str(len(aircraft)), 'type': 'drone', 'model': 'traffic-test',
            'longitude': 120.24, 'latitude': 30.24, 'battery': 100, 'payloadCapacity': 2, 'seats': 0})
        aircraft.append(value)
        return value

    def task(suffix, direction=0, altitude=80, assigned=True):
        start, end = (stations[0], stations[1]) if direction == 0 else (stations[2], stations[3])
        value = req('/sky/tasks', {'title': PREFIX + '_' + suffix, 'type': 'environment', 'startStationId': start,
            'endStationId': end, 'payload': 0, 'passengers': 0, 'speed': 5, 'cruiseAltitude': altitude, 'reason': PREFIX})
        tasks.append(value)
        if assigned: req('/sky/tasks/' + value + '/assign', {'aircraftId': resource(), 'reason': PREFIX})
        return value

    def action(task_id, action_name, expected=200):
        return req('/sky/tasks/' + task_id + '/' + action_name, {'reason': PREFIX}, expected)

    def state():
        return req('/sky/traffic')

    def plan(task_ids, lead=15, delay=120):
        value = req('/sky/traffic/plans', {'tasks': [{'taskId': t, 'expectedRevision': req('/sky/tasks/' + t + '/route')['plan']['revision']} for t in task_ids],
            'leadSeconds': lead, 'maxDelaySeconds': delay})
        plans.append(value['id'])
        return value

    def confirm(value, expected=200, reason=PREFIX):
        return req('/sky/traffic/plans/' + value['id'] + '/confirm', {'reason': reason}, expected)

    def cancel_reservation(t):
        req('/sky/traffic/slots/' + t + '/cancel', {'reason': PREFIX})

    def task_state(t):
        return mysql('SELECT status FROM st_task WHERE id=' + quote(t) + ';')

    def wait_until(predicate, seconds, description):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate(): return
            time.sleep(.5)
        raise AssertionError('Timeout: ' + description)

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
        check('dedicated database port 3307', mysql('SELECT @@port;') == '3307')
        _, denied = api(base, '/sky/traffic')
        check('anonymous cannot inspect traffic', denied.get('code') == 401)
        admin = h.login(base)
        tokens.append(admin)
        baseline = mysql("SELECT id,status,COALESCE(aircraft_id,''),duration_seconds FROM st_task ORDER BY id;")
        check('traffic service exposes explicit simulation thresholds and clock', state()['horizontalMeters'] == 100 and state()['projectionBufferMeters'] == 10 and state()['verticalMeters'] == 30)
        for i, (lon, lat) in enumerate([(120.238, 30.24), (120.242, 30.24), (120.24, 30.23827), (120.24, 30.24173)]):
            stations.append(req('/sky/stations', {'name': PREFIX + '_station_' + str(i), 'type': 'takeoff', 'longitude': lon, 'latitude': lat, 'status': 'enabled'}))
        a, b = task('crossA'), task('crossB', 1)
        p = plan([a, b], lead=30)
        check('same-height crossing predicts conflict and positive delay', p['result']['allowed'] and p['result']['slots'][0]['delaySeconds'] == 0 and p['result']['slots'][1]['delaySeconds'] > 0 and bool(p['result']['slots'][1]['conflicts']))
        check('preview does not reserve or launch tasks', task_state(a) == 'assigned' and mysql('SELECT COUNT(*) FROM st_traffic_slot WHERE task_id IN (' + ids([a, b]) + ');') == '0')
        no_delay = plan([a, b], delay=0)
        check('insufficient delay horizon blocks whole batch', not no_delay['result']['allowed'])
        confirm(no_delay, 409)
        req('/sky/traffic/plans', {'tasks': [], 'leadSeconds': 5, 'maxDelaySeconds': 120}, 500)
        req('/sky/traffic/plans', {'tasks': [{'taskId': a, 'expectedRevision': 1}] * 2, 'leadSeconds': 5, 'maxDelaySeconds': 120}, 409)
        req('/sky/traffic/plans', {'tasks': [{'taskId': a, 'expectedRevision': 999}], 'leadSeconds': 5, 'maxDelaySeconds': 120}, 409)
        check('invalid empty duplicate and stale-route selections rejected', True)
        high = task('high', 1, 120)
        separated = plan([a, high])
        check('sufficient cruise-height separation needs no delay', separated['result']['allowed'] and separated['result']['slots'][1]['delaySeconds'] == 0)
        action(high, 'cancel')
        read_only = viewer()
        req('/sky/traffic', token=read_only)
        req('/sky/traffic/plans/' + p['id'], token=read_only)
        req('/sky/traffic/plans', p['request'], 403, token=read_only)
        req('/sky/traffic/plans/' + p['id'] + '/confirm', {'reason': PREFIX}, 403, token=read_only)
        check('viewer reads but cannot reserve', True)
        confirmed = confirm(p)
        check('confirmation persists all slots atomically', confirmed['status'] == 'confirmed' and mysql("SELECT COUNT(*) FROM st_traffic_slot WHERE task_id IN (" + ids([a, b]) + ") AND status='reserved';") == '2')
        confirm(p, 409)
        action(a, 'start', 409)
        check('reservation cannot be started early or double-confirmed', task_state(a) == 'assigned')
        req('/sky/tasks/' + a + '/route', {'expectedRevision': 1, 'waypoints': [], 'reason': PREFIX}, 409, method='PUT')
        check('reserved route version is frozen', req('/sky/tasks/' + a + '/route')['plan']['revision'] == 1)
        cancel_reservation(a)
        cancel_reservation(b)
        req('/sky/tasks/' + a + '/route', {'expectedRevision': 1, 'waypoints': [], 'reason': PREFIX}, method='PUT')
        check('cancel releases reservation without cancelling task and allows editing', task_state(a) == 'assigned' and req('/sky/tasks/' + a + '/route')['plan']['revision'] == 2)
        confirm(plan([a, b], lead=30))
        action(a, 'cancel')
        cancel_reservation(b)
        check('task cancellation also releases reservation', next(s for s in state()['slots'] if s['taskId'] == a)['status'] == 'cancelled')
        action(b, 'cancel')
        c, d = task('raceA'), task('raceB', 1)
        with ThreadPoolExecutor(2) as pool:
            race = list(pool.map(lambda t: api(base, '/sky/tasks/' + t + '/start', 'POST', {'reason': PREFIX}, admin)[1], [c, d]))
        check('concurrent manual starts admit exactly one conflicting flight', sorted(x.get('code') for x in race) == [200, 409])
        winner, loser = (c, d) if race[0]['code'] == 200 else (d, c)
        check('denial evidence survives rejected transaction', mysql('SELECT COUNT(*) FROM st_traffic_check WHERE task_id=' + quote(loser) + ' AND allowed=0;') == '1')
        evidence_id = next(x['id'] for x in state()['checks'] if x['taskId'] == loser)
        evidence = req('/sky/traffic/checks/' + evidence_id)['evidence']
        check('denial freezes full timed route and conflicting route evidence', len(evidence['candidate']['points']) == 4 and bool(evidence['conflicts']) and bool(evidence['others']))
        action(winner, 'cancel')
        action(loser, 'start')
        check('termination releases flight occupancy for formerly conflicting launch', task_state(loser) == 'executing')
        action(loser, 'cancel')
        e, f = task('failureA'), task('failureB', 1)
        failure = plan([e, f], lead=30)
        mysql("DELIMITER $$\nCREATE TRIGGER " + trigger + " BEFORE INSERT ON st_audit FOR EACH ROW BEGIN IF NEW.action='traffic.reserve' AND NEW.entity_id=" + quote(f) + " AND NEW.reason=" + quote(PREFIX + '_fault') + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='traffic verification fault'; END IF; END$$\nDELIMITER ;\n")
        confirm(failure, 500, PREFIX + '_fault')
        check('late audit failure rolls back ALL slots and plan confirmation', mysql('SELECT COUNT(*) FROM st_traffic_slot WHERE task_id IN (' + ids([e, f]) + ');') == '0' and req('/sky/traffic/plans/' + failure['id'])['status'] == 'proposed' and mysql("SELECT COUNT(*) FROM st_audit WHERE entity_id IN (" + ids([e, f]) + ") AND action='traffic.reserve';") == '0')
        mysql('DROP TRIGGER ' + trigger + ';')
        first, second = plan([e, f], lead=30), plan([e, f], lead=30)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda x: api(base, '/sky/traffic/plans/' + x['id'] + '/confirm', 'POST', {'reason': PREFIX}, admin)[1], [first, second]))
        check('two concurrent plans cannot reserve the same tasks', sorted(x.get('code') for x in results) == [200, 409])
        cancel_reservation(e)
        cancel_reservation(f)
        action(e, 'cancel')
        action(f, 'cancel')
        stale = task('stale')
        old = plan([stale])
        req('/sky/tasks/' + stale + '/route', {'expectedRevision': 1, 'waypoints': [], 'reason': PREFIX}, method='PUT')
        confirm(old, 409)
        check('route change after preview invalidates confirmation', task_state(stale) == 'assigned')
        action(stale, 'cancel')
        # The following direct SQL changes only scoped fixtures, modelling resource/deadline changes.
        low = task('changed_battery')
        low_plan = plan([low], lead=30)
        low_aircraft = mysql('SELECT aircraft_id FROM st_task WHERE id=' + quote(low) + ';')
        mysql('UPDATE st_aircraft SET battery=20 WHERE id=' + quote(low_aircraft) + ';')
        confirm(low_plan, 409)
        check('confirmation rechecks current battery reserve', task_state(low) == 'assigned')
        action(low, 'cancel')
        order_id = req('/sky/logistics/orders', {'cargoName': PREFIX + '_deadline', 'weight': 1, 'startStationId': stations[0], 'endStationId': stations[1], 'deadlineMinutes': 30, 'reason': PREFIX})
        orders.append(order_id)
        order_task = req('/sky/logistics/orders/' + order_id)['taskId']
        tasks.append(order_task)
        carrier = req('/sky/aircraft', {'name': PREFIX + '_carrier', 'type': 'cargo', 'model': 'traffic-test', 'longitude': 120.24, 'latitude': 30.24, 'battery': 100, 'payloadCapacity': 20, 'seats': 0})
        aircraft.append(carrier)
        req('/sky/tasks/' + order_task + '/assign', {'aircraftId': carrier, 'reason': PREFIX})
        mysql('UPDATE st_logistics_order SET deadline_at=DATE_ADD(NOW(3),INTERVAL 25 SECOND) WHERE id=' + quote(order_id) + ';')
        deadline_plan = plan([order_task], lead=30, delay=0)
        check('waiting time is included in delivery deadline feasibility', not deadline_plan['result']['allowed'] and any('时限' in x for x in deadline_plan['result']['slots'][0]['problems']))
        mysql('UPDATE st_logistics_order SET deadline_at=DATE_ADD(NOW(3),INTERVAL 30 MINUTE) WHERE id=' + quote(order_id) + ';')
        confirm(plan([order_task], lead=5))
        mysql('UPDATE st_logistics_order SET deadline_at=NOW(3) WHERE id=' + quote(order_id) + ';')
        wait_until(lambda: next(s for s in state()['slots'] if s['taskId'] == order_task)['status'] == 'blocked', 15, 'deadline recheck')
        check('automatic launch rechecks wall-clock deadline after reservation', task_state(order_task) == 'assigned')
        action(order_task, 'cancel')
        # Persisted future slots must participate in the normal /start gate too.
        booked, intruder = task('reserved_corridor'), task('intruder_corridor')
        confirm(plan([booked], lead=5))
        action(intruder, 'start', 409)
        check('manual launch cannot intrude into a reserved future corridor', task_state(intruder) == 'assigned')
        cancel_reservation(booked)
        action(booked, 'cancel')
        action(intruder, 'cancel')
        zone_task = task('changed_policy')
        zone_plan = confirm(plan([zone_task], lead=5))
        zones.append(req('/sky/airspace/zones', {'name': PREFIX + '_late_zone', 'type': 'no_fly', 'west': 120.237, 'east': 120.243,
            'south': 30.237, 'north': 30.243, 'minAltitude': 0, 'maxAltitude': 120, 'startsAt': None, 'endsAt': None, 'enabled': True, 'reason': PREFIX}))
        wait_until(lambda: next(s for s in state()['slots'] if s['taskId'] == zone_task)['status'] == 'blocked', 15, 'changed policy launch block')
        check('arrival-time recheck blocks newly forbidden airspace without launching', task_state(zone_task) == 'assigned' and mysql('SELECT COUNT(*) FROM st_track WHERE task_id=' + quote(zone_task) + ';') == '0')
        # Disable only this fixture's zone via its normal API.
        req('/sky/airspace/zones/' + zones[-1], {'name': PREFIX + '_late_zone', 'type': 'no_fly', 'west': 120.237, 'east': 120.243,
            'south': 30.237, 'north': 30.243, 'minAltitude': 0, 'maxAltitude': 120, 'startsAt': None, 'endsAt': None, 'enabled': False, 'reason': PREFIX}, method='PUT')
        action(zone_task, 'cancel')
        cycle_a, cycle_b = task('cycle_atomic_A'), task('cycle_atomic_B', 1, 120)
        action(cycle_a, 'start')
        action(cycle_b, 'start')
        mysql("DELIMITER $$\nCREATE TRIGGER " + trigger + " BEFORE INSERT ON st_track FOR EACH ROW BEGIN IF NEW.task_id=" + quote(cycle_b) + " AND NEW.progress>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='traffic cycle verification fault'; END IF; END$$\nDELIMITER ;\n")
        time.sleep(2)
        frozen_sql = 'SELECT tick FROM st_traffic_clock WHERE id=1; SELECT id,elapsed_seconds,progress FROM st_task WHERE id IN (' + ids([cycle_a, cycle_b]) + ') ORDER BY id;'
        frozen = mysql(frozen_sql)
        time.sleep(2)
        check('late track failure rolls back shared clock and ALL aircraft progress', mysql(frozen_sql) == frozen)
        mysql('DROP TRIGGER ' + trigger + ';')
        action(cycle_a, 'cancel')
        action(cycle_b, 'cancel')
        run_a, run_b = task('scheduledA'), task('scheduledB', 1)
        running_plan = confirm(plan([run_a, run_b], lead=5))
        wait_until(lambda: task_state(run_a) == 'executing', 15, 'first reserved launch')
        if args.restart:
            with (ROOT / 'logs/traffic-restart-stop.log').open('w', encoding='utf-8') as output:
                stopped = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/stop.ps1'), '-Service', 'backend'], stdout=output, stderr=subprocess.STDOUT, timeout=35)
            assert stopped.returncode == 0
            before = mysql('SELECT tick FROM st_traffic_clock WHERE id=1; SELECT id,status,elapsed_seconds FROM st_task WHERE id IN (' + ids([run_a, run_b]) + ') ORDER BY id;')
            time.sleep(2)
            check('backend pause freezes clock and executing progress together', mysql('SELECT tick FROM st_traffic_clock WHERE id=1; SELECT id,status,elapsed_seconds FROM st_task WHERE id IN (' + ids([run_a, run_b]) + ') ORDER BY id;') == before)
            with (ROOT / 'logs/traffic-restart-start.log').open('w', encoding='utf-8') as output:
                started = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts/start.ps1'), '-Service', 'backend'], stdout=output, stderr=subprocess.STDOUT, timeout=110)
            assert started.returncode == 0
            check('restart retains exact confirmed schedule', req('/sky/traffic/plans/' + running_plan['id'])['result'] == running_plan['result'])
        print('INFO: waiting for both real Java scheduled flights', flush=True)
        wait_until(lambda: task_state(run_a) == task_state(run_b) == 'completed', 75, 'scheduled completion')
        check('both reserved flights automatically start and complete', all(next(s for s in state()['slots'] if s['taskId'] == t)['status'] == 'completed' for t in [run_a, run_b]))
        check('each scheduled task launches exactly once', all(mysql("SELECT COUNT(*) FROM st_audit WHERE entity_id=" + quote(t) + " AND action='task.start';") == '1' for t in [run_a, run_b]))
        tracks = [req('/sky/tasks/' + t + '/tracks') for t in [run_a, run_b]]
        check('scheduled flights preserve trajectories and finish landed', all(len(x) >= 21 and x[-1]['progress'] == 100 and x[-1]['altitude'] == 0 for x in tracks))
        REPORT['schedule'] = running_plan['result']
        if args.ui:
            ui_a, ui_b = task('uiA'), task('uiB', 1)
            env = dict(os.environ, SKYTWIN_UI_PREFIX=PREFIX, SKYTWIN_UI_TASKS=json.dumps([ui_a, ui_b]), SKYTWIN_UI_ADMIN_TOKEN=admin, SKYTWIN_UI_VIEWER_TOKEN=read_only)
            run = subprocess.run([h.RUNTIME['NodeExecutable'], str(ROOT / 'scripts/verify-traffic-ui.mjs')], cwd=ROOT.parent, env=env, timeout=160)
            check('real browser traffic workflow passes', run.returncode == 0)
        check('original user tasks retain state assignment and duration', mysql("SELECT id,status,COALESCE(aircraft_id,''),duration_seconds FROM st_task WHERE id NOT IN (" + ids(tasks) + ') ORDER BY id;') == baseline)
        REPORT['passed'] = True
    except Exception as e:
        REPORT['error'] = str(e)
        raise
    finally:
        try:
            mysql('DROP TRIGGER IF EXISTS ' + trigger + ';')
            recovered = mysql('SELECT id FROM st_task WHERE LEFT(title,' + str(len(PREFIX)) + ')=' + quote(PREFIX) + ' OR LEFT(title,' + str(len(PREFIX) + 3) + ')=' + quote('配送：' + PREFIX) + ';').splitlines()
            tasks[:] = list(dict.fromkeys(tasks + recovered))
            plans[:] = mysql('SELECT id FROM st_traffic_plan WHERE LOCATE(' + quote(PREFIX) + ',CAST(result_json AS CHAR))>0;').splitlines()
            checks = mysql('SELECT id FROM st_airspace_check WHERE task_id IN (' + ids(tasks) + ');').splitlines()
            entities = orders + tasks + aircraft + stations + plans + zones + checks
            mysql(f"""START TRANSACTION;
                SELECT tick FROM st_traffic_clock WHERE id=1 FOR UPDATE;
                SELECT id FROM st_task WHERE id IN ({ids(tasks)}) ORDER BY id FOR UPDATE;
                DELETE FROM st_audit WHERE entity_id IN ({ids(entities)});
                DELETE FROM st_traffic_check WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_airspace_check WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_traffic_slot WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_traffic_plan WHERE id IN ({ids(plans)});
                DELETE FROM st_track WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_report WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_event WHERE task_id IN ({ids(tasks)});
                DELETE FROM st_logistics_order WHERE id IN ({ids(orders)});
                DELETE FROM st_task WHERE id IN ({ids(tasks)});
                DELETE FROM st_aircraft WHERE id IN ({ids(aircraft)});
                DELETE FROM st_station WHERE id IN ({ids(stations)});
                DELETE FROM st_airspace_zone WHERE id IN ({ids(zones)});
                COMMIT;""")
            for user in users:
                if admin: req('/system/user/' + str(user), method='DELETE')
            REPORT['cleanup'] = {}
            for name, table, key, values in [('slots', 'st_traffic_slot', 'task_id', tasks), ('checks', 'st_traffic_check', 'task_id', tasks),
                    ('plans', 'st_traffic_plan', 'id', plans), ('tasks', 'st_task', 'id', tasks), ('aircraft', 'st_aircraft', 'id', aircraft),
                    ('stations', 'st_station', 'id', stations), ('zones', 'st_airspace_zone', 'id', zones), ('audits', 'st_audit', 'entity_id', entities)]:
                REPORT['cleanup'][name] = int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({ids(values)});'))
            REPORT['cleanup']['activeUsers'] = int(mysql('SELECT COUNT(*) FROM sys_user WHERE user_id IN (' + (','.join(map(str, users)) or '-1') + ") AND del_flag='0';"))
            REPORT['cleanup']['triggers'] = int(mysql("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME=" + quote(trigger) + ';'))
            if any(REPORT['cleanup'].values()): REPORT['passed'] = False
            for token in reversed(tokens): api(base, '/logout', 'POST', token=token)
        finally:
            (ROOT / 'logs/traffic-verification.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Report: ruoyi/logs/traffic-verification.json', flush=True)
    assert REPORT['passed'], 'Traffic verification failed'


if __name__ == '__main__':
    main()
