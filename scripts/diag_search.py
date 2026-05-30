import json
import sys
import os

print('CWD', os.getcwd())
print('PYTHONPATH', sys.path[:5])

# Ensure repository root is on sys.path so sibling packages like `backend` can be imported
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from backend.services import job_apis
except Exception as e:
    print('IMPORT_ERROR', e)
    raise


def run():
    diag={}
    results = job_apis.search_jobs('machine learning engineer', location='Pakistan', country_code='pk', diagnostics=diag)
    print('RESULT_COUNT', len(results))
    print(json.dumps(diag, indent=2))
    if results:
        print('SAMPLE', results[:2])


if __name__ == '__main__':
    run()
