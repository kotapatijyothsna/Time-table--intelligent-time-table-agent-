import datetime
import json
from django.utils import timezone
from apps.resources.models import Resource, ResourceBlock
from apps.faculty.models import Faculty
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException, ClassSwap

# Standard Academic Periods at VFSTR
PERIODS = {
    1: {'name': 'Period 1', 'start': datetime.time(8, 15), 'end': datetime.time(9, 5), 'label': 'Period 1 (08:15 - 09:05)'},
    2: {'name': 'Period 2', 'start': datetime.time(9, 5), 'end': datetime.time(9, 55), 'label': 'Period 2 (09:05 - 09:55)'},
    3: {'name': 'Period 3', 'start': datetime.time(10, 10), 'end': datetime.time(11, 0), 'label': 'Period 3 (10:10 - 11:00)'},
    4: {'name': 'Period 4', 'start': datetime.time(11, 0), 'end': datetime.time(11, 50), 'label': 'Period 4 (11:00 - 11:50)'},
    5: {'name': 'Period 5', 'start': datetime.time(11, 50), 'end': datetime.time(12, 40), 'label': 'Period 5 (11:50 - 12:40)'},
    6: {'name': 'Period 6', 'start': datetime.time(13, 40), 'end': datetime.time(14, 30), 'label': 'Period 6 (13:40 - 14:30)'},
    7: {'name': 'Period 7', 'start': datetime.time(14, 30), 'end': datetime.time(15, 20), 'label': 'Period 7 (14:30 - 15:20)'},
    8: {'name': 'Period 8', 'start': datetime.time(15, 20), 'end': datetime.time(16, 5), 'label': 'Period 8 (15:20 - 16:05)'},
}

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

