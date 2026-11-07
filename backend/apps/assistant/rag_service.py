"""
Smart Campus - Retrieval-Augmented Generation (RAG) Service for AIML Timetable
Powered by Groq LLM (e.g. LLaMA-3.3-70B) & Structured Academic Database Retrieval.
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
from apps.availability.services import AvailabilityService
from apps.scheduling.services import SchedulingService

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

        # Parse Day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        matched_day_idx = None
        for idx, d_name in enumerate(day_names):
            if d_name in prompt_lower:
                days_ahead = (idx - today.weekday()) % 7
                target_date = today + datetime.timedelta(days=days_ahead)
                matched_day_idx = idx
                break

        # Parse Period or Time
        period_match = re.search(r'\bperiod\s*([1-8])\b', prompt_lower)
        start_t = datetime.time(10, 10)
        end_t = datetime.time(11, 0)
        if period_match:
            p_num = int(period_match.group(1))
            from apps.availability.services import PERIODS
            if p_num in PERIODS:
                start_t = PERIODS[p_num]['start']
                end_t = PERIODS[p_num]['end']
        elif re.search(r'\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\s*(am|pm)\b|\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b|\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower):
            time_match = re.search(r'\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\s*(am|pm)\b|\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b|\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower)
            try:
                hr = None
                mn = 0
                if time_match.group(1):
                    hr = int(time_match.group(1))
                    mn = int(time_match.group(2) or 0)
                    ampm = time_match.group(3)
                    if ampm == 'pm' and hr < 12:
                        hr += 12
                    elif ampm == 'am' and hr == 12:
                        hr = 0
                elif time_match.group(4):
                    hr = int(time_match.group(4))
                    mn = int(time_match.group(5) or 0)
                elif time_match.group(6):
                    hr = int(time_match.group(6))
                    if hr in [1, 2, 3, 4]:
                        hr += 12
                if hr is not None and 0 <= hr <= 23:
                    start_t = datetime.time(hr, mn)
                    end_min = hr * 60 + mn + 50
                    end_t = datetime.time(min(end_min // 60, 23), end_min % 60)
            except Exception:
                pass

        version = AvailabilityService.get_active_version()
        retrieved_documents = []

        # 1. Check Faculty Match
        fac_candidates = []
        for f in Faculty.objects.filter(is_active=True):
            f_tokens = [tok.lower() for tok in re.findall(r'[a-zA-Z]{3,}', f.full_name) if tok.lower() not in ["prof", "assistant", "associate", "dr.", "mr.", "ms."]]
            score = sum(1 for tok in f_tokens if tok in prompt_lower)
            if score > 0 or (f.faculty_code and f.faculty_code.lower() in prompt_lower):
                fac_candidates.append((score, f))

        fac_candidates.sort(key=lambda x: x[0], reverse=True)
        if fac_candidates:
            target_faculty = fac_candidates[0][1]
            eval_res = AvailabilityService.evaluate_faculty_status(target_faculty, target_date, start_t, end_t)
            
            # Fetch faculty weekly schedule
            faculty_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                faculty=target_faculty,
                is_active=True
            ).select_related('section', 'subject', 'resource').order_by('day_of_week', 'start_time')[:8]

            schedule_summary = []
            for fe in faculty_entries:
                schedule_summary.append(
                    f"Day {day_names[fe.day_of_week].capitalize()} {fe.start_time.strftime('%H:%M')}-{fe.end_time.strftime('%H:%M')}: {fe.subject.name} for {fe.section.full_name} in Room {fe.resource.code if fe.resource else 'Unassigned'}"
                )

            retrieved_documents.append({
                "type": "FACULTY_PROFILE_AND_SCHEDULE",
                "entity": target_faculty.full_name,
                "faculty_code": target_faculty.faculty_code,
                "evaluated_slot": f"{target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')}) {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                "status": eval_res["status"],
                "reason": eval_res["reason"],
                "evidence": eval_res.get("evidence"),
                "sample_weekly_classes": schedule_summary
            })

        # 2. Check Room / Lab Match
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
                    room_sched.append(
                        f"Day {day_names[re_entry.day_of_week].capitalize()} {re_entry.start_time.strftime('%H:%M')}-{re_entry.end_time.strftime('%H:%M')}: {re_entry.subject.name} ({re_entry.section.full_name})"
                    )

                retrieved_documents.append({
                    "type": "RESOURCE_OCCUPANCY",
                    "room_code": res_obj.code,
                    "name": res_obj.name,
                    "capacity": res_obj.capacity,
                    "is_shared": res_obj.is_shared,
                    "evaluated_slot": f"{target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')}) {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                    "status": eval_res["status"],
                    "reason": eval_res["reason"],
                    "evidence": eval_res.get("evidence"),
                    "weekly_occupancy": room_sched
                })

        # 3. Check Section Match (e.g. "II ACSE-A", "IV CS", "III DS-B", "II CSBS", "II IOT")
        sec_obj = None
        # Try ACSE section match
        sec_match = re.search(r'\b(ii|iii|iv)\s*acse-?([a-l])\b', prompt_lower)
        if sec_match:
            sec_full = f"{sec_match.group(1).upper()} ACSE-{sec_match.group(2).upper()}"
            sec_obj = AcademicSection.objects.filter(full_name=sec_full).first()
        # Try other branch matches: CS, DS, CSBS, IOT
        if not sec_obj:
            branch_match = re.search(r'\b(ii|iii|iv)\s*(cs|ds|csbs|iot|mtech)\b', prompt_lower)
            if branch_match:
                yr = branch_match.group(1).upper()
                br = branch_match.group(2).upper()
                sec_obj = AcademicSection.objects.filter(full_name__istartswith=f"{yr} {br}").first()
        # Try generic section name search
        if not sec_obj:
            for sec_candidate in AcademicSection.objects.all():
                if sec_candidate.full_name.lower().replace('-', ' ').replace('  ', ' ') in prompt_lower:
                    sec_obj = sec_candidate
                    break
        if sec_obj:
                s_entries = TimetableEntry.objects.filter(
                    timetable_version=version,
                    section=sec_obj,
                    is_active=True
                ).select_related('subject', 'faculty', 'resource').order_by('day_of_week', 'start_time')

                day_filter = matched_day_idx if matched_day_idx is not None else target_date.weekday()
                day_classes = [
                    f"{e.start_time.strftime('%H:%M')}-{e.end_time.strftime('%H:%M')}: {e.subject.name} | Faculty: {e.faculty.full_name if e.faculty else 'Department Faculty'} | Room: {e.resource.code if e.resource else 'Unassigned'}"
                    for e in s_entries.filter(day_of_week=day_filter)
                ]

                retrieved_documents.append({
                    "type": "SECTION_SCHEDULE",
                    "section": sec_obj.full_name,
                    "day": day_names[day_filter].capitalize(),
                    "classes": day_classes
                })

        # 4. Check General Classroom Recommendations
        is_lab = bool(re.search(r'\b(?:labs?|laborator(?:y|ies))\b', prompt_lower))
        is_room = bool(re.search(r'\b(?:classrooms?|rooms?)\b', prompt_lower)) or "free room" in prompt_lower or "available room" in prompt_lower
        if is_lab or is_room:
            res_type = 'LABORATORY' if is_lab else 'CLASSROOM'
            recs = SchedulingService.recommend_classrooms(target_date, start_t, end_t, min_capacity=30, resource_type=res_type)
            retrieved_documents.append({
                "type": "AVAILABLE_RESOURCES_LIST",
                "resource_type": res_type,
                "slot": f"{target_date.strftime('%Y-%m-%d')} {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                "available_rooms": recs[:8]
            })

        # 5. Check Free Faculty List
        if any(k in prompt_lower for k in ["who is free", "free faculty", "available faculty", "free teacher", "faculty free"]) or \
           (any(w in prompt_lower for w in ["faculty", "teacher", "prof", "who"]) and any(w in prompt_lower for w in ["free", "available", "vacant"])):
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
                "slot": f"{target_date.strftime('%Y-%m-%d')} {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                "department_filter": dept_filter or "ALL",
                "total_available": len(free_facs),
                "free_faculty_sample": free_facs[:15]
            })

        # 6. Check Schedule Exceptions & Substitutions
        if any(w in prompt_lower for w in ["exception", "cancellation", "cancel", "substitut", "leave", "swap", "reallocat"]):
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
                "exceptions": ex_data
            })

                # 7. Check Timetable Clashes & Conflicts
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

        # 8. Check Class Swaps
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
                    'reason': s.reason,
                    'details': (
                        f"Within class {s.entry_1.section.full_name}: {s.faculty_2.full_name} teaches {s.entry_2.subject.name} in {s.entry_1.subject.name} slot ({s.entry_1.start_time.strftime('%H:%M')}-{s.entry_1.end_time.strftime('%H:%M')}), and {s.faculty_1.full_name} teaches {s.entry_1.subject.name} in {s.entry_2.subject.name} slot ({s.entry_2.start_time.strftime('%H:%M')}-{s.entry_2.end_time.strftime('%H:%M')})"
                        if is_same_sec else
                        f"{s.faculty_1.full_name} ({s.entry_1.section.full_name}) exchanged with {s.faculty_2.full_name} ({s.entry_2.section.full_name})"
                    )
                })
            retrieved_documents.append({
                'type': 'CLASS_SWAPS',
                'target_date': str(target_date),
                'total_swaps': len(swap_list),
                'swaps': swap_list
            })

        # 9. Check College Timings & Breaks
        if any(w in prompt_lower for w in ['break', 'breaks', 'college hours', 'working hours', 'college start', 'college end', 'class timing', 'period timing', 'lunch timing']):
            retrieved_documents.append({
                'type': 'COLLEGE_HOURS_AND_BREAKS',
                'working_hours': '08:15 AM - 04:05 PM (Monday to Saturday)',
                'morning_break': '09:55 AM - 10:10 AM (15 minutes)',
                'lunch_break': '12:40 PM - 01:40 PM (60 minutes)',
                'periods': [
                    'Period 1: 08:15 - 09:05',
                    'Period 2: 09:05 - 09:55',
                    'Morning Break: 09:55 - 10:10',
                    'Period 3: 10:10 - 11:00',
                    'Period 4: 11:00 - 11:50',
                    'Period 5: 11:50 - 12:40',
                    'Lunch Break: 12:40 - 13:40',
                    'Period 6: 13:40 - 14:30',
                    'Period 7: 14:30 - 15:20',
                    'Period 8: 15:20 - 16:05'
                ],
                'off_hours_rule': 'Before 08:15 AM and after 04:05 PM, as well as during official breaks, 0 classes run, and all classrooms, labs, and faculty are 100% available.'
            })

        # 10. Check CRT-FSD or Villas Sir
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
            "target_slot": f"{start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
            "retrieved_documents": retrieved_documents
        }

    @classmethod
    def generate_rag_response(cls, user_prompt, api_key=None, conversation_id="default"):
        """
        Augmentation & Generation Step:
        Builds grounded context from retrieved database records and executes
        high-speed inference with Groq LLM (LLaMA-3.3-70B).
        """
        from django.conf import settings
        groq_api_key = api_key or os.environ.get("GROQ_API_KEY") or getattr(settings, 'GROQ_API_KEY', None)

        # Step 1: Retrieve ground-truth documents from database
        context_data = cls.retrieve_context(user_prompt)
        docs = context_data["retrieved_documents"]

        # Step 2: Fallback to deterministic engine if no Groq API key is available
        if not groq_api_key:
            from apps.assistant.services import AIAssistantService
            fallback_res = AIAssistantService.handle_query(user_prompt, conversation_id)
            fallback_res["rag_metadata"] = {
                "rag_mode": "DETERMINISTIC_FALLBACK (No Groq API Key provided)",
                "retrieved_documents_count": len(docs),
                "retrieved_context": docs
            }
            fallback_res["reply"] += "\n\n*(Note: Groq LLM RAG mode is ready. Provide your Groq API key to activate real-time LLaMA-3.3-70B generation.)*"
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
            "5. If multiple faculty members are assigned to a session, name all of them.\n"
            "6. Present your answer clearly in formatted Markdown with bullet points where appropriate."
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

            # Available active models on this Groq account
            model_to_use = getattr(settings, 'GROQ_MODEL', None) or os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ],
                model=model_to_use,
                temperature=0.1,
                max_tokens=600
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
            # Fall back seamlessly to deterministic timetable service if network or Groq fails
            from apps.assistant.services import AIAssistantService
            fallback_res = AIAssistantService.handle_query(user_prompt, conversation_id)
            fallback_res["rag_metadata"] = {
                "rag_mode": f"DETERMINISTIC_FALLBACK (Groq: {str(e)[:100]})",
                "retrieved_documents_count": len(docs),
                "retrieved_context": docs
            }
            return fallback_res
