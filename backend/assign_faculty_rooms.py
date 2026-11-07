"""
Full rebuild v6: Complete faculty + room assignment across all 44 sections.
Features:
- Auto-registers visiting/inter-department faculty found in the official timetable so no class is left Unassigned
- Preserves all verified designations (Faculty / Teaching Assistant / Outsourcing Staff)
- Full extraction of multi-period classes (2 consecutive periods merged into 1 slot)
- Comprehensive acronym & bracket-code matching for all subjects
- Handles all branches: AIML (II, III, IV), CS, DS, CSBS, IOT, BS(DS), MSC(DS), M.TECH
"""
import os, sys, json, re, datetime
import openpyxl

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()

from apps.academics.models import Department, AcademicSection, Subject
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry

XLSX = r'C:/Users/Jyothsna/.gemini/antigravity/brain/268b8c3a-7aaf-4ae9-84fb-87f996a74602/.user_uploaded/media_1793902572071_cd19a6af.xlsx'
wb = openpyxl.load_workbook(XLSX)

DAYS = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5}

COL_PERIODS = {
    1:  ('1', datetime.time(8, 15),  datetime.time(9, 5)),
    2:  ('2', datetime.time(9, 5),   datetime.time(9, 55)),
    4:  ('3', datetime.time(10, 10), datetime.time(11, 0)),
    5:  ('4', datetime.time(11, 0),  datetime.time(11, 50)),
    6:  ('5', datetime.time(11, 50), datetime.time(12, 40)),
    8:  ('6', datetime.time(13, 40), datetime.time(14, 30)),
    9:  ('7', datetime.time(14, 30), datetime.time(15, 20)),
    10: ('8', datetime.time(15, 20), datetime.time(16, 5)),
}

TYPE_MAP = {'L': 'THEORY', 'T': 'TUTORIAL', 'P': 'PRACTICAL'}
STOP_WORDS = {'AND', 'OF', 'FOR', 'THE', 'IN', 'TO', 'WITH', 'A', 'AN', '&', 'DE', 'PE', 'OE', '1', '2', 'I', 'II'}

dept = Department.objects.get(code='AIML')
version = TimetableVersion.objects.filter(is_active=True).first()
print(f"Department: {dept} | Version: {version}")

# ── Build faculty lookup ─────────────────────────────────────────────────────
def canonical_norm(name):
    s = re.sub(r'^(dr\.?\s*|mr\.?\s*|ms\.?\s*|mrs\.?\s*|prof\.?\s*)', '', str(name).strip(), flags=re.I)
    s = re.sub(r'[^a-zA-Z0-9]', ' ', s).lower()
    return ' '.join(s.split())

fac_db = {canonical_norm(f.full_name): f for f in Faculty.objects.filter(is_active=True)}

def find_or_create_faculty(name):
    name = str(name).strip().rstrip('.').rstrip(',').strip()
    if not name or len(name) < 3:
        return None
    key = canonical_norm(name)
    if key in fac_db:
        return fac_db[key]
    for k, v in fac_db.items():
        if len(key) > 5 and (key in k or k in key):
            return v
    # Auto-create if genuine name from timetable
    if not re.match(r'^(none|nil|\*\*\*|room|lab)', key, re.I):
        clean_code = 'FAC_' + re.sub(r'[^A-Z0-9]', '', name.upper())[:10] + f"_{Faculty.objects.count() + 1}"
        obj = Faculty.objects.create(
            department=dept,
            full_name=name,
            faculty_code=clean_code,
            designation='Faculty',
            is_active=True,
        )
        fac_db[key] = obj
        return obj
    return None
        )
        fac_db[key] = obj
        return obj
    return None

# ── Step 1: Create rooms ─────────────────────────────────────────────────────
print("\n=== Step 1: Rooms ===")
all_rooms = set()
for sname in wb.sheetnames:
    if sname == 'LIBRARY SLOTS': continue
    ws = wb[sname]
    for row in ws.iter_rows(values_only=True):
        first = str(row[0]).strip() if row[0] else ''
        if first not in DAYS: continue
        for ci in COL_PERIODS:
            cell = str(row[ci]).strip() if ci < len(row) and row[ci] else ''
            if not cell or cell in ('BREAK','LUNCH','LIBRARY',''): continue
            parts = cell.split('\n')
            if len(parts) > 1:
                room = parts[1].strip()
                if room:
                    all_rooms.add(room)

