"""Real local GET acceptance: joins, naming, ordering, read-only access.

Imports HTTP/SQL/login helpers without running creation acceptance or its trigger.
Creates uniquely named fixtures and two temporary permission-test accounts.
Removes only this run's own fixtures/accounts; never prints credentials or JWTs.
"""
import argparse
import importlib.util
import json
import pathlib
import uuid
from datetime import datetime


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('creation_helpers', ROOT / 'scripts/verify-logistics-create.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
PREFIX = 'lq_' + uuid.uuid4().hex[:10]
REPORT = {'testPrefix': PREFIX, 'passed': False, 'checks': []}


def check(name, condition):
    assert condition, name
    REPORT['checks'].append(name)
    print('PASS: ' + name, flush=True)


def login_as(base, username, password):
    # Use the same local-captcha helper for a separately scoped temporary account.
    original_api = helpers.api

    def account_api(url, path, method='GET', body=None, token=None):
        if path == '/login':
            body = dict(body, username=username, password=password)
        return original_api(url, path, method, body, token)

    helpers.api = account_api
    try:
        return helpers.login(base)
    finally:
        helpers.api = original_api


def local_counts(station_ids=()):
    size, prefix = len(PREFIX), quote(PREFIX)
    station_audit = ' OR entity_id IN (' + ','.join(quote(value) for value in station_ids) + ')' if station_ids else ''
    return mysql(f"""
        SELECT JSON_OBJECT(
          'orders',(SELECT COUNT(*) FROM st_logistics_order WHERE LEFT(cargo_name,{size})={prefix}),
          'tasks',(SELECT COUNT(*) FROM st_task WHERE LEFT(reason,{size})={prefix}),
          'audit',(SELECT COUNT(*) FROM st_audit WHERE LEFT(reason,{size})={prefix}{station_audit}),
          'stations',(SELECT COUNT(*) FROM st_station WHERE LEFT(name,{size})={prefix}),
          'users',(SELECT COUNT(*) FROM sys_user WHERE LEFT(user_name,{size})={prefix} AND del_flag='0')
        );
    """)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:5174/dev-api')
    base = parser.parse_args().base_url.rstrip('/')
    assert base in ('http://127.0.0.1:8081', 'http://127.0.0.1:5174/dev-api',
                    'http://127.0.0.1:5173/java-api'), 'Only dedicated localhost services are supported'
    REPORT['baseUrl'] = base
    REPORT['startedAtLocal'] = datetime.now().astimezone().isoformat()
    admin = None
    tokens, stations, order_ids, user_ids = [], [], [], []
    REPORT['testStationIds'] = stations
    try:
        check('dedicated MySQL port is 3307', mysql('SELECT @@port;') == '3307')
        _, denied = api(base, '/sky/logistics/orders')
        check('anonymous request rejected', denied.get('code') == 401)
        admin = helpers.login(base)
        tokens.append(admin)
        _, baseline = api(base, '/sky/logistics/orders', token=admin)
        check('admin receives an array in data', baseline.get('code') == 200 and isinstance(baseline.get('data'), list))
        total_before = int(mysql('SELECT COUNT(*) FROM st_logistics_order;'))
        if total_before == 0:
            check('empty database returns data=[]', baseline['data'] == [])
        else:
            REPORT['emptyDatabaseCheck'] = 'Not run: existing orders preserved'

        for index in range(2):
            _, response = api(base, '/sky/stations', 'POST', {
                'name': PREFIX + '_station_' + str(index), 'type': 'logistics',
                'longitude': 120.19 + .003 * index, 'latitude': 30.215, 'status': 'enabled',
            }, admin)
            assert response.get('code') == 200, 'Station fixture creation failed'
            stations.append(response['data'])
        for index in range(2):
            _, response = api(base, '/sky/logistics/orders', 'POST', {
                'cargoName': PREFIX + '_cargo_' + str(index), 'weight': 2.5 + index,
                'startStationId': stations[0], 'endStationId': stations[1],
                'deadlineMinutes': 10, 'reason': PREFIX + '_order_' + str(index),
            }, admin)
            assert response.get('code') == 200, 'Order fixture creation failed'
            order_ids.append(response['data'])

        # Give these two fixtures the same date to check the id tie-breaker too.
        own_ids = ','.join(quote(value) for value in order_ids)
        mysql(f'UPDATE st_logistics_order SET created_time=NOW(3) WHERE id IN ({own_ids});')
        before_get = local_counts(stations)
        _, response = api(base, '/sky/logistics/orders', token=admin)
        assert response.get('code') == 200, 'GET failed'
        rows = response['data']
        expected_ids = mysql('SELECT id FROM st_logistics_order ORDER BY created_time DESC,id DESC LIMIT 200;').splitlines()
        check('list order and count match SQL including same-time id ordering', [row['id'] for row in rows] == expected_ids)
        own_rows = {row['id']: row for row in rows if row['id'] in order_ids}
        check('both created orders are returned', len(own_rows) == 2)
        required = {'id', 'cargoName', 'weight', 'deadlineAt', 'taskId', 'status',
                    'createdBy', 'createdTime', 'taskStatus', 'progress',
                    'startStationName', 'endStationName'}
        check('response fields use the expected camelCase names',
              all(required.issubset(row) and not any('_' in key for key in row) for row in own_rows.values()))
        check('JOIN returns correct station names and initial task state', all(
            row['startStationName'] == PREFIX + '_station_0'
            and row['endStationName'] == PREFIX + '_station_1'
            and row['taskStatus'] == 'created' and row['progress'] == 0
            for row in own_rows.values()))
        check('GET does not mutate business rows', local_counts(stations) == before_get)

        task_id = own_rows[order_ids[0]]['taskId']
        _, cancelled = api(base, '/sky/tasks/' + task_id + '/cancel', 'POST',
                           {'reason': PREFIX + '_cancel'}, admin)
        assert cancelled.get('code') == 200, 'Cancel test-only task failed'
        _, updated = api(base, '/sky/logistics/orders', token=admin)
        changed = next(row for row in updated['data'] if row['id'] == order_ids[0])
        check('taskStatus reflects task change while order status remains separate',
              changed['taskStatus'] == 'cancelled' and changed['status'] == 'created')
        REPORT['sampleOrder'] = changed

        _, roles = api(base, '/system/role/list?pageNum=1&pageSize=50', token=admin)
        viewer_role = next(role['roleId'] for role in roles['rows'] if role['roleKey'] == 'sky_viewer')
        for suffix, role_ids in (('v', [viewer_role]), ('n', [])):
            username = PREFIX + suffix
            password = uuid.uuid4().hex[:12] + 'A!7'
            _, created = api(base, '/system/user', 'POST', {
                'userName': username, 'nickName': username, 'password': password,
                'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': role_ids, 'postIds': [],
            }, admin)
            assert created.get('code') == 200, 'Create temporary permission account failed'
            _, found = api(base, '/system/user/list?userName=' + username, token=admin)
            user_ids.append(next(user['userId'] for user in found['rows'] if user['userName'] == username))
            token = login_as(base, username, password)
            tokens.append(token)
            _, result = api(base, '/sky/logistics/orders', token=token)
            if suffix == 'v':
                check('viewer with sky:read can query orders', result.get('code') == 200)
                _, forbidden_create = api(base, '/sky/logistics/orders', 'POST', {
                    'cargoName': PREFIX + '_forbidden', 'weight': 2,
                    'startStationId': stations[0], 'endStationId': stations[1],
                    'deadlineMinutes': 10, 'reason': PREFIX + '_forbidden',
                }, token)
                check('viewer cannot create an order', forbidden_create.get('code') == 403)
            else:
                check('signed-in account without sky:read is rejected', result.get('code') == 403)
        REPORT['passed'] = True
    finally:
        try:
            size, prefix = len(PREFIX), quote(PREFIX)
            # Only tasks bearing this run's unique reason prefix are removed.
            mysql(f"""
                START TRANSACTION;
                DELETE o FROM st_logistics_order o JOIN st_task t ON t.id=o.task_id WHERE LEFT(t.reason,{size})={prefix};
                DELETE r FROM st_report r JOIN st_task t ON t.id=r.task_id WHERE LEFT(t.reason,{size})={prefix};
                DELETE e FROM st_event e JOIN st_task t ON t.id=e.task_id WHERE LEFT(t.reason,{size})={prefix};
                DELETE p FROM st_track p JOIN st_task t ON t.id=p.task_id WHERE LEFT(t.reason,{size})={prefix};
                DELETE a FROM st_audit a LEFT JOIN st_station s ON s.id=a.entity_id
                  WHERE LEFT(a.reason,{size})={prefix} OR LEFT(s.name,{size})={prefix};
                DELETE FROM st_task WHERE LEFT(reason,{size})={prefix};
                DELETE FROM st_station WHERE LEFT(name,{size})={prefix};
                COMMIT;
            """)
            if admin:
                for user_id in user_ids:
                    _, result = api(base, '/system/user/' + str(user_id), 'DELETE', token=admin)
                    assert result.get('code') == 200, 'Temporary account cleanup failed'
            REPORT['cleanup'] = json.loads(local_counts(stations))
            assert all(value == 0 for value in REPORT['cleanup'].values()), REPORT['cleanup']
            print('PASS: own test business rows and temporary account access cleaned', flush=True)
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
            (ROOT / 'logs/logistics-list-verification.json').write_text(
                json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: logistics list acceptance completed', flush=True)


if __name__ == '__main__':
    main()
