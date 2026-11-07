"""
Import all ACSE timetable data into the Django database.
Loads sections for ALL branches: ACSE, CS, DS, CSBS, IOT, BS(DS), MSC(DS), M.TECH
"""

import os
import sys
import json
import re
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from apps.academics.models import Department, AcademicSection, Subject, AcademicTerm
from apps.faculty.models import Faculty
from apps.timetables.models import TimetableVersion, TimetableEntry

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# 1. Department
dept, created = Department.objects.update_or_create(
    code='ACSE',
    defaults={'name': 'Department of Advanced Computer Science and Engineering'}
)
# Remove old AIML dept if exists
Department.objects.filter(code='AIML').exclude(id=dept.id).delete()
print(f"Department: {'Created' if created else 'Updated'} - {dept}")

# 2. Academic Term
term, _ = AcademicTerm.objects.update_or_create(
    department=dept,
    academic_year='2026-27',
    semester=1,
    defaults={
        'start_date': datetime.date(2026, 8, 17),
        'end_date': datetime.date(2026, 12, 31),
        'is_current': True,
    }
)
print(f"Term: {term}")

# 3. Timetable Version (uses term + version_number)
version, _ = TimetableVersion.objects.update_or_create(
    term=term,
    version_number=7,
    defaults={
        'status': 'APPROVED',
        'is_active': True,
        'change_summary': 'ACSE V7 Timetable - W.e.f 17-08-2026',
    }
)
TimetableVersion.objects.exclude(id=version.id).update(is_active=False)
print(f"Version: {version}")

# 4. Load Sections
with open(os.path.join(DATA_DIR, 'section_master.json'), encoding='utf-8') as f:
    sections_data = json.load(f)

section_cache = {}
created_sec = 0
for s in sections_data:
    name = s['name'].strip()
    year_level = 2
    ym = re.match(r'^(IV|III|II|I)\s', name)
    if ym:
        year_level = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}.get(ym.group(1), 2)
    sec_code = name.split('-')[-1].strip()[:10] if '-' in name else name[:10]

    obj, cr = AcademicSection.objects.update_or_create(
        full_name=name,
        defaults={
            'department': dept,
            'year_level': year_level,
            'section_code': sec_code,
        }
    )
    section_cache[name] = obj
    if cr:
        created_sec += 1

print(f"Sections: {created_sec} created, {len(section_cache)} total")

# 5. Load Faculty
with open(os.path.join(DATA_DIR, 'faculty_master.json'), encoding='utf-8') as f:
    faculty_data = json.load(f)

faculty_cache = {}
created_fac = 0
for fac in faculty_data:
    name = fac['full_name'].strip()
    desig = fac.get('designation', 'Faculty')
    obj, cr = Faculty.objects.update_or_create(
        full_name=name,
        defaults={
            'department': dept,
            'designation': desig,
            'is_active': True,
        }
    )
    faculty_cache[name.lower()] = obj
    if cr:
        created_fac += 1

print(f"Faculty: {created_fac} created, {len(faculty_cache)} total")

# 6. Load Subjects
with open(os.path.join(DATA_DIR, 'subject_master.json'), encoding='utf-8') as f:
    subjects_data = json.load(f)

subject_cache = {}
created_subj = 0
for subj in subjects_data:
    code = subj.get('code', '').strip()
    name = subj.get('name', code).strip()
    if not code:
        continue
    sec_name = subj.get('section', '').strip()
    uniq_code = f"{sec_name}_{code}"[:30]
    obj, cr = Subject.objects.update_or_create(
        code=uniq_code,
        defaults={
            'department': dept,
            'name': name,
            'course_type': 'PRACTICAL' if subj.get('type') == 'P' else 'CORE',
        }
    )
    subject_cache[uniq_code] = obj
    if cr:
        created_subj += 1

print(f"Subjects: {created_subj} created, {len(subject_cache)} total")

# 7. Load Timetable Entries
with open(os.path.join(DATA_DIR, 'acse_timetable_entries.json'), encoding='utf-8') as f:
    entries_data = json.load(f)

PERIOD_TIMES = {
    '1': (datetime.time(8, 15), datetime.time(9, 5)),
    '2': (datetime.time(9, 5), datetime.time(9, 55)),
    '3': (datetime.time(10, 10), datetime.time(11, 0)),
    '4': (datetime.time(11, 0), datetime.time(11, 50)),
    '5': (datetime.time(11, 50), datetime.time(12, 40)),
    '6': (datetime.time(13, 40), datetime.time(14, 30)),
    '7': (datetime.time(14, 30), datetime.time(15, 20)),
    '8': (datetime.time(15, 20), datetime.time(16, 5)),
}
DAY_MAP = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5}
TYPE_MAP = {'L': 'THEORY', 'T': 'TUTORIAL', 'P': 'PRACTICAL'}

TimetableEntry.objects.filter(timetable_version=version).delete()
print("Cleared old timetable entries.")

created_entries = 0
skipped = 0
for e in entries_data:
    sec_name = e.get('section', '').strip()
    sec_obj = section_cache.get(sec_name)
    if not sec_obj:
        skipped += 1
        continue

    day_idx = DAY_MAP.get(e.get('day', 'MON').strip(), 0)
    period = str(e.get('period', '1'))
    start_t, end_t = PERIOD_TIMES.get(period, (datetime.time(8, 15), datetime.time(9, 5)))

    code = e.get('subject_code', '').strip()
    uniq_code = f"{sec_name}_{code}"[:30]
    subj_obj = subject_cache.get(uniq_code)
    if not subj_obj:
        subj_obj, _ = Subject.objects.get_or_create(
            code=uniq_code,
            defaults={'department': dept, 'name': e.get('subject_name', code), 'course_type': 'CORE'}
        )
        subject_cache[uniq_code] = subj_obj

    room_code = e.get('room', '').strip()
    session_type = TYPE_MAP.get(e.get('type', 'L'), 'THEORY')

    TimetableEntry.objects.create(
        timetable_version=version,
        section=sec_obj,
        subject=subj_obj,
        faculty=None,
        resource=None,
        day_of_week=day_idx,
        start_time=start_t,
        end_time=end_t,
        session_type=session_type,
        original_text=f"{code} | Room: {room_code}",
        is_active=True,
    )
    created_entries += 1

print(f"Timetable entries: {created_entries} created, {skipped} skipped")

# Summary
print("\n=== DATABASE IMPORT COMPLETE ===")
print(f"  Department : {dept.name}")
print(f"  Sections   : {AcademicSection.objects.filter(department=dept).count()}")
print(f"  Faculty    : {Faculty.objects.filter(department=dept).count()}")
print(f"  Subjects   : {Subject.objects.filter(department=dept).count()}")
print(f"  TT Entries : {TimetableEntry.objects.filter(timetable_version=version).count()}")

print("\nAll sections in DB:")
for sec in AcademicSection.objects.filter(department=dept).order_by('year_level', 'full_name'):
    print(f"  {sec.full_name}")
