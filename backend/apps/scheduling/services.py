import datetime
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.availability.services import AvailabilityService
from apps.timetables.models import TimetableVersion, TimetableEntry

class SchedulingService:
    @staticmethod
    def time_to_minutes(t):
        return t.hour * 60 + t.minute

    @staticmethod
    def minutes_to_time(m):
        return datetime.time(m // 60, m % 60)

    @classmethod
    def find_common_free_slots(cls, faculty_ids, check_date, min_duration=50):
        """
        Computes continuous intersecting free slots among multiple faculty members
        during campus working hours [08:15, 16:05).
        """
        version = AvailabilityService.get_active_version()
        if not version:
            return []

        day_of_week = check_date.weekday()
        if day_of_week > 5: # Sunday
            return []

        # Working hours boundary in minutes from midnight
        # 08:15 = 495 mins, 16:05 = 965 mins
        day_start = 8 * 60 + 15
        day_end = 16 * 60 + 5

        # Initialize timeline as fully free
        free_mask = [True] * (day_end - day_start)

        # Retrieve entries for all target faculty members
        entries = TimetableEntry.objects.filter(
            timetable_version=version,
            faculty_id__in=faculty_ids,
            day_of_week=day_of_week,
            is_active=True
        )

        for entry in entries:
            s_min = max(cls.time_to_minutes(entry.start_time), day_start)
            e_min = min(cls.time_to_minutes(entry.end_time), day_end)
            for m in range(s_min, e_min):
                free_mask[m - day_start] = False

        # Find continuous free blocks >= min_duration
        slots = []
        in_block = False
        block_start = 0

        for i, is_free in enumerate(free_mask):
            if is_free and not in_block:
                in_block = True
                block_start = i
            elif not is_free and in_block:
                in_block = False
                dur = i - block_start
                if dur >= min_duration:
                    slots.append({
                        "start_time": str(cls.minutes_to_time(day_start + block_start)),
                        "end_time": str(cls.minutes_to_time(day_start + i)),
                        "duration_minutes": dur
                    })

        if in_block:
            dur = len(free_mask) - block_start
            if dur >= min_duration:
                slots.append({
                    "start_time": str(cls.minutes_to_time(day_start + block_start)),
                    "end_time": str(cls.minutes_to_time(day_start + len(free_mask))),
                    "duration_minutes": dur
                })

        return slots

    @classmethod
    def recommend_classrooms(cls, check_date, req_start, req_end, min_capacity=40, resource_type='CLASSROOM'):
        """
        Recommends classrooms or labs meeting capacity criteria with verified availability.
        """
        candidates = Resource.objects.filter(
            resource_type=resource_type,
            capacity__gte=min_capacity
        ).order_by('capacity')

        recommendations = []
        for res in candidates:
            eval_res = AvailabilityService.evaluate_resource_status(res, check_date, req_start, req_end)
            if eval_res["status"].upper() in ["AVAILABLE", "UNOCCUPIED"]:
                recommendations.append({
                    "resource_id": str(res.id),
                    "code": res.code,
                    "name": res.name,
                    "capacity": res.capacity,
                    "status": "AVAILABLE",
                    "reason": eval_res["reason"]
                })
        return recommendations
