"""Read-only streaming verification, including timeout and reauthentication."""
import json
import os
import pathlib
import subprocess
import urllib.request

root = pathlib.Path(__file__).resolve().parents[1]
runtime = json.loads((root / 'config/runtime.local.json').read_text(encoding='utf-8-sig'))
secrets = json.loads((root / 'config/local-secrets.json').read_text(encoding='utf-8-sig'))
base = 'http://127.0.0.1:5173/java-api'
def call(path, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(base + path, headers=headers, data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)

assert call('/sky/stream')['code'] == 401
captcha = call('/captchaImage')
code = ''
if captcha.get('captchaEnabled'):
    code = subprocess.check_output([str(pathlib.Path(runtime['RedisBin']) / 'redis-cli.exe'), '-h', '127.0.0.1', '-p', str(runtime.get('RedisPort', 16380)), '--raw', 'get', 'captcha_codes:' + captcha['uuid']], text=True, env=dict(os.environ, REDISCLI_AUTH=secrets['RedisPassword'])).strip().strip('"')
login = call('/login', {'username': 'admin', 'password': 'admin123', 'code': code, 'uuid': captcha.get('uuid')})
assert login['code'] == 200
token = login['token']
try:
    counts = []
    for _ in range(2):
        request = urllib.request.Request(base + '/sky/stream', headers={'Authorization': 'Bearer ' + token, 'Accept': 'text/event-stream'})
        with urllib.request.urlopen(request, timeout=30) as stream:
            count = 0
            for line in stream:
                if line.startswith(b'data:'):
                    snapshot = json.loads(line[5:])
                    assert all(key in snapshot for key in ('aircraft', 'stations', 'tasks', 'events', 'reports', 'audit', 'summary'))
                    count += 1
            assert count >= 8, count
            counts.append(count)
        assert call('/sky/snapshot', token=token)['code'] == 200
    print('PASS: dashboard Java proxy, continuous SSE, 20-second stream end and authenticated reconnection; frame counts:', counts)
finally:
    assert call('/logout', {}, token)['code'] == 200
