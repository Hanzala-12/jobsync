import requests

base = 'http://127.0.0.1:8000'
email = 'autotest+api1779974523442@example.com'
password = 'Password123!'

resp = requests.post(base + '/auth/login', json={'email': email, 'password': password}, timeout=60)
print('LOGIN', resp.status_code)
print(resp.text)
if not resp.ok:
    raise SystemExit(1)

token = resp.json().get('access_token')
headers = {'Authorization': 'Bearer ' + token, 'X-Force-Rebuild': '1'}
r = requests.post(base + '/build_resume/34', headers=headers, timeout=120)
print('BUILD', r.status_code, r.headers.get('content-type'))
text = r.text
print('BODY_SNIPPET', text[:4000])

try:
    data = r.json()
    fixed = (data.get('fixed_resume_text') or '')
    keyword_debug = data.get('keyword_debug') or {}
    missing = keyword_debug.get('missing_keywords') or []
    print('FIXED_LEN', len(fixed))
    print('MISSING', missing)
    print('FOUND_COUNT', sum(1 for kw in ['azure', 'gcp', 'javascript', 'node.js', 'communication'] if kw.lower() in fixed.lower()))
    print('HAS_BACKSLASH', '\\' in fixed)
    print('HAS_DASH_BULLET', any(line.strip().startswith('- ') for line in fixed.splitlines()))
except Exception as exc:
    print('JSON_PARSE_ERR', repr(exc))
