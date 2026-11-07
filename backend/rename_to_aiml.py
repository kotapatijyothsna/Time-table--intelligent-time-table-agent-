"""Update database: rename ACSE dept to AIML, rename section full_names ACSE->AIML."""
import os, sys, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()

from apps.academics.models import Department, AcademicSection

# Rename department
dept = Department.objects.filter(code='ACSE').first()
if dept:
    dept.code = 'AIML'
    dept.name = 'Department of Artificial Intelligence & Machine Learning'
    dept.save()
    print(f"Department renamed to: {dept}")

# Rename sections: ACSE -> AIML
count = 0
for sec in AcademicSection.objects.filter(full_name__contains='ACSE'):
    old = sec.full_name
    sec.full_name = old.replace('ACSE', 'AIML')
    sec.save()
    count += 1
    print(f"  {old} -> {sec.full_name}")

print(f"\nRenamed {count} sections in DB")

# Also update JSON data files
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
for fname in ['section_master.json', 'subject_master.json', 'acse_timetable_entries.json', 'acse_faculty_assignments.json']:
    fpath = os.path.join(DATA, fname)
    if os.path.exists(fpath):
        with open(fpath, encoding='utf-8') as f:
            content = f.read()
        content = content.replace('ACSE', 'AIML')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated data file: {fname}")

# Rename data files
import shutil
old_tt = os.path.join(DATA, 'acse_timetable_entries.json')
new_tt = os.path.join(DATA, 'aiml_timetable_entries.json')
if os.path.exists(old_tt):
    shutil.copy2(old_tt, new_tt)
    print(f"Copied -> aiml_timetable_entries.json")

old_fa = os.path.join(DATA, 'acse_faculty_assignments.json')
new_fa = os.path.join(DATA, 'aiml_faculty_assignments.json')
if os.path.exists(old_fa):
    shutil.copy2(old_fa, new_fa)
    print(f"Copied -> aiml_faculty_assignments.json")

# List all sections
print("\nAll sections now:")
for s in AcademicSection.objects.all().order_by('year_level', 'full_name'):
    print(f"  {s.full_name}")
