"""
Smart Campus - Apply Enriched Faculty & Classroom Matches to Database
Updates Django models and database records with standardized mappings.
"""

import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.academics.models import Department, Subject, AcademicSection
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry

def apply_enrichment():
    dept = Department.objects.get(code="AIML")
    version = TimetableVersion.objects.filter(is_active=True).first()
    if not version:
        print("No active version found!")
        return

    # 1. Update/Add standardized faculty
    with open("../data/faculty_ids.csv", "r", encoding="utf-8") as f:
        lines = f.readlines()[1:] # skip header
    
    faculty_cache = {}
    for line in lines:
        parts = line.strip().split(",", 1)
        if len(parts) == 2:
            fid, fname = parts[0].strip(), parts[1].strip()
            fac, _ = Faculty.objects.update_or_create(
                faculty_code=fid,
                defaults={
                    "department": dept,
                    "full_name": fname,
                    "designation": "Professor" if "DR." in fname.upper() else "Assistant Professor",
                    "is_active": True
                }
            )
            faculty_cache[fname] = fac

    print(f"Verified {len(faculty_cache)} Faculty members in DB.")

    # 2. Update/Add standardized subjects
    with open("../data/subject_ids.csv", "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]
    
    subject_cache = {}
    for line in lines:
        parts = line.strip().split(",", 1)
        if len(parts) == 2:
            sid, sname = parts[0].strip(), parts[1].strip().strip('"')
            subj, _ = Subject.objects.update_or_create(
                code=sid,
                defaults={
                    "department": dept,
                    "name": sname,
                    "course_type": "CORE" if "DE" not in sname and "OE" not in sname else "ELECTIVE"
                }
            )
            subject_cache[sname] = subj

    print(f"Verified {len(subject_cache)} Subjects in DB.")

    # 3. Read matched timetable entries
    with open("../data/matched_timetable_with_faculty_and_rooms.json", "r", encoding="utf-8") as f:
        matched_entries = json.load(f)

    updated_count = 0
    for e in matched_entries:
        entry_id = e["id"]
        primary_fac_name = e.get("faculty_name")
        all_facs = e.get("all_assigned_faculty", [])
        matched_subj_name = e.get("matched_subject_name")
        room_code = e.get("room_code")

        # Resolve faculty object
        fac_obj = faculty_cache.get(primary_fac_name)
        if not fac_obj and all_facs:
            fac_obj = faculty_cache.get(all_facs[0])

        # Resolve subject object
        subj_obj = subject_cache.get(matched_subj_name)
        if not subj_obj:
            # Fallback search
            for sname, s_inst in subject_cache.items():
                if matched_subj_name.upper() in sname.upper() or sname.upper() in matched_subj_name.upper():
                    subj_obj = s_inst
                    break

        # Resolve resource
        res_obj = None
        if room_code and room_code != "Unassigned / General":
            res_obj = Resource.objects.filter(code=room_code).first()

        try:
            entry = TimetableEntry.objects.get(id=entry_id)
            if fac_obj:
                entry.faculty = fac_obj
            if subj_obj:
                entry.subject = subj_obj
            if res_obj:
                entry.resource = res_obj

            # Store the full assignment metadata in original_text as JSON
            meta = {
                "all_faculty": all_facs,
                "primary_faculty": primary_fac_name,
                "teaching_mode": e.get("teaching_mode", "L"),
                "subject_name": matched_subj_name,
                "room_code": room_code
            }
            entry.original_text = json.dumps(meta)
            entry.save()
            updated_count += 1
        except TimetableEntry.DoesNotExist:
            pass

    print(f"Successfully updated {updated_count} Timetable Entries with verified Faculty, Class, Subject & Room matches!")

if __name__ == "__main__":
    apply_enrichment()
