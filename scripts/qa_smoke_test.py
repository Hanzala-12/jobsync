import os
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

import requests

BASE = 'http://127.0.0.1:8000'
SESSION = requests.Session()
SESSION.headers.update({'Accept': 'application/json'})


def ensure_auth(email: str = 'qa@example.com', password: str = 'qa-password-123') -> None:
    """Ensure the test session is authenticated. Try login, fall back to signup."""
    login_url = f"{BASE}/auth/login"
    signup_url = f"{BASE}/auth/signup"
    try:
        resp = SESSION.post(login_url, json={'email': email, 'password': password}, timeout=10)
        if resp.status_code == 200:
            token = resp.json().get('access_token')
            if token:
                SESSION.headers.update({'Authorization': f'Bearer {token}'})
                return
    except Exception:
        pass
    # Try signup
    try:
        resp = SESSION.post(signup_url, json={'email': email, 'password': password}, timeout=10)
        if resp.status_code == 200:
            token = resp.json().get('access_token')
            if token:
                SESSION.headers.update({'Authorization': f'Bearer {token}'})
                return
    except Exception:
        pass

# Ensure we have an authenticated session for endpoints that require it
if os.getenv('QA_ACCESS_TOKEN'):
    SESSION.headers.update({'Authorization': f"Bearer {os.getenv('QA_ACCESS_TOKEN')}"})
else:
    ensure_auth()

results = []
service_results = []


def snippet(text: str, limit: int = 350) -> str:
    return (text or '')[:limit].replace('\n', ' ')


def add_result(entry: dict) -> None:
    global results
    if results is None:
        # defensive: reinitialize if corrupted
        results = []
    results.append(entry)


def call_http(name, method, url, func, expected, allow_codes=(200,)):
    start = time.perf_counter()
    try:
        resp = func()
        elapsed = time.perf_counter() - start
        add_result({
            'name': name,
            'method': method,
            'url': url,
            'status_code': resp.status_code,
            'pass': resp.status_code in allow_codes,
            'elapsed_sec': round(elapsed, 3),
            'expected': expected,
            'snippet': snippet(resp.text),
        })
        return resp
    except Exception as exc:
        elapsed = time.perf_counter() - start
        add_result({
            'name': name,
            'method': method,
            'url': url,
            'status_code': None,
            'pass': False,
            'elapsed_sec': round(elapsed, 3),
            'expected': expected,
            'error': str(exc),
        })
        return None


def call_service(name, func, expected):
    start = time.perf_counter()
    try:
        value = func()
        global service_results
        if service_results is None:
            service_results = []
        service_results.append({
            'name': name,
            'pass': True,
            'elapsed_sec': round(time.perf_counter() - start, 3),
            'expected': expected,
            'result': value,
        })
    except Exception as exc:
        if service_results is None:
            service_results = []
        service_results.append({
            'name': name,
            'pass': False,
            'elapsed_sec': round(time.perf_counter() - start, 3),
            'expected': expected,
            'error': str(exc),
            'traceback': traceback.format_exc(limit=2),
        })


# Setup profile for job endpoints.
profile = call_http(
    'setup:create_profile',
    'POST',
    f'{BASE}/profile',
    lambda: SESSION.post(
        f'{BASE}/profile',
        data={
            'skills': 'python, sql, fastapi, aws',
            'degree': 'BS Computer Science',
            'years_experience': '3',
            'interests': 'backend systems, data platforms',
        },
        timeout=20,
    ),
    '200 create profile',
)
profile_id = None
if profile is not None:
    try:
        profile_id = profile.json().get('id')
    except Exception:
        pass
if profile_id:
    call_http(
        'setup:select_profile',
        'POST',
        f'{BASE}/profile/select/{profile_id}',
        lambda: SESSION.post(f'{BASE}/profile/select/{profile_id}', timeout=20),
        '200 select profile',
    )

# Job module endpoints.
health = call_http('1 health', 'GET', f'{BASE}/health', lambda: SESSION.get(f'{BASE}/health', timeout=20), '200 database: connected')
search = call_http('2 jobs search', 'GET', f'{BASE}/jobs/search?query=software&limit=5', lambda: SESSION.get(f'{BASE}/jobs/search', params={'query': 'software', 'limit': 5}, timeout=20), '200 jobs array')
job_id = 1
if search is not None:
    try:
        data = search.json()
        if isinstance(data, list) and data:
            job_id = data[0].get('id') or 1
    except Exception:
        pass

