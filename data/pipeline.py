"""
Smart Campus - AIML Department Data Engineering Pipeline
Parses, normalizes, validates, and exports verified AIML timetable records.
"""

import csv
import json
import re
import uuid
from datetime import time

def clean_str(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', str(s)).strip()

def parse_time_slot(header_time):
    # E.g. "8:15-9:05", "9:05-09:55", "10:10-11:00", "08.15-09.05", "1:40-2:30", "12:40 - 1:40"
    cleaned = clean_str(header_time).replace('.', ':')
    parts = re.split(r'[-–]', cleaned)
    if len(parts) != 2:
        return None, None
    
    def to_time_str(t_str):
        t_str = t_str.strip()
        subparts = t_str.split(':')
        if len(subparts) != 2:
            return None
        hr = int(subparts[0])
        mn = int(subparts[1])
        # Afternoon conversion heuristic (periods 6, 7, 8 typically 1:40-4:05 PM)
        if hr in [1, 2, 3, 4] and hr < 8:
            hr += 12
        return f"{hr:02d}:{mn:02d}:00"

    t1 = to_time_str(parts[0])
    t2 = to_time_str(parts[1])
    return t1, t2

def run_pipeline():
    with open("data/aiml_raw_timetable.csv", "r", encoding="utf-8") as f:
        lines = f.readlines()

    sections = []
    current_section = None
    section_lines = []

    # Identify section blocks
    for line in lines:
        stripped = line.strip()
        # Section header match e.g. II AIML-A, III AIML-G, IV AIML-E
        match = re.match(r'^(II|III|IV)\s+AIML-([A-L])', stripped)
        if match:
            if current_section and section_lines:
                sections.append((current_section, section_lines))
            current_section = f"{match.group(1)} AIML-{match.group(2)}"
            section_lines = [line]
        elif current_section:
            section_lines.append(line)

    if current_section and section_lines:
        sections.append((current_section, section_lines))

    print(f"Discovered {len(sections)} AIML sections.")

    faculty_master = {}
    subject_master = {}
    resource_master = {}
    section_master = {}
    normalized_entries = []
    anomalies = []

    day_map = {
        "MON": 0, "MONDAY": 0,
        "TUE": 1, "TUESDAY": 1,
        "WED": 2, "WEDNESDAY": 2,
        "THU": 3, "THURSDAY": 3,
        "FRI": 4, "FRIDAY": 4,
        "SAT": 5, "SATURDAY": 5,
        "SUN": 6, "SUNDAY": 6
    }

    for sec_name, s_lines in sections:
        sec_parts = sec_name.split()
        year_str = sec_parts[0] # II, III, IV
        year_num = 2 if year_str == "II" else (3 if year_str == "III" else 4)
        sec_code = sec_parts[1].replace("AIML-", "")

        sec_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sec_{sec_name}"))
        section_master[sec_name] = {
            "id": sec_id,
            "full_name": sec_name,
            "year_level": year_num,
            "section_code": sec_code,
            "academic_year": "2026-27",
            "semester": 1
        }

        # Parse CSV lines for this section
        reader = list(csv.reader(s_lines))
        
        # Find period header & Day/Hour row
        day_hour_row_idx = None
        period_row_idx = None
        for idx, row in enumerate(reader):
            row_str = " ".join(row)
            if "Day/Hour" in row_str or "Day / Hour" in row_str:
                day_hour_row_idx = idx
                if idx > 0 and ("Period" in " ".join(reader[idx-1])):
                    period_row_idx = idx - 1
                break

        if day_hour_row_idx is None:
            anomalies.append({
                "section": sec_name,
                "type": "STRUCTURE_ERROR",
                "message": "Could not find Day/Hour header row."
            })
            continue

        day_hour_row = reader[day_hour_row_idx]
        
        # Build slot column map
        # Columns with valid time strings
        col_slots = {}
        for c_idx, cell in enumerate(day_hour_row):
            t1, t2 = parse_time_slot(cell)
            if t1 and t2:
                col_slots[c_idx] = (t1, t2)

        # Parse faculty/subject legend at the bottom of the section
        # Starts after Saturday row
        subject_faculty_map = {}
        sat_row_idx = None
        for idx in range(day_hour_row_idx + 1, len(reader)):
            row = reader[idx]
            if len(row) > 0 and clean_str(row[0]).upper().startswith("SAT"):
                sat_row_idx = idx
                break

        if sat_row_idx:
            for idx in range(sat_row_idx + 1, len(reader)):
                row = reader[idx]
                for cell in row:
                    cell_clean = clean_str(cell)
                    if ":" in cell_clean:
                        parts = cell_clean.split(":", 1)
                        subj_header = clean_str(parts[0])
                        fac_text = clean_str(parts[1])
                        if subj_header and fac_text and not subj_header.upper().startswith("COUNCELOR") and not subj_header.upper().startswith("FACULTY ADVISOR"):
                            # Extract subject short code if in parens e.g. "Statistical Foundation for Computing and Data Science(L)"
                            subject_faculty_map[subj_header] = fac_text
                            
                            # Clean subject name
                            base_subj = re.sub(r'\(.*?\)', '', subj_header).strip()
                            if base_subj not in subject_master:
                                subject_master[base_subj] = {
                                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"subj_{base_subj}")),
                                    "name": base_subj,
                                    "course_type": "CORE" if "DE" not in subj_header and "OE" not in subj_header else "ELECTIVE"
                                }

                            # Process faculty
                            fac_list = [f.strip() for f in fac_text.split(",") if f.strip() and f.strip() != "***"]
                            for f_name in fac_list:
                                if f_name and len(f_name) > 2:
                                    if f_name not in faculty_master:
                                        faculty_master[f_name] = {
                                            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fac_{f_name}")),
                                            "full_name": f_name,
                                            "designation": "Professor" if "DR." in f_name.upper() else "Assistant Professor"
                                        }

        # Parse schedule grid (rows between Day/Hour and footer)
        end_grid_idx = sat_row_idx + 1 if sat_row_idx else len(reader)
        for idx in range(day_hour_row_idx + 1, end_grid_idx):
            row = reader[idx]
            if not row or not clean_str(row[0]):
                continue
            day_token = clean_str(row[0]).upper()
            if day_token not in day_map:
                continue
            day_num = day_map[day_token]

            for col_idx, (t_start, t_end) in col_slots.items():
                if col_idx >= len(row):
                    continue
                cell_content = row[col_idx].strip()
                if not cell_content or cell_content.upper() in ["BREAK", "LUNCH", "LIB", "LIBRARY", "OE"]:
                    continue

                lines = [l.strip() for l in cell_content.split("\n") if l.strip()]
                if not lines:
                    continue

                raw_subj = lines[0]
                raw_room = lines[1] if len(lines) > 1 else None

                # Determine session type
                sess_type = "THEORY"
                if "(P)" in raw_subj or "LAB" in str(raw_room).upper():
                    sess_type = "PRACTICAL"
                elif "(T)" in raw_subj or "(T&P)" in raw_subj:
                    sess_type = "TUTORIAL"
                elif "COUNSELLING" in raw_subj.upper():
                    sess_type = "COUNSELLING"
                elif "SL" in raw_subj.upper() or "SELF LEARNING" in raw_subj.upper():
                    sess_type = "SELF_LEARNING"

                # Normalize room
                room_obj = None
                if raw_room:
                    cleaned_room = clean_str(raw_room).replace("(U-BLOCK)", "").strip()
                    if cleaned_room and cleaned_room != "--":
                        if cleaned_room not in resource_master:
                            is_lab = "LAB" in cleaned_room or cleaned_room in ["601", "604", "605", "606", "611", "612", "615", "616", "617"]
                            resource_master[cleaned_room] = {
                                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"res_{cleaned_room}")),
                                "code": cleaned_room,
                                "name": f"Room {cleaned_room}" if not is_lab else f"Computer Lab {cleaned_room}",
                                "resource_type": "LABORATORY" if is_lab else "CLASSROOM",
                                "capacity": 60,
                                "is_shared": cleaned_room in ["402", "501", "514-A", "514-B", "518", "608", "AFTF-7E", "AFTF-13", "AFTF-14", "LAB-1", "LAB-2"]
                            }
                        room_obj = resource_master[cleaned_room]

                # Match subject code
                subj_clean = re.sub(r'\(.*?\)', '', raw_subj).strip()
                matched_subj = None
                for s_key, s_val in subject_master.items():
                    if subj_clean.upper() in s_key.upper() or s_key.upper() in subj_clean.upper():
                        matched_subj = s_val
                        break
                if not matched_subj:
                    # Register subject code
                    matched_subj = {
                        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"subj_{subj_clean}")),
                        "name": subj_clean,
                        "course_type": "CORE"
                    }
                    subject_master[subj_clean] = matched_subj

                entry_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{sec_name}_{day_num}_{t_start}_{raw_subj}"))
                normalized_entries.append({
                    "id": entry_id,
                    "section_id": sec_id,
                    "section_name": sec_name,
                    "day_of_week": day_num,
                    "day_name": day_token,
                    "start_time": t_start,
                    "end_time": t_end,
                    "subject_id": matched_subj["id"],
                    "subject_name": matched_subj["name"],
                    "raw_subject": raw_subj,
                    "resource_id": room_obj["id"] if room_obj else None,
                    "resource_code": room_obj["code"] if room_obj else None,
                    "session_type": sess_type,
                    "source_cell_content": cell_content
                })

    print(f"Extraction Summary:")
    print(f"- Sections Extracted: {len(section_master)}")
    print(f"- Faculty Identified: {len(faculty_master)}")
    print(f"- Subjects Identified: {len(subject_master)}")
    print(f"- Resources Identified: {len(resource_master)}")
    print(f"- Normalized Timetable Entries: {len(normalized_entries)}")

    # Write deliverables to data directory
    with open("data/section_master.json", "w", encoding="utf-8") as f:
        json.dump(list(section_master.values()), f, indent=2)

    with open("data/faculty_master.json", "w", encoding="utf-8") as f:
        json.dump(list(faculty_master.values()), f, indent=2)

    with open("data/subject_master.json", "w", encoding="utf-8") as f:
        json.dump(list(subject_master.values()), f, indent=2)

    with open("data/resource_master.json", "w", encoding="utf-8") as f:
        json.dump(list(resource_master.values()), f, indent=2)

    with open("data/normalized_timetable_entries.json", "w", encoding="utf-8") as f:
        json.dump(normalized_entries, f, indent=2)

    with open("data/data_quality_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_sections": len(section_master),
            "total_faculty": len(faculty_master),
            "total_subjects": len(subject_master),
            "total_resources": len(resource_master),
            "total_entries": len(normalized_entries),
            "anomalies": anomalies
        }, f, indent=2)

if __name__ == "__main__":
    run_pipeline()