room_cache = {}
created_r = 0
for rcode in sorted(all_rooms):
    clean = rcode.strip()
    if not clean or len(clean) > 30 or clean in ['--', '/AL/IL', 'NIL', 'NONE', '***'] or clean.startswith('/'):
        continue
    is_lab = any(k in clean.lower() for k in ['lab','60','61','62','63','64'])
    obj, cr = Resource.objects.update_or_create(
        code=clean,
        defaults={
            'department': dept,
            'name': f"Room {clean}",
            'resource_type': 'LABORATORY' if is_lab else 'CLASSROOM',
            'capacity': 60,
            'is_shared': True,
        }
    )
    room_cache[clean] = obj
    if cr: created_r += 1

print(f"Rooms: {created_r} new, {len(room_cache)} total")

# ── Helper: generate all reasonable abbreviations for a subject name ────────
def generate_subject_keys(subj_name):
    keys = set()
    cleaned = re.sub(r'\((?:DE|PE|OE|HONORS|MINOR)[^\)]*\)', '', subj_name, flags=re.I).strip()
    words = re.sub(r'[^a-zA-Z0-9 ]', ' ', cleaned).split()
    if not words:
        return keys

    keys.add(cleaned.upper())
    meaningful = [w for w in words if w.upper() not in STOP_WORDS]
    if meaningful:
        keys.add(''.join(w[0].upper() for w in meaningful))
    keys.add(''.join(w[0].upper() for w in words))

    if len(words) == 1 and len(words[0]) <= 8:
        keys.add(words[0].upper())

    upper_words = [w.upper() for w in words]
    if 'INTERNET' in upper_words:
        keys.add('IOT')
        keys.add('IT')
    if 'GENERATIVE' in upper_words:
        keys.add('GEN AI')
        keys.add('GENAI')
        keys.add('GEN AI & AS')
    if 'CLOUD' in upper_words:
        keys.add('CC')
        keys.add('CS')
    if 'MLOPS' in upper_words or 'OPERATIONS' in upper_words:
        keys.add('MLOP')
        keys.add('MLOPS')
    if 'AGENTIC' in upper_words:
        keys.add('AAI')
    if 'IMAGE' in upper_words and 'PROCESSING' in upper_words:
        keys.add('FIP')
        keys.add('IP')
    if 'MOBILE' in upper_words:
        keys.add('MAD')
    if 'STATISTICAL' in upper_words or 'STATISTICS' in upper_words:
        keys.add('SFCDS')
        keys.add('SFFCADS')
        keys.add('SDS')
    if 'ENGINEERING' in upper_words and 'FOUNDATIONS' in upper_words:
        keys.add('DEF')
    if 'CRYPTOGRAPHY' in upper_words or 'NETWORK' in upper_words:
        keys.add('CNS')
        keys.add('NS')
    if 'ETHICS' in upper_words:
        keys.add('ETHICS')
    if 'TIME' in upper_words and 'SERIES' in upper_words:
        keys.add('TSAF')
    if 'WEB' in upper_words and 'SECURITY' in upper_words:
        keys.add('WDS')
    if 'DATABASE' in upper_words:
        keys.add('DBMS')
        keys.add('DMS')

    return keys

# ── Step 2: Parse faculty assignments + timetable cells ─────────────────────
print("\n=== Step 2: Parsing Excel ===")

sec_subj_fac = {}
abbr_full = {}
cell_map = {}

