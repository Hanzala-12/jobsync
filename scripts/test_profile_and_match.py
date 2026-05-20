import requests, time, json, os

BASE = os.getenv('API_BASE', 'http://127.0.0.1:8000')

def create_profile():
    files = {
        'resume': ('sample_resume.txt', open('samples/sample_resume.txt','rb'))
    }
    data = {
        'skills': 'python, sql, react',
        'degree': 'BS Computer Science',
        'years_experience': '3',
        'interests': 'web development'
    }
    r = requests.post(f"{BASE}/api/profile", data=data, files=files, timeout=120)
    print('create_profile', r.status_code, r.text[:200])
    time.sleep(1)

def test_search():
    t0 = time.time()
    r = requests.get(f"{BASE}/jobs/search", params={'query':'software engineer','location':'Pakistan'}, timeout=120)
    print('search_status', r.status_code, 'len', len(r.json()) if r.ok else r.text[:200], 'time', time.time()-t0)

def test_match_first_job():
    r = requests.get(f"{BASE}/jobs/search", params={'query':'software engineer','location':'Pakistan'}, timeout=120)
    jobs = r.json() if r.ok else []
    if not jobs:
        print('no jobs to match')
        return
    job = jobs[0]
    job_id = job.get('id') or job.get('external_id') or job.get('url')
    # If job has numeric id use match route
    if isinstance(job_id, int):
        r2 = requests.post(f"{BASE}/api/match/{job_id}", timeout=120)
        print('match', r2.status_code, r2.text[:400])
    else:
        print('job id not numeric, skip match')

if __name__ == '__main__':
    create_profile()
    test_search()
    test_match_first_job()
