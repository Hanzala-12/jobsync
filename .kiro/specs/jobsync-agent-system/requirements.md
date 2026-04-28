# Requirements Document

## Introduction

JobSync is a comprehensive job-hunting agent system that combines a standalone CLI agent with a web application to help job seekers analyze job postings, tailor resumes, prepare for interviews, and track applications. The system leverages LLM technology (OpenRouter API with meta-llama/llama-3.1-8b-instruct) for intelligent analysis while maintaining keyword-based fallback mechanisms. It implements the GAME framework (Goals, Actions, Memory, Evaluation) and provides both file-driven batch processing and real-time web-based interactions.

## Glossary

- **CLI_Agent**: The standalone command-line application (app.py) that processes files from input folders
- **Web_Application**: The FastAPI backend and React frontend providing browser-based access
- **LLM_Service**: The language model service (OpenRouter or Groq API) used for intelligent analysis
- **Application_Tracker**: The CSV-based system for tracking job application status and reminders
- **ATS_Score**: Applicant Tracking System score (0-100) measuring resume-job match quality
- **Job_API**: External job search APIs (Adzuna, RemoteOK, Arbeitnow)
- **Memory_System**: JSON-based session storage implementing GAME framework memory
- **Input_Folder**: Directories containing job postings, resumes, and knowledge base files
- **Output_Folder**: Directory where generated reports and analysis are saved
- **Tracker_Folder**: Directory containing application tracker CSV, reminders, and memory files
- **GAME_Framework**: Goals, Actions, Memory, Evaluation framework for agent design
- **Skill_Gap**: The difference between required job skills and candidate's current skills
- **Knowledge_Base**: Collection of interview preparation materials, course notes, and reference documents
- **Urgency_Level**: Classification of reminder priority (OVERDUE/TODAY/TOMORROW/THIS WEEK)
- **Round_Trip_Property**: Property where parsing then printing then parsing produces equivalent result

## Requirements

### Requirement 1: File Input Processing

**User Story:** As a job seeker, I want to provide job postings, resumes, and knowledge base materials as files, so that the system can analyze them without manual data entry.

#### Acceptance Criteria

1. THE CLI_Agent SHALL read all TXT files from the Input_Folder directories
2. THE CLI_Agent SHALL read all PDF files from the Input_Folder directories
3. WHEN a PDF file is provided, THE CLI_Agent SHALL extract text content using PyMuPDF
4. THE CLI_Agent SHALL maintain three separate Input_Folder directories: input_jobs, input_resumes, and input_kb
5. WHEN multiple files exist in an Input_Folder, THE CLI_Agent SHALL combine their content with file name markers
6. IF a file cannot be read, THE CLI_Agent SHALL log the error and continue processing other files
7. THE CLI_Agent SHALL support UTF-8 encoding for all text files

### Requirement 2: Job Description Analysis

**User Story:** As a job seeker, I want the system to analyze job descriptions and extract key requirements, so that I understand what skills and qualifications are needed.

#### Acceptance Criteria

1. WHEN job description text is provided, THE CLI_Agent SHALL extract required skills using LLM_Service
2. WHEN job description text is provided, THE CLI_Agent SHALL extract key responsibilities using LLM_Service
3. WHEN job description text is provided, THE CLI_Agent SHALL extract required qualifications using LLM_Service
4. WHEN job description text is provided, THE CLI_Agent SHALL extract nice-to-have skills using LLM_Service
5. THE CLI_Agent SHALL perform keyword extraction as fallback when LLM_Service is unavailable
6. THE CLI_Agent SHALL identify at least 20 predefined technical keywords (python, machine learning, sql, api, git, etc.)
7. THE CLI_Agent SHALL save job analysis results to Output_Folder as job_analysis_report.txt
8. THE Job_Analysis_Report SHALL include timestamp, file names, extracted keywords, and LLM analysis

### Requirement 3: Resume Analysis

**User Story:** As a job seeker, I want the system to analyze my resume and identify my skills, so that I can understand my current qualifications.

#### Acceptance Criteria

1. WHEN resume text is provided, THE CLI_Agent SHALL extract technical skills using LLM_Service
2. WHEN resume text is provided, THE CLI_Agent SHALL extract soft skills using LLM_Service
3. WHEN resume text is provided, THE CLI_Agent SHALL extract projects and achievements using LLM_Service
4. WHEN resume text is provided, THE CLI_Agent SHALL extract education and experience using LLM_Service
5. THE CLI_Agent SHALL perform keyword extraction as fallback when LLM_Service is unavailable
6. THE Web_Application SHALL calculate ATS_Score (0-100) for uploaded resumes
7. THE Web_Application SHALL store resume text and extracted skills in the database

