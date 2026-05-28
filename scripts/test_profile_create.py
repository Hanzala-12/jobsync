import requests, time
BASE = 'http://127.0.0.1:8000'
email = f'test_profile+{int(time.time()*1000)}@example.com'
password = 'Testpass123!'
print('Signing up', email)
r = requests.post(f'{BASE}/auth/signup', json={'email': email, 'password': password, 'name': 'TP'} )
print('signup', r.status_code, r.text)
# use a session to keep HttpOnly cookie
s = requests.Session()
print('Logging in')
r = s.post(f'{BASE}/auth/login', json={'email': email, 'password': password})
print('login', r.status_code, r.text)
access = r.json().get('access_token')
headers = {'Authorization': f'Bearer {access}'}
print('Creating profile via multipart/form-data')
pdf_bytes = b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj<< /Type /Pages /Count 0 >>\nendobj\ntrailer<< /Root 1 0 R >>\n%%EOF\n"
files = {'resume': ('sample.pdf', pdf_bytes, 'application/pdf')}
data = {'skills': 'Python,SQL', 'degree': 'BS', 'years_experience': '2', 'interests': 'Backend'}
r = s.post(f'{BASE}/profile', headers=headers, data=data, files=files)
print('profile create:', r.status_code, r.text)
