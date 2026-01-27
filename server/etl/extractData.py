import pdfplumber
import re
import json
import os

# Get the data directory (1 level up from this file, inside server folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SERVER_DIR, "data")

def clean_line(text):
    """Removes bullet points like 'O', extra spaces, and numeric prefixes."""
    if not text:
        return ""
    # Remove the specific 'O' bullet point seen in your PDF
    text = re.sub(r'^\s*O\s*', '', text) 
    # Remove leading numbers/dots if any (e.g. "1. Name")
    text = re.sub(r'^\d+\.?\s*', '', text)
    return text.strip()

def parse_faculty_section(faculty_text):
    """
    Splits the raw faculty text into categories.
    """
    faculty_obj = {
        "professors": [],
        "associate_professors": [],
        "assistant_professors": [],
        "lecturer": []
    }
    
    # We define the regex patterns for the headers within the faculty section
    # Note: We use IGNORECASE because casing can vary
    patterns = {
        "professors": r'Professors:',
        "associate_professors": r'Associate Professors:',
        "assistant_professors": r'Assistant Professors:',
        "lecturer": r'Lecturers?:'
    }
    
    # Sort patterns by position in text to process them in order
    found_headers = []
    for key, pattern in patterns.items():
        match = re.search(pattern, faculty_text, re.IGNORECASE)
        if match:
            found_headers.append((match.start(), key))
            
    # Sort by start position
    found_headers.sort()
    
    # If no headers found, return empty
    if not found_headers:
        return faculty_obj

    # Iterate through found headers to extract text chunks
    for i in range(len(found_headers)):
        start_idx = found_headers[i][0]
        key_name = found_headers[i][1]
        
        # The end index is the start of the NEXT header, or end of string
        if i + 1 < len(found_headers):
            end_idx = found_headers[i+1][0]
        else:
            end_idx = len(faculty_text)
            
        # Extract the chunk relevant to this header
        # We add the length of the header itself to skip the "Professors:" text
        header_len = len(re.match(patterns[key_name], faculty_text[start_idx:], re.IGNORECASE).group(0))
        raw_chunk = faculty_text[start_idx + header_len : end_idx]
        
        # Split into lines and clean
        names = raw_chunk.split('\n')
        clean_names = [clean_line(n) for n in names if len(clean_line(n)) > 3]
        
        faculty_obj[key_name] = clean_names

    return faculty_obj

def extract_uet_full_profile(pdf_path):
    print(f"Processing {pdf_path}...")
    full_text = ""
    
    # 1. Read PDF
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # 2. Split into Departments
    # Regex: Newline + number + dot + space + "Department" or "Institute"
    dept_chunks = re.split(r'\n(?=\d+\.\s+(?:Department|Institute|Center))', full_text)
    
    output_data = []

    for chunk in dept_chunks:
        # Skip junk
        if len(chunk) < 100 or "Table of Contents" in chunk:
            continue
            
        # Initialize the object structure you requested
        dept_obj = {
            "department": None,
            "Introduction": None,
            "offered_programs": [],
            "eligibility_criteria": [],
            "faculty_members": {
                "professors": [],
                "associate_professors": [],
                "assistant_professors": [],
                "lecturer": []
            }
        }

        # --- A. Extract Department Name ---
        name_match = re.search(r'^\d+\.\s+([^\n]+)', chunk.strip())
        if name_match:
            dept_obj["department"] = name_match.group(1).strip()
        else:
            continue # If we can't find a name, skip this chunk

        # --- B. Identify Section Boundaries ---
        # We look for the standard section numbers (e.g., 1.1, 1.2, 1.3, 1.4)
        # Note: The numbers change (e.g., 2.1, 8.1), so we use generic regex \d+\.\d+
        
        intro_match = re.search(r'Introduction:', chunk)
        prog_match = re.search(r'Offered Programs:', chunk)
        elig_match = re.search(r'Eligibility Criteria:', chunk)
        fac_match = re.search(r'Faculty Members:', chunk)

        # --- C. Extract Introduction ---
        if intro_match and prog_match:
            raw_intro = chunk[intro_match.end() : prog_match.start()]
            # Join lines to make a single paragraph
            dept_obj["Introduction"] = re.sub(r'\s+', ' ', raw_intro).strip()

        # --- D. Extract Offered Programs ---
        if prog_match and elig_match:
            raw_prog = chunk[prog_match.end() : elig_match.start()]
            # Split by lines and clean
            programs = [p.strip() for p in raw_prog.split('\n') if len(p.strip()) > 5]
            dept_obj["offered_programs"] = programs

        # --- E. Extract Eligibility Criteria ---
        if elig_match:
            # End of eligibility is start of Faculty, or end of chunk if no faculty
            end_pos = fac_match.start() if fac_match else len(chunk)
            raw_elig = chunk[elig_match.end() : end_pos]
            
            # We treat eligibility as a list of strings (usually one per program)
            # Regex: Look for lines that look like "Program Name: Requirement"
            # Or just split by newline and filter empty
            criteria_lines = [c.strip() for c in raw_elig.split('\n') if len(c.strip()) > 5]
            dept_obj["eligibility_criteria"] = criteria_lines

        # --- F. Extract Faculty Members ---
        if fac_match:
            raw_fac = chunk[fac_match.end() : ]
            dept_obj["faculty_members"] = parse_faculty_section(raw_fac)

        output_data.append(dept_obj)

    return output_data

# --- Execution ---
if __name__ == "__main__":
    pdf_file = os.path.join(DATA_DIR, "UET_lahore_Document.pdf")
    output_file = os.path.join(DATA_DIR, "uet_departments.json")
    
    try:
        data = extract_uet_full_profile(pdf_file)
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
        print(f"Success! Extracted {len(data)} departments.")
        print(f"Output saved to: {output_file}")
        
        # Preview the first one to verify structure
        if len(data) > 0:
            print("\n--- JSON Preview ---")
            print(json.dumps(data[0], indent=4))
            
    except Exception as e:
        print(f"An error occurred: {e}")