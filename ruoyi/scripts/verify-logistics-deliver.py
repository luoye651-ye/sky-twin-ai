"""Local delivery acceptance using isolated fixtures and real Java simulation.

Never delivers an existing user's order. A uniquely scoped temporary audit trigger
tests transaction rollback; it is removed in finally together with this run's data.
Passwords, captcha answers and tokens are never printed or saved in the report.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('delivery_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
helpers = listing.helpers
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
PREFIX = 'ld_' + uuid.uuid4().hex[:12]
TRIGGER = 'verify_' + PREFIX
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': [], 'cases': []}


def check(name, condition):
    assert condition, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def sql_ids(values):
    return ','.join(quote(value) for value in values) if values else "''"


def order_state(order_id):
    raw = mysql(f"""
        SELECT JSON_OBJECT('status',o.status,'deliveredBy',o.delivered_by,
          'deliveredAt',DATE_FORMAT(o.delivered_at,'%Y-%m-%d %H:%i:%s.%f'),
          'deliveryAudits',(SELECT COUNT(*) FROM st_audit
                            WHERE entity_id=o.id AND action='order.deliver'))
        FROM st_logistics_order o WHERE o.id={quote(order_id)};
    """)
    if not raw:
        exists = mysql('SELECT COUNT(*) FROM st_logistics_order WHERE id=' + quote(order_id) + ';')
        raise AssertionError('Verification order-state query returned empty output; matching rows=' + exists)
    return json.loads(raw)


def existing_orders():
    return mysql(f"""
        SELECT id,status,COALESCE(delivered_by,''),COALESCE(CAST(delivered_at AS CHAR),'')
        FROM st_logistics_order WHERE LEFT(cargo_name,{len(PREFIX)})<>{quote(PREFIX)}
        ORDER BY id;
    """)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:5173/java-api')
    parser.add_argument('--workflow', action='store_true', help='Also verify order dispatch/detail, deadline guards and restart recovery')
    parser.add_argument('--ui', action='store_true', help='Also run an isolated real browser workflow using this run\'s fixtures')
    parser.add_argument('--ui-only', action='store_true', help='Run only isolated browser acceptance and cleanup')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    workflow = args.workflow or args.ui or args.ui_only
    REPORT['workflow'] = workflow
    assert base in ('http://127.0.0.1:8081', 'http://127.0.0.1:5173/java-api',
                    'http://127.0.0.1:5174/dev-api'), 'Dedicated localhost endpoints only'
    REPORT['baseUrl'] = base
    REPORT['startedAtLocal'] = datetime.now().astimezone().isoformat()
    tokens, stations, aircraft, orders, tasks, users = [], [], [], [], [], []
    admin = None
    baseline = None

    def create_order(suffix):
        _, result = api(base, '/sky/logistics/orders', 'POST', {
            'cargoName': PREFIX + '_' + suffix, 'weight': 2.5,
            'startStationId': stations[0], 'endStationId': stations[1],
            'deadlineMinutes': 10, 'reason': PREFIX + '_' + suffix,
        }, admin)
        assert result.get('code') == 200, 'Test order creation failed'
        order_id = result['data']
        orders.append(order_id)
        task_id = mysql('SELECT task_id FROM st_logistics_order WHERE id=' + quote(order_id) + ';')
        tasks.append(task_id)
        return order_id, task_id

    def rejected(name, order_id, expected, body=None, token=None):
        before = order_state(order_id)
        http, result = api(base, '/sky/logistics/orders/' + order_id + '/deliver', 'POST',
                           body if body is not None else {'reason': PREFIX + '_' + name}, token)
        after = order_state(order_id)
        REPORT['cases'].append({'name': name, 'httpStatus': http,
                                'businessCode': result.get('code'), 'before': before, 'after': after})
        check(name + ': rejected without order/audit changes', result.get('code') == expected and before == after)

    def rejected_dispatch(name, order_id, task_id, action, plane, token, expected=409):
        before = mysql(f"SELECT status,COALESCE(aircraft_id,''),reason FROM st_task WHERE id={quote(task_id)};")
        audits = mysql(f"SELECT COUNT(*) FROM st_audit WHERE entity_id={quote(task_id)};")
        for path in ('/sky/logistics/orders/' + order_id, '/sky/tasks/' + task_id):
            _, result = api(base, path + '/' + action, 'POST',
                            {'aircraftId': plane, 'reason': PREFIX + '_guard'}, token)
            check(name + ' via ' + ('order' if 'orders' in path else 'task'), result.get('code') == expected)
        after = mysql(f"SELECT status,COALESCE(aircraft_id,''),reason FROM st_task WHERE id={quote(task_id)};")
        check(name + ' preserves task and audit', before == after and audits == mysql(
            f"SELECT COUNT(*) FROM st_audit WHERE entity_id={quote(task_id)};"))

    def create_viewer():
        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(role['roleId'] for role in roles['rows'] if role['roleKey'] == 'sky_viewer')
        username, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'A!7'
        _, result = api(base, '/system/user', 'POST', {
            'userName': username, 'nickName': username, 'password': password,
            'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [role], 'postIds': [],
        }, admin)
        assert result.get('code') == 200, 'Temporary viewer creation failed'
        _, found = api(base, '/system/user/list?userName=' + username, token=admin)
        users.append(next(user['userId'] for user in found['rows'] if user['userName'] == username))
        token = listing.login_as(base, username, password)
        tokens.append(token)
        return token

    def run_browser(viewer):
        environment = dict(os.environ,
            SKYTWIN_UI_PREFIX=PREFIX, SKYTWIN_UI_ADMIN_TOKEN=admin, SKYTWIN_UI_VIEWER_TOKEN=viewer)
        run = subprocess.run([helpers.RUNTIME['NodeExecutable'], str(ROOT / 'scripts/verify-logistics-ui.mjs')],
            cwd=ROOT.parent, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=240)
        print(run.stdout, end='', flush=True)
        if run.returncode:
            print(run.stderr, flush=True)
        assert run.returncode == 0, 'Isolated browser delivery workflow failed'
        ui_report = json.loads((ROOT / 'logs/logistics-ui-verification.json').read_text(encoding='utf-8'))
        check('real browser workflow and viewer controls pass', ui_report.get('passed') is True)
        REPORT['uiChecks'] = ui_report['checks']

    try:
        check('dedicated database port is 3307', mysql('SELECT @@port;') == '3307')
        baseline = existing_orders()
        admin = helpers.login(base)
        tokens.append(admin)
        for index in range(2):
            _, result = api(base, '/sky/stations', 'POST', {
                'name': PREFIX + '_station_' + str(index), 'type': 'logistics',
                'longitude': 120.19 + .003 * index, 'latitude': 30.215, 'status': 'enabled',
            }, admin)
            assert result.get('code') == 200, 'Test station creation failed'
            stations.append(result['data'])
        _, result = api(base, '/sky/aircraft', 'POST', {
            'name': PREFIX + '_aircraft', 'type': 'cargo', 'model': 'delivery-acceptance-simulator',
            'longitude': 120.19, 'latitude': 30.215, 'battery': 100,
            'payloadCapacity': 20, 'seats': 0,
        }, admin)
        assert result.get('code') == 200, 'Test aircraft creation failed'
        aircraft.append(result['data'])

        if args.ui_only:
            create_order('guards')
            run_browser(create_viewer())
            REPORT['passed'] = True
            print('PASS: isolated logistics UI acceptance completed', flush=True)
            return

        if workflow:
            guard_order, guard_task = create_order('guards')
            for suffix, kind, battery, payload in (
                ('ordinary', 'drone', 100, 20), ('low_battery', 'cargo', 10, 20), ('under_capacity', 'cargo', 100, 1)):
                _, created = api(base, '/sky/aircraft', 'POST', {
                    'name': PREFIX + '_' + suffix, 'type': kind, 'model': 'workflow-guard-test',
                    'longitude': 120.19, 'latitude': 30.215, 'battery': battery,
                    'payloadCapacity': payload, 'seats': 0,
                }, admin)
                assert created.get('code') == 200, 'Guard aircraft creation failed'
                aircraft.append(created['data'])
                rejected_dispatch(suffix + ' rejected', guard_order, guard_task, 'assign', created['data'], admin)
            for suffix, clock in (('expired', 'DATE_SUB(NOW(3),INTERVAL 1 MINUTE)'),
                                  ('insufficient_time', 'DATE_ADD(NOW(3),INTERVAL 5 SECOND)')):
                short_order, short_task = create_order(suffix)
                mysql(f'UPDATE st_logistics_order SET deadline_at={clock} WHERE id={quote(short_order)};')
                rejected_dispatch(suffix + ' rejected', short_order, short_task, 'assign', aircraft[0], admin)
            late_order, late_task = create_order('late_start')
            _, assigned = api(base, '/sky/logistics/orders/' + late_order + '/assign', 'POST',
                              {'aircraftId': aircraft[0], 'reason': PREFIX + '_late_assign'}, admin)
            assert assigned.get('code') == 200, 'Assign before expiry failed'
            mysql(f'UPDATE st_logistics_order SET deadline_at=DATE_SUB(NOW(3),INTERVAL 1 MINUTE) WHERE id={quote(late_order)};')
            rejected_dispatch('deadline rechecked on start', late_order, late_task, 'start', aircraft[0], admin)
            _, cancelled = api(base, '/sky/logistics/orders/' + late_order + '/cancel', 'POST',
                               {'reason': PREFIX + '_release_after_expiry'}, admin)
            check('order cancellation releases its aircraft', cancelled.get('code') == 200 and mysql(
                'SELECT status FROM st_aircraft WHERE id=' + quote(aircraft[0]) + ';') == 'idle')

        order_id, task_id = create_order('flight')
        rejected('created task cannot deliver', order_id, 409, token=admin)
        for action in ('assign', 'start'):
            endpoint = '/sky/logistics/orders/' + order_id if workflow else '/sky/tasks/' + task_id
            _, result = api(base, endpoint + '/' + action, 'POST',
                            {'aircraftId': aircraft[0], 'reason': PREFIX + '_' + action}, admin)
            assert result.get('code') == 200, 'Test task action failed: ' + action
            rejected(('assigned' if action == 'assign' else 'executing') + ' task cannot deliver',
                     order_id, 409, token=admin)
            if workflow and action == 'assign':
                rival_order, rival_task = create_order('contested')
                rejected_dispatch('occupied aircraft rejected', rival_order, rival_task, 'assign', aircraft[0], admin)
            if workflow and action == 'start':
                _, repeated_start = api(base, endpoint + '/start', 'POST', {'reason': PREFIX + '_repeated_start'}, admin)
                check('repeated start rejected', repeated_start.get('code') == 409)

        print('INFO: waiting for the real Java simulator to complete its test flight', flush=True)
        deadline = time.monotonic() + 65
        while True:
            status = mysql('SELECT status FROM st_task WHERE id=' + quote(task_id) + ';')
            if status == 'completed':
                break
            assert status == 'executing', 'Test flight ended unexpectedly: ' + status
            assert time.monotonic() < deadline, 'Test flight completion timeout'
            time.sleep(1)
        _, tracks = api(base, '/sky/tasks/' + task_id + '/tracks', token=admin)
        check('server simulator completed flight and persisted tracks',
              tracks.get('code') == 200 and len(tracks.get('data', [])) > 1)
        REPORT['testFlightTrackCount'] = len(tracks['data'])
        if workflow:
            _, detail = api(base, '/sky/logistics/orders/' + order_id, token=admin)
            _, order_tracks = api(base, '/sky/logistics/orders/' + order_id + '/tracks', token=admin)
            check('order detail includes aircraft and both operation histories', detail.get('code') == 200
                  and detail['data']['aircraftId'] == aircraft[0] and len(detail['data']['audit']) >= 5)
            check('order track endpoint resolves the correct task', order_tracks.get('code') == 200
                  and [point['id'] for point in order_tracks['data']] == [point['id'] for point in tracks['data']])

        rejected('empty reason', order_id, 500, {'reason': ''}, admin)
        rejected('blank reason', order_id, 500, {'reason': '   '}, admin)
        rejected('reason over 500 characters', order_id, 500, {'reason': 'x' * 501}, admin)
        rejected('anonymous cannot deliver', order_id, 401)
        for wrong_id in (PREFIX + '_missing', task_id):
            _, result = api(base, '/sky/logistics/orders/' + wrong_id + '/deliver', 'POST',
                            {'reason': PREFIX + '_wrong_id'}, admin)
            check('unknown order rejected: ' + ('task id' if wrong_id == task_id else 'missing id'),
                  result.get('code') == 404)

        for state, action in (('cancelled', 'cancel'), ('failed', 'fail')):
            other_order, other_task = create_order(state)
            _, result = api(base, '/sky/tasks/' + other_task + '/' + action, 'POST',
                            {'reason': PREFIX + '_' + state}, admin)
            assert result.get('code') == 200, 'Test terminal action failed'
            rejected(state + ' task cannot deliver', other_order, 409, token=admin)

        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        viewer_role = next(role['roleId'] for role in roles['rows'] if role['roleKey'] == 'sky_viewer')
        username, password = PREFIX + 'v', uuid.uuid4().hex[:12] + 'A!7'
        _, result = api(base, '/system/user', 'POST', {
            'userName': username, 'nickName': username, 'password': password,
            'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [viewer_role], 'postIds': [],
        }, admin)
        assert result.get('code') == 200, 'Temporary viewer creation failed'
        _, found = api(base, '/system/user/list?userName=' + username, token=admin)
        users.append(next(user['userId'] for user in found['rows'] if user['userName'] == username))
        viewer = listing.login_as(base, username, password)
        tokens.append(viewer)
        _, result = api(base, '/sky/logistics/orders', token=viewer)
        check('viewer can read orders', result.get('code') == 200)
        rejected('viewer cannot deliver', order_id, 403, token=viewer)
        if workflow:
            for suffix in ('', '/tracks'):
                _, readable = api(base, '/sky/logistics/orders/' + order_id + suffix, token=viewer)
                check('viewer can read order ' + ('detail' if not suffix else 'tracks'), readable.get('code') == 200)
                _, denied = api(base, '/sky/logistics/orders/' + order_id + suffix)
                check('anonymous cannot read order ' + ('detail' if not suffix else 'tracks'), denied.get('code') == 401)
            rejected_dispatch('viewer cannot dispatch', guard_order, guard_task, 'assign', aircraft[0], viewer, 403)

        # Fail AFTER order UPDATE, exactly on this test's audit INSERT.
        fault_reason = PREFIX + '_audit_fault'
        mysql(f"""
            DELIMITER //
            CREATE TRIGGER {TRIGGER} BEFORE INSERT ON st_audit FOR EACH ROW
            BEGIN
              IF NEW.entity_id={quote(order_id)} AND NEW.action='order.deliver'
                 AND NEW.reason={quote(fault_reason)} THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='VERIFY_DELIVERY_AUDIT_FAILURE';
              END IF;
            END//
            DELIMITER ;
        """)
        rejected('late audit failure rolls back delivered fields', order_id, 500,
                 {'reason': fault_reason}, admin)
        mysql('DROP TRIGGER ' + TRIGGER + ';')

        # Two simultaneous confirmations: exactly one success and one business rejection.
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(api, base, '/sky/logistics/orders/' + order_id + '/deliver',
                       'POST', {'reason': PREFIX + '_confirm_' + str(index), 'actor': 'spoofed-user'}, admin)
                       for index in range(2)]
            responses = [future.result() for future in futures]
        codes = sorted(result.get('code') for _, result in responses)
        after = order_state(order_id)
        check('concurrent confirmations yield one success and one 409', codes == [200, 409])
        check('delivery records server time, authenticated actor and one audit',
              after['status'] == 'delivered' and after['deliveredBy'] == 'admin'
              and bool(after['deliveredAt']) and after['deliveryAudits'] == 1)
        REPORT['deliveredOrder'] = after
        REPORT['concurrentBusinessCodes'] = codes
        rejected('repeated confirmation preserves time and audit', order_id, 409, token=admin)
        _, result = api(base, '/sky/logistics/orders', token=admin)
        saved = next(row for row in result['data'] if row['id'] == order_id)
        check('GET exposes delivered order and completed task separately',
              saved['status'] == 'delivered' and saved['taskStatus'] == 'completed'
              and saved['deliveredBy'] == 'admin' and bool(saved['deliveredAt']))
        if workflow:
            for action in ('assign', 'start', 'cancel'):
                _, denied = api(base, '/sky/logistics/orders/' + order_id + '/' + action, 'POST',
                                {'aircraftId': aircraft[0], 'reason': PREFIX + '_after_delivered'}, admin)
                check('delivered order rejects ' + action, denied.get('code') == 409)
            for service_action in ('stop', 'start'):
                command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                           str(ROOT / 'scripts' / (service_action + '.ps1')), '-Service', 'backend']
                # Windows background descendants may retain inherited PIPE handles.
                # Redirect to a file so completion follows PowerShell, not pipe EOF.
                with (ROOT / 'logs' / ('workflow-restart-' + service_action + '.log')).open('w', encoding='utf-8') as output:
                    run = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, text=True, timeout=110)
                assert run.returncode == 0, 'Backend ' + service_action + ' during recovery acceptance failed'
            _, recovered = api(base, '/sky/logistics/orders/' + order_id, token=admin)
            _, recovered_tracks = api(base, '/sky/logistics/orders/' + order_id + '/tracks', token=admin)
            check('Java restart preserves order, task, delivery audit and tracks',
                  recovered.get('code') == 200 and recovered['data']['status'] == 'delivered'
                  and recovered['data']['taskStatus'] == 'completed'
                  and len([a for a in recovered['data']['audit'] if a['action'] == 'order.deliver']) == 1
                  and recovered_tracks.get('code') == 200
                  and len(recovered_tracks['data']) == len(tracks['data'])
                  and order_state(order_id) == after)
        if args.ui:
            run_browser(viewer)
        REPORT['passed'] = True
    except Exception as error:
        REPORT['error'] = str(error)
        raise
    finally:
        try:
            mysql('DROP TRIGGER IF EXISTS ' + TRIGGER + ';')
            # Find this run's committed orders even if an HTTP response was interrupted.
            own = mysql(f'SELECT id,task_id FROM st_logistics_order WHERE LEFT(cargo_name,{len(PREFIX)})={quote(PREFIX)};')
            for line in own.splitlines():
                if line:
                    order_id, task_id = line.split('\t')
                    if order_id not in orders:
                        orders.append(order_id)
                    if task_id not in tasks:
                        tasks.append(task_id)
            # Also recover resources created just before a failed HTTP response.
            stations = mysql(f'SELECT id FROM st_station WHERE LEFT(name,{len(PREFIX)})={quote(PREFIX)};').splitlines()
            aircraft = mysql(f'SELECT id FROM st_aircraft WHERE LEFT(name,{len(PREFIX)})={quote(PREFIX)};').splitlines()
            airspace_checks = mysql(f'SELECT id FROM st_airspace_check WHERE task_id IN ({sql_ids(tasks)});').splitlines()
            entities = orders + tasks + stations + aircraft + airspace_checks
            mysql(f"""
                START TRANSACTION;
                SELECT id FROM st_task WHERE id IN ({sql_ids(tasks)}) ORDER BY id FOR UPDATE;
                DELETE FROM st_logistics_order WHERE id IN ({sql_ids(orders)});
                DELETE FROM st_report WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_event WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_track WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_audit WHERE entity_id IN ({sql_ids(entities)});
                DELETE FROM st_traffic_check WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_airspace_check WHERE task_id IN ({sql_ids(tasks)});
                DELETE FROM st_task WHERE id IN ({sql_ids(tasks)});
                DELETE FROM st_aircraft WHERE id IN ({sql_ids(aircraft)});
                DELETE FROM st_station WHERE id IN ({sql_ids(stations)});
                COMMIT;
            """)
            if admin:
                # Recover a temporary account if its create response failed.
                own_users = mysql(f"SELECT user_id FROM sys_user WHERE LEFT(user_name,{len(PREFIX)})={quote(PREFIX)} AND del_flag='0';")
                for user_id in own_users.splitlines():
                    _, result = api(base, '/system/user/' + user_id, 'DELETE', token=admin)
                    assert result.get('code') == 200, 'Temporary viewer cleanup failed'
            remaining = json.loads(mysql(f"""
                SELECT JSON_OBJECT(
                  'orders',(SELECT COUNT(*) FROM st_logistics_order WHERE id IN ({sql_ids(orders)})),
                  'tasks',(SELECT COUNT(*) FROM st_task WHERE id IN ({sql_ids(tasks)})),
                  'tracks',(SELECT COUNT(*) FROM st_track WHERE task_id IN ({sql_ids(tasks)})),
                  'reports',(SELECT COUNT(*) FROM st_report WHERE task_id IN ({sql_ids(tasks)})),
                  'events',(SELECT COUNT(*) FROM st_event WHERE task_id IN ({sql_ids(tasks)})),
                  'airspaceChecks',(SELECT COUNT(*) FROM st_airspace_check WHERE task_id IN ({sql_ids(tasks)})),
                  'businessAudit',(SELECT COUNT(*) FROM st_audit WHERE entity_id IN ({sql_ids(entities)})),
                  'stations',(SELECT COUNT(*) FROM st_station WHERE id IN ({sql_ids(stations)})),
                  'aircraft',(SELECT COUNT(*) FROM st_aircraft WHERE id IN ({sql_ids(aircraft)})),
                  'activeTestUsers',(SELECT COUNT(*) FROM sys_user WHERE LEFT(user_name,{len(PREFIX)})={quote(PREFIX)} AND del_flag='0'),
                  'triggers',(SELECT COUNT(*) FROM information_schema.TRIGGERS
                    WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME={quote(TRIGGER)})
                );
            """))
            REPORT['cleanup'] = remaining
            check('own test data, viewer access and trigger cleaned', all(value == 0 for value in remaining.values()))
            if baseline is not None:
                check('existing user orders retain their original delivery state', baseline == existing_orders())
        except Exception:
            REPORT['passed'] = False
            REPORT['cleanupFailed'] = True
            raise
        finally:
            for token in reversed(tokens):
                try:
                    api(base, '/logout', 'POST', token=token)
                except Exception:
                    pass
            REPORT['finishedAtLocal'] = datetime.now().astimezone().isoformat()
            report_name = 'logistics-ui-fixtures-verification.json' if args.ui_only else (
                'logistics-workflow-verification.json' if workflow else 'logistics-deliver-verification.json')
            (ROOT / 'logs' / report_name).write_text(
                json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: logistics delivery acceptance completed', flush=True)


if __name__ == '__main__':
    main()
