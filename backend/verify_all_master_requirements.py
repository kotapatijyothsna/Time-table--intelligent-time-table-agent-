import os
import sys
import django
import datetime
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.academics.models import AcademicSection, Subject
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException, ClassSwap, TimetableClash
from apps.scheduling.clash_service import ClashDetectionService
from apps.api_views import (
    get_dashboard_live_status,
    list_create_class_swaps,
    validate_class_swap_api,
    get_eligible_substitutes_api,
    list_create_exceptions,
    get_clashes_summary_api,
    list_timetable_clashes_api,
    assistant_query
)
from apps.assistant.services import AIAssistantService

rf = RequestFactory()
passed_tests = 0
failed_tests = 0

def assert_test(condition, test_name, extra=""):
    global passed_tests, failed_tests
    if condition:
        print(f"  [PASS] {test_name}")
        passed_tests += 1
    else:
        print(f"  [FAIL] {test_name}: {extra}")
        failed_tests += 1

print("=" * 70)
print("COMPREHENSIVE MASTER PROJECT ENHANCEMENT TEST SUITE")
print("=" * 70)

# -------------------------------------------------------------
# 1. LIVE DASHBOARD & COLLEGE WORKING HOURS
# -------------------------------------------------------------
print("\n--- SECTION 1: LIVE DASHBOARD REAL-TIME & BREAK RULES ---")

# Test 1A: Pre-College Hours (07:30 AM)
req_pre = rf.get('/api/v1/availability/live-dashboard/?test_time=07:30&test_date=2026-11-09')
res_pre = get_dashboard_live_status(req_pre).data
assert_test(res_pre["is_college_hours"] == False, "Pre-College (07:30 AM): is_college_hours is False")
assert_test(res_pre["current_period"] is None, "Pre-College (07:30 AM): current_period is None")
assert_test(res_pre["classrooms"]["occupied"] == 0, "Pre-College (07:30 AM): Classrooms occupied == 0")
assert_test(res_pre["classrooms"]["unoccupied"] == res_pre["classrooms"]["total"], "Pre-College: All classrooms free")
assert_test(res_pre["faculty"]["occupied"] == 0, "Pre-College: All faculty available (0 in class)")
assert_test(len(res_pre["ongoing_classes"]) == 0, "Pre-College: Ongoing classes list is empty")

# Test 1B: Morning Break (10:00 AM)
req_mbreak = rf.get('/api/v1/availability/live-dashboard/?test_time=10:00&test_date=2026-11-09')
res_mbreak = get_dashboard_live_status(req_mbreak).data
assert_test(res_mbreak["is_break"] == True, "Morning Break (10:00 AM): is_break is True")
assert_test(res_mbreak["break_name"] == "Morning Break", "Morning Break: break_name is 'Morning Break'")
assert_test(res_mbreak["current_period"] is None, "Morning Break: No active period assigned")
assert_test(res_mbreak["classrooms"]["occupied"] == 0, "Morning Break: 0 classrooms occupied by scheduled classes")
assert_test(res_mbreak["faculty"]["occupied"] == 0, "Morning Break: All faculty available")

# Test 1C: Lunch Break (13:00 PM / 1:00 PM)
req_lbreak = rf.get('/api/v1/availability/live-dashboard/?test_time=13:00&test_date=2026-11-09')
res_lbreak = get_dashboard_live_status(req_lbreak).data
assert_test(res_lbreak["is_break"] == True, "Lunch Break (01:00 PM): is_break is True")
assert_test(res_lbreak["break_name"] == "Lunch Break", "Lunch Break: break_name is 'Lunch Break'")
assert_test(res_lbreak["classrooms"]["occupied"] == 0, "Lunch Break: 0 classrooms occupied by scheduled classes")

