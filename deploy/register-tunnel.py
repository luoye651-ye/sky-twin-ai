"""Register routing metadata using the machine's standard HTTPS proxy settings."""
import json
from pathlib import Path
import sys
import urllib.request

root = Path(__file__).resolve().parents[1]
settings = json.loads((root / '.runtime/public-tunnel-settings.json').read_text(encoding='utf-8-sig'))
request = urllib.request.Request(
    'https://skytwin-ai-gateway.spicyangel15.chatgpt.site/_tunnel/register',
    method='POST', data=json.dumps({'origin': sys.argv[1]}).encode(),
    headers={'Authorization': 'Bearer ' + settings['secret'], 'Content-Type': 'application/json',
             'User-Agent': 'SkyTwinTunnelConnector/1.0'})
try:
    with urllib.request.urlopen(request, timeout=25) as response:
        assert response.status == 200 and json.load(response).get('registered')
except Exception:
    print('Route registration is temporarily unavailable', file=sys.stderr)
    sys.exit(1)
