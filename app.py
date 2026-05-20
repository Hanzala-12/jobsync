"""
CareerPrep Job-Hunting Agent
A file-driven AI agent for job search, resume tailoring, and application tracking
Enhanced with Groq LLM for intelligent analysis
"""

import os
import csv
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

from core.rag_service import generate_cover_letter_with_rag, save_cover_letter_artifacts

# Try to import PDF support (optional)
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Try to import FPDF for PDF export (optional)
try:
    from fpdf import FPDF
    PDF_EXPORT = True
except ImportError:
    PDF_EXPORT = False

# Load environment variables
load_dotenv()

# Folder paths
JOB_DIR = "input_jobs"
RESUME_DIR = "input_resumes"
KB_DIR = "input_kb"
OUTPUT_DIR = "outputs"
TRACKER_DIR = "tracker"
SAMPLES_DIR = "samples"

# Professor's required keywords (fallback)
KEYWORDS = [
    "python", "machine learning", "data preprocessing", "github", "git",
    "api", "prompt engineering", "sql", "communication", "problem solving",
    "oop", "database", "jupyter", "pandas", "numpy", "deep learning",
    "html", "css", "flask", "streamlit", "resume", "interview"
]

# Initialize LLM client (supports both Groq and OpenRouter)
try:
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.startswith("sk-or-v1-"):
        # OpenRouter API key detected
        from openai import OpenAI
        groq_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        LLM_MODEL = "meta-llama/llama-3.1-8b-instruct"
        LLM_AVAILABLE = True
        print("Using OpenRouter API with Llama 3")
    elif api_key and api_key.startswith("gsk_"):
        # Groq API key
        groq_client = Groq(api_key=api_key)
        LLM_MODEL = "llama3-8b-8192"
        LLM_AVAILABLE = True
        print("Using Groq API with Llama 3")
    else:
        LLM_AVAILABLE = False
        print("Warning: No valid API key. Using keyword-based analysis only.")
except Exception as e:
    LLM_AVAILABLE = False
    print(f"Warning: LLM API not available ({e}). Using keyword-based analysis only.")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_folders():
    """Create all required folders if they don't exist"""
    for folder in [JOB_DIR, RESUME_DIR, KB_DIR, OUTPUT_DIR, TRACKER_DIR, SAMPLES_DIR]:
        os.makedirs(folder, exist_ok=True)


def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    if not PDF_SUPPORT:
        return ""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""


def read_text_files(folder):
    """Read all TXT and PDF files from a folder"""
    combined_text = ""
    file_list = []
    
    if not os.path.exists(folder):
        return combined_text, file_list
    
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        
        if filename.lower().endswith(".txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    combined_text += f"\n\n--- FILE: {filename} ---\n{content}"
                    file_list.append(filename)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
        
        elif filename.lower().endswith(".pdf") and PDF_SUPPORT:
            content = extract_text_from_pdf(file_path)
            if content:
                combined_text += f"\n\n--- FILE: {filename} ---\n{content}"
                file_list.append(filename)
    
    return combined_text, file_list


def save_text(path, content):
    """Save text content to file"""
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"Error saving {path}: {e}")
        return False


def ask_llm(prompt, system_prompt="You are a helpful career AI assistant.", temperature=0.7):
    """Call LLM for intelligent analysis (supports Groq and OpenRouter)"""
    if not LLM_AVAILABLE:
        return None
    
    try:
        completion = groq_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        return None


# ============================================================================
# KEYWORD EXTRACTION (Fallback)
# ============================================================================

def extract_keywords(text):
    """Extract keywords from text (professor's requirement)"""
    text_lower = text.lower()
    found = []
    for keyword in KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)
    return list(set(found))


# ============================================================================
# LLM-ENHANCED ANALYSIS
# ============================================================================

def analyze_job_with_llm(job_text):
    """Use LLM to analyze job description"""
    prompt = f"""Analyze this job description and extract:
1. Required skills (technical and soft skills)
2. Key responsibilities
3. Required qualifications
4. Nice-to-have skills

Job Description:
{job_text[:2000]}

Provide a structured analysis."""
    
    llm_response = ask_llm(prompt)
    keyword_skills = extract_keywords(job_text)
    
    return {
        "llm_analysis": llm_response if llm_response else "LLM analysis not available",
        "keyword_skills": keyword_skills
    }


