"""
ATS-Friendly PDF Generation
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import os

def generate_resume_pdf(content: str, output_path: str) -> bool:
    """Generate ATS-friendly PDF from resume text"""
    try:
        doc = SimpleDocTemplate(
            output_path, 
            pagesize=letter,
            rightMargin=72, 
            leftMargin=72, 
            topMargin=72, 
            bottomMargin=18
        )
        
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        heading = styles["Heading2"]
        
        story = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.2*inch))
                continue
            
            # Detect headings (all caps or starts with common section names)
            if (line.isupper() or 
                line.startswith("SKILLS") or 
                line.startswith("EXPERIENCE") or
                line.startswith("EDUCATION") or
                line.startswith("PROJECTS")):
                story.append(Paragraph(line, heading))
            else:
                story.append(Paragraph(line, normal))
            
            story.append(Spacer(1, 6))
        
        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF generation error: {e}")
        return False
