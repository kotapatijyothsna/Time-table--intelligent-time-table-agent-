"""
Smart Campus - Match Subject Faculty to Classes & Classrooms
Uses standardized assignments to accurately bind faculty to class sessions and rooms.
"""

import csv
import json
import re
from collections import defaultdict

def normalize_name(n):
    return re.sub(r'\s+', ' ', str(n)).strip()

def build_subject_matcher():
    # Map raw short codes from timetable cells to standardized Subject Name
    return {
        "DS": "Data Structures",
        "DBMS": "Data Base Management Systems",
        "SFCDS": "Statistical Foundation for Computing and Data Science",
        "DMS": "Discrete Mathematical Structures",
        "AI": "Artificial Intelligence Search Methods for Problem Solving",
        "OOPS": "Object Oriented Programming",
        "DEF": "Data Engineering Foundations",
        "CC": "Coding Competency",
        "DL": "Deep Learning",
        "WT": "Web Technologies",
        "CV": "Computer Vision (DE-2)",
        "MLOP": "Machine Learning Operations (DE-1)",
        "ADS": "Advanced Data Structures (DE-1)",
        "FIP": "Fundamentals of Image Processing",
        "QALR": "Quantitative Aptitude & Logical Resoning",
        "IDP": "Inter Departmental Project with Agentic Tools",
        "KRR": "Knowledge Representation and Reasoning",
        "TM": "Text Mining",
        "CNS": "Cryptography and Network Security",
        "GEN AI": "Generative AI and Agentic Systems (DE)",
        "GEN AI & AS": "Generative AI and Agentic Systems (DE)",
        "GENAI": "Generative AI and Agentic Systems (DE)",
        "IOT": "Internet of Things (DE)",
        "ETHICS": "Ethics in computing and Aritificial Intelligence",
    }

def match_faculty_to_rooms():
    # 1. Load standardized assignments
    # Key: (class_name, subject_name, mode) -> list of faculty
    assignments = defaultdict(lambda: defaultdict(list))
    all_class_assignments = defaultdict(lambda: defaultdict(list))

    with open("data/detailed_teaching_assignments.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = normalize_name(row["Class / Section"])
            subj = normalize_name(row["Subject"])
            fac = normalize_name(row["Faculty"])
            mode = normalize_name(row["Teaching Mode"]).upper()
            
            assignments[(cls, subj)][mode].append(fac)
            all_class_assignments[(cls, subj)]["ALL"].append(fac)

    print(f"Loaded assignments for {len(assignments)} class-subject pairs.")

    # 2. Load timetable entries
    with open("data/normalized_timetable_entries.json", "r", encoding="utf-8") as f:
        entries = json.load(f)

    code_map = build_subject_matcher()

    enriched_entries = []
    matched_count = 0
    multi_faculty_count = 0

    for entry in entries:
        cls_name = entry["section_name"]
        raw_subj = entry["raw_subject"]
        clean_code = re.sub(r'\(.*?\)', '', raw_subj).strip()
        room = entry.get("resource_code")

        # Determine target subject name
        target_subj = code_map.get(clean_code, entry.get("subject_name", clean_code))
        
        # Determine mode
        is_practical = "(P)" in raw_subj or entry.get("session_type") == "PRACTICAL"
        is_tutorial = "(T)" in raw_subj or entry.get("session_type") == "TUTORIAL"
        
        target_mode = "P" if is_practical else ("T&P" if is_tutorial else "L")

        # Look up faculty list
        fac_list = []
        # Try exact mode
        if (cls_name, target_subj) in assignments:
            subj_modes = assignments[(cls_name, target_subj)]
            if is_practical and "P" in subj_modes:
                fac_list = subj_modes["P"]
            elif is_tutorial and ("T" in subj_modes or "T&P" in subj_modes):
                fac_list = subj_modes.get("T") or subj_modes.get("T&P")
            elif not is_practical and "L" in subj_modes:
                fac_list = subj_modes["L"]
            
            # Fallback to T&P or any mode if specific not found
            if not fac_list:
                fac_list = subj_modes.get("T&P") or subj_modes.get("P") or subj_modes.get("L", [])

        # If still empty, try substring match on subject name
        if not fac_list:
            for (c, s), modes in assignments.items():
                if c == cls_name and (clean_code.upper() in s.upper() or s.upper() in target_subj.upper()):
                    fac_list = modes.get(target_mode) or modes.get("T&P") or modes.get("L") or modes.get("P", [])
                    target_subj = s
                    break

        if fac_list:
            matched_count += 1
            if len(fac_list) > 1:
                multi_faculty_count += 1
            primary_fac = fac_list[0]
        else:
            primary_fac = "Department Faculty"
            fac_list = ["Department Faculty"]

        entry["matched_subject_name"] = target_subj
        entry["faculty_name"] = primary_fac
        entry["all_assigned_faculty"] = fac_list
        entry["room_code"] = room if room else "Unassigned / General"
        entry["teaching_mode"] = target_mode

        enriched_entries.append(entry)

    print(f"Enrichment Complete:")
    print(f"- Total Entries Processed: {len(enriched_entries)}")
    print(f"- Successfully Matched to Faculty: {matched_count}")
    print(f"- Multi-Faculty Lab Sessions Identified: {multi_faculty_count}")

    # Save enriched timetable dataset
    with open("data/matched_timetable_with_faculty_and_rooms.json", "w", encoding="utf-8") as f:
        json.dump(enriched_entries, f, indent=2)

    # Print sample matches
    print("\nSample Matched Sessions (Faculty -> Class -> Subject -> Classroom):")
    for sample in enriched_entries[:8]:
        facs = ", ".join(sample["all_assigned_faculty"])
        print(f"• [{sample['section_name']}] {sample['day_name']} {sample['start_time']}-{sample['end_time']}: {sample['matched_subject_name']} ({sample['teaching_mode']}) in Room {sample['room_code']} -> Assigned: {facs}")

if __name__ == "__main__":
    match_faculty_to_rooms()
