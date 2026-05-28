import requests, time
BASE = 'http://127.0.0.1:8000'
# use the last created test user from previous script (id 36), but safer to create new
email = f'select_test+{int(time.time()*1000)}@example.com'
password = 'Testpass123!'
print('Signup', email)
r = requests.post(f'{BASE}/auth/signup', json={'email': email, 'password': password, 'name': 'Selector'})
print('signup', r.status_code)
s = requests.Session()
print('Login')
r = s.post(f'{BASE}/auth/login', json={'email': email, 'password': password})
access = r.json().get('access_token')
headers = {'Authorization': f'Bearer {access}'}
# create a profile via multipart
files = {'resume': ('sample.pdf', b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n', 'application/pdf')}
data = {'skills': 'Go,Python', 'degree': 'MS', 'years_experience': '5', 'interests': 'SRE'}
r = s.post(f'{BASE}/profile', headers=headers, data=data, files=files)
print('create profile', r.status_code, r.text)
# list profiles
r = s.get(f'{BASE}/profile', headers=headers)
print('list profiles', r.status_code, r.text)
profiles = r.json().get('profiles', [])
if profiles:
    pid = profiles[0]['id']
    r = s.post(f'{BASE}/profile/select/{pid}', headers=headers)
    print('select', r.status_code, r.text)
    r = s.get(f'{BASE}/profile/selected', headers=headers)
    print('selected', r.status_code, r.text)
else:
    print('no profiles to select')
