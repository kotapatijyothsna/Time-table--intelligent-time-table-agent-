"""
Parse ACSE timetable Excel and generate all data JSON files for the system.
Replaces AIML department data with ACSE department data.
"""

import json
import uuid
import re
import openpyxl
from collections import defaultdict

XLSX = r'C:/Users/Jyothsna/.gemini/antigravity/brain/268b8c3a-7aaf-4ae9-84fb-87f996a74602/.user_uploaded/media_1793902572071_cd19a6af.xlsx'

DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
TIME_SLOTS = [
    ('1', '8:15-9:05'),
    ('2', '9:05-09:55'),
    ('3', '10:10-11:00'),
    ('4', '11:00-11:50'),
    ('5', '11:50-12:40'),
    ('6', '1:40-2:30'),
    ('7', '2:30-3:20'),
    ('8', '3:20-4:05'),
]

# Slot index → (period, time)
COL_TO_SLOT = {
    1: ('1', '8:15-9:05'),
    2: ('2', '9:05-09:55'),
    # col 3 = BREAK
    4: ('3', '10:10-11:00'),
    5: ('4', '11:00-11:50'),
    6: ('5', '11:50-12:40'),
    # col 7 = LUNCH
    8: ('6', '1:40-2:30'),
    9: ('7', '2:30-3:20'),
    10: ('8', '3:20-4:05'),
}

wb = openpyxl.load_workbook(XLSX)
print('Sheets:', wb.sheetnames)

# ── Storage ───────────────────────────────────────────────────────────────────
sections = {}       # section_name → {id, name, year, branch, batch}
subjects = {}       # subject_code → {id, code, name, section}
faculty_map = {}    # faculty_name_norm → {id, full_name, designation}
timetable_entries = []
faculty_assignments = defaultdict(set)  # faculty_id → set of subject_ids

def norm_name(n):
    return re.sub(r'\s+', ' ', n.strip().lower())

def get_or_create_faculty(name):
    name = name.strip().strip('.')
    if not name or len(name) < 2:
        return None
    key = norm_name(name)
    if key not in faculty_map:
        # Determine designation
        low = name.lower()
        if re.match(r'^dr[\.\s]', low):
            desig = 'Faculty'
        elif re.match(r'^prof[\.\s]', low):
            desig = 'Faculty'
        elif re.match(r'^(mr|ms|mrs)[\.\s]', low):
            desig = 'Faculty'
        else:
            desig = 'Teaching Assistant'
        faculty_map[key] = {
            'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, key)),
            'full_name': name,
            'designation': desig
        }
    return faculty_map[key]

def parse_cell(cell_val):
    """Parse a timetable cell like 'DS\\n619' → (subject_code, room)"""
    if not cell_val or str(cell_val).strip() in ('', 'BREAK', 'LUNCH'):
        return None, None
    val = str(cell_val).strip()
    # Split on newline
    parts = val.split('\n')
    subject_part = parts[0].strip()
    room = parts[1].strip() if len(parts) > 1 else ''
    # Clean subject: remove (P), (T), (L) markers for code
    subject_code = re.sub(r'\([PLT&]+\)', '', subject_part).strip()
    return subject_code, room

def parse_faculty_line(line):
    """Parse 'Subject Name(L/P): Faculty1, Faculty2' lines."""
    line = line.strip()
    if not line:
        return None, None, []
    # Match 'Subject(type): Faculty...'
    m = re.match(r'^(.+?)\(([LP&T]+)\)\s*:\s*(.+)$', line)
    if not m:
        # Try without type
        m2 = re.match(r'^(.+?):\s*(.+)$', line)
        if m2:
            return m2.group(1).strip(), 'L', [f.strip() for f in m2.group(2).split(',')]
        return None, None, []
    subject_name = m.group(1).strip()
    stype = m.group(2)
    faculty_str = m.group(3)
    faculty_names = [f.strip() for f in faculty_str.split(',') if f.strip()]
    return subject_name, stype, faculty_names

def get_year(sheet_name):
    sn = sheet_name.upper()
    if 'II' in sn and 'III' not in sn and 'IV' not in sn: return 'II'
    if 'III' in sn and 'IV' not in sn: return 'III'
    if 'IV' in sn: return 'IV'
    if 'I' in sn: return 'I'
    return sheet_name

def get_branch(sheet_name):
    sn = sheet_name.upper()
    for b in ['AIML', 'CSBS', 'IOT', 'DS', 'CS', 'BS(DS)', 'MSC(DS)', 'M.TECH']:
        if b in sn:
            return b
    return sn