for sname in wb.sheetnames:
    if sname == 'LIBRARY SLOTS': continue
    ws = wb[sname]
    rows = list(ws.iter_rows(values_only=True))
    current_section = None
    in_timetable = False

    for i, row in enumerate(rows):
        first = str(row[0]).strip() if row[0] else ''

        if re.match(r'^(I{1,4}V?|IV)\s+\w', first) and (len(row) < 2 or row[1] is None):
            current_section = first.strip()
            in_timetable = False
            continue

        if first == 'Period':
            in_timetable = True
            continue

        if in_timetable and first in DAYS and current_section:
            day_idx = DAYS[first]
            cols = [str(row[c]).strip() if c < len(row) and row[c] else '' for c in range(11)]

            col_content = {}
            for ci, (period, start_t, end_t) in COL_PERIODS.items():
                val = cols[ci]
                if not val or val in ('BREAK','LUNCH','LIBRARY','None',''):
                    continue
                next_ci = ci + 1
                is_multi = (next_ci in COL_PERIODS and cols[next_ci] == '')

                parts = val.split('\n')
                subj_part = parts[0].strip()
                room_code = parts[1].strip() if len(parts) > 1 else ''

                entry_type = 'L'
                if '(P)' in subj_part: entry_type = 'P'
                elif '(T)' in subj_part: entry_type = 'T'

                clean_code = re.sub(r'\([A-Z&]+\)', '', subj_part).strip()

                actual_end = end_t
                if is_multi and next_ci in COL_PERIODS:
                    actual_end = COL_PERIODS[next_ci][2]

                col_content[ci] = {
                    'code': clean_code,
                    'room': room_code,
                    'type': entry_type,
                    'start': start_t,
                    'end': actual_end,
                    'multi': is_multi,
                }

            for ci, cdata in col_content.items():
                key = (current_section, day_idx, cdata['start'])
                cell_map[key] = cdata
            continue

        if in_timetable and not first:
            in_timetable = False

        if current_section and ':' in first:
            for col_offset in [0, 5]:
                seg = str(row[col_offset]).strip() if col_offset < len(row) and row[col_offset] else ''
                if not seg or ':' not in seg: continue

                m = re.match(r'^(.+?)\(([LPT&]+)\)\s*:\s*(.+)$', seg)
                if not m:
                    m2 = re.match(r'^(.+?):\s*(.+)$', seg)
                    if not m2: continue
                    subj_name, fac_str = m2.group(1).strip(), m2.group(2).strip()
                else:
                    subj_name, fac_str = m.group(1).strip(), m.group(3).strip()

                if re.match(r'^(COUNCELOR|COUNSELOR|COUNSELLING)', subj_name, re.IGNORECASE):
                    fac_names = [fn.strip().rstrip(',').strip() for fn in fac_str.split(',')]
                    fac_objs = [f for f in (find_or_create_faculty(fn) for fn in fac_names if fn) if f]
                    if fac_objs:
                        for ckey in ['counselling', 'COUNSELLING', 'COUNSELOR', 'COUNSELORS', 'C']:
                            sec_subj_fac[(current_section, ckey)] = fac_objs
                    continue

                if re.match(r'^(Minor|Honor|NPTEL|FACULTY ADVISOR)', subj_name, re.IGNORECASE):
                    continue

                bracket_codes = re.findall(r'\[([A-Z0-9&\-]+)\]', subj_name.upper())

                fac_names = [fn.strip().rstrip(',').strip() for fn in fac_str.split(',')]
                fac_objs = [f for f in (find_or_create_faculty(fn) for fn in fac_names if fn) if f]

                if not fac_objs:
                    continue

                for key_variant in generate_subject_keys(subj_name):
                    abbr_full[key_variant] = subj_name
                    sec_key = (current_section, key_variant)
                    if sec_key not in sec_subj_fac:
                        sec_subj_fac[sec_key] = fac_objs

                for bc in bracket_codes:
                    abbr_full[bc] = subj_name
                    sec_key = (current_section, bc)
                    if sec_key not in sec_subj_fac:
                        sec_subj_fac[sec_key] = fac_objs

print(f"Cell entries parsed: {len(cell_map)}")
print(f"Faculty assignment keys: {len(sec_subj_fac)}")

# ── Faculty lookup for a cell ────────────────────────────────────────────────
def find_fac_for(sec_name, code):
    code_up = code.upper().strip()

    if (sec_name, code) in sec_subj_fac:
        return sec_subj_fac[(sec_name, code)]
    if (sec_name, code_up) in sec_subj_fac:
        return sec_subj_fac[(sec_name, code_up)]

    for (sn, k), facs in sec_subj_fac.items():
        if sn == sec_name:
            ku = k.upper()
            if ku == code_up:
                return facs
            if len(ku) >= 2 and len(code_up) >= 2:
                if ku.startswith(code_up) or code_up.startswith(ku):
                    return facs
                if ku in code_up or code_up in ku:
                    return facs

    return None

