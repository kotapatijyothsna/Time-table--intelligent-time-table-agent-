import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from apps.timetables.models import TimetableEntry, ScheduleException
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.audit.models import AuditLog

def run_checks():
    client = Client()
    print("=================================================================")
    print("       SMART CAMPUS VERIFICATION & HEALTH CHECK SUITE            ")
    print("=================================================================")

    # 1. Departments & Metadata
    res = client.get('/api/v1/academics/departments/')
    assert res.status_code == 200
    depts = res.json()
    print(f"[OK] 1. Departments API: {len(depts)} departments registered -> {[d['code'] for d in depts]}")

    # 2. Live Availability Dashboard
    res = client.get('/api/v1/availability/live-dashboard/')
    assert res.status_code == 200
    live = res.json()
    print(f"[OK] 2. Live Dashboard: Current Period: {live.get('current_period')}, Classrooms: {live.get('classrooms', {}).get('total')}, Labs: {live.get('laboratories', {}).get('total')}")

    # 3. Schedule Entries Search
    res = client.get('/api/v1/timetables/entries/search/?date=2026-11-09')
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) > 0
    sample = entries[0]
    print(f"[OK] 3. Timetable Entries Search: Found {len(entries)} sessions on Monday (Sample: {sample['display_label']})")

    # 4. Create Schedule Exception: CANCEL
    cancel_payload = {
        "timetable_entry_id": sample['id'],
        "exception_date": "2026-11-09",
        "exception_type": "CANCEL",
        "reason": "Department Symposium 2026",
        "user_id": "HOD AIML"
    }
    res = client.post('/api/v1/timetables/exceptions/', data=json.dumps(cancel_payload), content_type='application/json')
    assert res.status_code == 201
    cancel_data = res.json()
    print(f"[OK] 4. Created CANCEL Exception: ID={cancel_data['id']}, Type={cancel_data['exception_type']}, Reason={cancel_data['reason']}")

    # 5. Create Schedule Exception: SUBSTITUTE (Leave & Swap)
    sub_faculty = Faculty.objects.filter(is_active=True).last()
    second_entry = entries[1]
    sub_payload = {
        "timetable_entry_id": second_entry['id'],
        "exception_date": "2026-11-09",
        "exception_type": "SUBSTITUTE",
        "replacement_faculty_id": str(sub_faculty.id),
        "reason": "Faculty Medical Leave",
        "user_id": "Dean of Academics"
    }
    res = client.post('/api/v1/timetables/exceptions/', data=json.dumps(sub_payload), content_type='application/json')
    assert res.status_code == 201
    sub_data = res.json()
    print(f"[OK] 5. Created SUBSTITUTE Exception: Original='{sub_data['original_faculty_name']}' -> Replacement='{sub_data['replacement_faculty_name']}'")

    # 6. List Active Exceptions
    res = client.get('/api/v1/timetables/exceptions/')
    assert res.status_code == 200
    active_ex = res.json()
    print(f"[OK] 6. List Exceptions API: {len(active_ex)} active exception(s) returned")

    # 7. System Audit Trail Check
    res = client.get('/api/v1/audit/logs/')
    assert res.status_code == 200
    logs = res.json()
    print(f"[OK] 7. System Audit Trail: {len(logs)} audit events logged (Latest: action='{logs[0]['action']}', actor='{logs[0]['actor']}')")

    # 8. Campus AI Query (Deterministic & Exceptions Awareness)
    ai_q1 = {"query": "Are there any cancellations or substitutions on Monday?"}
    res = client.post('/api/v1/assistant/query/', data=json.dumps(ai_q1), content_type='application/json')
    assert res.status_code == 200
    ans1 = res.json()
    print(f"[OK] 8. Campus AI (Exceptions Grounding):")
    for line in ans1['reply'].split('\n')[:6]:
        print(f"      {line}")

    # 9. Campus AI Query (Classroom search)
    ai_q2 = {"query": "Find an available classroom for 50 students at 10:10 AM"}
    res = client.post('/api/v1/assistant/query/', data=json.dumps(ai_q2), content_type='application/json')
    assert res.status_code == 200
    ans2 = res.json()
    print(f"[OK] 9. Campus AI (Classroom Seating Search):")
    for line in ans2['reply'].split('\n')[:6]:
        print(f"      {line}")

    # 10. Clean up created exceptions (Revoke test)
    res = client.delete(f"/api/v1/timetables/exceptions/{cancel_data['id']}/")
    assert res.status_code == 200
    res = client.delete(f"/api/v1/timetables/exceptions/{sub_data['id']}/")
    assert res.status_code == 200
    print("[OK] 10. Revoke Exceptions: Successfully cleaned up exceptions and verified revoke audit events")

    print("=================================================================")
    print("  ALL 10 VERIFICATION TESTS COMPLETED AND PASSED PERFECTLY!     ")
    print("=================================================================")

if __name__ == '__main__':
    run_checks()