### Requirement 4: Skill Gap Calculation

**User Story:** As a job seeker, I want to see which skills I'm missing for a job, so that I can focus my learning efforts.

#### Acceptance Criteria

1. WHEN job skills and resume skills are available, THE CLI_Agent SHALL identify matched skills
2. WHEN job skills and resume skills are available, THE CLI_Agent SHALL identify missing skills
3. THE CLI_Agent SHALL calculate match percentage as (matched_skills / total_job_skills) * 100
4. THE CLI_Agent SHALL use LLM_Service to provide detailed skill gap explanation
5. THE CLI_Agent SHALL save skill gap analysis to Output_Folder as skill_gap_report.txt
6. THE Skill_Gap_Report SHALL include match score, matched skills list, missing skills list, and LLM analysis
7. THE Web_Application SHALL provide skill gap analysis comparing resume against multiple job descriptions
8. THE Web_Application SHALL calculate frequency of missing skills across multiple jobs

### Requirement 5: Resume Tailoring Suggestions

**User Story:** As a job seeker, I want specific suggestions to improve my resume for a job, so that I can increase my chances of getting interviews.

#### Acceptance Criteria

1. WHEN skill gap analysis is complete, THE CLI_Agent SHALL generate actionable resume improvement suggestions
2. THE CLI_Agent SHALL use LLM_Service to create specific bullet points for missing skills
3. THE CLI_Agent SHALL provide at least 3 concrete improvement tips
4. THE CLI_Agent SHALL save suggestions to Output_Folder as tailored_resume_suggestions.txt
5. THE Resume_Suggestions SHALL include evidence-based recommendations for top 5 missing skills
6. WHEN LLM_Service is unavailable, THE CLI_Agent SHALL provide template-based suggestions

### Requirement 6: Interview Question Generation

**User Story:** As a job seeker, I want practice interview questions based on the job and my knowledge base, so that I can prepare effectively.

#### Acceptance Criteria

1. WHEN job description and Knowledge_Base are available, THE CLI_Agent SHALL generate technical interview questions
2. WHEN job description and Knowledge_Base are available, THE CLI_Agent SHALL generate behavioral interview questions
3. WHEN job description and Knowledge_Base are available, THE CLI_Agent SHALL generate knowledge-base-specific questions
4. THE CLI_Agent SHALL generate at least 5 questions in each category (technical, behavioral, KB-based)
5. THE CLI_Agent SHALL save questions to Output_Folder as interview_questions.txt
6. THE Web_Application SHALL generate interview questions with suggested answers
7. THE Web_Application SHALL accept role and optional job description for question generation

### Requirement 7: Application Tracking

**User Story:** As a job seeker, I want to track my job applications with status and dates, so that I can manage my job search process.

#### Acceptance Criteria

1. THE CLI_Agent SHALL maintain application data in CSV format with 10 columns
2. THE Application_Tracker SHALL include columns: application_id, company, role, source, status, applied_date, interview_date, follow_up_date, next_action, notes
3. WHEN a new application is added, THE CLI_Agent SHALL generate unique application_id in format APP-YYYYMMDDHHMMSS
4. THE CLI_Agent SHALL support status values: Not Applied, Applied, Interview Scheduled, Rejected, Offered
5. WHEN status is "Applied", THE CLI_Agent SHALL automatically set follow_up_date to 5 days after applied_date
6. THE CLI_Agent SHALL allow updating application status, interview_date, follow_up_date, and next_action
7. THE CLI_Agent SHALL save Application_Tracker to Tracker_Folder as applications.csv
8. THE Web_Application SHALL store applications in SQLite database with similar fields
9. THE Web_Application SHALL support filtering applications by status
10. THE Web_Application SHALL link applications to job records when available

### Requirement 8: Reminder System

**User Story:** As a job seeker, I want reminders for upcoming interviews and follow-ups with urgency indicators, so that I don't miss important deadlines.

#### Acceptance Criteria

