"""Local integration verification against the dedicated RuoYi instance.
Creates only uniquely named test data and removes those exact IDs in finally.
Never prints JWTs, passwords or Redis credentials. Uses the local test captcha.
"""
import concurrent.futures
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = json.loads((ROOT / 'config/runtime.local.json').read_text(encoding='utf-8-sig'))
SECRETS = json.loads((ROOT / 'config/local-secrets.json').read_text(encoding='utf-8-sig'))
BASE = 'http://127.0.0.1:5174/dev-api'
PREFIX = 'verify_' + uuid.uuid4().hex[:8]
TASKS, AIRCRAFT, STATIONS, USERS, TOKENS = [], [], [], [], []

def request(path, method='GET', data=None, token=None, expected=200):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
    if expected is not None:
        assert result['code'] == expected, (path, result.get('code'), result.get('msg'))
    return result

def login(username='admin', password='admin123'):
    captcha = request('/captchaImage')
    code = ''
    if captcha.get('captchaEnabled'):
        env = dict(os.environ, REDISCLI_AUTH=SECRETS['RedisPassword'])
        code = subprocess.check_output([str(pathlib.Path(RUNTIME['RedisBin']) / 'redis-cli.exe'), '-h', '127.0.0.1', '-p', str(RUNTIME.get('RedisPort', 16380)), '--raw', 'get', 'captcha_codes:' + captcha['uuid']], env=env, text=True).strip().strip('"')
    result = request('/login', 'POST', {'username': username, 'password': password, 'uuid': captcha.get('uuid'), 'code': code})
    TOKENS.append(result['token'])
    return result['token']

def mysql(sql):
    result = subprocess.run([str(pathlib.Path(RUNTIME['MySqlBin']) / 'mysql.exe'), '--defaults-file=' + str(ROOT / 'config/mysql-root.cnf'), '--database=sky_twin_ruoyi', '--batch', '--skip-column-names'], input=sql, text=True, encoding='utf-8', capture_output=True, check=True)
    return result.stdout.strip()

def milestone(message):
    print('PASS: ' + message, flush=True)

def wait_for(predicate, seconds=75):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(1)
    raise AssertionError('Timed out waiting for persisted simulation state')