def analyze_resume_with_llm(resume_text):
    """Use LLM to analyze resume"""
    prompt = f"""Analyze this resume and extract:
1. Technical skills
2. Soft skills
3. Projects and achievements
4. Education and experience
5. Strengths

Resume:
{resume_text[:2000]}

Provide a structured analysis."""
    
    llm_response = ask_llm(prompt)
    keyword_skills = extract_keywords(resume_text)
    
    return {
        "llm_analysis": llm_response if llm_response else "LLM analysis not available",
        "keyword_skills": keyword_skills
    }


def calculate_skill_gap_with_llm(job_text, resume_text, job_skills, resume_skills):
    """Use LLM to calculate skill gap and match percentage"""
    matched = [skill for skill in job_skills if skill in resume_skills]
    missing = [skill for skill in job_skills if skill not in resume_skills]
    keyword_score = 0 if not job_skills else round((len(matched) / len(job_skills)) * 100, 2)
    
    prompt = f"""Compare this resume with the job requirements and provide:
1. Match percentage (0-100)
2. Matched skills
3. Missing skills
4. Detailed explanation

Job Requirements:
{job_text[:1500]}

Resume:
{resume_text[:1500]}

Provide detailed skill-gap analysis."""
    
    llm_response = ask_llm(prompt)
    
    return {
        "keyword_matched": matched,
        "keyword_missing": missing,
        "keyword_score": keyword_score,
        "llm_analysis": llm_response if llm_response else "LLM analysis not available"
    }


def generate_resume_suggestions_with_llm(job_text, resume_text, missing_skills):
    """Use LLM to generate tailored resume suggestions"""
    prompt = f"""Based on this job and resume, provide specific resume improvement suggestions:

Job Description:
{job_text[:1500]}

Resume:
{resume_text[:1500]}

Missing Skills: {', '.join(missing_skills)}

Provide actionable bullet points to improve the resume."""
    
    llm_response = ask_llm(prompt)
    
    basic_suggestions = f"""Tailored Resume Suggestions
===========================

Based on job requirements:

"""
    for skill in missing_skills[:5]:
        basic_suggestions += f"- Add evidence of {skill} experience\n"
    
    basic_suggestions += "\nSuggested bullets:\n"
    basic_suggestions += "- Developed Python projects with documentation\n"
    basic_suggestions += "- Used GitHub for version control\n"
    basic_suggestions += "- Applied problem-solving in projects\n"
    
    return {
        "llm_suggestions": llm_response if llm_response else basic_suggestions,
        "basic_suggestions": basic_suggestions
    }


def generate_interview_questions_with_llm(job_text, kb_text, job_skills):
    """Use LLM to generate interview questions"""
    prompt = f"""Generate interview questions for this role:

Job Description:
{job_text[:1500]}

Knowledge Base:
{kb_text[:1500]}

Skills: {', '.join(job_skills)}

Generate:
1. 5 technical questions
2. 5 behavioral questions
3. 5 KB-based questions"""
    
    llm_response = ask_llm(prompt)
    
    basic_questions = f"""Interview Questions
===================

Technical Questions:
"""
    for skill in job_skills[:5]:
        basic_questions += f"- Explain your experience with {skill}\n"
    
    basic_questions += "\nBehavioral Questions:\n"
    basic_questions += "- Tell me about yourself\n"
    basic_questions += "- Why this role?\n"
    basic_questions += "- Describe your best project\n"
    
    return {
        "llm_questions": llm_response if llm_response else basic_questions,
        "basic_questions": basic_questions
    }


# ============================================================================
# UNIQUE FEATURES
# ============================================================================

def generate_cover_letter(job_text, resume_summary, company_name, role, job_id=None, tone="professional"):
    """Generate a RAG-enhanced cover letter and persist provenance."""
    cover_letter, source_ids, retrieved_chunks = generate_cover_letter_with_rag(
        job_text,
        resume_summary,
        company_name=company_name,
        role=role,
        tone=tone,
        top_k=5,
    )
    save_cover_letter_artifacts(
        job_id,
        cover_letter,
        source_ids,
        retrieved_chunks,
        metadata={
            "company_name": company_name,
            "role": role,
            "job_text": job_text,
            "resume_summary": resume_summary,
        },
    )
    return cover_letter, source_ids


def generate_linkedin_message(company_name, role):
    """Generate LinkedIn message"""
    prompt = f"""Write a brief LinkedIn message:

Company: {company_name}
Role: {role}

100-150 words, professional."""
    
    llm_response = ask_llm(prompt, temperature=0.8)
    
    if llm_response:
        return llm_response
    else:
        return f"""Hi,

I'm interested in the {role} position at {company_name}.

Would you be open to a brief conversation?

Best regards"""


