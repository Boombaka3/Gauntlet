# apps/evidence/utils/pdf_parser.py
import io

import pdfplumber

SECTION_HEADERS = {
    "abstract", "introduction", "background",
    "methods", "methodology", "materials and methods",
    "results", "discussion", "conclusion", "conclusions",
    "related work", "limitations",
}


def extract_sections(pdf_bytes: bytes) -> dict:
    sections = {}
    current_section = "body"
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    stripped = line.strip().lower()
                    if stripped in SECTION_HEADERS:
                        current_section = stripped
                    else:
                        sections.setdefault(current_section, "")
                        sections[current_section] += line + "\n"
    except Exception as e:
        sections["body"] = f"PDF parse error: {e}"
    return sections


def get_main_sections(sections: dict) -> dict:
    priority = ["abstract", "results", "discussion",
                "conclusion", "conclusions", "methods"]
    result = {}
    for key in priority:
        if key in sections and sections[key].strip():
            result[key] = sections[key].strip()
    if not result:
        result = {k: v for k, v in sections.items() if v.strip()}
    return result
