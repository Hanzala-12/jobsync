import requests, sys
from time import sleep

url = 'http://127.0.0.1:8000/jobs/search/stream?query=software%20engineer&location=Pakistan'
print('connecting to', url)
with requests.get(url, stream=True) as r:
    if r.status_code != 200:
        print('status', r.status_code, r.text[:400])
        sys.exit(1)
    buf = ''
    count = 0
    for chunk in r.iter_content(chunk_size=1):
        if not chunk:
            break
        try:
            s = chunk.decode('utf-8')
        except Exception:
            continue
        buf += s
        if buf.endswith('\n\n'):
            # one SSE event
            line = buf.strip()
            print('EVENT:', line[:400])
            buf = ''
            count += 1
            if count >= 6:
                break
print('done')