admin = None
try:
    request('/sky/snapshot', expected=401)
    admin = login()
    baseline = request('/sky/snapshot', token=admin)['data']
    assert len(baseline['aircraft']) >= 4 and len(baseline['stations']) >= 6
    roles = request('/system/role/list?pageNum=1&pageSize=50', token=admin)['rows']
    role_ids = {role['roleKey']: role['roleId'] for role in roles}
    user_tokens = {}
    for role in ('sky_viewer', 'sky_dispatcher'):
        username = PREFIX + ('v' if role == 'sky_viewer' else 'd')
        password = uuid.uuid4().hex[:12] + 'A!7'
        request('/system/user', 'POST', {'userName': username, 'nickName': username, 'password': password, 'deptId': 100, 'status': '0', 'sex': '0', 'roleIds': [role_ids[role]], 'postIds': []}, admin)
        created = request('/system/user/list?userName=' + username, token=admin)['rows'][0]
        USERS.append(created['userId'])
        user_tokens[role] = login(username, password)
    viewer, dispatcher = user_tokens['sky_viewer'], user_tokens['sky_dispatcher']
    request('/sky/snapshot', token=viewer)
    request('/sky/tasks', 'POST', {'title': 'forbidden', 'type': 'environment', 'startStationId': 'S-01', 'endStationId': 'S-02', 'payload': 0, 'passengers': 0, 'speed': 10, 'cruiseAltitude': 60, 'reason': 'permission check'}, viewer, expected=403)
    request('/sky/aircraft', 'POST', {'name': 'forbidden', 'type': 'drone', 'model': 'test', 'longitude': 121.47, 'latitude': 31.23, 'battery': 100, 'payloadCapacity': 2, 'seats': 0}, dispatcher, expected=403)
    milestone('anonymous/viewer/dispatcher/admin permissions enforced by Java')

    for index in range(2):
        body = {'name': PREFIX + '_station' + str(index), 'type': 'takeoff', 'longitude': 121.4737 + index * .003, 'latitude': 31.2304, 'status': 'enabled'}
        station = request('/sky/stations', 'POST', body, admin)['data']; STATIONS.append(station)
        body['name'] += '_edited'
        request('/sky/stations/' + station, 'PUT', body, admin)
    aircraft_data = []
    for index in range(6):
        body = {'name': PREFIX + '_aircraft' + str(index), 'type': 'evtol' if index == 1 else 'cargo' if index == 0 else 'drone', 'model': 'TestModel', 'longitude': 121.4737, 'latitude': 31.2304, 'battery': 30.04 if index == 5 else 100, 'payloadCapacity': 20, 'seats': 4 if index == 1 else 0}
        aircraft = request('/sky/aircraft', 'POST', body, admin)['data']; AIRCRAFT.append(aircraft); aircraft_data.append(body)
        request('/sky/aircraft/' + aircraft, 'PUT', body, admin)
    invalid = dict(aircraft_data[0], latitude=200)
    assert request('/sky/aircraft', 'POST', invalid, admin, expected=None)['code'] != 200
    milestone('aircraft/station CRUD and invalid coordinate rejection')

    def create(kind='environment', name='task', start=None, end=None):
        body = {'title': PREFIX + '_' + name, 'type': kind, 'startStationId': start or STATIONS[0], 'endStationId': end or STATIONS[1], 'payload': 1, 'passengers': 2 if kind == 'commute' else 0, 'speed': 20, 'cruiseAltitude': 60, 'reason': 'integration verification'}
        task_id = request('/sky/tasks', 'POST', body, dispatcher)['data']; TASKS.append(task_id)
        return task_id
    def action(task, operation, aircraft=None, token=dispatcher, expected=200):
        return request('/sky/tasks/' + task + '/' + operation, 'POST', {'aircraftId': aircraft, 'reason': 'integration verification: ' + operation}, token, expected)
    def snapshot():
        return request('/sky/snapshot', token=admin)['data']
    def task(task_id):
        return next(t for t in snapshot()['tasks'] if t['id'] == task_id)

    race = [create(name='race1'), create(name='race2')]
    with concurrent.futures.ThreadPoolExecutor(2) as executor:
        outcomes = list(executor.map(lambda t: action(t, 'assign', AIRCRAFT[0], expected=None)['code'], race))
    assert sorted(outcomes) == [200, 409], outcomes
    for t in race:
        action(t, 'cancel')
    milestone('concurrent assignment reserves a single aircraft exactly once')

    running = []
    for index, kind in enumerate(('logistics', 'commute', 'environment', 'rescue', 'airspace')):
        t = create(kind, kind, 'S-05' if kind == 'commute' else None, 'S-06' if kind == 'commute' else None)
        action(t, 'start', expected=409)
        action(t, 'assign', AIRCRAFT[index]); action(t, 'start'); running.append(t)
    low = create(name='low_battery'); action(low, 'assign', AIRCRAFT[5]); action(low, 'start'); running.append(low)
    request('/sky/aircraft/' + AIRCRAFT[0], 'PUT', aircraft_data[0], admin, expected=409)
    request('/sky/stations/' + STATIONS[0], 'DELETE', token=admin, expected=409)
    assert sum(t['status'] == 'executing' for t in snapshot()['tasks'] if t['id'] in running) == 6

    stream_request = urllib.request.Request(BASE + '/sky/stream', headers={'Authorization': 'Bearer ' + viewer, 'Accept': 'text/event-stream'})
    with urllib.request.urlopen(stream_request, timeout=10) as stream:
        assert 'text/event-stream' in stream.headers.get('Content-Type', '')
        while True:
            line = stream.readline()
            if line.startswith(b'data:'):
                streamed = json.loads(line[5:])
                assert any(t['id'] == running[0] for t in streamed['tasks'])
                break
    milestone('six simultaneous flights plus authenticated live SSE snapshot')
    wait_for(lambda: task(running[0])['progress'] >= 5)
    before = task(running[0])['progress']
    assert request('/sky/tasks/' + running[0] + '/tracks', token=viewer)['data']

    def script(name):
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'scripts' / name), '-Service', 'backend'], check=True)
    script('stop.ps1')
    persisted = float(mysql("SELECT progress FROM st_task WHERE id='" + running[0] + "';"))
    assert persisted >= before
    script('start.ps1')
    wait_for(lambda: request('/sky/snapshot', token=admin)['data'])
    assert task(running[0])['progress'] >= persisted
    milestone('Java restart preserves active tasks, positions and tracks')

    wait_for(lambda: all(task(t)['status'] == 'completed' for t in running), seconds=85)
    state = snapshot()
    for t in running:
        assert task(t)['progress'] == 100
        assert any(r['taskId'] == t for r in state['reports'])
        assert any(a['entityId'] == t and a['action'] == 'task.complete' and a['actor'] == 'simulator' for a in state['audit'])
        points = request('/sky/tasks/' + t + '/tracks', token=viewer)['data']
        assert points[-1]['progress'] == 100 and points[-1]['altitude'] == 0
    assert all(a['status'] == 'idle' for a in state['aircraft'] if a['id'] in AIRCRAFT)
    milestone('server completes five task types without any browser animation; report/track/audit persisted')

    failed = create(name='failed'); action(failed, 'assign', AIRCRAFT[0]); action(failed, 'start'); action(failed, 'fail')
    action(failed, 'cancel', expected=409)
    event = next(e for e in snapshot()['events'] if e['taskId'] == failed)
    request('/sky/events/' + str(event['id']) + '/resolve', 'POST', {'reason': 'verification resolved'}, dispatcher)
    request('/sky/events/' + str(event['id']) + '/resolve', 'POST', {'reason': 'repeat'}, dispatcher, expected=409)
    assert any(e['taskId'] == low and e['severity'] == 'medium' for e in snapshot()['events'])
    milestone('low battery/failed-task alerts and audited one-time event resolution')

    completed_ids = set(running)
    script('stop.ps1'); script('start.ps1')
    state = snapshot()
    assert completed_ids.issubset({r['taskId'] for r in state['reports']})
    assert completed_ids.issubset({t['id'] for t in state['tasks'] if t['status'] == 'completed'})
    milestone('completed reports, events and history remain queryable after second restart')
    (ROOT / 'logs/foundation-verification.json').write_text(json.dumps({'passed': True, 'checks': ['permissions', 'CRUD', 'validation', 'concurrent assignment', 'six flights', 'authenticated SSE', 'restart recovery', 'server completion', 'tracks/reports/audit', 'events'], 'testDataPrefix': PREFIX}, indent=2), encoding='utf-8')
