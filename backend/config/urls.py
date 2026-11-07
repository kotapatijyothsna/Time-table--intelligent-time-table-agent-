"""
URL configuration for Smart Campus AIML Department.
Versioned REST APIs under /api/v1/ and React SPA at /
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render

from apps.api_views import (
    get_current_availability,
    search_faculty_availability,
    search_resource_availability,
    find_common_free_slots_api,
    get_section_timetable,
    get_faculty_timetable,
    get_resource_timetable,
    list_all_resources,
    list_all_faculty,
    get_dashboard_live_status,
    list_sections,
    list_departments,
    list_periods_api,
    assistant_query,
    list_create_exceptions,
    delete_exception,
    search_timetable_entries,
    list_audit_logs,
    list_create_class_swaps,
    validate_class_swap_api,
    update_swap_status_api,
    delete_class_swap_api,
    get_eligible_substitutes_api,
    get_clashes_summary_api,
    list_timetable_clashes_api,
    run_clash_scan_api,
    resolve_timetable_clash_api
)

from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve
from pathlib import Path

dist_dir = settings.BASE_DIR.parent / 'frontend' / 'dist'
assets_dir = dist_dir / 'assets'

def index_view(request):
    dist_index = dist_dir / 'index.html'
    if dist_index.exists():
        try:
            with open(dist_index, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read(), content_type='text/html')
        except Exception:
            pass
    return render(request, 'index.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index_view, name='index-app'),
    path('assets/<path:path>', serve, {'document_root': assets_dir}),

    # Metadata & Reference APIs
    path('api/v1/academics/departments/', list_departments, name='list-departments'),
    path('api/v1/timetables/periods/', list_periods_api, name='list-periods'),
    path('api/v1/resources/all/', list_all_resources, name='list-all-resources'),
    path('api/v1/faculty/all/', list_all_faculty, name='list-all-faculty'),

    # Availability APIs
    path('api/v1/availability/current/', get_current_availability, name='avail-current'),
    path('api/v1/availability/live-dashboard/', get_dashboard_live_status, name='avail-live-dashboard'),
    path('api/v1/availability/faculty/', search_faculty_availability, name='avail-faculty'),
    path('api/v1/availability/resources/', search_resource_availability, name='avail-resources'),

    # Scheduling APIs
    path('api/v1/scheduling/common-slots/', find_common_free_slots_api, name='common-slots'),

    # Timetable APIs (Section-wise, Faculty-wise, Room-wise)
    path('api/v1/timetables/sections/', list_sections, name='list-sections'),
    path('api/v1/timetables/sections/<uuid:section_id>/', get_section_timetable, name='section-timetable'),
    path('api/v1/timetables/faculty/<uuid:faculty_id>/', get_faculty_timetable, name='faculty-timetable'),
    path('api/v1/timetables/resources/<uuid:resource_id>/', get_resource_timetable, name='resource-timetable'),
    path('api/v1/timetables/entries/search/', search_timetable_entries, name='search-timetable-entries'),

    # Schedule Exceptions & Substitutions Management
    path('api/v1/timetables/exceptions/', list_create_exceptions, name='list-create-exceptions'),
    path('api/v1/timetables/exceptions/<uuid:exception_id>/', delete_exception, name='delete-exception'),
    path('api/v1/timetables/substitutions/eligible-faculty/', get_eligible_substitutes_api, name='eligible-substitutes'),

    # Faculty Class Swaps Management
    path('api/v1/timetables/swaps/', list_create_class_swaps, name='list-create-class-swaps'),
    path('api/v1/timetables/swaps/validate/', validate_class_swap_api, name='validate-class-swap'),
    path('api/v1/timetables/swaps/<uuid:swap_id>/status/', update_swap_status_api, name='update-swap-status'),
    path('api/v1/timetables/swaps/<uuid:swap_id>/', delete_class_swap_api, name='delete-class-swap'),

    # Timetable Clash Detection APIs
    path('api/v1/timetables/clashes/summary/', get_clashes_summary_api, name='clashes-summary'),
    path('api/v1/timetables/clashes/', list_timetable_clashes_api, name='list-timetable-clashes'),
    path('api/v1/timetables/clashes/scan/', run_clash_scan_api, name='run-clash-scan'),
    path('api/v1/timetables/clashes/<uuid:clash_id>/resolve/', resolve_timetable_clash_api, name='resolve-clash'),

    # Audit & Governance Logs API
    path('api/v1/audit/logs/', list_audit_logs, name='list-audit-logs'),

    # AI Assistant API
    path('api/v1/assistant/query/', assistant_query, name='assistant-query'),
]