1. WHEN Application_Tracker contains interview_date, THE CLI_Agent SHALL generate interview preparation reminders
2. WHEN Application_Tracker contains follow_up_date, THE CLI_Agent SHALL generate follow-up reminders
3. WHEN status is "Not Applied", THE CLI_Agent SHALL generate application reminders
4. THE CLI_Agent SHALL calculate Urgency_Level based on date difference from current date
5. WHEN date difference is negative, THE CLI_Agent SHALL mark reminder as "OVERDUE (X days)"
6. WHEN date difference is 0, THE CLI_Agent SHALL mark reminder as "TODAY"
7. WHEN date difference is 1, THE CLI_Agent SHALL mark reminder as "TOMORROW"
8. WHEN date difference is 2-7, THE CLI_Agent SHALL mark reminder as "THIS WEEK (X days)"
9. WHEN date difference is greater than 7, THE CLI_Agent SHALL mark reminder as "In X days"
10. THE CLI_Agent SHALL save reminders to Tracker_Folder as reminders.txt
11. THE Reminders_File SHALL include urgency level, application_id, company, date, and action

### Requirement 9: Application Dashboard

**User Story:** As a job seeker, I want a summary dashboard of my applications by status, so that I can see my job search progress at a glance.

#### Acceptance Criteria

1. WHEN Application_Tracker exists, THE CLI_Agent SHALL generate dashboard summary
2. THE Dashboard SHALL display total number of applications
3. THE Dashboard SHALL display count of applications for each status
4. THE Dashboard SHALL calculate percentage for each status relative to total
5. THE Dashboard SHALL format status counts with alignment and percentage display
6. THE Dashboard SHALL be included in final report and viewable via menu option
7. THE Web_Application SHALL display dashboard on home page with visual charts

### Requirement 10: Cover Letter Generation

**User Story:** As a job seeker, I want AI-generated cover letters tailored to specific jobs, so that I can save time while maintaining quality.

#### Acceptance Criteria

1. WHEN job description, resume, company name, and role are provided, THE CLI_Agent SHALL generate cover letter
2. THE CLI_Agent SHALL use LLM_Service with temperature 0.8 for creative writing
3. THE Cover_Letter SHALL be 250-300 words in length
4. THE Cover_Letter SHALL include professional greeting, body, and closing
5. THE CLI_Agent SHALL save cover letter to Output_Folder as cover_letter.txt
6. WHEN LLM_Service is unavailable, THE CLI_Agent SHALL generate template-based cover letter
7. THE Web_Application SHALL accept job description, company, and role for cover letter generation
8. THE Web_Application SHALL return cover letter draft via API endpoint

### Requirement 11: LinkedIn Message Generation

**User Story:** As a job seeker, I want professional LinkedIn outreach messages, so that I can network effectively with recruiters and hiring managers.

#### Acceptance Criteria

1. WHEN company name and role are provided, THE CLI_Agent SHALL generate LinkedIn message
2. THE CLI_Agent SHALL use LLM_Service with temperature 0.8 for creative writing
3. THE LinkedIn_Message SHALL be 100-150 words in length
4. THE LinkedIn_Message SHALL maintain professional and friendly tone
5. THE CLI_Agent SHALL save message to Output_Folder as linkedin_message.txt
6. WHEN LLM_Service is unavailable, THE CLI_Agent SHALL generate template-based message

### Requirement 12: Memory System

**User Story:** As a job seeker, I want the system to remember my previous analysis sessions, so that I can track my progress over time.

#### Acceptance Criteria

1. WHEN analysis is complete, THE CLI_Agent SHALL save session data to Memory_System
2. THE Memory_System SHALL store timestamp, job_skills, resume_skills, kb_topics, and match_score
3. THE Memory_System SHALL use JSON format for data storage
4. THE CLI_Agent SHALL save memory to Tracker_Folder as memory.json
5. THE Memory_System SHALL implement GAME_Framework memory component
6. THE Memory_System SHALL be readable by both CLI_Agent and Web_Application

### Requirement 13: LLM Integration

**User Story:** As a job seeker, I want intelligent AI-powered analysis beyond simple keyword matching, so that I get deeper insights.

#### Acceptance Criteria

1. THE CLI_Agent SHALL support OpenRouter API with meta-llama/llama-3.1-8b-instruct model
2. THE CLI_Agent SHALL support Groq API with llama3-8b-8192 model
3. WHEN API key starts with "sk-or-v1-", THE CLI_Agent SHALL use OpenRouter endpoint
4. WHEN API key starts with "gsk_", THE CLI_Agent SHALL use Groq endpoint
5. THE CLI_Agent SHALL load API key from environment variable GROQ_API_KEY
6. THE LLM_Service SHALL accept system prompt, user prompt, and temperature parameters
7. THE LLM_Service SHALL use max_tokens limit of 1024
8. WHEN LLM_Service call fails, THE CLI_Agent SHALL fall back to keyword-based analysis
9. THE Web_Application SHALL use Groq API for all AI-powered features
10. THE LLM_Service SHALL handle API errors gracefully and return error messages

