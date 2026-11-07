"""
Step 1: Department Setup & Section Reassignment
Step 2: Faculty Deduplication with Foreign Key Re-pointing
"""
import os, sys, django, re
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.academics.models import Department, AcademicSection
from apps.faculty.models import Faculty
from apps.timetables.models import TimetableEntry, ScheduleException

print("=== Step 1: Setting up Departments ===")
DEPARTMENTS = [
    ('AIML', 'Artificial Intelligence and Machine Learning'),
    ('CS', 'Computer Science and Engineering'),
    ('DS', 'Data Science'),
    ('CSBS', 'Computer Science and Business Systems'),
    ('IOT', 'Internet of Things'),
    ('BS(DS)', 'B.Sc (Data Science)'),
    ('MSC(DS)', 'M.Sc (Data Science)'),
    ('M.TECH', 'M.Tech (Data Science)'),
]

dept_objs = {}
for code, name in DEPARTMENTS:
    obj, created = Department.objects.get_or_create(code=code, defaults={'name': name})
    dept_objs[code] = obj
    if created:
        print(f"Created department: {code} - {name}")
    else:
        print(f"Existing department: {code} - {name}")

def get_dept_code_for_section(name):
    u = name.upper()
    if 'CSBS' in u: return 'CSBS'
    if 'IOT' in u: return 'IOT'
    if 'MTECH' in u or 'M.TECH' in u: return 'M.TECH'
    if 'MSC' in u: return 'MSC(DS)'
    if 'BS(DS)' in u or 'BS (DS)' in u: return 'BS(DS)'
    if 'AIML' in u: return 'AIML'
    if 'CS' in u: return 'CS'
    if 'DS' in u: return 'DS'
    return 'AIML'

print("\n=== Re-assigning Academic Sections to their respective Departments ===")
for sec in AcademicSection.objects.all():
    target_code = get_dept_code_for_section(sec.full_name)
    sec.department = dept_objs[target_code]
    sec.save()
    print(f"  {sec.full_name:30} -> {target_code}")

print("\n=== Step 2: Faculty Deduplication ===")
def canonical_norm(name):
    s = re.sub(r'^(dr\.?\s*|mr\.?\s*|ms\.?\s*|mrs\.?\s*|prof\.?\s*)', '', str(name).strip(), flags=re.I)
    s = re.sub(r'[^a-zA-Z0-9]', ' ', s).lower()
    return ' '.join(s.split())

def score_faculty_profile(f):
    score = 0
    # Prefer records with designations other than default 'Faculty' (like Teaching Assistant)
    if f.designation in ['Teaching Assistant', 'Outsourcing Staff']:
        score += 50
    # Prefer proper title format with a period and space
    if re.match(r'^(Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)\s+[A-Z]', f.full_name):
        score += 20
    # Prefer records that already have assigned timetable entries
    t_cnt = TimetableEntry.objects.filter(faculty=f).count()
    score += t_cnt * 2
    # Prefer records with official code
    if f.faculty_code and not f.faculty_code.startswith('FAC_'):
        score += 15
    return score

all_fac = list(Faculty.objects.all())
print(f"Initial total faculty count in DB: {len(all_fac)}")

grouped = defaultdict(list)
for f in all_fac:
    key = canonical_norm(f.full_name)
    grouped[key].append(f)

merged_count = 0
deleted_count = 0

for norm_name, members in grouped.items():
    if len(members) <= 1:
        continue

    # Sort so highest score is first (canonical)
    members.sort(key=score_faculty_profile, reverse=True)
    canonical = members[0]
    duplicates = members[1:]

    # Check if any duplicate has a specific designation we should adopt
    if canonical.designation == 'Faculty':
        for d in duplicates:
            if d.designation in ['Teaching Assistant', 'Outsourcing Staff']:
                canonical.designation = d.designation
                canonical.save()
                break

    print(f"\nMerging group [{norm_name}]:")
    print(f"  Canonical -> ID: {canonical.id} | Name: '{canonical.full_name}' | Desig: {canonical.designation}")

    for dup in duplicates:
        # Re-point TimetableEntry
        entries_updated = TimetableEntry.objects.filter(faculty=dup).update(faculty=canonical)
        # Re-point ScheduleException
        exceptions_updated = ScheduleException.objects.filter(replacement_faculty=dup).update(replacement_faculty=canonical)
        print(f"    Re-pointed {entries_updated} TimetableEntries, {exceptions_updated} Exceptions from '{dup.full_name}'")
        dup.delete()
        deleted_count += 1
        merged_count += 1

remaining_fac = Faculty.objects.count()
print(f"\nDeduplication Complete!")
print(f"  Deleted duplicate profiles: {deleted_count}")
print(f"  Final unique faculty in DB: {remaining_fac}")

# Verify no duplicate normalized names remain
post_grouped = defaultdict(list)
for f in Faculty.objects.all():
    post_grouped[canonical_norm(f.full_name)].append(f)
dups_remaining = {k: v for k, v in post_grouped.items() if len(v) > 1}
print(f"  Remaining duplicate groups: {len(dups_remaining)}")
assert len(dups_remaining) == 0, f"Error: duplicates still exist: {dups_remaining}"
print("All faculty profiles are strictly unique!")
