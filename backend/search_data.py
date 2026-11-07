import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.faculty.models import Faculty
from apps.timetables.models import TimetableEntry, ScheduleException
from apps.academics.models import Subject

# Check if any TimetableEntry or ScheduleException references J.Divya.M. Francis Xavier
combined = Faculty.objects.filter(full_name__icontains='Divya').first()
print("Combined faculty:", combined)
if combined:
    t_entries = TimetableEntry.objects.filter(faculty=combined)
    print("Timetable entries referencing combined:", t_entries.count())
    exceptions = ScheduleException.objects.filter(replacement_faculty=combined)
    print("Exceptions referencing combined:", exceptions.count())

# Let's search across all TimetableEntry for original_text containing Divya or Francis or Alumolu or Vidya
for term in ['Divya', 'Francis', 'Jagadeesh', 'Vidya', 'Gopi', 'Kumar Sai', 'Villas', 'CRT']:
    c1 = TimetableEntry.objects.filter(original_text__icontains=term).count()
    c2 = TimetableEntry.objects.filter(faculty__full_name__icontains=term).count()
    c3 = Faculty.objects.filter(full_name__icontains=term).count()
    print(f"Term '{term}': {c3} Faculty, {c2} TimetableEntry.faculty, {c1} TimetableEntry.original_text")