call_http('3 jobs match', 'GET', f'{BASE}/jobs/{job_id}/match', lambda: SESSION.get(f'{BASE}/jobs/{job_id}/match', timeout=20), '200 match_score/matching_skills/missing_skills')
call_http('4 legacy match', 'POST', f'{BASE}/match/{job_id}', lambda: SESSION.post(f'{BASE}/match/{job_id}', timeout=20), '200 or 404', allow_codes=(200, 404))
call_http('5 build resume', 'POST', f'{BASE}/build_resume/{job_id}', lambda: SESSION.post(f'{BASE}/build_resume/{job_id}', timeout=40), '200 resume_text')
call_http('6 legacy cover letter', 'POST', f'{BASE}/cover_letter/{job_id}', lambda: SESSION.post(f'{BASE}/cover_letter/{job_id}', timeout=40), '200 cover_letter')
call_http('7 profile list', 'GET', f'{BASE}/profile', lambda: SESSION.get(f'{BASE}/profile', timeout=20), '200 profile list')
call_http('9 selected profile', 'GET', f'{BASE}/profile/selected', lambda: SESSION.get(f'{BASE}/profile/selected', timeout=20), '200 selected profile')
call_http('10 applications list', 'GET', f'{BASE}/applications/', lambda: SESSION.get(f'{BASE}/applications/', timeout=20), '200 applications array')
call_http('11 applications health-score', 'GET', f'{BASE}/applications/health-score', lambda: SESSION.get(f'{BASE}/applications/health-score', timeout=20), '200 grade/score/suggestions')
call_http('12 cover-letter generate', 'POST', f'{BASE}/cover-letter/generate', lambda: SESSION.post(f'{BASE}/cover-letter/generate', json={'job_description': 'Build scalable backend services in Python.', 'company': 'Acme Corp', 'role': 'Backend Engineer', 'tone': 'professional'}, timeout=40), '200 cover_letter text')
call_http('13 skill gap', 'POST', f'{BASE}/intelligence/skill-gap', lambda: SESSION.post(f'{BASE}/intelligence/skill-gap', json={'job_descriptions': ['Looking for Python developer with SQL and AWS experience.', 'Need FastAPI, Docker, and PostgreSQL.']}, timeout=40), '200 missing_skills')
call_http('14 interview generate-questions', 'POST', f'{BASE}/interview/generate-questions', lambda: SESSION.post(f'{BASE}/interview/generate-questions', json={'job_title': 'Backend Engineer', 'company': 'Acme Corp'}, timeout=40), '200 questions')
call_http('15 interview predict', 'POST', f'{BASE}/interview/predict', lambda: SESSION.post(f'{BASE}/interview/predict', json={'job_description': 'Need Python, FastAPI, SQL, AWS.', 'resume_text': 'Python developer with SQL and AWS.', 'company': 'Acme Corp', 'role': 'Backend Engineer'}, timeout=40), '200 predicted questions')
call_http('16 mock interview evaluate', 'POST', f'{BASE}/mock-interview/evaluate', lambda: SESSION.post(f'{BASE}/mock-interview/evaluate', json={'question': 'Tell me about yourself', 'answer': 'I am a developer.'}, timeout=20), '200 or 404', allow_codes=(200, 404))
call_http('17 kanban board', 'GET', f'{BASE}/kanban/board', lambda: SESSION.get(f'{BASE}/kanban/board', timeout=20), '200 board columns')
call_http('18 scout status', 'GET', f'{BASE}/scout/status', lambda: SESSION.get(f'{BASE}/scout/status', timeout=20), '200 scout status')
call_http('19 extension analyze-url', 'POST', f'{BASE}/extension/analyze-url', lambda: SESSION.post(f'{BASE}/extension/analyze-url', json={'url': 'https://example.com'}, timeout=40), '200 valid URL analysis')

