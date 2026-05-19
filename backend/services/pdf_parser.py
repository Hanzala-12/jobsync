def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fitz).

    If PyMuPDF is not installed, return an empty string and do not raise
    an ImportError so the backend can start without the optional dependency.
    """
    try:
        import fitz  # PyMuPDF
    except Exception:
        return ""

    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception:
        return ""
