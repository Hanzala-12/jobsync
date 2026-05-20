import requests
r = requests.get('http://127.0.0.1:8000/openapi.json', timeout=10)
print(r.status_code)
if r.ok:
    data = r.json()
    paths = sorted(list(data.get('paths', {}).keys()))
    for p in paths:
        print(p)
else:
    print(r.text[:1000])