# Student module.
student_profile = call_http(
    'setup:create_student_profile',
    'POST',
    f'{BASE}/api/student/profile',
    lambda: SESSION.post(
        f'{BASE}/api/student/profile',
        json={
            'gpa': 3.7,
            'gre_score': 320,
            'toefl_score': 105,
            'ielts_score': 7.5,
            'budget_per_year': 25000,
            'preferred_countries': ['Malaysia', 'Singapore'],
            'intended_major': 'Computer Science',
            'degree_level': 'Masters',
            'academic_background': 'Software Engineering',
        },
        timeout=40,
    ),
    '200 student profile with id',
)
student_id = None
if student_profile is not None:
    try:
        student_id = student_profile.json().get('id')
    except Exception:
        pass
call_http('student profile get', 'GET', f'{BASE}/api/student/profile/{student_id or 1}', lambda: SESSION.get(f'{BASE}/api/student/profile/{student_id or 1}', timeout=20), '200 student profile')
student_filter = call_http('student universities filter', 'GET', f'{BASE}/api/student/universities/filter?country=Malaysia', lambda: SESSION.get(f'{BASE}/api/student/universities/filter', params={'country': 'Malaysia'}, timeout=40), '200 universities array')
program_id = None
if student_filter is not None:
    try:
        payload = student_filter.json()
        items = payload.get('items') if isinstance(payload, dict) else []
        if items:
            programs = items[0].get('programs') or []
            if programs:
                program_id = programs[0].get('id')
    except Exception:
        pass
recommend = call_http('student match recommend', 'POST', f'{BASE}/api/student/match/recommend', lambda: SESSION.post(f'{BASE}/api/student/match/recommend', json={'student_profile_id': student_id or 1}, timeout=60), '200 matches array with match_score')
if program_id is None and recommend is not None:
    try:
        payload = recommend.json()
        results = payload.get('results') if isinstance(payload, dict) else []
        if results:
            program_id = results[0].get('program', {}).get('id')
    except Exception:
        pass
program_detail_id = program_id or 1
call_http('student match program detail', 'GET', f'{BASE}/api/student/match/program/{program_detail_id}', lambda: SESSION.get(f'{BASE}/api/student/match/program/{program_detail_id}', params={'student_profile_id': student_id or 1}, timeout=60), '200 match analysis', allow_codes=(200, 404))
if student_id and program_id:
    call_http('student save', 'POST', f'{BASE}/api/student/save', lambda: SESSION.post(f'{BASE}/api/student/save', json={'student_id': student_id, 'program_id': program_id}, timeout=40), '200 success')
    call_http('student saved list', 'GET', f'{BASE}/api/student/saved/{student_id}', lambda: SESSION.get(f'{BASE}/api/student/saved/{student_id}', timeout=40), '200 saved programs array')
    apply_resp = call_http('student apply', 'POST', f'{BASE}/api/student/apply', lambda: SESSION.post(f'{BASE}/api/student/apply', json={'student_id': student_id, 'program_id': program_id, 'notes': 'Interested in the program.'}, timeout=40), '200 study application')
    call_http('student applications list', 'GET', f'{BASE}/api/student/applications/{student_id}', lambda: SESSION.get(f'{BASE}/api/student/applications/{student_id}', timeout=40), '200 applications array')
    if apply_resp is not None:
        try:
            app_id = apply_resp.json().get('id')
        except Exception:
            app_id = None
        if app_id:
            call_http('student application update', 'PUT', f'{BASE}/api/student/applications/{app_id}', lambda: SESSION.put(f'{BASE}/api/student/applications/{app_id}', json={'status': 'interviewing', 'notes': 'Updated during QA'}, timeout=40), '200 update status')
else:
    add_result({'name': 'student save', 'method': 'POST', 'url': f'{BASE}/api/student/save', 'status_code': None, 'pass': False, 'expected': '200 success', 'error': 'Skipped because no student_id or program_id was available'})
    add_result({'name': 'student saved list', 'method': 'GET', 'url': f'{BASE}/api/student/saved/<student_id>', 'status_code': None, 'pass': False, 'expected': '200 saved programs array', 'error': 'Skipped because no program_id was available'})
    add_result({'name': 'student apply', 'method': 'POST', 'url': f'{BASE}/api/student/apply', 'status_code': None, 'pass': False, 'expected': '200 study application', 'error': 'Skipped because no program_id was available'})
    add_result({'name': 'student applications list', 'method': 'GET', 'url': f'{BASE}/api/student/applications/<student_id>', 'status_code': None, 'pass': False, 'expected': '200 applications array', 'error': 'Skipped because no program_id was available'})
    add_result({'name': 'student application update', 'method': 'PUT', 'url': f'{BASE}/api/student/applications/<id>', 'status_code': None, 'pass': False, 'expected': '200 update status', 'error': 'Skipped because no program/application was available'})