### Requirement 14: Job Search Integration

**User Story:** As a job seeker, I want to search for jobs from multiple sources in one place, so that I can find more opportunities efficiently.

#### Acceptance Criteria

1. THE Web_Application SHALL integrate with RemoteOK API for remote job listings
2. THE Web_Application SHALL integrate with Arbeitnow API for job listings
3. THE Web_Application SHALL integrate with Adzuna API for job listings
4. WHEN job search is requested, THE Web_Application SHALL fetch jobs from all three Job_API sources
5. THE Web_Application SHALL deduplicate jobs by external_id across sources
6. THE Web_Application SHALL store fetched jobs in database with source attribution
7. THE Web_Application SHALL include fields: source, external_id, title, company, location, description, url, posted_date
8. THE Web_Application SHALL prevent duplicate storage of jobs with same external_id
9. THE Web_Application SHALL accept search query parameter for job filtering

### Requirement 15: Interactive CLI Menu

**User Story:** As a job seeker, I want an easy-to-use menu interface, so that I can access all features without remembering commands.

#### Acceptance Criteria

1. THE CLI_Agent SHALL display menu with 9 options on startup
2. THE CLI_Agent SHALL support option 1: Run Full Analysis
3. THE CLI_Agent SHALL support option 2: List Job Files
4. THE CLI_Agent SHALL support option 3: List Resume Files
5. THE CLI_Agent SHALL support option 4: Add Application
6. THE CLI_Agent SHALL support option 5: Update Application
7. THE CLI_Agent SHALL support option 6: List Applications
8. THE CLI_Agent SHALL support option 7: View Reminders
9. THE CLI_Agent SHALL support option 8: View Dashboard
10. THE CLI_Agent SHALL support option 9: Exit
11. THE CLI_Agent SHALL loop menu until user selects Exit
12. WHEN invalid option is entered, THE CLI_Agent SHALL display error message and redisplay menu

### Requirement 16: Report Generation

**User Story:** As a job seeker, I want comprehensive reports of all analysis results, so that I can review and share my job search insights.

#### Acceptance Criteria

1. WHEN full analysis is complete, THE CLI_Agent SHALL generate final_agent_report.txt
2. THE Final_Report SHALL include summary section with file counts and match statistics
3. THE Final_Report SHALL include complete job analysis report
4. THE Final_Report SHALL include complete skill gap report
5. THE Final_Report SHALL include complete resume suggestions
6. THE Final_Report SHALL include complete interview questions
7. THE Final_Report SHALL include application dashboard
8. THE Final_Report SHALL include reminders with urgency levels
9. THE Final_Report SHALL include generation timestamp
10. THE CLI_Agent SHALL save Final_Report to Output_Folder
11. WHERE PDF export library is available, THE CLI_Agent SHALL export Final_Report as PDF

### Requirement 17: Web Application Frontend

**User Story:** As a job seeker, I want a modern web interface to access job search features, so that I can work from any device with a browser.

#### Acceptance Criteria

1. THE Web_Application SHALL provide React-based frontend with 7 pages
2. THE Web_Application SHALL include Dashboard page showing application statistics
3. THE Web_Application SHALL include Resume page for uploading and analyzing resumes
4. THE Web_Application SHALL include Jobs page for searching and viewing job listings
5. THE Web_Application SHALL include Applications page for managing job applications
6. THE Web_Application SHALL include CoverLetter page for generating cover letters
7. THE Web_Application SHALL include Interview page for interview preparation
8. THE Web_Application SHALL include SkillGap page for skill gap analysis
9. THE Web_Application SHALL use React Router for navigation between pages
10. THE Web_Application SHALL provide consistent layout with navigation menu

### Requirement 18: API Endpoints

**User Story:** As a developer, I want RESTful API endpoints for all features, so that I can integrate job search functionality into other applications.

#### Acceptance Criteria