# ── Step 3: Rebuild TimetableEntry records ───────────────────────────────────
print("\n=== Step 3: Rebuilding timetable entries ===")
TimetableEntry.objects.filter(timetable_version=version).delete()

session_cache = {}
for sec in AcademicSection.objects.filter(department=dept):
    session_cache[sec.full_name] = sec

subj_cache = {}

def get_or_make_subject(sec_name, code, name, stype):
    ukey = f"{sec_name}_{code}"[:30]
    if ukey in subj_cache:
        return subj_cache[ukey]
    obj, _ = Subject.objects.get_or_create(
        code=ukey,
        defaults={'department': dept, 'name': name or code, 'course_type': TYPE_MAP.get(stype, 'CORE')}
    )
    subj_cache[ukey] = obj
    return obj

created = 0
skipped = 0
multi_period = 0

for (sec_name, day_idx, start_t), cdata in cell_map.items():
    sec_obj = session_cache.get(sec_name)
    if not sec_obj:
        skipped += 1
        continue

    code = cdata['code']
    if not code:
        skipped += 1
        continue

    room_code = cdata['room']
    end_t = cdata['end']
    etype = cdata['type']
    is_multi = cdata['multi']

    fac_list = find_fac_for(sec_name, code)
    fac_obj = fac_list[0] if fac_list else None
    all_fac_names = [f.full_name for f in fac_list] if fac_list else []

    res_obj = room_cache.get(room_code)
    full_name = abbr_full.get(code, abbr_full.get(code.upper(), code))
    subj_obj = get_or_make_subject(sec_name, code, full_name, etype)

    if full_name != code and subj_obj.name == code:
        subj_obj.name = full_name
        subj_obj.save()

    session_type = TYPE_MAP.get(etype, 'THEORY')

    meta = {
        'subject_code': code,
        'subject_name': full_name,
        'room_code': room_code,
        'type': etype,
        'multi_period': is_multi,
        'all_faculty': all_fac_names,
    }

    TimetableEntry.objects.create(
        timetable_version=version,
        section=sec_obj,
        subject=subj_obj,
        faculty=fac_obj,
        resource=res_obj,
        day_of_week=day_idx,
        start_time=start_t,
        end_time=end_t,
        session_type=session_type,
        original_text=json.dumps(meta, ensure_ascii=False),
        is_active=True,
    )
    created += 1
    if is_multi:
        multi_period += 1

print(f"Entries created : {created}")
print(f"Multi-period    : {multi_period}")
print(f"Skipped         : {skipped}")

# ── Final summary ─────────────────────────────────────────────────────────────
total = TimetableEntry.objects.filter(timetable_version=version).count()
with_fac  = TimetableEntry.objects.filter(timetable_version=version, faculty__isnull=False).count()
with_room = TimetableEntry.objects.filter(timetable_version=version, resource__isnull=False).count()
no_fac    = TimetableEntry.objects.filter(timetable_version=version, faculty__isnull=True)

print("\n=== FINAL SUMMARY ===")
print(f"  Total entries : {total}")
print(f"  With faculty  : {with_fac}  ({100*with_fac//max(total,1)}%)")
print(f"  With room     : {with_room} ({100*with_room//max(total,1)}%)")
print(f"  Rooms in DB   : {Resource.objects.filter(department=dept).count()}")
print(f"  Faculty in DB : {Faculty.objects.filter(is_active=True).count()}")

import collections
missing_codes = collections.Counter()
for e in no_fac:
    meta = json.loads(e.original_text) if e.original_text else {}
    missing_codes[meta.get('subject_code', '?')] += 1
print("\n  Remaining unmatched codes (Electives / Self-study / Institutional):")
for code, cnt in missing_codes.most_common(20):
    print(f"    [{cnt}x] {code}")

print("Done!")
