from groq import Groq
import json
import os
import pdfplumber
from dotenv import load_dotenv
 
load_dotenv()
 
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
 
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
 
def parse_form16_with_gemini(pdf_path):
    raw_text = extract_text_from_pdf(pdf_path)
 
    prompt = f"""You are a tax expert. Extract all financial details from this Indian Form 16 tax document.
Return ONLY a valid JSON object with exactly these fields. No explanation, no markdown, no backticks.
{{
  "employee_name": "",
  "pan_number": "",
  "employer_name": "",
  "employer_tan": "",
  "assessment_year": "2025-26",
  "gross_salary": 0,
  "hra_exemption": 0,
  "standard_deduction": 50000,
  "professional_tax": 0,
  "total_tds_deducted": 0,
  "net_taxable_salary": 0,
  "section_80c": 0,
  "section_80d": 0,
  "nps_80ccd": 0,
  "other_deductions": 0
}}
Rules:
- All amounts must be numbers only, no commas, no currency symbols
- If a field is not found, use 0 for numbers and empty string for text
- assessment_year should be like "2025-26"
- Return ONLY the JSON object, nothing else
 
Form 16 Text:
{raw_text}"""
 
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
 
    result = response.choices[0].message.content.strip()
 
    # Clean up response
    result = result.replace("```json", "").replace("```", "").strip()
 
    # Parse JSON
    data = json.loads(result)
 
    # Ensure all numeric fields are integers
    numeric_fields = [
        "gross_salary", "hra_exemption", "standard_deduction",
        "professional_tax", "total_tds_deducted", "net_taxable_salary",
        "section_80c", "section_80d", "nps_80ccd", "other_deductions"
    ]
    for field in numeric_fields:
        try:
            data[field] = int(float(str(data.get(field, 0)).replace(",", "")))
        except:
            data[field] = 0
 
    return data