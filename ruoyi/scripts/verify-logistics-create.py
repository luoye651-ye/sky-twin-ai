"""Verify real logistics HTTP requests and database effects on local 3307 only.

Uses uniquely marked data, a narrowly guarded temporary trigger for a late-write
failure, and finally cleanup. Never prints passwords, captcha answers or JWTs.
This is an integration test; the trigger is not application business logic.
"""
import argparse
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = json.loads((ROOT / 'config/runtime.local.json').read_text(encoding='utf-8-sig'))
SECRETS = json.loads((ROOT / 'config/local-secrets.json').read_text(encoding='utf-8-sig'))
PREFIX = 'lc_' + uuid.uuid4().hex[:12]
TRIGGER = 'verify_lc_' + uuid.uuid4().hex[:12]
FAULT = 'VERIFY_ORDER_WRITE_' + uuid.uuid4().hex[:12]
REPORT = {'testPrefix': PREFIX, 'cases': [], 'passed': False}


def sql_value(value):
    return "'" + str(value).replace('\\', '\\\\').replace("'", "''") + "'"


def mysql(sql):
    process = subprocess.run([
        str(pathlib.Path(RUNTIME['MySqlBin']) / 'mysql.exe'),
        '--defaults-file=' + str(ROOT / 'config/mysql-root.cnf'),
        '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi',
        '--batch', '--skip-column-names',
    ], input=sql, text=True, encoding='utf-8', capture_output=True)
    if process.returncode:
        raise RuntimeError('Local verification SQL failed: ' + process.stderr.strip())
    return process.stdout.strip()


def api(base, path, method='GET', body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = json.dumps(body).encode('utf-8') if body is not None else None
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read().decode('utf-8'))


def login(base):
    _, captcha = api(base, '/captchaImage')
    assert captcha['code'] == 200, 'Captcha endpoint unavailable'
    code = ''
    if captcha.get('captchaEnabled'):
        environment = dict(os.environ, REDISCLI_AUTH=SECRETS['RedisPassword'])
        code = subprocess.check_output([
            str(pathlib.Path(RUNTIME['RedisBin']) / 'redis-cli.exe'),
            '-h', '127.0.0.1', '-p', str(RUNTIME.get('RedisPort', 16380)), '--raw', 'get',
            'captcha_codes:' + captcha['uuid'],
        ], env=environment, text=True, encoding='utf-8').strip().strip('"')
    _, result = api(base, '/login', 'POST', {
        'username': 'admin', 'password': os.environ.get('SKYTWIN_TEST_PASSWORD', 'admin123'),
        'uuid': captcha.get('uuid'), 'code': code,
    })
    assert result.get('code') == 200, 'Local verification account login failed'
    return result['token']


def counts(marker):
    quoted = sql_value(marker)
    return json.loads(mysql(f"""
        SELECT JSON_OBJECT(
          'orders',(SELECT COUNT(*) FROM st_logistics_order o JOIN st_task t
                    ON t.id=o.task_id WHERE t.reason={quoted}),
          'tasks',(SELECT COUNT(*) FROM st_task WHERE reason={quoted}),
          'audit',(SELECT COUNT(*) FROM st_audit WHERE reason={quoted})
        );
    """))


def all_test_counts(station_ids=()):
    prefix, size = sql_value(PREFIX), len(PREFIX)
    station_audit = ' OR entity_id IN (' + ','.join(sql_value(value) for value in station_ids) + ')' if station_ids else ''
    return json.loads(mysql(f"""
        SELECT JSON_OBJECT(
          'orders',(SELECT COUNT(*) FROM st_logistics_order WHERE LEFT(cargo_name,{size})={prefix}),
          'tasks',(SELECT COUNT(*) FROM st_task WHERE LEFT(reason,{size})={prefix}),
          'audit',(SELECT COUNT(*) FROM st_audit WHERE LEFT(reason,{size})={prefix}{station_audit}),
          'stations',(SELECT COUNT(*) FROM st_station WHERE LEFT(name,{size})={prefix}),
          'triggers',(SELECT COUNT(*) FROM information_schema.TRIGGERS
             WHERE TRIGGER_SCHEMA='sky_twin_ruoyi' AND TRIGGER_NAME={sql_value(TRIGGER)})
        );
    """))


