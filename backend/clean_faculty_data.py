import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import transaction
from apps.faculty.models import Faculty
from apps.timetables.models import TimetableEntry, ScheduleException
from apps.academics.models import Department

def clean_faculty_data():
    report = {
        'renamed': [],
        'merged': [],
        'separated': [],
        'unchanged': []
    }

    with transaction.atomic():
        print("Starting Faculty Name Cleaning and Data Validation...")

        # 1. Handle J.Divya.M. Francis Xavier
        combined_record = Faculty.objects.filter(full_name__icontains='Divya').filter(full_name__icontains='Francis').first()
        if combined_record:
            dept = combined_record.department
            print(f"Found combined record: '{combined_record.full_name}' (ID: {combined_record.id})")
            
            # Check or create J. Divya
            j_divya, created_d = Faculty.objects.get_or_create(
                full_name='J. Divya',
                department=dept,
                defaults={'designation': 'Assistant Professor', 'faculty_code': 'FAC-J-DIVYA'}
            )
            # Check or create M. Francis Xavier
            m_francis, created_f = Faculty.objects.get_or_create(
                full_name='M. Francis Xavier',
                department=dept,
                defaults={'designation': 'Assistant Professor', 'faculty_code': 'FAC-M-FRANCIS'}
            )

            # Reassign any references from combined_record
            t_count = TimetableEntry.objects.filter(faculty=combined_record).update(faculty=j_divya)
            s_count = ScheduleException.objects.filter(replacement_faculty=combined_record).update(replacement_faculty=j_divya)

            # Delete the combined anomaly record
            combined_record.delete()
            report['separated'].append({
                'original': 'J.Divya.M. Francis Xavier',
                'separated_into': ['J. Divya', 'M. Francis Xavier'],
                'reassigned_entries': t_count,
                'reassigned_exceptions': s_count
            })
            print("Successfully separated 'J.Divya.M. Francis Xavier' into 'J. Divya' and 'M. Francis Xavier'.")

        # 2. Weekday pattern cleaning: e.g. (WED), (wed), (TUESDAY), (MON), (THURSDAY)
        weekday_pattern = re.compile(r'\s*\((?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\)', re.IGNORECASE)

        facs_with_weekdays = [f for f in Faculty.objects.all() if weekday_pattern.search(f.full_name)]
        print(f"Found {len(facs_with_weekdays)} faculty records with weekday annotations.")

        for f in facs_with_weekdays:
            orig_name = f.full_name
            clean_name = weekday_pattern.sub('', orig_name).strip()
            
            # Look for an existing faculty with clean_name in the same department
            existing = Faculty.objects.filter(full_name__iexact=clean_name).exclude(id=f.id).first()
            if existing:
                # Merge into existing record
                t_count = TimetableEntry.objects.filter(faculty=f).update(faculty=existing)
                ex_count = ScheduleException.objects.filter(replacement_faculty=f).update(replacement_faculty=existing)
                f.delete()
                report['merged'].append({
                    'original': orig_name,
                    'merged_into': existing.full_name,
                    'target_id': str(existing.id),
                    'reassigned_entries': t_count,
                    'reassigned_exceptions': ex_count
                })
                print(f"Merged '{orig_name}' into existing '{existing.full_name}' (ID: {existing.id}).")
            else:
                # Rename the current record
                f.full_name = clean_name
                f.save()
                report['renamed'].append({
                    'original': orig_name,
                    'new_name': clean_name,
                    'id': str(f.id)
                })
                print(f"Renamed '{orig_name}' to '{clean_name}'.")

        # 3. Clean up any remaining records that have duplicate or double weekday entries
        # e.g., YARAGALLA KUMAR SAI might have had both (MON) and (THURSDAY)
        kumar_sai_list = list(Faculty.objects.filter(full_name__iexact='YARAGALLA KUMAR SAI'))
        if len(kumar_sai_list) > 1:
            primary = kumar_sai_list[0]
            for duplicate in kumar_sai_list[1:]:
                TimetableEntry.objects.filter(faculty=duplicate).update(faculty=primary)
                ScheduleException.objects.filter(replacement_faculty=duplicate).update(replacement_faculty=primary)
                duplicate.delete()
            print(f"Deduplicated YARAGALLA KUMAR SAI records into primary ID {primary.id}.")

        # 4. Also scan original_text in TimetableEntry and replace any raw weekday names in JSON
        entries_with_wed = TimetableEntry.objects.filter(original_text__icontains='(wed')
        for e in entries_with_wed:
            e.original_text = weekday_pattern.sub('', e.original_text)
            e.save(update_fields=['original_text'])

    print("\nFaculty Data Cleaning Complete! Report Summary:")
    print(report)
    return report

if __name__ == '__main__':
    clean_faculty_data()
