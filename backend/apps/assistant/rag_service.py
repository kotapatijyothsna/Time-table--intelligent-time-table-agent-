"""
Smart Campus - Retrieval-Augmented Generation (RAG) Service for Academic Timetable
Powered by Groq LLM (e.g. Qwen / LLaMA) & Structured Academic Database Retrieval.
"""

import os
import re
import json
import datetime
from django.utils import timezone
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.academics.models import AcademicSection, Subject
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException, ClassSwap, TimetableClash
from apps.availability.services import AvailabilityService, PERIODS, DAY_NAMES
from apps.scheduling.services import SchedulingService
from apps.assistant.services import (
    parse_time_slot_and_period,
    find_faculty_in_prompt,
    find_section_in_prompt,
    find_subject_in_prompt
)

class TimetableRAGService:
    @classmethod
    def retrieve_context(cls, query_text):
        """
        Retrieval Step: Fetches relevant timetable sessions, faculty allocations,
        and room vacancies matching the query from the verified database.
        """
        prompt_lower = query_text.lower()
        today = datetime.date.today()
        target_date = today

        # 1. Parse Day of week
        day_names_list = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        matched_day_idx = None
        for idx, d_name in enumerate(day_names_list):
            if d_name in prompt_lower:
                days_ahead = (idx - today.weekday()) % 7
                target_date = today + datetime.timedelta(days=days_ahead)
                matched_day_idx = idx
                break

        # 2. Parse Period & Time
        start_t, end_t, period_num, slot_label = parse_time_slot_and_period(prompt_lower)

        version = AvailabilityService.get_active_version()
        retrieved_documents = []

        # 3. Check Faculty Match (Fuzzy & Substring)
        fac_target, fac_score = find_faculty_in_prompt(prompt_lower)
        if fac_target and fac_score >= 20:
            eval_res = AvailabilityService.evaluate_faculty_status(fac_target, target_date, start_t, end_t)

            # Fetch today's schedule
            day_idx = target_date.weekday()
            today_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                faculty=fac_target,
                day_of_week=day_idx,
                is_active=True
            ).select_related('section', 'subject', 'resource').order_by('start_time')

            today_classes = []
            for te in today_entries:
                r_code = te.resource.code if te.resource else "Unassigned"
                today_classes.append(
                    f"{te.start_time.strftime('%H:%M')}-{te.end_time.strftime('%H:%M')}: {te.subject.name} for {te.section.full_name} in Room {r_code}"
                )

            # Fetch weekly sample schedule
            weekly_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                faculty=fac_target,
                is_active=True
            ).select_related('section', 'subject', 'resource').order_by('day_of_week', 'start_time')[:10]

            weekly_summary = []
            for we in weekly_entries:
                r_code = we.resource.code if we.resource else "Unassigned"
                d_name = day_names_list[we.day_of_week].capitalize() if we.day_of_week < len(day_names_list) else 'Day'
                weekly_summary.append(
                    f"{d_name} {we.start_time.strftime('%H:%M')}-{we.end_time.strftime('%H:%M')}: {we.subject.name} ({we.section.full_name}) in Room {r_code}"
                )

            retrieved_documents.append({
                "type": "FACULTY_PROFILE_AND_SCHEDULE",
                "entity": fac_target.full_name,
                "faculty_code": fac_target.faculty_code,
                "department": fac_target.department.code if fac_target.department else "AIML",
                "evaluated_slot": f"{target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')}) {slot_label}",
                "status": eval_res["status"],
                "reason": eval_res["reason"],
                "evidence": eval_res.get("evidence"),
                "classes_on_target_day": today_classes,
                "weekly_schedule_sample": weekly_summary
            })

        # 4. Check Room / Lab Match
        room_match = re.search(r'\b(?:room|lab)\s*([a-zA-Z0-9\-]+)\b', prompt_lower)
        if room_match:
            rcode = room_match.group(1).upper()
            res_obj = Resource.objects.filter(code__iexact=rcode).first()
            if res_obj:
                eval_res = AvailabilityService.evaluate_resource_status(res_obj, target_date, start_t, end_t)
                room_entries = TimetableEntry.objects.filter(
                    timetable_version=version,
                    resource=res_obj,
                    is_active=True
                ).select_related('section', 'subject', 'faculty').order_by('day_of_week', 'start_time')[:8]

                room_sched = []
                for re_entry in room_entries:
                    d_name = day_names_list[re_entry.day_of_week].capitalize() if re_entry.day_of_week < len(day_names_list) else 'Day'
                    fac_n = re_entry.faculty.full_name if re_entry.faculty else "Unassigned"
                    room_sched.append(
                        f"{d_name} {re_entry.start_time.strftime('%H:%M')}-{re_entry.end_time.strftime('%H:%M')}: {re_entry.subject.name} ({re_entry.section.full_name}) | Faculty: {fac_n}"
                    )

                retrieved_documents.append({
                    "type": "RESOURCE_OCCUPANCY",
                    "room_code": res_obj.code,
                    "name": res_obj.name,
                    "capacity": res_obj.capacity,
                    "is_shared": res_obj.is_shared,
                    "evaluated_slot": f"{target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')}) {slot_label}",
                    "status": eval_res["status"],
                    "reason": eval_res["reason"],
                    "evidence": eval_res.get("evidence"),
                    "weekly_occupancy": room_sched
                })

        # 5. Check Section Match (e.g. 'II AIML-A', 'IV CS', 'III DS')
        sec_obj = find_section_in_prompt(prompt_lower)
        if sec_obj:
            day_filter = matched_day_idx if matched_day_idx is not None else target_date.weekday()
            s_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                section=sec_obj,
                day_of_week=day_filter,
                is_active=True
            ).select_related('subject', 'faculty', 'resource').order_by('start_time')

            day_classes = [
                f"{e.start_time.strftime('%H:%M')}-{e.end_time.strftime('%H:%M')}: {e.subject.name} | Faculty: {e.faculty.full_name if e.faculty else 'Department Faculty'} | Room: {e.resource.code if e.resource else 'Unassigned'}"
                for e in s_entries
            ]

            retrieved_documents.append({
                "type": "SECTION_SCHEDULE",
                "section": sec_obj.full_name,
                "department": sec_obj.department.code if sec_obj.department else "AIML",
                "day": day_names_list[day_filter].capitalize(),
                "classes": day_classes
            })

        # 6. Check Subject Match (e.g. 'Deep Learning', 'Text Mining')
        sub_obj = find_subject_in_prompt(prompt_lower)
        if sub_obj:
            sub_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                subject=sub_obj,
                faculty__isnull=False,
                is_active=True
            ).select_related('faculty', 'section', 'resource').order_by('section__full_name')

            teacher_map = {}
            for se in sub_entries:
                fn = se.faculty.full_name
                sec_n = se.section.full_name
                if fn not in teacher_map:
                    teacher_map[fn] = set()
                teacher_map[fn].add(sec_n)

            retrieved_documents.append({
                "type": "SUBJECT_FACULTY_ALLOCATION",
                "subject_name": sub_obj.name,
                "subject_code": sub_obj.code,
                "allocated_teachers": [
                    {"faculty": fn, "sections": sorted(list(secs))}
                    for fn, secs in teacher_map.items()
                ]
            })

        # 7. Check Room / Lab Vacancy Recommendations
        is_lab = bool(re.search(r'\b(?:labs?|laborator(?:y|ies))\b', prompt_lower))
        is_room = bool(re.search(r'\b(?:classrooms?|rooms?)\b', prompt_lower)) or "free room" in prompt_lower or "available room" in prompt_lower
        if is_lab or is_room:
            res_type = 'LABORATORY' if is_lab else 'CLASSROOM'
            cap_match = re.search(r'\b(?:for\s+)?(\d{2,3})\s*(?:students?|seats?|capacity)?\b', prompt_lower)
            min_cap = int(cap_match.group(1)) if cap_match and int(cap_match.group(1)) <= 150 else 30
            recs = SchedulingService.recommend_classrooms(target_date, start_t, end_t, min_capacity=min_cap, resource_type=res_type)
            retrieved_documents.append({
                "type": "AVAILABLE_RESOURCES_LIST",
                "resource_type": res_type,
                "slot": f"{target_date.strftime('%Y-%m-%d')} {slot_label}",
                "min_capacity": min_cap,
                "available_rooms": recs[:8]
            })

        # 8. Check Free Faculty List
        if any(k in prompt_lower for k in ["who is free", "free faculty", "available faculty", "free teacher", "faculty free", "teachers free"]):
            free_facs = []
            seen = set()
            dept_filter = None
            for d in ["aiml", "cs", "ds", "csbs", "iot"]:
                if d in prompt_lower.split() or f" {d} " in f" {prompt_lower} ":
                    dept_filter = d.upper()
                    break

            fac_qs = Faculty.objects.filter(is_active=True).select_related('department').order_by('full_name')
            if dept_filter:
                fac_qs = fac_qs.filter(department__code__iexact=dept_filter)

            for f in fac_qs:
                norm = " ".join(f.full_name.lower().split())
                if norm in seen:
                    continue
                eval_res = AvailabilityService.evaluate_faculty_status(f, target_date, start_t, end_t)
                if eval_res["status"].upper() in ["AVAILABLE", "UNOCCUPIED"]:
                    seen.add(norm)
                    dept_str = f" [{f.department.code}]" if f.department else ""
                    free_facs.append(f"{f.full_name} ({f.faculty_code or 'ID Unassigned'}){dept_str}")

            retrieved_documents.append({
                "type": "AVAILABLE_FACULTY_LIST",
                "slot": f"{target_date.strftime('%Y-%m-%d')} {slot_label}",
                "department_filter": dept_filter or "ALL",
                "total_available": len(free_facs),
                "free_faculty_sample": free_facs[:15]
            })

        # 9. Check Schedule Exceptions & Substitutions
        if any(w in prompt_lower for w in ["exception", "cancellation", "cancel", "substitut", "leave", "reallocat", "can 4th year"]):
            exceptions = ScheduleException.objects.filter(
                exception_date=target_date
            ).select_related('timetable_entry', 'timetable_entry__section', 'timetable_entry__subject', 'replacement_faculty', 'replacement_resource')
            ex_data = []
            for ex in exceptions:
                ex_data.append({
                    "type": ex.exception_type,
                    "date": str(ex.exception_date),
                    "section": ex.timetable_entry.section.full_name,
                    "subject": ex.timetable_entry.subject.name,
                    "replacement_faculty": ex.replacement_faculty.full_name if ex.replacement_faculty else None,
                    "replacement_room": ex.replacement_resource.code if ex.replacement_resource else None,
                    "reason": ex.reason
                })
            retrieved_documents.append({
                "type": "SCHEDULE_EXCEPTIONS",
                "target_date": str(target_date),
                "total_exceptions": len(ex_data),
                "exceptions": ex_data,
                "fourth_year_policy": "Faculty members exclusively assigned to 4th-year cohorts (e.g. Abdul Rehman) are strictly restricted from substituting for 2nd-year or 3rd-year classes."
            })

        # 10. Check Timetable Clashes & Conflicts
        if any(w in prompt_lower for w in ['clash', 'clashes', 'conflict', 'conflicts', 'collision', 'double booking', 'overlap']):
            unresolved = TimetableClash.objects.filter(status='UNRESOLVED')
            sample_clashes = []
            for c in unresolved[:8]:
                sample_clashes.append({
                    'clash_type': c.clash_type,
                    'day_of_week': c.day_of_week,
                    'overlap': f"{c.overlap_start.strftime('%H:%M')}-{c.overlap_end.strftime('%H:%M')} ({c.overlap_duration_minutes} min)",
                    'explanation': c.explanation
                })
            retrieved_documents.append({
                'type': 'TIMETABLE_CLASHES_AUDIT',
                'total_unresolved_clashes': unresolved.count(),
                'faculty_clashes': unresolved.filter(clash_type='FACULTY_CLASH').count(),
                'classroom_clashes': unresolved.filter(clash_type='CLASSROOM_CLASH').count(),
                'lab_clashes': unresolved.filter(clash_type='LAB_CLASH').count(),
                'section_clashes': unresolved.filter(clash_type='SECTION_CLASH').count(),
                'sample_clashes': sample_clashes
            })

        # 11. Check Class Swaps
        if any(w in prompt_lower for w in ['swap', 'swaps', 'swapped', 'exchange class', 'exchanged']):
            swaps = ClassSwap.objects.filter(swap_date=target_date).select_related(
                'faculty_1', 'faculty_2', 'entry_1', 'entry_2',
                'entry_1__section', 'entry_1__subject', 'entry_2__section', 'entry_2__subject'
            )
            swap_list = []
            for s in swaps:
                is_same_sec = (s.entry_1.section_id == s.entry_2.section_id)
                swap_list.append({
                    'faculty_1': s.faculty_1.full_name,
                    'subject_1': s.entry_1.subject.name,
                    'slot_1': f"{s.entry_1.start_time.strftime('%H:%M')}-{s.entry_1.end_time.strftime('%H:%M')}",
                    'class_1': s.entry_1.section.full_name,
                    'faculty_2': s.faculty_2.full_name,
                    'subject_2': s.entry_2.subject.name,
                    'slot_2': f"{s.entry_2.start_time.strftime('%H:%M')}-{s.entry_2.end_time.strftime('%H:%M')}",
                    'class_2': s.entry_2.section.full_name,
                    'is_same_class': is_same_sec,
                    'status': s.status,
                    'reason': s.reason
                })
            retrieved_documents.append({
                'type': 'CLASS_SWAPS',
                'target_date': str(target_date),
                'total_swaps': len(swap_list),
                'swaps': swap_list
            })

        # 12. Check College Timings & Breaks
        if any(w in prompt_lower for w in ['break', 'breaks', 'college hours', 'working hours', 'college start', 'college end', 'class timing', 'period timing', 'lunch timing', 'morning break']):
            retrieved_documents.append({
                'type': 'COLLEGE_HOURS_AND_BREAKS',
                'working_hours': '08:15 AM - 04:05 PM (Monday to Saturday)',
                'morning_break': '09:55 AM - 10:10 AM (15 minutes)',
                'lunch_break': '12:40 PM - 01:40 PM (60 minutes)',
                'periods': [
                    'Period 1: 08:15 - 09:05',
                    'Period 2: 09:05 - 09:55',
                    'Morning Break: 09:55 - 10:10 (Rooms and Faculty free)',
                    'Period 3: 10:10 - 11:00',
                    'Period 4: 11:00 - 11:50',
                    'Period 5: 11:50 - 12:40',
                    'Lunch Break: 12:40 - 13:40 (Rooms and Faculty free)',
                    'Period 6: 13:40 - 14:30',
                    'Period 7: 14:30 - 15:20',
                    'Period 8: 15:20 - 16:05'
                ],
                'off_hours_rule': 'Before 08:15 AM and after 04:05 PM, as well as during official breaks, 0 classes run, and all classrooms, labs, and faculty are 100% available.'
            })

        # 13. Check CRT-FSD or Villas Sir
        if any(w in prompt_lower for w in ['crt', 'fsd', 'villas', 'outsourced']):
            villas = Faculty.objects.filter(full_name__icontains='villas').first()
            if villas:
                eval_v = AvailabilityService.evaluate_faculty_status(villas, target_date, start_t, end_t)
                retrieved_documents.append({
                    'type': 'CRT_FSD_OUTSOURCED_FACULTY',
                    'name': villas.full_name,
                    'designation': 'Outsourced Corporate Trainer',
                    'faculty_type': villas.faculty_type,
                    'subject': 'CRT-FSD (Campus Recruitment Training - Full Stack Development)',
                    'weekly_sessions': 21,
                    'status_at_slot': eval_v['status'],
                    'reason': eval_v['reason']
                })

        return {
            "query": query_text,
            "target_date": str(target_date),
            "target_slot": slot_label,
            "retrieved_documents": retrieved_documents
        }

    @classmethod
    def generate_rag_response(cls, user_prompt, api_key=None, conversation_id="default"):
        """
        Augmentation & Generation Step:
        Builds grounded context from retrieved database records and executes
        high-speed inference with Groq LLM (LLaMA / Qwen).
        """
        from django.conf import settings
        groq_api_key = api_key or os.environ.get("GROQ_API_KEY") or getattr(settings, 'GROQ_API_KEY', None)

        # Step 1: Retrieve ground-truth documents from database
        context_data = cls.retrieve_context(user_prompt)
        docs = context_data["retrieved_documents"]

        # Step 2: Fallback to intelligent deterministic engine if no Groq API key is available
        if not groq_api_key:
            from apps.assistant.services import AIAssistantService
            fallback_res = AIAssistantService.handle_query(user_prompt, conversation_id)
            fallback_res["rag_metadata"] = {
                "rag_mode": "DETERMINISTIC_FALLBACK (No Groq API Key provided)",
                "retrieved_documents_count": len(docs),
                "retrieved_context": docs
            }
            return fallback_res

        # Step 3: Format Context for Groq LLM
        context_str = json.dumps(docs, indent=2)

        system_instruction = (
            "You are the official Smart Campus AI Assistant for all academic departments and branches "
            "(CS, DS, CSBS, IoT, AIML, BS-DS, M.Sc-DS, and M.Tech) at Vignan's Foundation for Science, Technology and Research (VFSTR).\n\n"
            "STRICT GROUNDING RULES:\n"
            "1. Answer the user's question accurately using ONLY the provided RETRIEVED ACADEMIC CONTEXT.\n"
            "2. Never hallucinate, estimate, or invent timetable records, faculty assignments, or room occupancy.\n"
            "3. For classrooms and laboratories, use strictly 'Occupied' or 'Unoccupied'. Do not use Not Verified, Unknown, or Pending.\n"
            "4. If a room or faculty is Occupied, explicitly mention the Subject, Section cohort, Department, Room code, and exact Time slot.\n"
            "5. If a faculty member is verified AVAILABLE, confirm their availability for that specific period/time slot, and if schedule data is provided, mention their other classes for that day.\n"
            "6. Present your answer clearly in clean Markdown with bullet points where appropriate."
        )

        user_content = (
            f"User Question: {user_prompt}\n\n"
            f"Evaluated Target Date: {context_data['target_date']}\n"
            f"Evaluated Target Time Slot: {context_data['target_slot']}\n\n"
            f"=== RETRIEVED VERIFIED TIMETABLE CONTEXT (Source of Truth) ===\n"
            f"{context_str}\n"
            f"=== END CONTEXT ==="
        )

        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)

            model_to_use = getattr(settings, 'GROQ_MODEL', None) or os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ],
                model=model_to_use,
                temperature=0.1,
                max_tokens=700
            )

            llm_reply = chat_completion.choices[0].message.content

            return {
                "conversation_id": conversation_id,
                "reply": llm_reply,
                "tools_invoked": [
                    {
                        "tool_name": "groq_timetable_rag_retrieval",
                        "model": model_to_use,
                        "documents_retrieved": len(docs)
                    }
                ],
                "evidence": docs,
                "rag_metadata": {
                    "rag_mode": f"ACTIVE (Groq {model_to_use})",
                    "retrieved_documents_count": len(docs)
                }
            }

        except Exception as e:
            # Fall back seamlessly to intelligent timetable service if network or Groq fails
            from apps.assistant.services import AIAssistantService
            fallback_res = AIAssistantService.handle_query(user_prompt, conversation_id)
            fallback_res["rag_metadata"] = {
                "rag_mode": f"DETERMINISTIC_FALLBACK (Groq: {str(e)[:100]})",
                "retrieved_documents_count": len(docs),
                "retrieved_context": docs
            }
            return fallback_res