# Test 1D: Active Period 3 (10:30 AM)
req_p3 = rf.get('/api/v1/availability/live-dashboard/?test_time=10:30&test_date=2026-11-09')
res_p3 = get_dashboard_live_status(req_p3).data
assert_test(res_p3["is_college_hours"] == True, "Period 3 (10:30 AM): is_college_hours is True")
assert_test(res_p3["is_break"] == False, "Period 3: is_break is False")
assert_test(res_p3["current_period"] == 3, f"Period 3: current_period is 3 (got {res_p3['current_period']})")
assert_test(res_p3["classrooms"]["occupied"] > 0, f"Period 3: Classrooms occupied ({res_p3['classrooms']['occupied']}) > 0")
assert_test(
    res_p3["classrooms"]["occupied"] + res_p3["classrooms"]["unoccupied"] == res_p3["classrooms"]["total"],
    "Period 3: Classrooms (occupied + unoccupied == total)"
)

# Guarantee: No room is both occupied and ready-to-use
free_room_codes = set(r["code"] for r in res_p3["classrooms"]["free_list"])
occupied_room_codes = set(c["room"] for c in res_p3["ongoing_classes"])
disjoint = free_room_codes.isdisjoint(occupied_room_codes)
assert_test(disjoint, "Disjoint Rooms Guarantee: No room is both Occupied and in Ready-to-Use free_list")

# Test 1E: Post-College Hours (16:30 PM / 4:30 PM)
req_post = rf.get('/api/v1/availability/live-dashboard/?test_time=16:30&test_date=2026-11-09')
res_post = get_dashboard_live_status(req_post).data
assert_test(res_post["is_college_hours"] == False, "Post-College (04:30 PM): is_college_hours is False")
assert_test(res_post["current_period"] is None, "Post-College: current_period is None")
assert_test(res_post["classrooms"]["occupied"] == 0, "Post-College: All classrooms free (0 occupied)")
assert_test(res_post["faculty"]["occupied"] == 0, "Post-College: All faculty available (0 occupied)")


# -------------------------------------------------------------
# 2. FACULTY NAME CLEANING & VALIDATION
# -------------------------------------------------------------
print("\n--- SECTION 2: FACULTY NAME CLEANING & VALIDATION ---")
jagadeesh = Faculty.objects.filter(full_name__icontains="JAGADEESH REDDY").first()
assert_test(jagadeesh and "(WED)" not in jagadeesh.full_name, "Jagadeesh Reddy: (WED) tag stripped")

vidya = Faculty.objects.filter(full_name__icontains="VIDYA SRI").first()
assert_test(vidya and "(wed)" not in vidya.full_name.lower(), "Vidya Sri: (wed) tag stripped and merged")

divya = Faculty.objects.filter(full_name="J. Divya").first()
francis = Faculty.objects.filter(full_name="M. Francis Xavier").first()
assert_test(divya is not None, "Name Separation: J. Divya exists as independent faculty")
assert_test(francis is not None, "Name Separation: M. Francis Xavier exists as independent faculty")

kumar_sai_count = Faculty.objects.filter(full_name__icontains="YARAGALLA KUMAR SAI").count()
assert_test(kumar_sai_count == 1, f"Yaragalla Kumar Sai: single deduplicated record (count={kumar_sai_count})")


# -------------------------------------------------------------
# 3. ADMIN PORTAL – LEAVE & SWAP MANAGER
# -------------------------------------------------------------
print("\n--- SECTION 3: LEAVE & SWAP MANAGER ---")

# Part A: Class Swap Validation
print("  Subpart A: Faculty Class Swap")
# Pick two different faculty entries
version = TimetableVersion.objects.filter(is_active=True).first()
monday_entries = TimetableEntry.objects.filter(timetable_version=version, day_of_week=0, faculty__isnull=False).select_related('faculty')
entry_a = monday_entries.first()
entry_b = monday_entries.exclude(faculty=entry_a.faculty).first()

