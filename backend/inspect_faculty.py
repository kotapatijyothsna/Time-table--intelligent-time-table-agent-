import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.faculty.models import Faculty
from apps.timetables.models import TimetableEntry, ScheduleException

facs = list(Faculty.objects.all().order_by('full_name'))
print(f"Total Faculty Count: {len(facs)}")

weekday_pattern = re.compile(r'\s*\((?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\)', re.IGNORECASE)

weekday_tagged = []
combined_names = []
other_parentheses = []

for f in facs:
    name = f.full_name
    if weekday_pattern.search(name):
        weekday_tagged.append(f)
    elif 'divya' in name.lower() and 'francis' in name.lower():
        combined_names.append(f)
    elif '(' in name or ')' in name:
        other_parentheses.append(f)

print(f"\n--- Faculty with Weekday Annotations ({len(weekday_tagged)}) ---")
for f in weekday_tagged:
    entries = TimetableEntry.objects.filter(faculty=f).count()
    cleaned = weekday_pattern.sub('', f.full_name).strip()
    clean_target = Faculty.objects.filter(full_name__iexact=cleaned).first()
    target_info = f"Matches existing ID {clean_target.id}" if clean_target else "No existing clean record"
    print(f"ID: {f.id} | '{f.full_name}' -> '{cleaned}' | Entries: {entries} | {target_info}")

print(f"\n--- Combined Names ({len(combined_names)}) ---")
for f in combined_names:
    entries = TimetableEntry.objects.filter(faculty=f).count()
    print(f"ID: {f.id} | '{f.full_name}' | Entries: {entries}")

print(f"\n--- Other Parentheses Names ({len(other_parentheses)}) ---")
for f in other_parentheses:
    entries = TimetableEntry.objects.filter(faculty=f).count()
    print(f"ID: {f.id} | '{f.full_name}' | Entries: {entries}")

# Also search original_text in TimetableEntry for J.Divya or Francis
print("\n--- TimetableEntry original_text / faculty references with 'divya' or 'francis' ---")
divya_entries = TimetableEntry.objects.filter(original_text__icontains='divya')
print(f"Entries matching 'divya' in original_text: {divya_entries.count()}")
for e in divya_entries[:10]:
    print(f"  Entry: {e.section.full_name} | {e.subject.name} | Faculty: {e.faculty} | Text: {e.original_text[:100]}")

francis_entries = TimetableEntry.objects.filter(original_text__icontains='francis')
print(f"Entries matching 'francis' in original_text: {francis_entries.count()}")
for e in francis_entries[:10]:
    print(f"  Entry: {e.section.full_name} | {e.subject.name} | Faculty: {e.faculty} | Text: {e.original_text[:100]}")
