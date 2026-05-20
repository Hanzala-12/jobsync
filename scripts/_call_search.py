import requests, time
try:
    t0 = time.time()
    r = requests.get('http://127.0.0.1:8000/jobs/search', params={'query':'software engineer','location':'Pakistan'}, timeout=120)
    print('status', r.status_code)
    if r.ok:
        print('len', len(r.json()))
    else:
        print(r.text[:1000])
    print('elapsed', time.time()-t0)
except Exception as e:
    print('error', type(e), e)