def generate_application_dashboard(tracker_path):
    """Generate dashboard"""
    if not os.path.exists(tracker_path):
        return "No applications yet."
    
    status_counts = {}
    total = 0
    
    with open(tracker_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            status = row.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            total += 1
    
    dashboard = "\n" + "="*50 + "\n"
    dashboard += "APPLICATION DASHBOARD\n"
    dashboard += "="*50 + "\n\n"
    dashboard += f"Total: {total}\n\n"
    
    for status, count in sorted(status_counts.items()):
        pct = (count / total * 100) if total > 0 else 0
        dashboard += f"{status:.<25} {count:>3} ({pct:.1f}%)\n"
    
    dashboard += "="*50 + "\n"
    return dashboard


def calculate_reminder_urgency(date_str):
    """Calculate urgency"""
    if not date_str:
        return "No date"
    
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now()
        diff = (target - today).days
        
        if diff < 0:
            return f"OVERDUE ({abs(diff)} days)"
        elif diff == 0:
            return "TODAY"
        elif diff == 1:
            return "TOMORROW"
        elif diff <= 7:
            return f"THIS WEEK ({diff} days)"
        else:
            return f"In {diff} days"
    except:
        return "Invalid date"


def export_report_as_pdf(final_report, output_path):
    """Export as PDF"""
    if not PDF_EXPORT:
        return False
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        for line in final_report.split('\n'):
            pdf.multi_cell(0, 5, txt=line, align='L')
        
        pdf.output(output_path)
        return True
    except:
        return False


# ============================================================================
# MEMORY SYSTEM
# ============================================================================

def save_memory(job_skills, resume_skills, kb_topics, match_score):
    """Save session memory"""
    memory = {
        "timestamp": datetime.now().isoformat(),
        "job_skills": job_skills,
        "resume_skills": resume_skills,
        "kb_topics": kb_topics,
        "match_score": match_score
    }
    
    memory_path = os.path.join(TRACKER_DIR, "memory.json")
    try:
        with open(memory_path, "w", encoding="utf-8") as file:
            json.dump(memory, file, indent=2)
        return True
    except:
        return False


# ============================================================================
# TRACKER
# ============================================================================

def create_tracker_if_not_exists():
    """Create tracker CSV"""
    tracker_path = os.path.join(TRACKER_DIR, "applications.csv")
    
    if not os.path.exists(tracker_path):
        with open(tracker_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "application_id", "company", "role", "source", "status",
                "applied_date", "interview_date", "follow_up_date", "next_action", "notes"
            ])
    
    return tracker_path


def add_application(company, role, source, status="Not Applied", notes=""):
    """Add application"""
    tracker_path = create_tracker_if_not_exists()
    
    app_id = f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    applied_date = datetime.now().strftime("%Y-%m-%d") if status != "Not Applied" else ""
    follow_up_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d") if status == "Applied" else ""
    next_action = "Tailor resume and apply" if status == "Not Applied" else "Wait for response"
    
    with open(tracker_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            app_id, company, role, source, status,
            applied_date, "", follow_up_date, next_action, notes
        ])
    
    print(f"\nApplication {app_id} added!")
    return app_id


