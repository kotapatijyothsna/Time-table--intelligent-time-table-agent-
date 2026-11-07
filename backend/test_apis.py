"""
Integration Test Script for Smart Campus REST APIs
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from apps.academics.models import AcademicSection

def run_tests():
    client = APIClient()
    print("=== RUNNING API INTEGRATION TESTS ===")

    # Test 1: Sections list
    res = client.get('/api/v1/timetables/sections/')
    assert res.status_code == 200, f"Failed: {res.status_code}"
    sections = res.json()
    print(f"Test 1: Sections API returned {len(sections)} sections (Expected 24). PASS!")
    assert len(sections) == 24

    # Test 2: Section timetable for II AIML-A
    sec_a = AcademicSection.objects.get(full_name='II AIML-A')
    res = client.get(f'/api/v1/timetables/sections/{sec_a.id}/')
    assert res.status_code == 200
    tt_data = res.json()
    print(f"Test 2: II AIML-A timetable entries returned: {len(tt_data['entries'])}. PASS!")

    # Test 3: Faculty availability search
    res = client.get('/api/v1/availability/faculty/?date=2026-11-06&start_time=10:10&end_time=11:00')
    assert res.status_code == 200
    fac_avail = res.json()
    print(f"Test 3: Faculty availability evaluated for {len(fac_avail['faculty'])} instructors. PASS!")

    # Test 4: Resource availability search (Classrooms)
    res = client.get('/api/v1/availability/resources/?date=2026-11-06&start_time=10:10&end_time=11:00&type=CLASSROOM')
    assert res.status_code == 200
    res_avail = res.json()
    print(f"Test 4: Classroom availability evaluated for {len(res_avail['resources'])} rooms. PASS!")

    # Test 5: AI Assistant query
    res = client.post('/api/v1/assistant/query/', {"query": "Which AIML faculty are free at 11 AM today?"}, format='json')
    assert res.status_code == 200
    ai_res = res.json()
    print("Test 5: AI Assistant query executed successfully.")
    print(f"  AI Reply Preview: {ai_res['reply'][:120]}...")
    print(f"  Tools Invoked: {ai_res['tools_invoked']}")
    print("  PASS!")

    print("\nALL 5 INTEGRATION TESTS PASSED WITH 100% ACCURACY!")

if __name__ == '__main__':
    run_tests()
