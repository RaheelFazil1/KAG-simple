import json
import os
import re

# Get the data directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SERVER_DIR, "data")

def clean_text(text):
    """Remove bullet points, 'o ' prefix, extra whitespace, and trailing section numbers."""
    if not text:
        return text
    
    # Remove bullet points (• or \u2022)
    text = text.replace('\u2022', '').replace('•', '')
    
    # Remove 'o ' prefix commonly found in faculty names
    text = re.sub(r'^o\s+', '', text.strip())
    
    # Remove trailing section numbers like "1.2", "2.2" at the end
    text = re.sub(r'\s+\d+\.\d+\s*$', '', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def clean_department_name(name):
    """Clean and complete truncated department names."""
    if not name:
        return name
    
    name = clean_text(name)
    
    # Fix truncated department names
    name_fixes = {
        "Department of Transportation Engineering &": "Department of Transportation Engineering & Management",
        "Institute of Environmental Engineering &": "Institute of Environmental Engineering & Research",
        "Department of Architectural Engineering &": "Department of Architectural Engineering & Design",
        "Department of Industrial & Manufacturing": "Department of Industrial & Manufacturing Engineering",
        "Department of Mechatronics & Control": "Department of Mechatronics & Control Engineering",
        "Department of Metallurgical & Materials": "Department of Metallurgical & Materials Engineering",
        "Center of Excellence in Water Resources": "Center of Excellence in Water Resources Engineering",
    }
    
    return name_fixes.get(name, name)

def clean_list_items(items):
    """Clean a list of strings."""
    if not items:
        return []
    
    cleaned = []
    for item in items:
        cleaned_item = clean_text(item)
        if cleaned_item and len(cleaned_item) > 2:
            cleaned.append(cleaned_item)
    return cleaned

def merge_eligibility_criteria(criteria):
    """Merge multi-line eligibility criteria into single entries."""
    if not criteria:
        return []
    
    merged = []
    current = ""
    
    for line in criteria:
        line = clean_text(line)
        if not line:
            continue
            
        # Check if this line starts a new criterion (starts with program name pattern)
        if re.match(r'^(M\.Sc\.|M\.Phil\.|Ph\.D\.|MBA|Master|Executive|M\.PID|M\.Arch)', line):
            if current:
                merged.append(current.strip())
            current = line
        else:
            # Continue previous criterion
            current += " " + line
    
    if current:
        merged.append(current.strip())
    
    return merged

def clean_faculty_members(faculty):
    """Clean faculty member names and remove junk data."""
    if not faculty:
        return {
            "professors": [],
            "associate_professors": [],
            "assistant_professors": [],
            "lecturers": []
        }
    
    cleaned = {}
    
    # Junk patterns to filter out
    junk_patterns = [
        r'^Automotive Engineering Centre',
        r'^\d+\s+Introduction',
        r'^\d+\s+Offered Programs',
        r'^\d+\s+Eligibility Criteria',
        r'^\d+\s+Faculty Members',
        r'^Professors:',
        r'^Associate Professors:',
        r'^Assistant Professors:',
        r'^Lecturers?:',
        r'The .+ was initiated',
        r'A wide variety of',
        r'requirements\.$',
    ]
    
    for key, names in faculty.items():
        cleaned_names = []
        for name in names:
            name = clean_text(name)
            if not name or len(name) < 3:
                continue
            
            # Skip junk entries
            is_junk = False
            for pattern in junk_patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    is_junk = True
                    break
            
            if not is_junk:
                cleaned_names.append(name)
        
        # Rename 'lecturer' to 'lecturers' for consistency
        new_key = "lecturers" if key == "lecturer" else key
        cleaned[new_key] = cleaned_names
    
    return cleaned

def clean_data(data):
    """Clean the entire dataset."""
    cleaned_data = []
    
    for dept in data:
        cleaned_dept = {
            "department": clean_department_name(dept.get("department")),
            "introduction": clean_text(dept.get("Introduction")),
            "offered_programs": clean_list_items(dept.get("offered_programs", [])),
            "eligibility_criteria": merge_eligibility_criteria(dept.get("eligibility_criteria", [])),
            "faculty_members": clean_faculty_members(dept.get("faculty_members", {}))
        }
        
        # Only include departments with valid names
        if cleaned_dept["department"]:
            cleaned_data.append(cleaned_dept)
    
    return cleaned_data

if __name__ == "__main__":
    input_file = os.path.join(DATA_DIR, "uet_departments.json")
    output_file = os.path.join(DATA_DIR, "uet_departments_clean.json")
    
    try:
        # Load the data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clean the data
        cleaned_data = clean_data(data)
        
        # Save cleaned data (compact for model consumption)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        print(f"Success! Cleaned {len(cleaned_data)} departments.")
        print(f"Output saved to: {output_file}")
        
        # Preview first department
        if cleaned_data:
            print("\n--- Preview ---")
            print(json.dumps(cleaned_data[0], indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"An error occurred: {e}")
