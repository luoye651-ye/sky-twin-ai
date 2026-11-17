"""Anonymous public checks with HTTP proxies disabled. Never sends credentials."""
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
base = json.loads((root / '.runtime/domestic-demo.json').read_text(encoding='utf-8-sig'))['publicOrigin']
assert base.startswith('https://')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
checks = {}


def read(path, expected=200):
    req = urllib.request.Request(base + path, headers={'User-Agent': 'SkyTwinDirectAccessVerifier/1.0', 'Origin': base, 'Accept-Encoding': 'gzip'})
    try:
        response = opener.open(req, timeout=40)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.code == expected, (path, response.code, expected)
        value = response.read()
        if response.headers.get('Content-Encoding') == 'gzip':
            value = gzip.decompress(value)
        return value


html = read('/').decode()
assert 'id="app"' in html
checks['public_home_without_http_proxy'] = True
assert 'id="app"' in read('/ai-workbench').decode()
checks['spa_deep_link'] = True
config = read('/deployment-config.js').decode()
assert "apiOrigin: ''" in config and 'chatgpt.site' not in config
checks['same_origin_api_without_sites'] = True
script = re.search(r'<script[^>]*\bsrc="(/assets/[^\"]+\.js)"', html)
assert script and len(read(script.group(1))) > 1000
checks['frontend_module_download_and_gzip'] = True
captcha = json.loads(read('/java-api/captchaImage'))
assert captcha.get('code') == 200 and (not captcha.get('captchaEnabled') or (captcha.get('uuid') and captcha.get('img')))
checks['public_captcha'] = True
assert json.loads(read('/agent-api/health')).get('ready')
checks['agent_ready_without_model_call'] = True
assert json.loads(read('/java-api/sky/snapshot', 401)).get('code') == 401
checks['anonymous_business_access_blocked'] = True
assert json.loads(read('/java-api/system/user/list', 404)).get('code') == 404
checks['system_admin_api_blocked'] = True
report = {'origin': base, 'verified_utc': datetime.now(timezone.utc).isoformat(), 'http_proxy_disabled': True,
          'authenticated_business_read': False, 'paid_model_calls': 0, 'checks': checks}
(root / '.runtime/domestic-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for name in checks:
    print('PASS:', name)
print('Direct-access public URL:', base)