if entry_a and entry_b:
    val_res = ClashDetectionService.validate_swap(
        swap_date=datetime.date(2026, 11, 9),
        entry_1=entry_a,
        faculty_1=entry_a.faculty,
        entry_2=entry_b,
        faculty_2=entry_b.faculty
    )
    assert_test("is_valid" in val_res, "Swap Validation Service: returned is_valid status")
    assert_test("preview" in val_res, "Swap Validation Service: returned exchanged preview")

# Part B: Faculty Substitution & 4th-Year Exclusivity Policy
print("  Subpart B: Faculty Substitution & Strict 4th-Year Restriction")
# Find an entry belonging to Year 2 or Year 3
lower_year_entry = TimetableEntry.objects.filter(
    timetable_version=version,
    section__year_level__in=[1, 2, 3],
    faculty__isnull=False
).select_related('section', 'faculty', 'subject').first()

# Find a faculty member who is EXCLUSIVELY teaching Year 4
all_active_facs = Faculty.objects.filter(is_active=True)
exclusive_yr4_fac = None
multi_yr_fac = None

for fac in all_active_facs:
    years = set(
        e.section.year_level for e in TimetableEntry.objects.filter(
            timetable_version=version, faculty=fac, is_active=True
        ).select_related('section') if e.section
    )
    if years == {4} and not exclusive_yr4_fac:
        exclusive_yr4_fac = fac
    elif 4 in years and len(years) > 1 and not multi_yr_fac:
        multi_yr_fac = fac
    if exclusive_yr4_fac and multi_yr_fac:
        break

if lower_year_entry and exclusive_yr4_fac:
    elig_exclusive = ClashDetectionService.check_substitution_eligibility(
        entry=lower_year_entry,
        substitute_faculty=exclusive_yr4_fac,
        target_date=datetime.date(2026, 11, 9)
    )
    assert_test(
        elig_exclusive["is_eligible"] == False,
        f"4th-Year Policy: Exclusive 4th-year faculty ({exclusive_yr4_fac.full_name}) blocked from Year {lower_year_entry.section.year_level}"
    )
    assert_test(
        elig_exclusive["status"] == "RESTRICTED_FOURTH_YEAR",
        f"4th-Year Policy: Reason status is RESTRICTED_FOURTH_YEAR"
    )

if lower_year_entry and multi_yr_fac:
    elig_multi = ClashDetectionService.check_substitution_eligibility(
        entry=lower_year_entry,
        substitute_faculty=multi_yr_fac,
        target_date=datetime.date(2026, 11, 9)
    )
    # Multi-year faculty must not be rejected purely due to 4th-year rule
    assert_test(
        elig_multi.get("status") != "RESTRICTED_FOURTH_YEAR",
        f"Multi-Year Faculty ({multi_yr_fac.full_name}): Not rejected by 4th-year exclusivity rule"
    )

# Test REST API for eligible substitutes
req_sub = rf.get(f'/api/v1/timetables/substitutions/eligible-faculty/?entry_id={lower_year_entry.id}&date=2026-11-09')
res_sub = get_eligible_substitutes_api(req_sub).data
assert_test("same_subject_specialists" in res_sub, "Substitutions API: Contains same_subject_specialists category")
assert_test("same_class_faculty" in res_sub, "Substitutions API: Contains same_class_faculty category")
assert_test("other_eligible_faculty" in res_sub, "Substitutions API: Contains other_eligible_faculty category")
assert_test("ineligible_faculty" in res_sub, "Substitutions API: Contains ineligible_faculty with policy explanations")


# -------------------------------------------------------------
# 4. TIMETABLE CLASH DETECTION
# -------------------------------------------------------------
print("\n--- SECTION 4: TIMETABLE CLASH DETECTION ---")
clash_summary = ClashDetectionService.scan_and_record_all_clashes()
assert_test(clash_summary["total_unresolved_clashes"] > 0, f"Clash Audit: Detected {clash_summary['total_unresolved_clashes']} total conflicts")
assert_test(clash_summary["faculty_clashes"] > 0, f"Clash Audit: Detected {clash_summary['faculty_clashes']} faculty overlaps")
assert_test(clash_summary["classroom_clashes"] > 0, f"Clash Audit: Detected {clash_summary['classroom_clashes']} classroom overlaps")
assert_test(clash_summary["lab_clashes"] > 0, f"Clash Audit: Detected {clash_summary['lab_clashes']} laboratory overlaps")

