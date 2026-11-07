import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.timetables.models import TimetableEntry, TimetableVersion

version = TimetableVersion.objects.filter(is_active=True).first()
print(f"Active Timetable Version: {version}")

entries = list(TimetableEntry.objects.filter(timetable_version=version, is_active=True).select_related(
    'section', 'subject', 'faculty', 'resource'
))
print(f"Total entries in active version: {len(entries)}")

# 1. Faculty clashes:
faculty_clashes = []
# 2. Classroom clashes:
room_clashes = []
# 3. Lab clashes:
lab_clashes = []
# 4. Section clashes:
section_clashes = []

for i in range(len(entries)):
    e1 = entries[i]
    for j in range(i + 1, len(entries)):
        e2 = entries[j]
        if e1.day_of_week != e2.day_of_week:
            continue
        # Overlap condition: Start1 < End2 and Start2 < End1
        if e1.start_time < e2.end_time and e2.start_time < e1.end_time:
            # Overlap exists
            # Check Faculty clash:
            if e1.faculty and e2.faculty and e1.faculty_id == e2.faculty_id:
                faculty_clashes.append((e1, e2))
            
            # Check Resource clash:
            if e1.resource and e2.resource and e1.resource_id == e2.resource_id:
                if e1.resource.resource_type == 'LABORATORY':
                    lab_clashes.append((e1, e2))
                else:
                    room_clashes.append((e1, e2))
            
            # Check Section clash:
            if e1.section_id == e2.section_id:
                section_clashes.append((e1, e2))

print(f"\n--- CLASH DETECTION AUDIT REPORT ---")
print(f"Faculty Clashes: {len(faculty_clashes)}")
for e1, e2 in faculty_clashes[:5]:
    print(f"  Faculty {e1.faculty.full_name} on Day {e1.day_of_week}:")
    print(f"    Class 1: {e1.section.full_name} | {e1.subject.name} ({e1.start_time}-{e1.end_time}) [Room: {e1.resource.code if e1.resource else 'None'}]")
    print(f"    Class 2: {e2.section.full_name} | {e2.subject.name} ({e2.start_time}-{e2.end_time}) [Room: {e2.resource.code if e2.resource else 'None'}]")

print(f"\nClassroom Clashes: {len(room_clashes)}")
for e1, e2 in room_clashes[:5]:
    print(f"  Room {e1.resource.code} on Day {e1.day_of_week}:")
    print(f"    Class 1: {e1.section.full_name} | {e1.subject.name} ({e1.start_time}-{e1.end_time}) [Faculty: {e1.faculty.full_name if e1.faculty else 'None'}]")
    print(f"    Class 2: {e2.section.full_name} | {e2.subject.name} ({e2.start_time}-{e2.end_time}) [Faculty: {e2.faculty.full_name if e2.faculty else 'None'}]")

print(f"\nLaboratory Clashes: {len(lab_clashes)}")
for e1, e2 in lab_clashes[:5]:
    print(f"  Lab {e1.resource.code} on Day {e1.day_of_week}:")
    print(f"    Class 1: {e1.section.full_name} | {e1.subject.name} ({e1.start_time}-{e1.end_time})")
    print(f"    Class 2: {e2.section.full_name} | {e2.subject.name} ({e2.start_time}-{e2.end_time})")

print(f"\nSection Clashes: {len(section_clashes)}")
for e1, e2 in section_clashes[:5]:
    print(f"  Section {e1.section.full_name} on Day {e1.day_of_week}:")
    print(f"    Sub 1: {e1.subject.name} ({e1.start_time}-{e1.end_time})")
    print(f"    Sub 2: {e2.subject.name} ({e2.start_time}-{e2.end_time})")
