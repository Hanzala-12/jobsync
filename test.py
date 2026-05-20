from retrieve_and_generate import generate_cover_letter

def main():
    job = "Junior Data Engineer needed. Responsibilities: build ETL, write SQL, work with AWS S3 and PostgreSQL. Prefer experience with Python and Airflow."
    resume = "Data engineer with 2 years experience building ETL pipelines in Python, experience with PostgreSQL and AWS S3. Familiar with Airflow."
    cover, ids, _ = generate_cover_letter(job, resume)
    print('--- Generated Cover Letter ---')
    print(cover)
    print('\n--- Retrieved chunk IDs ---')
    print(ids)

if __name__ == '__main__':
    main()