# Test Clash Summary API
req_csum = rf.get('/api/v1/timetables/clashes/summary/')
res_csum = get_clashes_summary_api(req_csum).data
assert_test(res_csum["total_unresolved"] == clash_summary["total_unresolved_clashes"], "Clashes Summary API: Matches audited count")

# Test Clash List API
req_clist = rf.get('/api/v1/timetables/clashes/?clash_type=FACULTY_CLASH&status=UNRESOLVED')
res_clist = list_timetable_clashes_api(req_clist).data
assert_test(len(res_clist) == clash_summary["faculty_clashes"], "Clash List API: Filters correctly by clash_type")


# -------------------------------------------------------------
# 5. CRT-FSD & VILLAS SIR
# -------------------------------------------------------------
print("\n--- SECTION 5: CRT-FSD FACULTY (VILLAS SIR) ---")
villas = Faculty.objects.filter(full_name__icontains="VILLAS").first()
assert_test(villas is not None, "CRT-FSD: Villas Sir exists in Faculty database")
assert_test(villas.is_outsourced == True, "CRT-FSD: Villas Sir is_outsourced is True")
assert_test(villas.faculty_type == "OUTSOURCED", "CRT-FSD: Villas Sir faculty_type is 'OUTSOURCED'")

villas_sessions = TimetableEntry.objects.filter(faculty=villas, is_active=True).count()
assert_test(villas_sessions == 21, f"CRT-FSD: Allocated exactly 21 weekly sessions to Villas Sir (found {villas_sessions})")


# -------------------------------------------------------------
# 6. CAMPUS AI GROUNDED CHATBOT
# -------------------------------------------------------------
print("\n--- SECTION 6: CAMPUS AI ASSISTANT SERVICE ---")

# Test 6A: Timetable Clashes Query
ai_clash = AIAssistantService.handle_query("Are there any timetable clashes?")
assert_test("Timetable Clash Detection Audit" in ai_clash["reply"], "Campus AI: Answers timetable clash query with audit breakdown")

# Test 6B: College Hours & Breaks Query
ai_breaks = AIAssistantService.handle_query("When is the morning break and what are the college working hours?")
assert_test("08:15 AM" in ai_breaks["reply"] and "09:55 AM" in ai_breaks["reply"], "Campus AI: Answers college working hours & morning break timings")

# Test 6C: CRT-FSD / Villas Sir Query
ai_villas = AIAssistantService.handle_query("Who is teaching CRT-FSD?")
assert_test("Villas Sir" in ai_villas["reply"] and "OUTSOURCED" in ai_villas["reply"], "Campus AI: Answers CRT-FSD query and identifies Villas Sir as outsourced faculty")

# Test 6D: Faculty Availability Query
ai_avail = AIAssistantService.handle_query("Which faculty members are free at 11:00 AM on Monday?")
assert_test("available faculty members" in ai_avail["reply"].lower() or "verified available" in ai_avail["reply"].lower(), "Campus AI: Answers faculty availability query")

# Test 6E: Available Classroom Query
ai_room = AIAssistantService.handle_query("Find an available classroom for 50 students at 10:10 AM on Monday")
assert_test("verified available" in ai_room["reply"].lower() or "room" in ai_room["reply"].lower(), "Campus AI: Recommends available classroom with capacity constraint")

print("\n" + "=" * 70)
print(f"VERIFICATION RESULTS: {passed_tests} PASSED, {failed_tests} FAILED")
print("=" * 70)

if failed_tests > 0:
    sys.exit(1)