finally:
    if admin:
        for t in TASKS:
            try:
                request('/sky/tasks/' + t + '/cancel', 'POST', {'reason': 'verification cleanup'}, admin, expected=None)
            except Exception:
                pass
        # Only IDs returned by this run are eligible for physical test cleanup.
        def quoted(values):
            return ','.join("'" + str(value).replace("'", "''") + "'" for value in values)
        if TASKS:
            ids = quoted(TASKS)
            event_ids = mysql('SELECT id FROM st_event WHERE task_id IN(' + ids + ');').splitlines()
            if event_ids:
                mysql('DELETE FROM st_audit WHERE entity_id IN(' + quoted(['event-' + event_id for event_id in event_ids]) + ');')
            mysql(';'.join('DELETE FROM ' + table + ' WHERE task_id IN(' + ids + ')' for table in ('st_track', 'st_report', 'st_event')) + ';DELETE FROM st_task WHERE id IN(' + ids + ');')
        if AIRCRAFT:
            mysql('DELETE FROM st_aircraft WHERE id IN(' + quoted(AIRCRAFT) + ');')
        if STATIONS:
            mysql('DELETE FROM st_station WHERE id IN(' + quoted(STATIONS) + ');')
        all_ids = TASKS + AIRCRAFT + STATIONS
        if all_ids:
            mysql('DELETE FROM st_audit WHERE entity_id IN(' + quoted(all_ids) + ');')
        for user in USERS:
            request('/system/user/' + str(user), 'DELETE', token=admin, expected=None)
        for token in TOKENS:
            try:
                request('/logout', 'POST', token=token, expected=None)
            except Exception:
                pass
        print('Test-only resources and sessions cleaned up.', flush=True)
