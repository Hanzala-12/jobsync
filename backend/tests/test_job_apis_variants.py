from backend.services import job_apis


def test_ai_query_variants_include_broader_terms():
    variants = job_apis._query_variants('machine learning engineer')

    assert 'machine learning engineer' in variants
    assert 'ai engineer' in variants
    assert 'machine learning' in variants


def test_search_jobs_tries_broader_ai_variants_when_exact_query_returns_nothing(monkeypatch):
    seen = []

    def fake_fetch_adzuna(query, country_code='pk', where='', results_per_page=20):
        seen.append((query, country_code, where))
        if query == 'ai engineer':
            return [{
                'title': 'AI Engineer',
                'company': 'TestCo',
                'location': 'Remote',
                'description': 'AI role',
                'url': 'https://example.com',
            }]
        return []

    monkeypatch.setattr(job_apis, 'fetch_adzuna', fake_fetch_adzuna)
    monkeypatch.setattr(job_apis, 'fetch_rozee_pakistan', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, 'fetch_mustakbil_pakistan', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, 'fetch_bing_pakistan', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, 'fetch_linkedin_indexed', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, 'fetch_company_careers', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, 'fetch_brightspyre', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, 'fetch_indexed_pakistan', lambda *args, **kwargs: [])
    monkeypatch.setattr(job_apis, '_search_cache', {})

    results = job_apis.search_jobs('machine learning engineer', location='Pakistan', country_code='pk')

    assert results
    assert any(query == 'ai engineer' for query, _, _ in seen)
