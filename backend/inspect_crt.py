import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.timetables.models import TimetableEntry

crt_entries = TimetableEntry.objects.filter(original_text__icontains='CRT')
print(f"Total CRT entries in timetable: {crt_entries.count()}")
for e in crt_entries:
    print(f"ID: {e.id} | Day: {e.day_of_week} ({e.start_time}-{e.end_time}) | Section: {e.section.full_name} | Subject: {e.subject.name} | Faculty: {e.faculty} | Room: {e.resource} | Text: {e.original_text}")
