import os
import json
import uuid
from datetime import date
from django.core.management.base import BaseCommand
from apps.academics.models import Department, AcademicTerm, AcademicSection, Subject
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry

class Command(BaseCommand):
    help = 'Seeds database with verified AIML timetable records from Phase 1 data artifacts'

    def handle(self, *args, **kwargs):
        self.stdout.write("Beginning AIML database seeding...")

        # 1. Department
        dept, _ = Department.objects.get_or_create(
            code="AIML",
            defaults={"name": "Department of Artificial Intelligence and Machine Learning"}
        )
        self.stdout.write(f"Department verified: {dept}")

        # 2. Academic Term
        term, _ = AcademicTerm.objects.get_or_create(
            department=dept,
            academic_year="2026-27",
            semester=1,
            defaults={
                "start_date": date(2026, 8, 17),
                "end_date": date(2026, 12, 31),
                "is_current": True
            }
        )
        self.stdout.write(f"Academic Term verified: {term}")

        # 3. Sections
        with open("../data/section_master.json", "r", encoding="utf-8") as f:
            sections_data = json.load(f)
        for s in sections_data:
            AcademicSection.objects.update_or_create(
                id=s["id"],
                defaults={
                    "department": dept,
                    "year_level": s["year_level"],
                    "section_code": s["section_code"],
                    "full_name": s["full_name"]
                }
            )
        self.stdout.write(f"Seeded {len(sections_data)} Sections.")

        # 4. Faculty
        with open("../data/faculty_master.json", "r", encoding="utf-8") as f:
            faculty_data = json.load(f)
        for fac in faculty_data:
            Faculty.objects.update_or_create(
                id=fac["id"],
                defaults={
                    "department": dept,
                    "full_name": fac["full_name"],
                    "designation": fac.get("designation", "Assistant Professor"),
                    "is_active": True
                }
            )
        self.stdout.write(f"Seeded {len(faculty_data)} Faculty records.")

        # 5. Subjects
        with open("../data/subject_master.json", "r", encoding="utf-8") as f:
            subject_data = json.load(f)
        for subj in subject_data:
            Subject.objects.update_or_create(
                id=subj["id"],
                defaults={
                    "department": dept,
                    "name": subj["name"],
                    "course_type": subj.get("course_type", "CORE")
                }
            )
        self.stdout.write(f"Seeded {len(subject_data)} Subjects.")

        # 6. Resources
        with open("../data/resource_master.json", "r", encoding="utf-8") as f:
            resource_data = json.load(f)
        for r in resource_data:
            Resource.objects.update_or_create(
                id=r["id"],
                defaults={
                    "department": dept,
                    "code": r["code"],
                    "name": r["name"],
                    "resource_type": r["resource_type"],
                    "capacity": r.get("capacity", 60),
                    "is_shared": r.get("is_shared", False)
                }
            )
        self.stdout.write(f"Seeded {len(resource_data)} Physical Resources.")

        # 7. Active Timetable Version
        version, _ = TimetableVersion.objects.get_or_create(
            term=term,
            version_number=1,
            defaults={
                "status": "APPROVED",
                "is_active": True,
                "change_summary": "Initial ingestion from ACSE TIMETABLE (V7) - W.e.f 17-8-2026.xlsx"
            }
        )

        # 8. Timetable Entries
        with open("../data/normalized_timetable_entries.json", "r", encoding="utf-8") as f:
            entries_data = json.load(f)

        entries_to_create = []
        for e in entries_data:
            entries_to_create.append(TimetableEntry(
                id=e["id"],
                timetable_version=version,
                section_id=e["section_id"],
                subject_id=e["subject_id"],
                resource_id=e["resource_id"],
                day_of_week=e["day_of_week"],
                start_time=e["start_time"],
                end_time=e["end_time"],
                session_type=e["session_type"],
                original_text=e.get("source_cell_content", "")
            ))

        TimetableEntry.objects.filter(timetable_version=version).delete()
        TimetableEntry.objects.bulk_create(entries_to_create)
        self.stdout.write(f"Successfully seeded {len(entries_to_create)} Timetable Entries into Version 1.")