1. THE Web_Application SHALL provide POST /resume/analyze endpoint accepting PDF file upload
2. THE Web_Application SHALL provide GET /jobs/search endpoint accepting query parameter
3. THE Web_Application SHALL provide GET /jobs/{job_id}/match endpoint for job matching
4. THE Web_Application SHALL provide POST /applications endpoint for creating applications
5. THE Web_Application SHALL provide GET /applications endpoint for listing applications
6. THE Web_Application SHALL provide GET /applications/{app_id} endpoint for retrieving application
7. THE Web_Application SHALL provide PATCH /applications/{app_id}/status endpoint for status updates
8. THE Web_Application SHALL provide POST /intelligence/skill-gap endpoint for skill gap analysis
9. THE Web_Application SHALL provide POST /intelligence/interview-prep endpoint for interview questions
10. THE Web_Application SHALL provide POST /cover-letter/generate endpoint for cover letter generation
11. THE Web_Application SHALL use FastAPI framework for API implementation
12. THE Web_Application SHALL enable CORS for frontend access

### Requirement 19: Database Management

**User Story:** As a system administrator, I want persistent storage of user data, so that job seekers can access their information across sessions.

#### Acceptance Criteria

1. THE Web_Application SHALL use SQLite database for data persistence
2. THE Web_Application SHALL define UserProfile table with fields: id, resume_text, skills, latest_ats_score, created_at
3. THE Web_Application SHALL define Job table with fields: id, source, external_id, title, company, location, description, url, posted_date, fetched_at
4. THE Web_Application SHALL define Application table with fields: id, job_id, company, role, applied_date, status, notes, resume_version, contact_email
5. THE Web_Application SHALL enforce unique constraint on Job.external_id
6. THE Web_Application SHALL use SQLAlchemy ORM for database operations
7. THE Web_Application SHALL create tables automatically on startup if they don't exist

### Requirement 20: Error Handling and Fallbacks

**User Story:** As a job seeker, I want the system to work even when external services fail, so that I can continue my job search without interruption.

#### Acceptance Criteria

1. WHEN LLM_Service is unavailable, THE CLI_Agent SHALL use keyword-based analysis
2. WHEN PDF library is unavailable, THE CLI_Agent SHALL skip PDF files and process TXT files
3. WHEN Job_API request fails, THE Web_Application SHALL return empty results without crashing
4. WHEN file read fails, THE CLI_Agent SHALL log error and continue with other files
5. WHEN JSON parsing fails for LLM response, THE Web_Application SHALL return fallback values
6. THE CLI_Agent SHALL display warning message when LLM_Service is not available
7. THE CLI_Agent SHALL display warning message when PDF support is not available
8. WHEN database query fails, THE Web_Application SHALL return appropriate HTTP error status
9. THE System SHALL handle UTF-8 encoding errors gracefully

### Requirement 21: Configuration Management

**User Story:** As a job seeker, I want to configure API keys and settings without modifying code, so that I can easily set up the system.

#### Acceptance Criteria

1. THE System SHALL load configuration from .env file in root directory
2. THE System SHALL read GROQ_API_KEY from environment variables
3. THE Web_Application SHALL read ADZUNA_APP_ID from environment variables
4. THE Web_Application SHALL read ADZUNA_APP_KEY from environment variables
5. THE System SHALL provide .env.example files showing required configuration
6. THE System SHALL function with partial configuration (e.g., without Adzuna keys)
7. THE System SHALL validate API key format on startup

### Requirement 22: Folder Structure Management

**User Story:** As a job seeker, I want the system to create necessary folders automatically, so that I don't have to set up the directory structure manually.

#### Acceptance Criteria

1. WHEN CLI_Agent starts, THE CLI_Agent SHALL create input_jobs folder if it doesn't exist
2. WHEN CLI_Agent starts, THE CLI_Agent SHALL create input_resumes folder if it doesn't exist
3. WHEN CLI_Agent starts, THE CLI_Agent SHALL create input_kb folder if it doesn't exist
4. WHEN CLI_Agent starts, THE CLI_Agent SHALL create outputs folder if it doesn't exist
5. WHEN CLI_Agent starts, THE CLI_Agent SHALL create tracker folder if it doesn't exist
6. WHEN CLI_Agent starts, THE CLI_Agent SHALL create samples folder if it doesn't exist
7. THE CLI_Agent SHALL use os.makedirs with exist_ok=True for folder creation

### Requirement 23: Sample Data Provision

**User Story:** As a new user, I want sample files to test the system, so that I can understand how it works before adding my own data.

#### Acceptance Criteria

1. THE System SHALL provide sample_job_poster.txt in samples folder
2. THE System SHALL provide sample_resume.txt in samples folder
3. THE System SHALL provide sample_kb.txt in samples folder
4. THE Sample_Files SHALL contain realistic example content
5. THE Documentation SHALL explain how to use sample files for testing

