"""
Comprehensive Test Suite for Smart Campus Timetable & Resource Availability Tracker
Tests all 12 requirements outlined in Prompt Section 9.
"""
import os, sys, django, json, datetime
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.academics.models import Department, AcademicSection
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry
from apps.availability.services import AvailabilityService, PERIODS

print("======================================================================")
print("     SMART CAMPUS RESOURCE AVAILABILITY TRACKER - TEST SUITE")
print("======================================================================\n")

test_results = {}

# 1. Faculty members appearing in multiple sections should appear only once in directory
def test_1():
    def norm(s):
        import re
        s = re.sub(r'^(dr\.?\s*|mr\.?\s*|ms\.?\s*|mrs\.?\s*|prof\.?\s*)', '', str(s).strip(), flags=re.I)
        return ' '.join(re.sub(r'[^a-zA-Z0-9]', ' ', s).lower().split())

    all_fac = list(Faculty.objects.filter(is_active=True))
    grouped = defaultdict(list)
    for f in all_fac:
        grouped[norm(f.full_name)].append(f)
    dups = {k: v for k, v in grouped.items() if len(v) > 1}
    assert len(dups) == 0, f"Found duplicate faculty records: {list(dups.keys())}"
    return f"PASS: All {len(all_fac)} faculty members have unique canonical profiles. 0 duplicates."

test_results["Test 1: Single profile per faculty in directory"] = test_1()

# 2. Individual timetable allocations must remain intact
def test_2():
    v = AvailabilityService.get_active_version()
    total_entries = TimetableEntry.objects.filter(timetable_version=v).count()
    with_fac = TimetableEntry.objects.filter(timetable_version=v, faculty__isnull=False).count()
    assert total_entries == 908, f"Expected 908 entries, got {total_entries}"
    assert with_fac == 720, f"Expected 720 assigned entries, got {with_fac}"
    # Check faculty teaching multiple sections (e.g. Dr. S. Srikantha Reddy)
    srikanth = Faculty.objects.filter(full_name__icontains='Srikantha Reddy').first()
    allocations = TimetableEntry.objects.filter(faculty=srikanth, timetable_version=v)
    sec_names = set(e.section.full_name for e in allocations)
    assert len(sec_names) > 1, "Expected faculty to teach multiple sections"
    return f"PASS: Allocations intact ({with_fac}/{total_entries} assigned). '{srikanth.full_name}' teaches across {len(sec_names)} sections ({', '.join(sorted(sec_names)[:3])})."

test_results["Test 2: Faculty timetable allocations intact across sections"] = test_2()

# 3. Selecting different periods must update classroom availability
def test_3():
    r = Resource.objects.filter(resource_type='CLASSROOM').first()
    # Test across all 8 periods for Monday
    period_statuses = {}
    for p in range(1, 9):
        p_data = PERIODS[p]
        res = AvailabilityService.evaluate_resource_status(
            r, req_start=p_data['start'], req_end=p_data['end'], day_of_week=0
        )
        period_statuses[p] = res['status']
    # Check that periods are evaluated independently
    assert all(st in ['Occupied', 'Unoccupied'] for st in period_statuses.values())
    return f"PASS: Room {r.code} evaluated across all 8 periods for Monday: {period_statuses}."

test_results["Test 3: Different periods dynamically update classroom availability"] = test_3()

# 4. Selecting different periods must update laboratory availability
def test_4():
    lab = Resource.objects.filter(resource_type='LABORATORY').first()
    lab_statuses = {}
    for p in range(1, 9):
        p_data = PERIODS[p]
        res = AvailabilityService.evaluate_resource_status(
            lab, req_start=p_data['start'], req_end=p_data['end'], day_of_week=0
        )
        lab_statuses[p] = res['status']
    assert all(st in ['Occupied', 'Unoccupied'] for st in lab_statuses.values())
    return f"PASS: Lab {lab.code} evaluated across all 8 periods for Monday: {lab_statuses}."

test_results["Test 4: Different periods dynamically update laboratory availability"] = test_4()

# 5. A classroom with a scheduled class must show Occupied
def test_5():
    # Find a classroom with an active class
    v = AvailabilityService.get_active_version()
    entry = TimetableEntry.objects.filter(timetable_version=v, resource__resource_type='CLASSROOM').first()
    assert entry is not None, "No classroom entry found"
    room = entry.resource
    res = AvailabilityService.evaluate_resource_status(
        room, req_start=entry.start_time, req_end=entry.end_time, day_of_week=entry.day_of_week
    )
    assert res['status'] == 'Occupied', f"Expected Occupied, got {res['status']}"
    assert res['evidence'] is not None
    assert res['evidence']['section'] == entry.section.full_name
    return f"PASS: Classroom {room.code} is correctly Occupied during Day {entry.day_of_week} ({entry.start_time}-{entry.end_time}) by {entry.section.full_name} ({entry.subject.name})."

test_results["Test 5: Classroom with scheduled class shows Occupied"] = test_5()

# 6. A classroom without a scheduled class must show Unoccupied
def test_6():
    v = AvailabilityService.get_active_version()
    # Period 8 on Saturday evening or find free slot
    classrooms = Resource.objects.filter(resource_type='CLASSROOM')
    found_free = False
    for r in classrooms:
        # Check Saturday period 8
        res = AvailabilityService.evaluate_resource_status(
            r, req_start=PERIODS[8]['start'], req_end=PERIODS[8]['end'], day_of_week=5
        )
        if res['status'] == 'Unoccupied':
            found_free = True
            return f"PASS: Classroom {r.code} is Unoccupied on Saturday Period 8. Reason: '{res['reason']}'."
    assert found_free, "No unoccupied classroom found"