class AvailabilityService:
    @staticmethod
    def get_active_version():
        return TimetableVersion.objects.filter(is_active=True).first()

    @classmethod
    def resolve_slot(cls, period=None, start_time=None, end_time=None):
        """
        Resolves period number or start/end time strings into datetime.time objects.
        """
        if period and int(period) in PERIODS:
            p_data = PERIODS[int(period)]
            return p_data['start'], p_data['end'], p_data['label'], int(period)

        req_start = datetime.time.fromisoformat(start_time) if isinstance(start_time, str) else (start_time or datetime.time(10, 10))
        req_end = datetime.time.fromisoformat(end_time) if isinstance(end_time, str) else (end_time or datetime.time(11, 0))

        # Check if matches any defined period
        detected_p = None
        for p_num, p_data in PERIODS.items():
            if p_data['start'] == req_start and p_data['end'] == req_end:
                detected_p = p_num
                break

        slot_label = f"{req_start.strftime('%H:%M')} - {req_end.strftime('%H:%M')}"
        if detected_p:
            slot_label = PERIODS[detected_p]['label']

        return req_start, req_end, slot_label, detected_p

    @staticmethod
    def is_time_overlapping(s_t, e_t, req_start, req_end):
        if req_start and req_end:
            return s_t < req_end and e_t > req_start
        elif req_start:
            return s_t <= req_start < e_t
        elif req_end:
            return s_t < req_end <= e_t
        return True

    @classmethod
    def evaluate_resource_status(cls, resource, check_date=None, req_start=None, req_end=None, day_of_week=None):
        """
        Evaluates availability of a Classroom or Laboratory strictly based on imported timetable data.
        Returns ONLY:
          - "Occupied"
          - "Unoccupied"
        No "Not Verified", "Unknown", "Pending", or "Unscheduled".
        Considers all departments and branches (CS, DS, CSBS, IoT, AIML, BS, MSC, MTech).
        """
        version = cls.get_active_version()

        if day_of_week is None:
            day_of_week = check_date.weekday() if check_date else 0

        # Maintenance block check: if blocked, it is Occupied
        if check_date and req_start and req_end:
            dt_start = timezone.make_aware(datetime.datetime.combine(check_date, req_start))
            dt_end = timezone.make_aware(datetime.datetime.combine(check_date, req_end))
            block = ResourceBlock.objects.filter(
                resource=resource,
                start_datetime__lt=dt_end,
                end_datetime__gt=dt_start
            ).first()
            if block:
                return {
                    "status": "Occupied",
                    "reason": f"Maintenance block: {block.reason}",
                    "evidence": None
                }

        if not version:
            return {
                "status": "Unoccupied",
                "reason": "No active timetable sessions scheduled.",
                "evidence": None
            }

        # Check Active Timetable Entries across ALL departments and sections
        # Multi-period classes are naturally captured by interval overlap:
        # entry.start_time < req_end AND entry.end_time > req_start
        resource_entries_qs = TimetableEntry.objects.filter(
            timetable_version=version,
            resource=resource,
            day_of_week=day_of_week,
            is_active=True
        ).select_related('section', 'section__department', 'subject', 'faculty')

        if req_start and req_end:
            resource_entries_qs = resource_entries_qs.filter(start_time__lt=req_end, end_time__gt=req_start)
        elif req_start:
            resource_entries_qs = resource_entries_qs.filter(start_time__lte=req_start, end_time__gt=req_start)
        elif req_end:
            resource_entries_qs = resource_entries_qs.filter(start_time__lt=req_end, end_time__gte=req_end)

        conflicting_entry = None
        for cand in resource_entries_qs:
            # Check if this baseline session is relieved on check_date via CANCEL, RESOURCE_CHANGE, or RESCHEDULE
            if check_date:
                ex = ScheduleException.objects.filter(
                    timetable_entry=cand,
                    exception_date=check_date
                ).exclude(status='REJECTED').first()
                if ex and ex.exception_type in ['CANCEL', 'RESOURCE_CHANGE', 'RESCHEDULE']:
                    # The room is relieved from this baseline class!
                    continue
            conflicting_entry = cand
            break

        if conflicting_entry:
            fac_display = conflicting_entry.faculty.full_name if conflicting_entry.faculty else "Unassigned"
            all_facs = [fac_display] if conflicting_entry.faculty else []
            subj_display = conflicting_entry.subject.name

            # Check if faculty was substituted or swapped for this room's class
            if check_date:
                sub_ex = ScheduleException.objects.filter(
                    timetable_entry=conflicting_entry,
                    exception_date=check_date,
                    exception_type='SUBSTITUTE'
                ).exclude(status='REJECTED').select_related('replacement_faculty').first()
                if sub_ex and sub_ex.replacement_faculty:
                    fac_display = f"{sub_ex.replacement_faculty.full_name} (Substitute for {conflicting_entry.faculty.full_name if conflicting_entry.faculty else 'Faculty'})"
                    all_facs = [sub_ex.replacement_faculty.full_name]
                else:
                    swap1 = ClassSwap.objects.filter(status='APPROVED', swap_date=check_date, entry_1=conflicting_entry).select_related('faculty_1', 'faculty_2', 'entry_2', 'entry_2__subject').first()
                    if swap1:
                        fac_display = f"{swap1.faculty_2.full_name} (Swapped with {swap1.faculty_1.full_name})"
                        all_facs = [swap1.faculty_2.full_name]
                        if swap1.entry_1.section_id == swap1.entry_2.section_id:
                            subj_display = f"{swap1.entry_2.subject.name} [SWAP: {swap1.entry_1.subject.name} SLOT]"
                    else:
                        swap2 = ClassSwap.objects.filter(status='APPROVED', swap_date=check_date, entry_2=conflicting_entry).select_related('faculty_1', 'faculty_2', 'entry_1', 'entry_1__subject').first()
                        if swap2:
                            fac_display = f"{swap2.faculty_1.full_name} (Swapped with {swap2.faculty_2.full_name})"
                            all_facs = [swap2.faculty_1.full_name]
                            if swap2.entry_1.section_id == swap2.entry_2.section_id:
                                subj_display = f"{swap2.entry_1.subject.name} [SWAP: {swap2.entry_2.subject.name} SLOT]"

            try:
                meta = json.loads(conflicting_entry.original_text)
                if isinstance(meta, dict) and meta.get("all_faculty") and not check_date:
                    all_facs = meta["all_faculty"]
                    fac_display = ", ".join(all_facs)
            except Exception:
                pass

            dept_code = conflicting_entry.section.department.code if conflicting_entry.section.department else "AIML"

            return {
                "status": "Occupied",
                "reason": f"Scheduled class for {conflicting_entry.section.full_name}",
                "evidence": {
                    "section": conflicting_entry.section.full_name,
                    "department": dept_code,
                    "subject": subj_display,
                    "faculty": fac_display,
                    "all_faculty": all_facs,
                    "session_type": conflicting_entry.session_type,
                    "start_time": str(conflicting_entry.start_time),
                    "end_time": str(conflicting_entry.end_time)
                }
            }

        # Check for reallocated/rescheduled session moving TO or scheduled in this resource
        if check_date:
            reallocated_qs = ScheduleException.objects.filter(
                exception_date=check_date
            ).exclude(status='REJECTED').select_related(
                'timetable_entry', 'timetable_entry__section', 'timetable_entry__section__department',
                'timetable_entry__subject', 'timetable_entry__faculty', 'replacement_faculty', 'replacement_resource'
            )
            for reallocated in reallocated_qs:
                e = reallocated.timetable_entry
                is_target_res = (reallocated.replacement_resource == resource) or \
                                (e.resource == resource and reallocated.exception_type == 'RESCHEDULE' and not reallocated.replacement_resource)
                if not is_target_res:
                    continue

                s_t = reallocated.new_start_time or e.start_time
                e_t = reallocated.new_end_time or e.end_time
                if cls.is_time_overlapping(s_t, e_t, req_start, req_end):
                    fac_display = reallocated.replacement_faculty.full_name if reallocated.replacement_faculty else (e.faculty.full_name if e.faculty else "Unassigned")
                    dept_code = e.section.department.code if e.section.department else "AIML"
                    return {
                        "status": "Occupied",
                        "reason": f"{reallocated.exception_type} session: {reallocated.reason}",
                        "evidence": {
                            "section": e.section.full_name,
                            "department": dept_code,
                            "subject": f"{e.subject.name} [{reallocated.exception_type}]",
                            "faculty": fac_display,
                            "all_faculty": [fac_display],
                            "session_type": e.session_type,
                            "start_time": str(s_t),
                            "end_time": str(e_t)
                        }
                    }

        return {
            "status": "Unoccupied",
            "reason": "No classes scheduled during this period.",
            "evidence": None
        }

    @classmethod
    def evaluate_faculty_status(cls, faculty, check_date=None, req_start=None, req_end=None, day_of_week=None):
        """
        Determines availability of a faculty member across all departments and sections.
        Returns:
          - "Occupied" (if faculty has any class in that period)
          - "Available" (if no class is scheduled)
        """
        version = cls.get_active_version()
        if not version:
            return {"status": "Available", "reason": "No active timetable sessions scheduled.", "evidence": None}

        if day_of_week is None:
            day_of_week = check_date.weekday() if check_date else 0

        # Query all overlapping timetable entries across every department & section
        faculty_entries_qs = TimetableEntry.objects.filter(
            timetable_version=version,
            day_of_week=day_of_week,
            is_active=True
        ).select_related('section', 'section__department', 'subject', 'resource', 'faculty')

        if req_start and req_end:
            faculty_entries_qs = faculty_entries_qs.filter(start_time__lt=req_end, end_time__gt=req_start)
        elif req_start:
            faculty_entries_qs = faculty_entries_qs.filter(start_time__lte=req_start, end_time__gt=req_start)
        elif req_end:
            faculty_entries_qs = faculty_entries_qs.filter(start_time__lt=req_end, end_time__gte=req_end)

        overlapping_entries = faculty_entries_qs

        matching_entry = None
        for entry in faculty_entries_qs:
            is_fac_entry = (entry.faculty == faculty)
            if not is_fac_entry:
                try:
                    meta = json.loads(entry.original_text)
                    if isinstance(meta, dict) and "all_faculty" in meta:
                        fac_name = faculty.full_name.upper().strip()
                        if any(fac_name in f.upper().strip() or f.upper().strip() in fac_name for f in meta["all_faculty"]):
                            is_fac_entry = True
                except Exception:
                    pass

            if is_fac_entry:
                # Check if this faculty is relieved from this entry on check_date
                if check_date:
                    ex = ScheduleException.objects.filter(
                        timetable_entry=entry,
                        exception_date=check_date
                    ).exclude(status='REJECTED').first()
                    # If CANCEL, SUBSTITUTE, or RESCHEDULE -> faculty is relieved from this original slot!
                    if ex and ex.exception_type in ['CANCEL', 'SUBSTITUTE', 'RESCHEDULE']:
                        continue
                    # If ClassSwap gave away this class -> faculty is relieved!
                    if ClassSwap.objects.filter(status='APPROVED', swap_date=check_date, faculty_1=faculty, entry_1=entry).exists() or \
                       ClassSwap.objects.filter(status='APPROVED', swap_date=check_date, faculty_2=faculty, entry_2=entry).exists():
                        continue
                matching_entry = entry
                break

        if matching_entry:
            dept_code = matching_entry.section.department.code if matching_entry.section.department else "AIML"
            room_code = matching_entry.resource.code if matching_entry.resource else "Unassigned"
            # If classroom was changed for this class on check_date:
            if check_date:
                room_ex = ScheduleException.objects.filter(
                    timetable_entry=matching_entry,
                    exception_date=check_date,
                    exception_type='RESOURCE_CHANGE'
                ).exclude(status='REJECTED').select_related('replacement_resource').first()
                if room_ex and room_ex.replacement_resource:
                    room_code = room_ex.replacement_resource.code

            return {
                "status": "Occupied",
                "reason": f"Teaching {matching_entry.subject.name} for {matching_entry.section.full_name}",
                "evidence": {
                    "section": matching_entry.section.full_name,
                    "department": dept_code,
                    "subject": matching_entry.subject.name,
                    "room": room_code,
                    "start_time": str(matching_entry.start_time),
                    "end_time": str(matching_entry.end_time)
                }
            }

        # Check for substitute session assigned TO this faculty
        if check_date:
            sub_exceptions = ScheduleException.objects.filter(
                replacement_faculty=faculty,
                exception_date=check_date,
                exception_type='SUBSTITUTE'
            ).exclude(status='REJECTED').select_related('timetable_entry', 'timetable_entry__section', 'timetable_entry__subject', 'timetable_entry__resource', 'replacement_resource')
            for sub_exception in sub_exceptions:
                e = sub_exception.timetable_entry
                s_t = sub_exception.new_start_time or e.start_time
                e_t = sub_exception.new_end_time or e.end_time
                if cls.is_time_overlapping(s_t, e_t, req_start, req_end):
                    room_display = sub_exception.replacement_resource.code if sub_exception.replacement_resource else (e.resource.code if e.resource else "Unassigned")
                    return {
                        "status": "Occupied",
                        "reason": f"Substitute session: {sub_exception.reason}",
                        "evidence": {
                            "section": e.section.full_name,
                            "department": e.section.department.code if e.section.department else "AIML",
                            "subject": f"{e.subject.name} [SUBSTITUTE]",
                            "room": room_display,
                            "start_time": str(s_t),
                            "end_time": str(e_t)
                        }
                    }

            # Check for rescheduled session assigned to / taught by this faculty
            resched_exceptions = ScheduleException.objects.filter(
                exception_date=check_date,
                exception_type='RESCHEDULE'
            ).exclude(status='REJECTED').select_related('timetable_entry', 'timetable_entry__section', 'timetable_entry__subject', 'timetable_entry__faculty', 'timetable_entry__resource', 'replacement_faculty', 'replacement_resource')
            for r_ex in resched_exceptions:
                is_fac = (r_ex.replacement_faculty == faculty) or (r_ex.timetable_entry.faculty == faculty and not r_ex.replacement_faculty)
                if not is_fac:
                    continue
                s_t = r_ex.new_start_time or r_ex.timetable_entry.start_time
                e_t = r_ex.new_end_time or r_ex.timetable_entry.end_time
                if cls.is_time_overlapping(s_t, e_t, req_start, req_end):
                    room_display = r_ex.replacement_resource.code if r_ex.replacement_resource else (r_ex.timetable_entry.resource.code if r_ex.timetable_entry.resource else "Unassigned")
                    return {
                        "status": "Occupied",
                        "reason": f"Rescheduled session: {r_ex.reason}",
                        "evidence": {
                            "section": r_ex.timetable_entry.section.full_name,
                            "department": r_ex.timetable_entry.section.department.code if r_ex.timetable_entry.section.department else "AIML",
                            "subject": f"{r_ex.timetable_entry.subject.name} [RESCHEDULED]",
                            "room": room_display,
                            "start_time": str(s_t),
                            "end_time": str(e_t)
                        }
                    }

            # Check for class swap assigned TO this faculty
            swap_takeover_1_qs = ClassSwap.objects.filter(
                status='APPROVED',
                swap_date=check_date,
                faculty_1=faculty
            ).select_related('entry_2', 'entry_2__section', 'entry_2__subject', 'entry_2__resource', 'faculty_2', 'entry_1', 'entry_1__subject')

            for swap_takeover_1 in swap_takeover_1_qs:
                e = swap_takeover_1.entry_2
                if cls.is_time_overlapping(e.start_time, e.end_time, req_start, req_end):
                    is_same_sec = (swap_takeover_1.entry_1.section_id == e.section_id)
                    teaching_subj = swap_takeover_1.entry_1.subject.name if is_same_sec else e.subject.name
                    slot_info = f" ({e.subject.name} Slot)" if is_same_sec else ""
                    return {
                        "status": "Occupied",
                        "reason": f"Swapped Period: Teaching {teaching_subj} for {e.section.full_name}{slot_info} (Exchanged with {swap_takeover_1.faculty_2.full_name})",
                        "evidence": {
                            "section": e.section.full_name,
                            "department": e.section.department.code if e.section.department else "AIML",
                            "subject": f"{teaching_subj} [SWAP]",
                            "room": e.resource.code if e.resource else "Unassigned",
                            "start_time": str(e.start_time),
                            "end_time": str(e.end_time)
                        }
                    }

            swap_takeover_2_qs = ClassSwap.objects.filter(
                status='APPROVED',
                swap_date=check_date,
                faculty_2=faculty
            ).select_related('entry_1', 'entry_1__section', 'entry_1__subject', 'entry_1__resource', 'faculty_1', 'entry_2', 'entry_2__subject')

            for swap_takeover_2 in swap_takeover_2_qs:
                e = swap_takeover_2.entry_1
                if cls.is_time_overlapping(e.start_time, e.end_time, req_start, req_end):
                    is_same_sec = (swap_takeover_2.entry_2.section_id == e.section_id)
                    teaching_subj = swap_takeover_2.entry_2.subject.name if is_same_sec else e.subject.name
                    slot_info = f" ({e.subject.name} Slot)" if is_same_sec else ""
                    return {
                        "status": "Occupied",
                        "reason": f"Swapped Period: Teaching {teaching_subj} for {e.section.full_name}{slot_info} (Exchanged with {swap_takeover_2.faculty_1.full_name})",
                        "evidence": {
                            "section": e.section.full_name,
                            "department": e.section.department.code if e.section.department else "AIML",
                            "subject": f"{teaching_subj} [SWAP]",
                            "room": e.resource.code if e.resource else "Unassigned",
                            "start_time": str(e.start_time),
                            "end_time": str(e.end_time)
                        }
                    }

        return {
            "status": "Available",
            "reason": "No assigned classes during this period.",
            "evidence": None
        }