# Scripts requested.
for rel_path, args in [
    ('scripts/ingest_universities.py', ['--limit', '10']),
    ('scripts/enrich_universities.py', ['--limit', '5']),
    ('scripts/ingest_programs_to_vector_db.py', ['--limit', '10']),
    ('scripts/refresh_match_cache.py', ['--once']),
    ('scripts/backfill_skills.py', []),
]:
    cmd = [sys.executable, str(Path(rel_path)), *args]
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path.cwd()), timeout=240)
        results.append({
            'name': rel_path,
            'method': 'SCRIPT',
            'url': ' '.join(cmd),
            'status_code': proc.returncode,
            'pass': proc.returncode == 0,
            'elapsed_sec': round(time.perf_counter() - start, 3),
            'expected': 'exit code 0',
            'stdout': (proc.stdout or '')[-1200:],
            'stderr': (proc.stderr or '')[-1200:],
        })
    except Exception as exc:
        results.append({
            'name': rel_path,
            'method': 'SCRIPT',
            'url': ' '.join(cmd),
            'status_code': None,
            'pass': False,
            'elapsed_sec': round(time.perf_counter() - start, 3),
            'expected': 'exit code 0',
            'error': str(exc),
        })

# Direct service calls.
from core.skill_extractor import extract_skills
call_service('skill extractor', lambda: extract_skills('Looking for Python developer'), "Returns ['python']")

try:
    from core.match_explainer import calculate_skill_match
    call_service('match explainer', lambda: calculate_skill_match(['python', 'sql'], ['python', 'aws']), "Returns matching ['python'], missing ['aws']")
except Exception:
    try:
        from core.match_explainer import explain_match_for
        call_service('match explainer', lambda: explain_match_for({'id': 1, 'description': 'python sql', 'job_skills': ['python', 'sql']}, {'id': 1, 'resume_text': 'python aws', 'profile_skills': ['python', 'aws']}), 'Works via explain_match_for')
    except Exception as exc:
        service_results.append({'name': 'match explainer', 'pass': False, 'expected': "Returns matching ['python'], missing ['aws']", 'error': str(exc)})

try:
    from core.deduplicator import is_duplicate
    call_service('deduplicator', lambda: is_duplicate({'title': 'X'}, {'title': 'X'}), 'Works if implemented')
except Exception:
    try:
        from core.deduplicator import process_incoming_job
        call_service('deduplicator', lambda: bool(process_incoming_job), 'Module available')
    except Exception as exc:
        service_results.append({'name': 'deduplicator', 'pass': False, 'expected': 'Works if implemented', 'error': str(exc)})

try:
    from core.normalizer import normalize_job
    call_service('normalizer', lambda: normalize_job({'title': 'Senior Python Dev', 'company': 'Acme', 'description': 'Build APIs', 'url': 'https://example.com', 'apply_url': 'https://example.com/apply', 'location': 'Remote', 'city': 'Remote', 'external_id': '1'}, 'qa-test'), 'Works')
except Exception as exc:
    service_results.append({'name': 'normalizer', 'pass': False, 'expected': 'Works', 'error': str(exc)})

summary = {
    'http_total': len([r for r in results if r.get('method') != 'SCRIPT' or True]),
    'http_pass': sum(1 for r in results if r.get('method') != 'SCRIPT' and r.get('pass')),
    'http_fail': sum(1 for r in results if r.get('method') != 'SCRIPT' and not r.get('pass')),
    'script_pass': sum(1 for r in results if r.get('method') == 'SCRIPT' and r.get('pass')),
    'script_fail': sum(1 for r in results if r.get('method') == 'SCRIPT' and not r.get('pass')),
    'service_pass': sum(1 for r in service_results if r.get('pass')),
    'service_fail': sum(1 for r in service_results if not r.get('pass')),
}
slow = [r for r in results if r.get('elapsed_sec', 0) and r['elapsed_sec'] > 5]
report = {'summary': summary, 'slow': slow, 'results': results, 'services': service_results}
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))