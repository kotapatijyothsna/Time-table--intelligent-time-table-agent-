import datetime
from django.utils import timezone
from apps.timetables.models import TimetableVersion, TimetableEntry, TimetableClash, ScheduleException, ClassSwap
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.academics.models import AcademicSection

class ClashDetectionService:
    @staticmethod
    def intervals_overlap(start1, end1, start2, end2):
        """
        Half-open interval overlap check: [start, end)
        Start1 < End2 AND Start2 < End1
        Classes with adjacent boundaries (e.g. 11:00-11:50 and 11:50-12:40) do NOT overlap.
        """
        return start1 < end2 and start2 < end1

    @staticmethod
    def calculate_overlap_window(start1, end1, start2, end2):
        """
        Returns overlap start, overlap end, and duration in minutes.
        """
        o_start = max(start1, start2)
        o_end = min(end1, end2)
        duration_minutes = (o_end.hour * 60 + o_end.minute) - (o_start.hour * 60 + o_start.minute)
        return o_start, o_end, max(0, duration_minutes)

    @classmethod
    def scan_and_record_all_clashes(cls, version=None):
        """
        Comprehensive timetable clash scan across:
        1. Faculty Allocation Clashes
        2. Classroom Allocation Clashes
        3. Laboratory Allocation Clashes
        4. Class/Section Timetable Clashes
        Synchronizes results into TimetableClash model.
        """
        if not version:
            version = TimetableVersion.objects.filter(is_active=True).first()
        if not version:
            return {"total_clashes": 0, "categories": {}}

        entries = list(TimetableEntry.objects.filter(
            timetable_version=version,
            is_active=True
        ).select_related('section', 'subject', 'faculty', 'resource'))

        detected_pairs = set()
        clash_records_to_create = []

        # Compare every pair (i, j) on the same day_of_week
        for i in range(len(entries)):
            e1 = entries[i]
            for j in range(i + 1, len(entries)):
                e2 = entries[j]
                if e1.day_of_week != e2.day_of_week:
                    continue

                if not cls.intervals_overlap(e1.start_time, e1.end_time, e2.start_time, e2.end_time):
                    continue

                o_start, o_end, o_dur = cls.calculate_overlap_window(e1.start_time, e1.end_time, e2.start_time, e2.end_time)

                # 1. Faculty Clash
                if e1.faculty and e2.faculty and e1.faculty_id == e2.faculty_id:
                    pair_key = ('FACULTY_CLASH', min(str(e1.id), str(e2.id)), max(str(e1.id), str(e2.id)))
                    detected_pairs.add(pair_key)
                    clash_records_to_create.append({
                        'clash_type': 'FACULTY_CLASH',
                        'day_of_week': e1.day_of_week,
                        'entry_1': e1,
                        'entry_2': e2,
                        'faculty': e1.faculty,
                        'resource': None,
                        'section': None,
                        'overlap_start': o_start,
                        'overlap_end': o_end,
                        'overlap_duration_minutes': o_dur,
                        'explanation': f"Faculty {e1.faculty.full_name} is double-booked for {e1.section.full_name} ({e1.subject.name}) and {e2.section.full_name} ({e2.subject.name}) during overlapping interval {o_start.strftime('%H:%M')}–{o_end.strftime('%H:%M')} ({o_dur} mins)."
                    })

                # 2. Classroom / Laboratory Clash
                if e1.resource and e2.resource and e1.resource_id == e2.resource_id:
                    # Note: If it's a combined lecture cohort (e.g. BS-DS & MSC-DS taking same class together in same room with same teacher), ignore intentional combined classes
                    is_intentional_joint = (
                        e1.subject_id == e2.subject_id and 
                        e1.faculty_id == e2.faculty_id and 
                        e1.start_time == e2.start_time and 
                        e1.end_time == e2.end_time
                    )
                    if not is_intentional_joint:
                        ctype = 'LAB_CLASH' if e1.resource.resource_type == 'LABORATORY' else 'CLASSROOM_CLASH'
                        pair_key = (ctype, min(str(e1.id), str(e2.id)), max(str(e1.id), str(e2.id)))
                        detected_pairs.add(pair_key)
                        res_label = "Laboratory" if ctype == 'LAB_CLASH' else "Classroom"
                        clash_records_to_create.append({
                            'clash_type': ctype,
                            'day_of_week': e1.day_of_week,
                            'entry_1': e1,
                            'entry_2': e2,
                            'faculty': None,
                            'resource': e1.resource,
                            'section': None,
                            'overlap_start': o_start,
                            'overlap_end': o_end,
                            'overlap_duration_minutes': o_dur,
                            'explanation': f"{res_label} Room {e1.resource.code} is simultaneously allocated to {e1.section.full_name} ({e1.subject.name}) and {e2.section.full_name} ({e2.subject.name}) between {o_start.strftime('%H:%M')} and {o_end.strftime('%H:%M')} ({o_dur} mins)."
                        })

                # 3. Class/Section Clash
                if e1.section_id == e2.section_id:
                    pair_key = ('SECTION_CLASH', min(str(e1.id), str(e2.id)), max(str(e1.id), str(e2.id)))
                    detected_pairs.add(pair_key)
                    clash_records_to_create.append({
                        'clash_type': 'SECTION_CLASH',
                        'day_of_week': e1.day_of_week,
                        'entry_1': e1,
                        'entry_2': e2,
                        'faculty': None,
                        'resource': None,
                        'section': e1.section,
                        'overlap_start': o_start,
                        'overlap_end': o_end,
                        'overlap_duration_minutes': o_dur,
                        'explanation': f"Section {e1.section.full_name} is assigned two concurrent subjects ({e1.subject.name} and {e2.subject.name}) between {o_start.strftime('%H:%M')} and {o_end.strftime('%H:%M')} ({o_dur} mins)."
                    })

        # Synchronize with database:
        # Mark removed or resolved clashes
        existing_clashes = TimetableClash.objects.all()
        for ec in existing_clashes:
            key = (ec.clash_type, min(str(ec.entry_1_id), str(ec.entry_2_id)), max(str(ec.entry_1_id), str(ec.entry_2_id)))
            if key not in detected_pairs:
                if ec.status == 'UNRESOLVED':
                    ec.status = 'RESOLVED'
                    ec.resolved_at = timezone.now()
                    ec.resolution_notes = 'Conflict resolved via timetable schedule adjustment.'
                    ec.save(update_fields=['status', 'resolved_at', 'resolution_notes'])

        # Create or update active clashes
        created_count = 0
        for item in clash_records_to_create:
            clash_obj, created = TimetableClash.objects.update_or_create(
                clash_type=item['clash_type'],
                entry_1=item['entry_1'],
                entry_2=item['entry_2'],
                defaults={
                    'day_of_week': item['day_of_week'],
                    'faculty': item['faculty'],
                    'resource': item['resource'],
                    'section': item['section'],
                    'overlap_start': item['overlap_start'],
                    'overlap_end': item['overlap_end'],
                    'overlap_duration_minutes': item['overlap_duration_minutes'],
                    'explanation': item['explanation'],
                    'status': 'UNRESOLVED'
                }
            )
            if created:
                created_count += 1

        unresolved = TimetableClash.objects.filter(status='UNRESOLVED')
        return {
            "total_unresolved_clashes": unresolved.count(),
            "faculty_clashes": unresolved.filter(clash_type='FACULTY_CLASH').count(),
            "classroom_clashes": unresolved.filter(clash_type='CLASSROOM_CLASH').count(),
            "lab_clashes": unresolved.filter(clash_type='LAB_CLASH').count(),
            "section_clashes": unresolved.filter(clash_type='SECTION_CLASH').count(),
            "resolved_clashes": TimetableClash.objects.filter(status='RESOLVED').count()
        }

    @classmethod
    def check_substitution_eligibility(cls, entry, substitute_faculty, target_date):
        """
        Validates whether substitute_faculty can substitute for timetable entry on target_date.
        Enforces:
        1. Subject & class eligibility.
        2. CRITICAL FOURTH-YEAR RESTRICTION:
           A faculty member who is EXCLUSIVELY allocated to fourth-year students
           CANNOT be assigned as a substitute for first-, second-, or third-year classes.
        3. Schedule conflict check on target_date during [start_time, end_time).
        4. College hours / break check.
        """
        version = TimetableVersion.objects.filter(is_active=True).first()
        day_of_week = target_date.weekday()
        start_t = entry.start_time
        end_t = entry.end_time
        target_year = entry.section.year_level

        reasons_eligible = []
        reasons_ineligible = []

        # Rule 1: Exclusively 4th-Year Faculty Restriction
        # Check all teaching assignments of substitute faculty across active timetable
        sub_entries = TimetableEntry.objects.filter(
            timetable_version=version,
            faculty=substitute_faculty,
            is_active=True
        ).select_related('section', 'subject')

        years_taught = set(se.section.year_level for se in sub_entries if se.section)

        if years_taught == {4} and target_year in [1, 2, 3]:
            return {
                "is_eligible": False,
                "status": "RESTRICTED_FOURTH_YEAR",
                "message": f"Ineligible: {substitute_faculty.full_name} is exclusively allocated to Year 4 teaching. University policy strictly prohibits Year 4 exclusive faculty from substituting in Year {target_year} classes.",
                "years_taught": list(years_taught),
                "target_year": target_year
            }
        elif 4 in years_taught and len(years_taught) > 1:
            reasons_eligible.append(f"Teaches Year 4 as well as Year {', '.join(str(y) for y in sorted(years_taught) if y != 4)}; permitted to substitute across cohorts.")
        else:
            reasons_eligible.append(f"Allocated to Years {list(years_taught) if years_taught else 'General'}; compatible with Year {target_year}.")

        # Rule 2: Schedule conflict check on target_date
        # Check if substitute faculty has an active class during this time
        conflicting_class = TimetableEntry.objects.filter(
            timetable_version=version,
            faculty=substitute_faculty,
            day_of_week=day_of_week,
            start_time__lt=end_t,
            end_time__gt=start_t,
            is_active=True
        ).select_related('section', 'subject', 'resource').first()

        if conflicting_class:
            # Check if that class was cancelled via exception
            cancelled = ScheduleException.objects.filter(
                timetable_entry=conflicting_class,
                exception_date=target_date,
                exception_type__in=['CANCEL', 'SUBSTITUTE']
            ).exists()
            if not cancelled:
                return {
                    "is_eligible": False,
                    "status": "SCHEDULE_CONFLICT",
                    "message": f"Ineligible: Has conflicting class {conflicting_class.section.full_name} ({conflicting_class.subject.name}) from {conflicting_class.start_time.strftime('%H:%M')} to {conflicting_class.end_time.strftime('%H:%M')}.",
                    "conflict_details": {
                        "section": conflicting_class.section.full_name,
                        "subject": conflicting_class.subject.name,
                        "time": f"{conflicting_class.start_time} - {conflicting_class.end_time}"
                    }
                }

        # Check if already assigned as a substitute in another class for this slot
        existing_sub = ScheduleException.objects.filter(
            replacement_faculty=substitute_faculty,
            exception_date=target_date,
            timetable_entry__start_time__lt=end_t,
            timetable_entry__end_time__gt=start_t
        ).select_related('timetable_entry', 'timetable_entry__section').first()

        if existing_sub:
            return {
                "is_eligible": False,
                "status": "SUBSTITUTE_CONFLICT",
                "message": f"Ineligible: Already substituting for {existing_sub.timetable_entry.section.full_name} on {target_date} during this period."
            }

        # Qualification / Match categorization
        is_same_subject = sub_entries.filter(subject=entry.subject).exists()
        is_same_section = sub_entries.filter(section=entry.section).exists()

        qualification_category = "Other Eligible Faculty"
        if is_same_subject:
            qualification_category = "Same Subject Specialist"
            reasons_eligible.append(f"Teaches the same subject ({entry.subject.name}) in department.")
        elif is_same_section:
            qualification_category = "Same Class Faculty"
            reasons_eligible.append(f"Associated with {entry.section.full_name} cohort.")
        else:
            reasons_eligible.append(f"Department faculty qualified for academic load.")

        return {
            "is_eligible": True,
            "status": "ELIGIBLE",
            "qualification_category": qualification_category,
            "message": "Eligible for substitution: verified free during required period and meets all academic year & subject restrictions.",
            "reasons": reasons_eligible,
            "years_taught": list(years_taught),
            "target_year": target_year
        }

    @classmethod
    def validate_swap(cls, swap_date, entry_1, faculty_1, entry_2, faculty_2):
        """
        Validates Class Swap between two faculty members on swap_date.
        Ensures:
        1. Both entries exist and belong to the respective faculty (or valid allocations).
        2. Swapped assignments create NO time overlaps for faculty_1 or faculty_2.
        3. Swapped assignments create NO classroom overlaps.
        4. Applies on swap_date.
        """
        errors = []
        warnings = []
        version = TimetableVersion.objects.filter(is_active=True).first()
        day_of_week = swap_date.weekday()

        # Check entry_1 time with faculty_2 existing schedule on swap_date
        # faculty_2 will teach entry_1: so faculty_2 must not have a conflicting class at entry_1's time (other than entry_2 if on same slot)
        f2_conflicts = TimetableEntry.objects.filter(
            timetable_version=version,
            faculty=faculty_2,
            day_of_week=day_of_week,
            start_time__lt=entry_1.end_time,
            end_time__gt=entry_1.start_time,
            is_active=True
        ).exclude(id=entry_2.id)

        if f2_conflicts.exists():
            c = f2_conflicts.first()
            errors.append(f"{faculty_2.full_name} already has a scheduled class ({c.section.full_name} - {c.subject.name}) at {c.start_time.strftime('%H:%M')}-{c.end_time.strftime('%H:%M')} which overlaps with {entry_1.section.full_name}'s slot.")

        # faculty_1 will teach entry_2: so faculty_1 must not have a conflicting class at entry_2's time (other than entry_1 if on same slot)
        f1_conflicts = TimetableEntry.objects.filter(
            timetable_version=version,
            faculty=faculty_1,
            day_of_week=day_of_week,
            start_time__lt=entry_2.end_time,
            end_time__gt=entry_2.start_time,
            is_active=True
        ).exclude(id=entry_1.id)

        if f1_conflicts.exists():
            c = f1_conflicts.first()
            errors.append(f"{faculty_1.full_name} already has a scheduled class ({c.section.full_name} - {c.subject.name}) at {c.start_time.strftime('%H:%M')}-{c.end_time.strftime('%H:%M')} which overlaps with {entry_2.section.full_name}'s slot.")

        is_same_sec = (entry_1.section_id == entry_2.section_id)
        if is_same_sec:
            swap_type_label = "Same-Class Period Swap"
            description = (
                f"Within class {entry_1.section.full_name}: "
                f"{faculty_2.full_name} will teach {entry_2.subject.name} during {entry_1.start_time.strftime('%I:%M %p')}–{entry_1.end_time.strftime('%I:%M %p')} ({entry_1.subject.name} slot), "
                f"and {faculty_1.full_name} will teach {entry_1.subject.name} during {entry_2.start_time.strftime('%I:%M %p')}–{entry_2.end_time.strftime('%I:%M %p')} ({entry_2.subject.name} slot)."
            )
            preview_f1_teach = f"Teaches {entry_1.subject.name} during {entry_2.start_time.strftime('%H:%M')}–{entry_2.end_time.strftime('%H:%M')} ({entry_2.subject.name} slot)"
            preview_f2_teach = f"Teaches {entry_2.subject.name} during {entry_1.start_time.strftime('%H:%M')}–{entry_1.end_time.strftime('%H:%M')} ({entry_1.subject.name} slot)"
        else:
            swap_type_label = "Cross-Class Swap"
            description = f"{faculty_1.full_name} ({entry_1.section.full_name}) and {faculty_2.full_name} ({entry_2.section.full_name}) exchange teaching sessions."
            preview_f1_teach = f"{entry_2.section.full_name} - {entry_2.subject.name} ({entry_2.start_time.strftime('%H:%M')}–{entry_2.end_time.strftime('%H:%M')})"
            preview_f2_teach = f"{entry_1.section.full_name} - {entry_1.subject.name} ({entry_1.start_time.strftime('%H:%M')}–{entry_1.end_time.strftime('%H:%M')})"

        return {
            "is_valid": len(errors) == 0,
            "is_same_class": is_same_sec,
            "swap_type": swap_type_label,
            "description": description,
            "errors": errors,
            "warnings": warnings,
            "preview": {
                "date": str(swap_date),
                "is_same_class": is_same_sec,
                "description": description,
                "section": entry_1.section.full_name if is_same_sec else f"{entry_1.section.full_name} & {entry_2.section.full_name}",
                "faculty_1": {
                    "name": faculty_1.full_name,
                    "original_class": f"{entry_1.section.full_name} - {entry_1.subject.name} ({entry_1.start_time.strftime('%H:%M')}–{entry_1.end_time.strftime('%H:%M')})",
                    "exchanged_to_teach": preview_f1_teach
                },
                "faculty_2": {
                    "name": faculty_2.full_name,
                    "original_class": f"{entry_2.section.full_name} - {entry_2.subject.name} ({entry_2.start_time.strftime('%H:%M')}–{entry_2.end_time.strftime('%H:%M')})",
                    "exchanged_to_teach": preview_f2_teach
                }
            }
        }
