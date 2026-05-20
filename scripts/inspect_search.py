from backend.services.job_apis import search_jobs
import time,traceback,sys

def main():
    t=time.time()
    try:
        res = search_jobs('software engineer','Pakistan', None, False, 'pk', False)
        print('RESULT_LEN', len(res))
        print('DURATION', time.time()-t)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
