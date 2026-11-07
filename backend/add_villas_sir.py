import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import transaction
from apps.faculty.models import Faculty
from apps.academics.models import Department, Subject
from apps.timetables.models import TimetableEntry

def setup_villas_sir():
    with transaction.atomic():
        aiml_dept = Department.objects.filter(code__iexact='AIML').first()
        if not aiml_dept:
            aiml_dept = Department.objects.first()

        # 1. Create or get Villas Sir
        villas, created = Faculty.objects.get_or_create(
            full_name='Villas Sir',
            defaults={
                'department': aiml_dept,
                'faculty_code': 'FAC-VILLAS-CRT',
                'designation': 'External / Outsourced Faculty',
                'faculty_type': 'OUTSOURCED',
                'is_outsourced': True,
                'is_active': True,
                'email': 'villas.crt@vignan.ac.in'
            }
        )
        if not created:
            villas.faculty_type = 'OUTSOURCED'
            villas.is_outsourced = True
            villas.designation = 'External / Outsourced Faculty'
            villas.save()

        print(f"Villas Sir record configured: ID={villas.id}, Type={villas.faculty_type}, Outsourced={villas.is_outsourced}")

        # 2. Check CRT-FSD subject
        crt_subj = Subject.objects.filter(name__icontains='CRT').first()
        print(f"CRT Subject: {crt_subj}")

        # 3. Associate all 21 CRT-FSD timetable entries with Villas Sir
        crt_entries = TimetableEntry.objects.filter(original_text__icontains='CRT')
        count = 0
        for e in crt_entries:
            e.faculty = villas
            try:
                meta = json.loads(e.original_text)
                meta['all_faculty'] = ['Villas Sir']
                e.original_text = json.dumps(meta)
            except Exception:
                pass
            e.save(update_fields=['faculty', 'original_text'])
            count += 1

        print(f"Successfully allocated {count} CRT-FSD timetable sessions to Villas Sir.")

        # Clean up any dummy 'FSD' teaching assistant record if present
        fsd_dummy = Faculty.objects.filter(full_name__iexact='FSD').first()
        if fsd_dummy and TimetableEntry.objects.filter(faculty=fsd_dummy).count() == 0:
            fsd_dummy.delete()
            print("Cleaned up orphaned dummy 'FSD' record.")

if __name__ == '__main__':
    setup_villas_sir()
