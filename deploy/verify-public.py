"""Read-only smoke checks through the public tunnel; no model calls or task writes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://skytwin-ai-demo.spicyangel15.chatgpt.site'


def verify(base):
    result = {}
    token = ''

    def request(path, method='GET', body=None, authenticated=False):
        headers = {'Origin': SITE, 'Content-Type': 'application/json', 'User-Agent': 'SkyTwinDeploymentVerifier/1.0'}
        if authenticated:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(base + path, method=method, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
        return urllib.request.urlopen(req, timeout=35)

    def value(path, **kwargs):
        with request(path, **kwargs) as response:
            assert response.headers.get('Access-Control-Allow-Origin') == SITE
            return json.load(response)

    def rejected(path, status):
        try:
            request(path)
            raise AssertionError('Unexpected anonymous access')
        except urllib.error.HTTPError as error:
            assert error.code == status, (path, error.code)

    rejected('/java-api/sky/snapshot', 401)
    rejected('/java-api/system/user/list', 404)
    result['anonymous_and_admin_routes_blocked'] = True
    captcha = value('/java-api/captchaImage')
    credentials = json.loads((ROOT / '.runtime/public-demo-credentials.json').read_text(encoding='utf-8-sig'))
    assert 5 <= len(credentials['password']) <= 20, 'Demo password violates RuoYi login policy'
    code = ''
    if captcha.get('captchaEnabled'):
        runtime = json.loads((ROOT / 'ruoyi/config/runtime.local.json').read_text(encoding='utf-8-sig'))
        secrets = json.loads((ROOT / 'ruoyi/config/local-secrets.json').read_text(encoding='utf-8-sig'))
        env = dict(os.environ, REDISCLI_AUTH=secrets['RedisPassword'])
        code = subprocess.check_output([str(Path(runtime['RedisBin']) / 'redis-cli.exe'), '-h', '127.0.0.1',
                                       '-p', str(runtime.get('RedisPort', 16380)), '--raw', 'get',
                                       'captcha_codes:' + captcha['uuid']], env=env).decode().strip().strip('"')
    login = value('/java-api/login', method='POST', body={
        'username': credentials['username'], 'password': credentials['password'],
        'uuid': captcha.get('uuid', ''), 'code': code})
    assert login.get('code') == 200 and login.get('token'), 'Public demo login failed'
    token = login['token']
    try:
        info = value('/java-api/getInfo', authenticated=True)
        assert info['code'] == 200 and info['user']['userName'] == 'sky_demo'
        permissions = set(info['permissions'])
        assert {'sky:read', 'sky:operate'} <= permissions
        assert '*:*:*' not in permissions and not any(p.startswith('system:') for p in permissions)
        result['dedicated_business_account_login'] = True
        snapshot = value('/java-api/sky/snapshot', authenticated=True)
        assert snapshot['code'] == 200 and isinstance(snapshot['data'], dict)
        result['authenticated_snapshot'] = True
        with request('/java-api/sky/stream', authenticated=True) as stream:
            assert 'text/event-stream' in stream.headers.get('Content-Type', '')
            for _ in range(20):
                line = stream.readline()
                if line.startswith(b'data:'):
                    assert isinstance(json.loads(line[5:]), dict)
                    result['public_sse_first_snapshot'] = True
                    break
            assert result.get('public_sse_first_snapshot'), 'No SSE snapshot received'
        assert value('/agent-api/health')['ready']
        result['agent_ready'] = True
        config = value('/agent-api/workbench/config', authenticated=True)
        assert not config.get('demo_only')
        result['real_workbench_config'] = True
        vision = value('/agent-api/vision-chat/health', authenticated=True)
        assert vision.get('ready'), 'Vision configuration not ready'
        result['vision_config_ready_without_model_request'] = True
    finally:
        value('/java-api/logout', method='POST', authenticated=True)
    invalid = value('/java-api/getInfo', authenticated=True)
    assert invalid.get('code') == 401
    result['logout_invalidates_token'] = True
    (ROOT / '.runtime/public-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    for key in result:
        print('PASS:', key)


if __name__ == '__main__':
    verify(sys.argv[1])