def check_case(base, token, case_name, body, expected, message):
    before = counts(body['reason'])
    assert before == {'orders': 0, 'tasks': 0, 'audit': 0}, before
    http_status, result = api(base, '/sky/logistics/orders', 'POST', body, token)
    after = counts(body['reason'])
    case = {'name': case_name, 'request': body, 'httpStatus': http_status,
            'businessCode': result.get('code'), 'message': result.get('msg'),
            'before': before, 'after': after}
    REPORT['cases'].append(case)
    assert result.get('code') == expected, (case_name, result.get('code'), result.get('msg'))
    assert message in result.get('msg', ''), (case_name, result.get('msg'))
    assert after == {'orders': 0, 'tasks': 0, 'audit': 0}, (case_name, after)
    case['passed'] = True
    print(f'PASS: {case_name}; HTTP={http_status}, code={expected}; no order/task/business-audit residue', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:5174/dev-api')
    base = parser.parse_args().base_url.rstrip('/')
    # The test reads local secrets and must never send them to a remote server.
    assert base in ('http://127.0.0.1:8081', 'http://127.0.0.1:5174/dev-api',
                    'http://127.0.0.1:5173/java-api'), 'Only the dedicated local deployment is supported'
    REPORT['baseUrl'] = base
    REPORT['startedAtLocal'] = datetime.now().astimezone().isoformat()
    token = None
    stations = []
    REPORT['testStationIds'] = stations
    trigger_created = False
    try:
        # Refuse to test against a different database endpoint.
        assert mysql('SELECT @@port;') == '3307', 'Not the dedicated project MySQL'
        for table in ('st_logistics_order', 'st_task', 'st_audit'):
            assert mysql(f"SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='sky_twin_ruoyi' AND TABLE_NAME={sql_value(table)};") == 'InnoDB', table
        token = login(base)
        for index in range(2):
            _, created = api(base, '/sky/stations', 'POST', {
                'name': PREFIX + '_station_' + str(index),
                'type': 'takeoff' if index == 0 else 'logistics',
                'longitude': 120.19 + .003 * index, 'latitude': 30.215,
                'status': 'enabled',
            }, token)
            assert created.get('code') == 200 and created.get('data'), 'Create isolated station failed'
            stations.append(created['data'])

        def payload(case_name, **changes):
            body = {'cargoName': PREFIX + '_' + case_name, 'weight': 2.5,
                    'startStationId': stations[0], 'endStationId': stations[1],
                    'deadlineMinutes': 10, 'reason': PREFIX + '_' + case_name}
            body.update(changes)
            return body

        normal = payload('normal')
        http_status, result = api(base, '/sky/logistics/orders', 'POST', normal, token)
        case = {'name': 'normal', 'request': normal, 'httpStatus': http_status,
                'businessCode': result.get('code'), 'message': result.get('msg')}
        REPORT['cases'].append(case)
        assert result.get('code') == 200 and isinstance(result.get('data'), str), case
        order_id = result['data']
        saved = json.loads(mysql(f"""
            SELECT JSON_OBJECT('orderId',o.id,'taskId',t.id,'cargoName',o.cargo_name,
              'weight',o.weight,'payload',t.payload,'orderStatus',o.status,
              'taskStatus',t.status,'taskType',t.type,'createdBy',o.created_by,
              'startStationId',t.start_station_id,'endStationId',t.end_station_id,
              'deadlineSeconds',TIMESTAMPDIFF(SECOND,o.created_time,o.deadline_at))
            FROM st_logistics_order o JOIN st_task t ON t.id=o.task_id
            WHERE o.id={sql_value(order_id)};
        """))
        assert saved['cargoName'] == normal['cargoName'] and saved['createdBy'] == 'admin', saved
        assert saved['weight'] == saved['payload'] == 2.5, saved
        assert saved['orderStatus'] == saved['taskStatus'] == 'created', saved
        assert saved['taskType'] == 'logistics', saved
        assert saved['startStationId'] == stations[0] and saved['endStationId'] == stations[1], saved
        assert 590 <= saved['deadlineSeconds'] <= 610, saved
        case['saved'] = saved
        case['after'] = counts(normal['reason'])
        assert case['after'] == {'orders': 1, 'tasks': 1, 'audit': 2}, case
        case['passed'] = True
        print('PASS: normal; one order, one linked logistics task, two business audits; pending assignment', flush=True)

        check_case(base, token, 'empty_name', payload('empty_name', cargoName=''), 500, '货物名称不能为空')
        check_case(base, token, 'blank_name', payload('blank_name', cargoName='   '), 500, '货物名称不能为空')
        check_case(base, token, 'same_station', payload('same_station', endStationId=stations[0]), 409, '起点与终点不能相同')
        check_case(base, token, 'missing_station', payload('missing_station', endStationId=PREFIX + '_missing'), 404, '记录不存在或已移除')
        check_case(base, token, 'weight_precision', payload('weight_precision', weight=2.555), 500, '重量最多保留两位小数')

        # Fail specifically at the order INSERT, after the task INSERT has run.
        # All other cargo names remain unaffected. Remove the trigger immediately.
        rollback = payload('rollback')
        mysql(f"""
            DELIMITER //
            CREATE TRIGGER `{TRIGGER}` BEFORE INSERT ON st_logistics_order
            FOR EACH ROW
            BEGIN
              IF NEW.cargo_name={sql_value(rollback['cargoName'])} THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT={sql_value(FAULT)};
              END IF;
            END//
            DELIMITER ;
        """)
        trigger_created = True
        try:
            check_case(base, token, 'late_order_write_failure', rollback, 500, FAULT)
        finally:
            mysql(f'DROP TRIGGER `{TRIGGER}`;')
            trigger_created = False
        assert all(case.get('passed') for case in REPORT['cases'])
        REPORT['passed'] = True
    finally:
        # Keep failures visible while still removing only this run's own records.
        try:
            if trigger_created:
                mysql(f'DROP TRIGGER IF EXISTS `{TRIGGER}`;')
            prefix, size = sql_value(PREFIX), len(PREFIX)
            mysql(f"""
                START TRANSACTION;
                DELETE o FROM st_logistics_order o JOIN st_task t ON t.id=o.task_id
                  WHERE LEFT(t.reason,{size})={prefix};
                DELETE a FROM st_audit a LEFT JOIN st_station s ON s.id=a.entity_id
                  WHERE LEFT(a.reason,{size})={prefix} OR LEFT(s.name,{size})={prefix};
                DELETE t FROM st_task t WHERE LEFT(t.reason,{size})={prefix};
                DELETE s FROM st_station s WHERE LEFT(s.name,{size})={prefix};
                COMMIT;
            """)
            REPORT['cleanup'] = all_test_counts(stations)
            assert all(value == 0 for value in REPORT['cleanup'].values()), REPORT['cleanup']
            print('PASS: own test rows and temporary trigger removed; existing business data preserved', flush=True)
        except Exception:
            REPORT['passed'] = False
            REPORT['cleanupFailed'] = True
            raise
        finally:
            if token:
                try:
                    api(base, '/logout', 'POST', token=token)
                except Exception:
                    REPORT['logoutFailed'] = True
            REPORT['finishedAtLocal'] = datetime.now().astimezone().isoformat()
            (ROOT / 'logs/logistics-create-verification.json').write_text(
                json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: logistics create acceptance completed', flush=True)


if __name__ == '__main__':
    main()
