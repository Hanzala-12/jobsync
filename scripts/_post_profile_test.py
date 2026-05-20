import requests, os
BASE='http://127.0.0.1:8000'
files={'resume':('sample_resume.txt', open('samples/sample_resume.txt','rb'))}
data={'skills':'python,sql','degree':'BS','years_experience':'3'}
resp = requests.post(BASE+'/api/profile', data=data, files=files, timeout=10)
print(resp.status_code)
print(resp.text)
