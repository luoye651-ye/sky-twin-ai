"""Real local dispatch acceptance with isolated fixtures, cleanup and no token output."""
import argparse
import importlib.util
import json
import pathlib
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dispatch_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
helpers = listing.helpers
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
PREFIX = 'ds_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


def check(name, condition):
    assert condition, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def ids(values):
    return ','.join(quote(value) for value in values) if values else "''"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:5173/java-api')
    base = parser.parse_args().base_url.rstrip('/')
    assert base in ('http://127.0.0.1:5173/java-api', 'http://127.0.0.1:8081')
    stations, aircraft, tasks, plans, users, tokens = [], [], [], [], [], []
    admin = None
    trigger = 'verify_' + PREFIX

    def request(path, body=None, token=None, expected=200, method=None):
        _, result = api(base, path, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert result.get('code') == expected, (path, result.get('code'), result.get('msg'))
        return result.get('data')

    def new_aircraft(suffix, kind='cargo', battery=100, capacity=20, lon=120.19, seats=0):
        value = request('/sky/aircraft', {'name': PREFIX + '_' + suffix, 'type': kind, 'model': 'dispatch-test',
            'longitude': lon, 'latitude': 30.215, 'battery': battery, 'payloadCapacity': capacity, 'seats': seats})
        aircraft.append(value)
        return value

    def new_task(suffix, kind='environment', payload=1, passengers=0):
        value = request('/sky/tasks', {'title': PREFIX + '_' + suffix, 'type': kind,
            'startStationId': stations[0], 'endStationId': stations[1], 'payload': payload,
            'passengers': passengers, 'speed': 10, 'cruiseAltitude': 60, 'reason': PREFIX + '_' + suffix})
        tasks.append(value)
        return value

    def preview(selected, fleet, priorities=None):
        value = request('/sky/dispatch/plans', {'tasks': [{'taskId': value, 'priority': (priorities or {}).get(value, 1)} for value in selected], 'aircraftIds': fleet})
        plans.append(value['id'])
        return value

    def confirm(plan, reason='confirm', expected=200):
        return request('/sky/dispatch/plans/' + plan['id'] + '/confirm', {'reason': PREFIX + '_' + reason}, expected=expected)

    def state(task):
        return mysql('SELECT status FROM st_task WHERE id=' + quote(task))

    def viewer():
        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(row['roleId'] for row in roles['rows'] if row['roleKey'] == 'sky_viewer')
        username, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'Aa!2'
        request('/system/user', {'userName': username, 'nickName': username, 'password': password,
            'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [role], 'postIds': []})
        _, found = api(base, '/system/user/list?userName=' + username, token=admin)
        users.append(next(row['userId'] for row in found['rows'] if row['userName'] == username))
        token = listing.login_as(base, username, password)
        tokens.append(token)
        return token

    try:
        check('dedicated MySQL is 3307', mysql('SELECT @@port') == '3307')
        baseline = mysql('SELECT id,status,COALESCE(aircraft_id,\'\') FROM st_task ORDER BY id')
        _, denied = api(base, '/sky/dispatch/plans')
        check('anonymous cannot read dispatch', denied.get('code') == 401)
        admin = helpers.login(base)
        tokens.append(admin)
        for index in range(2):
            stations.append(request('/sky/stations', {'name': PREFIX + '_s' + str(index), 'type': 'logistics',
                'longitude': 120.19 + .003 * index, 'latitude': 30.215, 'status': 'enabled'}))
        cargo = new_aircraft('cargo')
        scout = new_aircraft('scout', 'drone', 95, 2, 120.191)
        low = new_aircraft('low', battery=10)
        small = new_aircraft('small', capacity=.5)
        evtol = new_aircraft('evtol', 'evtol', seats=4)
        patrol = new_task('1patrol')
        delivery = new_task('2delivery', 'logistics', 5)
        plan = preview([patrol, delivery], [cargo, scout])
        # UUID order is randomized; benchmark is deliberately fixed in the pure algorithm checks.
        check('preview globally covers patrol and cargo-only task', plan['result']['optimized']['assignedCount'] == 2)
        check('preview does not reserve tasks or aircraft', state(patrol) == state(delivery) == 'created'
            and mysql('SELECT status FROM st_aircraft WHERE id=' + quote(cargo)) == 'idle')
        check('plan exposes baseline and measured algorithm time', plan['result']['baseline']['assignedCount'] >= 1
            and plan['result']['calculationMs'] >= 0 and plan['algorithm'] == 'fleet-mincost-v1')
        check('plan detail is persisted', request('/sky/dispatch/plans/' + plan['id'])['result'] == plan['result'])
        check('history includes saved plan', any(row['id'] == plan['id'] for row in request('/sky/dispatch/plans')))
        invalid = preview([delivery], [scout, low, small, evtol])
        candidates = invalid['result']['decisions'][0]['candidates']
        check('ineligible fleet explains type battery and payload', invalid['result']['optimized']['assignedCount'] == 0
            and len(candidates) == 4 and all(row['reasons'] and not row['eligible'] for row in candidates))
        confirm(invalid, expected=409)
        check('empty allocation cannot be confirmed', state(delivery) == 'created')
        for body in ({'tasks': [], 'aircraftIds': [cargo]},
                     {'tasks': [{'taskId': delivery, 'priority': 4}], 'aircraftIds': [cargo]},
                     {'tasks': [None], 'aircraftIds': [cargo]}):
            _, result = api(base, '/sky/dispatch/plans', 'POST', body, admin)
            check('invalid preview input rejected ' + str(len(REPORT['checks'])), result.get('code') != 200)
        duplicate = {'tasks': [{'taskId': delivery, 'priority': 1}] * 2, 'aircraftIds': [cargo]}
        request('/sky/dispatch/plans', duplicate, expected=409)
        check('duplicate task cannot produce a plan', True)
        read_only = viewer()
        request('/sky/dispatch/plans/' + plan['id'], token=read_only)
        request('/sky/dispatch/plans', {'tasks': [{'taskId': delivery, 'priority': 1}], 'aircraftIds': [cargo]}, token=read_only, expected=403)
        request('/sky/dispatch/plans/' + plan['id'] + '/confirm', {'reason': PREFIX}, token=read_only, expected=403)
        check('viewer can inspect but cannot plan or confirm', True)
        stale = preview([delivery], [cargo])
        mysql('UPDATE st_dispatch_plan SET expires_at=DATE_SUB(NOW(3), INTERVAL 1 SECOND) WHERE id=' + quote(stale['id']))
        confirm(stale, expected=409)
        check('expired plan cannot reserve resources', state(delivery) == 'created')
        # Candidate state changes after planning must be rejected at confirm time.
        changed = preview([delivery], [cargo])
        mysql('UPDATE st_aircraft SET battery=5 WHERE id=' + quote(cargo))
        confirm(changed, expected=409)
        check('confirmation rechecks current battery', state(delivery) == 'created')
        mysql('UPDATE st_aircraft SET battery=100 WHERE id=' + quote(cargo))
        # A late audit write failure proves cross-task and plan changes roll back together.
        rollback = preview([patrol, delivery], [cargo, scout])
        last = sorted([patrol, delivery])[-1]
        mysql(f"""DELIMITER //
            CREATE TRIGGER {trigger} BEFORE INSERT ON st_audit FOR EACH ROW
            BEGIN IF NEW.entity_id={quote(last)} AND NEW.action='task.assign'
            AND NEW.reason={quote(PREFIX + '_fault')} THEN SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT='Scoped dispatch acceptance fault'; END IF; END//
            DELIMITER ;
            """)
        try:
            _, result = api(base, '/sky/dispatch/plans/' + rollback['id'] + '/confirm', 'POST', {'reason': PREFIX + '_fault'}, admin)
            check('injected late failure is reported', result.get('code') != 200)
            check('late failure rolls back every task and plan', state(patrol) == state(delivery) == 'created'
                and mysql('SELECT status FROM st_dispatch_plan WHERE id=' + quote(rollback['id'])) == 'proposed'
                and mysql('SELECT COUNT(*) FROM st_audit WHERE reason=' + quote(PREFIX + '_fault')) == '0')
        finally:
            mysql('DROP TRIGGER IF EXISTS ' + trigger)
        confirmed = confirm(plan)
        check('batch confirms both tasks atomically', state(patrol) == state(delivery) == 'assigned'
            and confirmed['status'] == 'confirmed' and confirmed['confirmedBy'] == 'admin')
        confirm(plan, expected=409)
        check('repeat confirm cannot duplicate audit', mysql("SELECT COUNT(*) FROM st_audit WHERE action='dispatch.confirm' AND entity_id=" + quote(plan['id'])) == '1')
        for task in [patrol, delivery]:
            request('/sky/tasks/' + task + '/cancel', {'reason': PREFIX + '_reset'})
        # Competing plans for a shared aircraft: exactly one batch may win.
        first, second = new_task('race1'), new_task('race2')
        plan1, plan2 = preview([first], [scout]), preview([second], [scout])
        def race(value):
            return api(base, '/sky/dispatch/plans/' + value['id'] + '/confirm', 'POST', {'reason': PREFIX + '_race'}, admin)[1]['code']
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(race, [plan1, plan2]))
        assigned_count = mysql("SELECT COUNT(*) FROM st_task WHERE aircraft_id=" + quote(scout) + " AND status='assigned';")
        REPORT['race'] = {'codes': codes, 'assignedCount': assigned_count}
        check('concurrent plans cannot double-book aircraft', sorted(codes) == [200, 409] and assigned_count == '1')
        for task in [first, second]:
            if state(task) == 'assigned':
                request('/sky/tasks/' + task + '/cancel', {'reason': PREFIX + '_reset'})
        # Mixed stale batch must not partially apply even if the stale task comes last.
        batch1, batch2 = new_task('stale1'), new_task('stale2')
        stale_batch = preview([batch1, batch2], [cargo, scout])
        last = sorted([batch1, batch2])[-1]
        request('/sky/tasks/' + last + '/cancel', {'reason': PREFIX + '_cancel_late'})
        confirm(stale_batch, expected=409)
        other = next(value for value in [batch1, batch2] if value != last)
        check('stale task makes entire batch roll back', state(other) == 'created'
            and mysql('SELECT status FROM st_aircraft WHERE id=' + quote(cargo)) == 'idle')
        # Real flight after optimized assignment is still owned by Java state machine.
        flight = new_task('flight')
        flight_plan = preview([flight], [scout])
        confirm(flight_plan)
        request('/sky/tasks/' + flight + '/start', {'reason': PREFIX + '_flight'})
        limit = time.monotonic() + 50
        while time.monotonic() < limit and state(flight) != 'completed':
            time.sleep(1)
        check('optimized task completes through real Java simulation', state(flight) == 'completed'
            and int(mysql('SELECT COUNT(*) FROM st_track WHERE task_id=' + quote(flight))) >= 20)
        REPORT['benchmark'] = plan['result']
        # Existing user task state should be unchanged; no existing task is selected by this script.
        existing = mysql('SELECT id,status,COALESCE(aircraft_id,\'\') FROM st_task WHERE id NOT IN (' + ids(tasks) + ') ORDER BY id')
        check('existing user task assignments preserved', baseline == existing)
        REPORT['passed'] = True
    finally:
        if admin:
            for task in tasks:
                if state(task) in ('assigned', 'executing'):
                    api(base, '/sky/tasks/' + task + '/cancel', 'POST', {'reason': PREFIX + '_cleanup'}, admin)
            mysql('DROP TRIGGER IF EXISTS ' + trigger)
            # IDs originate only in this run's API responses; do not delete by broad name pattern.
            airspace_checks = mysql('SELECT id FROM st_airspace_check WHERE task_id IN (' + ids(tasks) + ');').splitlines()
            mysql(f"DELETE FROM st_track WHERE task_id IN ({ids(tasks)}); DELETE FROM st_event WHERE task_id IN ({ids(tasks)}); "
                  f"DELETE FROM st_report WHERE task_id IN ({ids(tasks)}); DELETE FROM st_logistics_order WHERE task_id IN ({ids(tasks)}); "
                  f"DELETE FROM st_audit WHERE entity_id IN ({ids(tasks + plans + stations + aircraft + airspace_checks)}); "
                  f"DELETE FROM st_traffic_check WHERE task_id IN ({ids(tasks)}); "
                  f"DELETE FROM st_airspace_check WHERE task_id IN ({ids(tasks)}); "
                  f"DELETE FROM st_dispatch_plan WHERE id IN ({ids(plans)}); DELETE FROM st_task WHERE id IN ({ids(tasks)}); "
                  f"DELETE FROM st_aircraft WHERE id IN ({ids(aircraft)}); DELETE FROM st_station WHERE id IN ({ids(stations)});")
            for user in users:
                api(base, '/system/user/' + str(user), 'DELETE', token=admin)
            REPORT['cleanup'] = {}
            for label, table, key, values in (
                ('tasks', 'st_task', 'id', tasks), ('plans', 'st_dispatch_plan', 'id', plans),
                ('aircraft', 'st_aircraft', 'id', aircraft), ('stations', 'st_station', 'id', stations),
                ('airspaceChecks', 'st_airspace_check', 'task_id', tasks),
                ('audits', 'st_audit', 'entity_id', tasks + plans + stations + aircraft + airspace_checks)):
                REPORT['cleanup'][label] = int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({ids(values)});'))
            REPORT['cleanup']['activeUsers'] = int(mysql(f"SELECT COUNT(*) FROM sys_user WHERE user_id IN ({','.join(map(str,users)) or '-1'}) AND del_flag='0';"))
            REPORT['cleanup']['triggers'] = int(mysql("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME=" + quote(trigger) + ';'))
            if any(REPORT['cleanup'].values()):
                REPORT['passed'] = False
            for token in reversed(tokens):
                api(base, '/logout', 'POST', token=token)
        (ROOT / 'logs/dispatch-verification.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Report: ruoyi/logs/dispatch-verification.json', flush=True)
    assert REPORT['passed'], 'Dispatch acceptance failed'


if __name__ == '__main__':
    main()