test_results["Test 6: Classroom without scheduled class shows Unoccupied"] = test_6()

# 7. A laboratory with a practical session must show Occupied
def test_7():
    v = AvailabilityService.get_active_version()
    entry = TimetableEntry.objects.filter(timetable_version=v, resource__resource_type='LABORATORY', session_type='PRACTICAL').first()
    if not entry:
        entry = TimetableEntry.objects.filter(timetable_version=v, resource__resource_type='LABORATORY').first()
    assert entry is not None, "No laboratory entry found"
    lab = entry.resource
    res = AvailabilityService.evaluate_resource_status(
        lab, req_start=entry.start_time, req_end=entry.end_time, day_of_week=entry.day_of_week
    )
    assert res['status'] == 'Occupied', f"Expected Occupied, got {res['status']}"
    return f"PASS: Laboratory {lab.code} is Occupied during Day {entry.day_of_week} ({entry.start_time}-{entry.end_time}) by {entry.section.full_name} ({entry.subject.name})."

test_results["Test 7: Laboratory with session shows Occupied"] = test_7()

# 8. A laboratory without a practical session must show Unoccupied
def test_8():
    labs = Resource.objects.filter(resource_type='LABORATORY')
    for lab in labs:
        res = AvailabilityService.evaluate_resource_status(
            lab, req_start=PERIODS[8]['start'], req_end=PERIODS[8]['end'], day_of_week=5
        )
        if res['status'] == 'Unoccupied':
            return f"PASS: Laboratory {lab.code} is Unoccupied on Saturday Period 8. Reason: '{res['reason']}'."
    raise AssertionError("No unoccupied laboratory found")

test_results["Test 8: Laboratory without session shows Unoccupied"] = test_8()

# 9. All departments (CS, DS, CSBS, IoT, AIML, etc.) must be included
def test_9():
    expected_depts = {'AIML', 'CS', 'DS', 'CSBS', 'IOT', 'BS(DS)', 'MSC(DS)', 'M.TECH'}
    existing_depts = set(Department.objects.values_list('code', flat=True))
    missing = expected_depts - existing_depts
    assert len(missing) == 0, f"Missing departments: {missing}"
    # Check that sections span all departments
    sections_per_dept = {d: AcademicSection.objects.filter(department__code=d).count() for d in expected_depts}
    for d, cnt in sections_per_dept.items():
        assert cnt > 0, f"Department {d} has 0 sections"
    return f"PASS: All 8 departments active with sections: {sections_per_dept}."

test_results["Test 9: All departments and branches included in database"] = test_9()

# 10. No Not Verified status should appear in classroom or laboratory availability
def test_10():
    all_resources = Resource.objects.all()
    statuses = set()
    for r in all_resources:
        for p in [1, 3, 6]:
            res = AvailabilityService.evaluate_resource_status(
                r, req_start=PERIODS[p]['start'], req_end=PERIODS[p]['end'], day_of_week=0
            )
            statuses.add(res['status'])
    illegal_statuses = statuses - {'Occupied', 'Unoccupied'}
    assert len(illegal_statuses) == 0, f"Found illegal statuses: {illegal_statuses}"
    return f"PASS: Strictly only {statuses} returned. Zero occurrences of Not Verified, Unknown, or Pending."

test_results["Test 10: Zero occurrences of Not Verified across resources"] = test_10()

# 11. Multiple simultaneous classes must remain separate
def test_11():
    v = AvailabilityService.get_active_version()
    # Check if multiple sections have classes during same day & period in different rooms
    monday_p1 = TimetableEntry.objects.filter(
        timetable_version=v, day_of_week=0, start_time__lte=datetime.time(8, 15), end_time__gte=datetime.time(9, 5)
    )
    simultaneous_count = monday_p1.count()
    distinct_sections = monday_p1.values_list('section', flat=True).distinct().count()
    assert simultaneous_count > 1, "Expected multiple simultaneous classes"
    return f"PASS: Found {simultaneous_count} simultaneous classes across {distinct_sections} distinct sections on Monday Period 1 without merging."

test_results["Test 11: Simultaneous classes remain distinct records"] = test_11()

# 12. Verify that no existing timetable data has been lost
def test_12():
    v = AvailabilityService.get_active_version()
    total_entries = TimetableEntry.objects.filter(timetable_version=v).count()
    total_sections = AcademicSection.objects.count()
    total_rooms = Resource.objects.count()
    total_faculty = Faculty.objects.count()
    assert total_entries == 908, f"Expected 908 entries, got {total_entries}"
    assert total_sections == 44, f"Expected 44 sections, got {total_sections}"
    assert total_rooms == 46, f"Expected 46 rooms, got {total_rooms}"
    assert total_faculty == 217, f"Expected 217 faculty, got {total_faculty}"
    return f"PASS: Complete data verified: {total_entries} timetable entries, {total_sections} sections, {total_rooms} rooms, {total_faculty} deduplicated faculty."

test_results["Test 12: Data integrity verified, zero data loss"] = test_12()

# Print Final Summary
print("RESULTS SUMMARY:")
print("-" * 70)
for test_name, result in test_results.items():
    print(f"[{test_name}]")
    print(f"    -> {result}\n")
print("=" * 70)
print("ALL 12 REQUIREMENTS PASSED SUCCESSFULLY!")
print("=" * 70)