# ── Main parsing loop ─────────────────────────────────────────────────────────
for sheet_name in wb.sheetnames:
    if sheet_name in ('LIBRARY SLOTS',):
        continue

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    year = get_year(sheet_name)
    branch = get_branch(sheet_name)

    current_section = None
    in_timetable = False
    day_row_idx = -1
    subject_faculty_lines = []

    i = 0
    while i < len(rows):
        row = rows[i]
        first_cell = str(row[0]).strip() if row[0] is not None else ''

        # Detect section header e.g. "II AIML-A", "III AIML-B"
        if re.match(r'^(I{1,3}V?|IV)\s+\w+', first_cell) and row[1] is None:
            # New section block
            current_section = first_cell.replace('AIML', 'ACSE').strip()
            in_timetable = False
            subject_faculty_lines = []
            if current_section not in sections:
                sections[current_section] = {
                    'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, current_section)),
                    'name': current_section,
                    'year': year,
                    'branch': 'ACSE',
                    'batch': 'A' if '-A' in current_section else ('B' if '-B' in current_section else 'C' if '-C' in current_section else ''),
                }
            i += 1
            continue

        # Detect timetable header row (Period row)
        if first_cell == 'Period':
            i += 1  # skip to Day/Hour row
            day_row_idx = i
            in_timetable = True
            i += 1
            continue

        # Parse timetable day rows
        if in_timetable and first_cell in DAYS and current_section:
            day = first_cell
            # cols: 0=day, 1=p1, 2=p2, 3=break, 4=p3, 5=p4, 6=p5, 7=lunch, 8=p6, 9=p7, 10=p8
            col_map = {1:0, 2:1, 4:2, 5:3, 6:4, 8:5, 9:6, 10:7}
            for col_idx, slot_num in [(1,'1'),(2,'2'),(4,'3'),(5,'4'),(6,'5'),(8,'6'),(9,'7'),(10,'8')]:
                cell_val = row[col_idx] if col_idx < len(row) else None
                if not cell_val:
                    continue
                cell_str = str(cell_val).strip()
                if cell_str in ('BREAK', 'LUNCH', 'LIBRARY', ''):
                    continue

                subject_code, room = parse_cell(cell_val)
                if not subject_code:
                    continue

                # Determine type
                entry_type = 'L'
                if '(P)' in str(cell_val):
                    entry_type = 'P'
                elif '(T)' in str(cell_val):
                    entry_type = 'T'

                # Clean subject code
                clean_code = re.sub(r'\([A-Z&]+\)', '', subject_code).strip()
                if not clean_code:
                    continue

                # Register subject
                subj_key = f"{current_section}_{clean_code}"
                if subj_key not in subjects:
                    subjects[subj_key] = {
                        'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, subj_key)),
                        'code': clean_code,
                        'name': clean_code,  # will update from faculty lines
                        'section_id': sections[current_section]['id'],
                        'section': current_section,
                        'type': entry_type,
                    }

                timetable_entries.append({
                    'id': str(uuid.uuid4()),
                    'section': current_section,
                    'section_id': sections[current_section]['id'],
                    'day': day,
                    'period': slot_num,
                    'subject_code': clean_code,
                    'subject_name': clean_code,
                    'room': room,
                    'type': entry_type,
                })
            i += 1
            continue

        # Detect end of timetable (empty row or new section)
        if in_timetable and not first_cell and all(c is None for c in row[:5]):
            in_timetable = False
            i += 1
            continue

        # Parse subject-faculty assignment lines
        if current_section and not in_timetable and first_cell and ':' in first_cell:
            subj_name, stype, faculty_names = parse_faculty_line(first_cell)
            if subj_name:
                subject_faculty_lines.append({
                    'section': current_section,
                    'subject_name': subj_name,
                    'type': stype,
                    'faculty': faculty_names,
                })
                # Create faculty entries
                for fn in faculty_names:
                    get_or_create_faculty(fn)
        i += 1

# ── Update subject names from faculty lines ───────────────────────────────────
# Build a mapping from (section, short_code) → full subject name
abbr_to_full = {}
for fl in subject_faculty_lines:
    sec = fl['section']
    full = fl['subject_name']
    # Generate abbreviation: take first letter of each major word
    words = re.sub(r'[^a-zA-Z0-9 ]', '', full).split()
    abbr = ''.join(w[0].upper() for w in words if len(w) > 2)
    key = f"{sec}_{abbr}"
    abbr_to_full[key] = full

for subj_key, subj in subjects.items():
    code = subj['code']
    sec = subj['section']
    lookup = f"{sec}_{code}"
    if lookup in abbr_to_full:
        subjects[subj_key]['name'] = abbr_to_full[lookup]

# Also update timetable entries
code_to_name = {}
for subj in subjects.values():
    code_to_name[(subj['section'], subj['code'])] = subj['name']

for entry in timetable_entries:
    key = (entry['section'], entry['subject_code'])
    if key in code_to_name:
        entry['subject_name'] = code_to_name[key]

# ── Load existing faculty_master.json and merge ───────────────────────────────
with open('faculty_master.json', encoding='utf-8') as f:
    existing_faculty = json.load(f)

existing_norm = {norm_name(e['full_name']): e for e in existing_faculty}

# Merge new faculty found in ACSE timetable
for key, fac in faculty_map.items():
    if key not in existing_norm:
        existing_faculty.append(fac)
        existing_norm[key] = fac
    else:
        # Update id reference to existing
        faculty_map[key]['id'] = existing_norm[key]['id']

# ── Save all files ────────────────────────────────────────────────────────────
print(f'\nSections: {len(sections)}')
print(f'Subjects: {len(subjects)}')
print(f'Faculty: {len(existing_faculty)}')
print(f'Timetable entries: {len(timetable_entries)}')
print(f'Subject-faculty assignments: {len(subject_faculty_lines)}')

section_list = list(sections.values())
subject_list = list(subjects.values())

with open('section_master.json', 'w', encoding='utf-8') as f:
    json.dump(section_list, f, indent=2, ensure_ascii=False)

with open('subject_master.json', 'w', encoding='utf-8') as f:
    json.dump(subject_list, f, indent=2, ensure_ascii=False)

with open('faculty_master.json', 'w', encoding='utf-8') as f:
    json.dump(existing_faculty, f, indent=2, ensure_ascii=False)

with open('acse_timetable_entries.json', 'w', encoding='utf-8') as f:
    json.dump(timetable_entries, f, indent=2, ensure_ascii=False)

with open('acse_faculty_assignments.json', 'w', encoding='utf-8') as f:
    json.dump(subject_faculty_lines, f, indent=2, ensure_ascii=False)

# Update the raw timetable CSV name reference
print('\nSection breakdown:')
for s in section_list:
    print(f"  {s['name']} ({s['year']} year, {s['branch']})")

print('\nAll files saved successfully!')