def update_application_status(app_id, new_status, interview_date=None, follow_up_date=None, next_action=None):
    """Update status"""
    tracker_path = create_tracker_if_not_exists()
    
    rows = []
    updated = False
    
    with open(tracker_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        
        for row in reader:
            if row["application_id"] == app_id:
                row["status"] = new_status
                if interview_date:
                    row["interview_date"] = interview_date
                if follow_up_date:
                    row["follow_up_date"] = follow_up_date
                if next_action:
                    row["next_action"] = next_action
                updated = True
            rows.append(row)
    
    if updated:
        with open(tracker_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nApplication {app_id} updated!")
    else:
        print(f"\nApplication {app_id} not found.")
    
    return updated


def list_applications():
    """List all applications"""
    tracker_path = create_tracker_if_not_exists()
    
    print("\n" + "="*80)
    print("ALL APPLICATIONS")
    print("="*80)
    
    with open(tracker_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            print(f"\nID: {row['application_id']}")
            print(f"Company: {row['company']}")
            print(f"Role: {row['role']}")
            print(f"Status: {row['status']}")
            if row['applied_date']:
                print(f"Applied: {row['applied_date']}")
            if row['interview_date']:
                print(f"Interview: {row['interview_date']}")
            print(f"Next: {row['next_action']}")
            print("-" * 80)


def generate_reminders():
    """Generate reminders"""
    tracker_path = create_tracker_if_not_exists()
    
    reminders = "\n" + "="*80 + "\n"
    reminders += "APPLICATION REMINDERS\n"
    reminders += "="*80 + "\n\n"
    
    with open(tracker_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            app_id = row.get("application_id", "")
            company = row.get("company", "")
            role = row.get("role", "")
            status = row.get("status", "")
            interview_date = row.get("interview_date", "")
            follow_up_date = row.get("follow_up_date", "")
            next_action = row.get("next_action", "")
            
            if status == "Interview Scheduled" and interview_date:
                urgency = calculate_reminder_urgency(interview_date)
                reminders += f"[{urgency}] {app_id}: Interview with {company}\n"
                reminders += f"  Date: {interview_date}\n"
                reminders += f"  Action: {next_action}\n\n"
            
            elif status == "Not Applied":
                reminders += f"[PENDING] {app_id}: Not applied for {role} at {company}\n"
                reminders += f"  Action: {next_action}\n\n"
            
            elif status == "Applied" and follow_up_date:
                urgency = calculate_reminder_urgency(follow_up_date)
                reminders += f"[{urgency}] {app_id}: Follow up with {company}\n"
                reminders += f"  Date: {follow_up_date}\n\n"
    
    reminders += "="*80 + "\n"
    return reminders


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def run_full_analysis():
    """Run complete analysis"""
    print("\n" + "="*80)
    print("RUNNING FULL ANALYSIS")
    print("="*80 + "\n")
    
    print("Reading files...")
    job_text, job_files = read_text_files(JOB_DIR)
    resume_text, resume_files = read_text_files(RESUME_DIR)
    kb_text, kb_files = read_text_files(KB_DIR)
    
    if not job_files or not resume_files or not kb_files:
        print("\nError: Missing files!")
        print(f"Jobs: {len(job_files)}, Resumes: {len(resume_files)}, KB: {len(kb_files)}")
        print("\nAdd .txt or .pdf files to input folders")
        return
    
    print(f"[OK] {len(job_files)} job file(s)")
    print(f"[OK] {len(resume_files)} resume file(s)")
    print(f"[OK] {len(kb_files)} KB file(s)")
    
    print("\nAnalyzing...")
    job_analysis = analyze_job_with_llm(job_text)
    resume_analysis = analyze_resume_with_llm(resume_text)
    skill_gap = calculate_skill_gap_with_llm(
        job_text, resume_text,
        job_analysis["keyword_skills"],
        resume_analysis["keyword_skills"]
    )
    resume_suggestions = generate_resume_suggestions_with_llm(
        job_text, resume_text,
        skill_gap["keyword_missing"]
    )
    interview_questions = generate_interview_questions_with_llm(
        job_text, kb_text,
        job_analysis["keyword_skills"]
    )
    
    print("Generating extras...")
    cover_letter, cover_letter_sources = generate_cover_letter(job_text, resume_text, "Company", "Role")
    linkedin_msg = generate_linkedin_message("Company", "Role")
    
    save_memory(
        job_analysis["keyword_skills"],
        resume_analysis["keyword_skills"],
        kb_files,
        skill_gap["keyword_score"]
    )
    
    print("\nSaving outputs...")
    
    # Job Analysis
    job_report = f"""JOB ANALYSIS REPORT
{'='*80}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FILES: {', '.join(job_files)}

KEYWORDS: {', '.join(job_analysis['keyword_skills'])}

LLM ANALYSIS:
{job_analysis['llm_analysis']}

{'='*80}
"""
    save_text(os.path.join(OUTPUT_DIR, "job_analysis_report.txt"), job_report)
    
    # Skill Gap
    gap_report = f"""SKILL GAP REPORT
{'='*80}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

MATCH SCORE: {skill_gap['keyword_score']}%

MATCHED:
{chr(10).join('- ' + s for s in skill_gap['keyword_matched'])}

MISSING:
{chr(10).join('- ' + s for s in skill_gap['keyword_missing'])}

LLM ANALYSIS:
{skill_gap['llm_analysis']}

{'='*80}
"""
    save_text(os.path.join(OUTPUT_DIR, "skill_gap_report.txt"), gap_report)
    
    # Resume Suggestions
    suggestions_report = f"""TAILORED RESUME SUGGESTIONS
{'='*80}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{resume_suggestions['llm_suggestions']}

{'='*80}
"""
    save_text(os.path.join(OUTPUT_DIR, "tailored_resume_suggestions.txt"), suggestions_report)
    
    # Interview Questions
    questions_report = f"""INTERVIEW QUESTIONS
{'='*80}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{interview_questions['llm_questions']}

{'='*80}
"""
    save_text(os.path.join(OUTPUT_DIR, "interview_questions.txt"), questions_report)
    
    save_text(os.path.join(OUTPUT_DIR, "cover_letter.txt"), cover_letter)
    save_text(os.path.join(OUTPUT_DIR, "cover_letter_sources.txt"), "\n".join(cover_letter_sources))
    save_text(os.path.join(OUTPUT_DIR, "linkedin_message.txt"), linkedin_msg)
    
    reminders = generate_reminders()
    save_text(os.path.join(TRACKER_DIR, "reminders.txt"), reminders)
    
    tracker_path = create_tracker_if_not_exists()
    dashboard = generate_application_dashboard(tracker_path)
    
    # Final Report
    final_report = f"""CAREERPREP JOB-HUNTING AGENT - FINAL REPORT
{'='*80}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Jobs: {len(job_files)}
- Resumes: {len(resume_files)}
- KB: {len(kb_files)}
- Match: {skill_gap['keyword_score']}%
- Matched: {len(skill_gap['keyword_matched'])}
- Missing: {len(skill_gap['keyword_missing'])}

{job_report}

{gap_report}

{suggestions_report}

{questions_report}

{dashboard}

{reminders}

{'='*80}
"""
    save_text(os.path.join(OUTPUT_DIR, "final_agent_report.txt"), final_report)
    
    if PDF_EXPORT:
        pdf_path = os.path.join(OUTPUT_DIR, "final_agent_report.pdf")
        if export_report_as_pdf(final_report, pdf_path):
            print(f"[OK] PDF exported")
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"\nMatch: {skill_gap['keyword_score']}%")
    print(f"Matched: {len(skill_gap['keyword_matched'])}")
    print(f"Missing: {len(skill_gap['keyword_missing'])}")
    print("\nOutputs saved!")
    print(dashboard)


# ============================================================================
# MENU
# ============================================================================

def show_menu():
    """Display menu"""
    print("\n" + "="*80)
    print("CAREERPREP JOB-HUNTING AGENT")
    print("="*80)
    print("\n1. Run Full Analysis")
    print("2. List Job Files")
    print("3. List Resume Files")
    print("4. Add Application")
    print("5. Update Application")
    print("6. List Applications")
    print("7. View Reminders")
    print("8. View Dashboard")
    print("9. Exit")
    print("\n" + "="*80)


def main():
    """Main function"""
    ensure_folders()
    
    while True:
        show_menu()
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            run_full_analysis()
        
        elif choice == "2":
            _, files = read_text_files(JOB_DIR)
            print(f"\nJob files: {', '.join(files) if files else 'None'}")
        
        elif choice == "3":
            _, files = read_text_files(RESUME_DIR)
            print(f"\nResume files: {', '.join(files) if files else 'None'}")
        
        elif choice == "4":
            company = input("Company: ").strip()
            role = input("Role: ").strip()
            source = input("Source: ").strip()
            status = input("Status (Not Applied/Applied/Interview Scheduled): ").strip()
            notes = input("Notes: ").strip()
            add_application(company, role, source, status, notes)
        
        elif choice == "5":
            app_id = input("Application ID: ").strip()
            status = input("New Status: ").strip()
            interview = input("Interview Date (YYYY-MM-DD or blank): ").strip()
            followup = input("Follow-up Date (YYYY-MM-DD or blank): ").strip()
            action = input("Next Action: ").strip()
            update_application_status(
                app_id, status,
                interview if interview else None,
                followup if followup else None,
                action if action else None
            )
        
        elif choice == "6":
            list_applications()
        
        elif choice == "7":
            reminders = generate_reminders()
            print(reminders)
        
        elif choice == "8":
            tracker_path = create_tracker_if_not_exists()
            dashboard = generate_application_dashboard(tracker_path)
            print(dashboard)
        
        elif choice == "9":
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice!")


if __name__ == "__main__":
    main()