### Requirement 24: Professional Output Formatting

**User Story:** As a job seeker, I want well-formatted reports that are easy to read, so that I can quickly understand the analysis results.

#### Acceptance Criteria

1. THE CLI_Agent SHALL use separator lines (80 characters) for report sections
2. THE CLI_Agent SHALL include timestamps in all generated reports
3. THE CLI_Agent SHALL use consistent heading styles across all reports
4. THE CLI_Agent SHALL format lists with bullet points or dashes
5. THE CLI_Agent SHALL align dashboard statistics for readability
6. THE CLI_Agent SHALL include file names in reports to show data sources
7. THE Reports SHALL use clear section labels (SUMMARY, MATCHED, MISSING, etc.)

### Requirement 25: Performance and Scalability

**User Story:** As a job seeker with many applications, I want the system to handle large amounts of data efficiently, so that I don't experience slowdowns.

#### Acceptance Criteria

1. THE CLI_Agent SHALL process files with content up to 10,000 characters without performance degradation
2. THE CLI_Agent SHALL truncate LLM prompts to 2000 characters to stay within token limits
3. THE Web_Application SHALL limit job search results to prevent API overload
4. THE Web_Application SHALL use database indexing on frequently queried fields
5. THE LLM_Service SHALL use timeout of 10 seconds for API requests
6. THE Application_Tracker SHALL handle at least 1000 application records efficiently

### Requirement 26: Cross-Platform Compatibility

**User Story:** As a job seeker using different operating systems, I want the system to work on Windows, Mac, and Linux, so that I can use my preferred platform.

#### Acceptance Criteria

1. THE CLI_Agent SHALL use os.path.join for cross-platform file path handling
2. THE CLI_Agent SHALL use UTF-8 encoding for all file operations
3. THE System SHALL use Python 3.8+ compatible syntax and libraries
4. THE Web_Application SHALL use standard HTTP protocols for cross-platform browser access
5. THE Documentation SHALL include setup instructions for multiple platforms

### Requirement 27: Testing and Validation

**User Story:** As a developer, I want to verify that all features work correctly, so that I can ensure system reliability.

#### Acceptance Criteria

1. THE System SHALL provide test scripts for running CLI_Agent
2. THE System SHALL provide test scripts for running Web_Application
3. THE Documentation SHALL include testing procedures
4. THE System SHALL validate that all required files are present before analysis
5. THE System SHALL display clear error messages when validation fails
6. THE CLI_Agent SHALL confirm successful file reading with [OK] status messages
7. THE CLI_Agent SHALL display completion message after full analysis

### Requirement 28: Documentation and Help

**User Story:** As a new user, I want comprehensive documentation, so that I can set up and use the system without external help.

#### Acceptance Criteria

1. THE System SHALL provide README.md with setup instructions
2. THE System SHALL provide QUICKSTART.md with quick start guide
3. THE Documentation SHALL explain GAME framework implementation
4. THE Documentation SHALL list all 10+ unique features
5. THE Documentation SHALL include API endpoint documentation
6. THE Documentation SHALL explain folder structure and file organization
7. THE Documentation SHALL provide troubleshooting guidance
8. THE Web_Application SHALL provide API documentation at /docs endpoint

### Requirement 29: Version Control Integration

**User Story:** As a developer, I want the system to integrate with version control, so that I can track changes and collaborate.

#### Acceptance Criteria

1. THE System SHALL provide .gitignore file excluding sensitive data
2. THE .gitignore SHALL exclude .env files containing API keys
3. THE .gitignore SHALL exclude venv and node_modules folders
4. THE .gitignore SHALL exclude database files
5. THE System SHALL include all source code in version control
6. THE System SHALL provide setup scripts for easy deployment

### Requirement 30: Deployment Support

**User Story:** As a user, I want easy deployment scripts, so that I can quickly set up the system on new machines.

#### Acceptance Criteria

1. THE System SHALL provide setup.sh script for CLI_Agent setup
2. THE System SHALL provide setup-all.sh script for full system setup
3. THE System SHALL provide run.sh script for starting backend server
4. THE System SHALL provide run-all.sh script for starting all services
5. THE Setup_Scripts SHALL install Python dependencies from requirements.txt
6. THE Setup_Scripts SHALL install Node.js dependencies for frontend
7. THE Setup_Scripts SHALL create virtual environment for Python
8. THE Documentation SHALL explain deployment process step-by-step
